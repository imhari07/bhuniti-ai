"""Role-scoped collaboration in expiring process memory. No disk or database writes."""
import copy,json,math,secrets,time,threading
from datetime import datetime,timezone
from fastapi import APIRouter,Header,HTTPException
from pydantic import BaseModel,ConfigDict,Field
from .analysis import parse,number

router=APIRouter(prefix='/api/community',tags=['Citizen and official portals'])
LOCK=threading.RLock(); SESSIONS={}; TTL=7200; MAX_SESSIONS=12
REQUIRED=['project_id','parcel_id','citizen_id','area_name']
OPTIONAL=['citizen_name','project_name','acquisition_status','approval_status','compensation_due_inr','compensation_paid_inr','land_area_ha','latitude','longitude','status_date','source_reference']

def now():return datetime.now(timezone.utc).isoformat()
def clean_sessions():
    for key in list(SESSIONS):
        if SESSIONS[key]['expires']<=time.time():del SESSIONS[key]

def janitor():
    while True:
        time.sleep(30)
        with LOCK:clean_sessions()
threading.Thread(target=janitor,daemon=True).start()

class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class Open(Strict):
    csv_text:str=Field(min_length=1,max_length=3_000_000)
    geojson:dict|None=None
    verified_register:bool=False
class Access(Strict):session_id:str
class Report(Strict):
    project_id:str
    parcel_id:str
    category:str=Field(pattern='^(compensation|approval|access|livelihood|records|other)$')
    description:str=Field(min_length=10,max_length=2000)
class Response(Strict):
    status:str=Field(pattern='^(received|under_review|resolved)$')
    message:str=Field(min_length=3,max_length=2000)
    officer:str=Field(min_length=2,max_length=100)
class Option(Strict):
    schedule_days:float=Field(ge=0,le=36500,allow_inf_nan=False)
    incremental_cost_inr:float=Field(ge=0,le=1e15,allow_inf_nan=False)
    disrupted_citizens:int=Field(ge=0,le=1000000)
class Decision(Strict):
    project_id:str
    acquire_now:Option
    wait:Option
    schedule_weight:float=Field(ge=0,le=1,allow_inf_nan=False)
    cost_weight:float=Field(ge=0,le=1,allow_inf_nan=False)
    citizen_weight:float=Field(ge=0,le=1,allow_inf_nan=False)
    schedule_scale_days:float=Field(gt=0,le=36500,allow_inf_nan=False)
    cost_scale_inr:float=Field(gt=0,le=1e15,allow_inf_nan=False)
    basis:str=Field(pattern='^(documented_estimates|user_assumptions)$')
    source_note:str=Field(min_length=5,max_length=2000)
    procedures_confirmed:bool=False
    officer:str=Field(min_length=2,max_length=100)
class RecordDecision(Strict):
    evaluation_id:str
    choice:str=Field(pattern='^(acquire_now_review|wait_and_resolve|request_more_evidence)$')
    reason:str=Field(min_length=5,max_length=2000)
    officer:str=Field(min_length=2,max_length=100)

def auth(sid,token,role=None):
    clean_sessions();s=SESSIONS.get(sid)
    if not s:raise HTTPException(410,'Session expired or closed. Ask the official to open a new session.')
    if not token.isascii() or len(token)>100:raise HTTPException(403,'Invalid access code.')
    if secrets.compare_digest(token,s['official_token']): identity={'role':'official'}
    else:
        cid=next((cid for cid,key in s['citizen_tokens'].items() if secrets.compare_digest(token,key)),None)
        if cid is None:raise HTTPException(403,'Invalid access code.')
        identity={'role':'citizen','citizen_id':cid}
    if role and identity['role']!=role:raise HTTPException(403,'This action requires an official session.')
    return s,identity

def validate_geo(geo,projects):
    if geo is None:return {'type':'FeatureCollection','features':[]}
    if len(json.dumps(geo))>1_000_000:raise ValueError('GeoJSON exceeds 1 MB.')
    if geo.get('type')!='FeatureCollection' or not isinstance(geo.get('features'),list) or len(geo['features'])>300:raise ValueError('Use a GeoJSON FeatureCollection with at most 300 features.')
    out=[];points=0
    for f in geo['features']:
        if not isinstance(f,dict) or f.get('type')!='Feature':raise ValueError('Each geometry must be a GeoJSON Feature.')
        props=f.get('properties');g=f.get('geometry')
        if not isinstance(props,dict) or not isinstance(g,dict):raise ValueError('Feature properties and geometry must be objects.')
        kind=g.get('type');coords=g.get('coordinates')
        if not isinstance(props.get('project_id'),str) or props.get('project_id') not in projects:raise ValueError('Every geometry needs properties.project_id matching a parcel-register project.')
        if kind not in ['Point','LineString','MultiLineString','Polygon','MultiPolygon']:raise ValueError('Only points, lines and polygons are supported.')
        def position(p):
            nonlocal points
            if not isinstance(p,list) or len(p)!=2 or any(type(v) not in [int,float] or not math.isfinite(v) for v in p) or not -180<=p[0]<=180 or not -90<=p[1]<=90:raise ValueError('GeoJSON positions must be finite [longitude, latitude] pairs.')
            points+=1
            if points>30000:raise ValueError('Geometry exceeds 30,000 positions.')
        def line(p):
            if not isinstance(p,list) or len(p)<2:raise ValueError('Lines require two or more positions.')
            for a in p:position(a)
        def polygon(p):
            if not isinstance(p,list) or not p:raise ValueError('Polygon rings required.')
            for ring in p:
                line(ring)
                if len(ring)<4 or ring[0]!=ring[-1]:raise ValueError('Polygon rings require at least four positions and must close.')
        if kind=='Point':position(coords)
        elif kind=='LineString':line(coords)
        elif kind=='Polygon':polygon(coords)
        elif kind=='MultiLineString':
            if not isinstance(coords,list) or not coords:raise ValueError('Lines required.')
            for c in coords:line(c)
        else:
            if not isinstance(coords,list) or not coords:raise ValueError('Polygons required.')
            for c in coords:polygon(c)
        if props.get('stage') not in ['planned','under_acquisition','acquired','unknown']:raise ValueError('Geometry stage must be planned, under_acquisition, acquired or unknown.')
        if not isinstance(props.get('source_reference'),str) or not props['source_reference'].strip():raise ValueError('Each geometry requires a source_reference.')
        out.append({'type':'Feature','geometry':{'type':kind,'coordinates':coords},'properties':{k:str(props.get(k,''))[:1000] for k in ['project_id','area_name','stage','source_reference']}})
    return {'type':'FeatureCollection','features':out}

def parse_register(text):
    headers,raw=parse(text)
    if set(REQUIRED)-set(headers):raise ValueError('Parcel CSV requires project_id, parcel_id, citizen_id and area_name.')
    if len(raw)>3000:raise ValueError('Maximum 3,000 parcel records per session.')
    seen=set();parcels=[]
    for i,r in enumerate(raw):
        v={k:r.get(k,'').strip() for k in REQUIRED+OPTIONAL}
        if any(not v[k] for k in REQUIRED):raise ValueError(f'Row {i+1}: all required identifiers and area are needed.')
        if any(len(v[k])>1000 or any(ord(c)<32 for c in v[k]) for k in v):raise ValueError('Register text must be at most 1,000 characters per field without control characters.')
        pair=(v['project_id'],v['parcel_id'])
        if pair in seen:raise ValueError('Use one row per project/parcel with a single authorized citizen account. Resolve co-ownership before import; do not duplicate amounts.')
        seen.add(pair)
        for k in ['compensation_due_inr','compensation_paid_inr','land_area_ha']:
            if v[k] and number(v[k]) is None:raise ValueError(f'Row {i+1}: {k} must be finite and nonnegative.')
            v[k]=number(v[k])
            if v[k] is not None and v[k]>1e15:raise ValueError('Numeric register values must not exceed 1e15.')
        if v['compensation_due_inr'] is not None and v['compensation_paid_inr'] is not None and v['compensation_paid_inr']>v['compensation_due_inr']:raise ValueError('Paid amount exceeds total compensation due. Reconcile before upload.')
        if bool(v['latitude'])!=bool(v['longitude']):raise ValueError('Supply latitude and longitude together or leave both blank.')
        for k,limit in [('latitude',90),('longitude',180)]:
            if v[k]:
                try:n=float(v[k])
                except ValueError:raise ValueError('Invalid coordinate.')
                if not math.isfinite(n) or abs(n)>limit:raise ValueError('Coordinate outside geographic bounds.')
                v[k]=n
            else:v[k]=None
        for k,allowed in [('acquisition_status',['acquired','pending','partial','unknown']),('approval_status',['approved','pending','rejected','unknown'])]:
            v[k]=v[k] or 'unknown'
            if v[k] not in allowed:raise ValueError(f'{k} must be one of: '+', '.join(allowed))
        if v['status_date']:
            try:d=datetime.strptime(v['status_date'],'%Y-%m-%d').date()
            except ValueError:raise ValueError('status_date must use YYYY-MM-DD.')
            if d>datetime.now(timezone.utc).date():raise ValueError('Observed status date cannot be in the future.')
        due,paid=v['compensation_due_inr'],v['compensation_paid_inr']
        v['compensation_pending_inr']=None if due is None or paid is None else due-paid
        parcels.append(v)
    return parcels

def report_summary(s,parcels):
    areas=[]
    for project,area in sorted(set((p['project_id'],p['area_name']) for p in parcels)):
        ps=[p for p in parcels if p['area_name']==area and p['project_id']==project];keys={(p['project_id'],p['parcel_id']) for p in ps}
        rs=[r for r in s['reports'] if (r['project_id'],r['parcel_id']) in keys];active=[r for r in rs if r['status']!='resolved']
        people={p['citizen_id'] for p in ps};affected={r['citizen_id'] for r in active}
        areas.append({'project_id':project,'area':area,'report_count':len(rs),'unresolved_reports':len(active),'reporting_citizens':len(affected),'registered_citizens':len(people),'reporting_share_pct':100*len(affected)/len(people),'categories':{k:sum(r['category']==k for r in active) for k in ['compensation','approval','access','livelihood','records','other']}})
    return sorted(areas,key=lambda a:(-a['reporting_citizens'],-a['unresolved_reports'],a['area']))

def view(s,who):
    ps=s['parcels'] if who['role']=='official' else [p for p in s['parcels'] if p['citizen_id']==who['citizen_id']]
    projects={p['project_id'] for p in ps};reports=s['reports'] if who['role']=='official' else [r for r in s['reports'] if r['citizen_id']==who['citizen_id']]
    geo={'type':'FeatureCollection','features':[f for f in s['geojson']['features'] if f['properties']['project_id'] in projects]}
    result={'role':who['role'],'expires_at':datetime.fromtimestamp(s['expires'],timezone.utc).isoformat(),'parcels':ps,'reports':reports,'updates':[u for u in s['updates'] if who['role']=='official' or u['citizen_id']==who['citizen_id']],'geometry':geo,'projects':sorted(projects),'note':'Expiring local session. Statuses are uploaded records; issue reports are citizen statements, not independently established facts.'}
    if who['role']=='official':
        result.update({'area_summary':report_summary(s,ps),'decisions':s['decisions'],'impact':{'registered_citizens':len(set(p['citizen_id'] for p in ps)),'parcels':len(ps),'pending_approval_parcels':sum(p['approval_status']=='pending' for p in ps),'unknown_approval_parcels':sum(p['approval_status']=='unknown' for p in ps),'compensation_pending_inr':sum(p['compensation_pending_inr'] for p in ps) if all(p['compensation_pending_inr'] is not None for p in ps) else None,'known_compensation_pending_subtotal_inr':sum(p['compensation_pending_inr'] or 0 for p in ps),'compensation_unknown_parcels':sum(p['compensation_pending_inr'] is None for p in ps),'citizens_with_recorded_pending_compensation':len(set(p['citizen_id'] for p in ps if (p['compensation_pending_inr'] or 0)>0))}})
    return copy.deepcopy(result)

@router.post('/sessions')
def create(req:Open):
    if not req.verified_register:raise ValueError('Confirm that this parcel register is authorized and its project/parcel/citizen associations are verified.')
    ps=parse_register(req.csv_text);geo=validate_geo(req.geojson,{p['project_id'] for p in ps})
    with LOCK:
        clean_sessions()
        if len(SESSIONS)>=MAX_SESSIONS:raise HTTPException(429,'Session capacity reached. Close an existing session or wait for expiry.')
        sid=secrets.token_urlsafe(18);token=secrets.token_urlsafe(32)
        SESSIONS[sid]={'official_token':token,'citizen_tokens':{cid:secrets.token_urlsafe(32) for cid in {p['citizen_id'] for p in ps}},'parcels':ps,'geojson':geo,'reports':[],'decisions':[],'evaluations':{},'updates':[],'revision':0,'expires':time.time()+TTL}
        return {'session_id':sid,'access_code':token,'expires_in_seconds':TTL}
@router.get('/{sid}')
def get(sid:str,x_access_code:str=Header(default='')):
    with LOCK:s,who=auth(sid,x_access_code);return view(s,who)
@router.get('/{sid}/invitations')
def invitations(sid:str,x_access_code:str=Header(default='')):
    with LOCK:
        s,who=auth(sid,x_access_code,'official')
        return [{'citizen_id':cid,'access_code':key} for cid,key in sorted(s['citizen_tokens'].items())]
@router.post('/{sid}/reports')
def report(sid:str,req:Report,x_access_code:str=Header(default='')):
    with LOCK:
        s,who=auth(sid,x_access_code,'citizen')
        parcel=next((p for p in s['parcels'] if p['project_id']==req.project_id and p['parcel_id']==req.parcel_id and p['citizen_id']==who['citizen_id']),None)
        if not parcel:raise HTTPException(403,'You can report only on your linked parcel.')
        if len(req.description.strip())<10:raise ValueError('Describe the issue in at least 10 nonblank characters.')
        own=[r for r in s['reports'] if r['citizen_id']==who['citizen_id']]
        if len(s['reports'])>=1000 or len(own)>=30:raise HTTPException(429,'Session report limit reached.')
        if any(r['project_id']==req.project_id and r['parcel_id']==req.parcel_id and r['category']==req.category and r['status']!='resolved' for r in own):raise HTTPException(409,'An open report in this category already exists for this parcel.')
        r={**req.model_dump(),'id':secrets.token_urlsafe(9),'citizen_id':who['citizen_id'],'area_name':parcel['area_name'],'created_at':now(),'status':'received','responses':[]}
        s['reports'].append(r);s['revision']+=1;return copy.deepcopy(r)
@router.post('/{sid}/reports/{rid}/response')
def respond(sid:str,rid:str,req:Response,x_access_code:str=Header(default='')):
    with LOCK:
        s,who=auth(sid,x_access_code,'official');r=next((r for r in s['reports'] if r['id']==rid),None)
        if r is None:raise HTTPException(404,'Report not found.')
        if len(req.message.strip())<3 or len(req.officer.strip())<2:raise ValueError('Officer and response must be nonblank.')
        if len(r['responses'])>=50:raise HTTPException(429,'Response limit reached.')
        r['status']=req.status;r['responses'].append({**req.model_dump(),'timestamp':now()});s['revision']+=1;return copy.deepcopy(r)
@router.post('/{sid}/evaluate-decision')
def decide(sid:str,req:Decision,x_access_code:str=Header(default='')):
    with LOCK:
        s,who=auth(sid,x_access_code,'official');ps=[p for p in s['parcels'] if p['project_id']==req.project_id]
        if not ps:raise ValueError('Choose a project in the register.')
        people=len(set(p['citizen_id'] for p in ps))
        if max(req.acquire_now.disrupted_citizens,req.wait.disrupted_citizens)>people:raise ValueError('Disrupted citizens cannot exceed the registered citizens for this project.')
        if len(req.source_note.strip())<5 or len(req.officer.strip())<2:raise ValueError('Provide officer and estimate/source rationale.')
        weights=[req.schedule_weight,req.cost_weight,req.citizen_weight];total=sum(weights)
        if total<=0:raise ValueError('At least one objective weight must be positive.')
        weights=[w/total for w in weights];gates=[]
        if any(p['acquisition_status']=='unknown' for p in ps):gates.append('Some acquisition statuses are unknown.')
        if any(p['approval_status']!='approved' for p in ps):gates.append('Some approvals are pending, rejected or unknown.')
        if any(p['compensation_pending_inr'] is None for p in ps):gates.append('Compensation totals are incomplete.')
        if any((p['compensation_pending_inr'] or 0)>0 for p in ps):gates.append('Recorded compensation remains outstanding.')
        if any(not p['status_date'] or not p['source_reference'] for p in ps):gates.append('Some parcel statuses lack an observation date or source reference.')
        if not req.procedures_confirmed:gates.append('Responsible officer has not confirmed procedural readiness.')
        if all(p['acquisition_status']=='acquired' for p in ps):gates.append('All registered parcels are already acquired; timing comparison is not applicable.')
        if req.acquire_now.schedule_days>req.schedule_scale_days or req.wait.schedule_days>req.schedule_scale_days or req.acquire_now.incremental_cost_inr>req.cost_scale_inr or req.wait.incremental_cost_inr>req.cost_scale_inr:raise ValueError('Scales must cover both option estimates; increase the declared comparison scales.')
        def utility(o):
            terms=[100*(1-o.schedule_days/req.schedule_scale_days),100*(1-o.incremental_cost_inr/req.cost_scale_inr),100*(1-o.disrupted_citizens/people)]
            return {'score':sum(a*b for a,b in zip(terms,weights)),'components':dict(zip(['schedule','cost','citizen'],terms))}
        a,b=utility(req.acquire_now),utility(req.wait);margin=a['score']-b['score']
        result={'id':secrets.token_urlsafe(9),'timestamp':now(),'inputs':req.model_dump(),'normalized_weights':dict(zip(['schedule','cost','citizen'],weights)),'acquire_now':a,'wait':b,'gates':gates,'recommendation':'Resolve readiness gaps before acquisition review' if gates else 'Options tied: officer review required' if abs(margin)<1e-8 else 'Acquire-now option has higher estimated utility' if margin>0 else 'Wait option has higher estimated utility','margin':margin,'registered_citizens':people,'revision':s['revision'],'parcel_snapshot':copy.deepcopy(ps),'reported_impact':report_summary(s,ps),'note':'Weighted preference analysis of supplied estimates, not an XGBoost prediction or causal guarantee. Procedural checks are conservative review gates, not legal authorization. Status dates must be reviewed for freshness by the officer.'}
        if len(s['evaluations'])>=100:raise HTTPException(429,'Evaluation limit reached.')
        s['evaluations'][result['id']]=result;return copy.deepcopy(result)
@router.post('/{sid}/decisions')
def record_decision(sid:str,req:RecordDecision,x_access_code:str=Header(default='')):
    with LOCK:
        s,who=auth(sid,x_access_code,'official');ev=s['evaluations'].get(req.evaluation_id)
        if not ev:raise ValueError('Evaluate the options before recording a decision.')
        if ev['revision']!=s['revision']:raise ValueError('The parcel register or reports changed. Re-evaluate before recording your decision.')
        if req.choice=='acquire_now_review' and ev['gates']:raise ValueError('Resolve the recorded readiness gates before selecting acquisition review.')
        if len(req.reason.strip())<5 or len(req.officer.strip())<2:raise ValueError('Officer and reason are required.')
        if len(s['decisions'])>=100:raise HTTPException(429,'Decision limit reached.')
        entry={**req.model_dump(),'timestamp':now(),'evaluation':copy.deepcopy(ev)};s['decisions'].append(entry);return copy.deepcopy(entry)
@router.get('/{sid}/export')
def export(sid:str,x_access_code:str=Header(default='')):
    with LOCK:
        s,who=auth(sid,x_access_code)
        return view(s,who)
@router.delete('/{sid}')
def close(sid:str,x_access_code:str=Header(default='')):
    with LOCK:auth(sid,x_access_code,'official');del SESSIONS[sid];return {'closed':True}


class ParcelUpdate(Strict):
    project_id:str
    parcel_id:str
    acquisition_status:str=Field(pattern='^(acquired|pending|partial|unknown)$')
    approval_status:str=Field(pattern='^(approved|pending|rejected|unknown)$')
    compensation_due_inr:float|None=Field(default=None,ge=0,le=1e15,allow_inf_nan=False)
    compensation_paid_inr:float|None=Field(default=None,ge=0,le=1e15,allow_inf_nan=False)
    status_date:str
    source_reference:str=Field(min_length=3,max_length=1000)
    officer:str=Field(min_length=2,max_length=100)
    reason:str=Field(min_length=5,max_length=2000)

@router.post('/{sid}/parcel-update')
def update_parcel(sid:str,req:ParcelUpdate,x_access_code:str=Header(default='')):
    with LOCK:
        s,who=auth(sid,x_access_code,'official')
        p=next((p for p in s['parcels'] if p['project_id']==req.project_id and p['parcel_id']==req.parcel_id),None)
        if not p:raise HTTPException(404,'Parcel not found.')
        if len(req.officer.strip())<2 or len(req.reason.strip())<5 or len(req.source_reference.strip())<3:raise ValueError('Officer, source and reason must be nonblank.')
        try:d=datetime.strptime(req.status_date,'%Y-%m-%d').date()
        except ValueError:raise ValueError('Use YYYY-MM-DD for status date.')
        if d>datetime.now(timezone.utc).date():raise ValueError('An observed status date cannot be in the future.')
        if p['status_date'] and req.status_date<p['status_date']:raise ValueError('The new status date cannot precede the currently recorded status date.')
        due,paid=req.compensation_due_inr,req.compensation_paid_inr
        if due is not None and paid is not None and paid>due:raise ValueError('Paid compensation exceeds total compensation due.')
        if len(s['updates'])>=500:raise HTTPException(429,'Status update limit reached.')
        before=copy.deepcopy(p)
        for k in ['acquisition_status','approval_status','compensation_due_inr','compensation_paid_inr','status_date','source_reference']:p[k]=getattr(req,k)
        p['compensation_pending_inr']=None if due is None or paid is None else due-paid
        s['updates'].append({'project_id':p['project_id'],'parcel_id':p['parcel_id'],'citizen_id':p['citizen_id'],'before':before,'after':copy.deepcopy(p),'officer':req.officer,'reason':req.reason,'timestamp':now()})
        s['revision']+=1
        return copy.deepcopy(p)
