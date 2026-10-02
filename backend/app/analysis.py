"""Pure request-scoped analysis; no record persistence or inference of missing operands."""
import csv
import io
import math
from collections import Counter
from datetime import datetime
import pandas as pd
from .schemas import FIELDS

DATE_KEYS=['sanction_date','date_3a','date_3A','date_3D','observation_date','source_date','planned_completion','actual_completion']
DATE_FORMATS={'ISO':'%Y-%m-%d','DMY':'%d/%m/%Y','MDY':'%m/%d/%Y'}
FACTORS={'hectares':1,'acres':0.40468564224,'square_metres':.0001}
MONEY={'INR':1,'INR_lakh':100000,'INR_crore':10000000}

def parse(raw):
    reader=csv.reader(io.StringIO(raw.lstrip('\ufeff')),strict=True)
    try:
        headers=next(reader,[])
        if not headers or any(not h.strip() for h in headers) or len(set(headers))!=len(headers):
            raise ValueError('Use nonempty, unique column headers.')
        if len(headers)>100: raise ValueError('Maximum 100 columns.')
        rows=[]
        for row in reader:
            if not row or all(not v.strip() for v in row): continue
            if len(row)!=len(headers): raise ValueError(f'Record {len(rows)+1} has a different number of columns.')
            if any(len(v)>20000 for v in row): raise ValueError('A cell exceeds 20,000 characters.')
            rows.append(row)
            if len(rows)>10000: raise ValueError('Maximum 10,000 records.')
        if not rows: raise ValueError('The file contains no records.')
    except csv.Error as exc: raise ValueError('Malformed CSV quoting.') from exc
    # Construct a string-only frame after structural validation; preserve blanks and literal NA.
    frame=pd.DataFrame(rows,columns=headers,dtype=str)
    return headers,frame.to_dict(orient='records')

def number(value):
    try:
        n=float(value)
        return n if math.isfinite(n) and n>=0 else None
    except (ValueError,TypeError): return None

def date_list(value,fmt):
    if not value.strip(): return None
    try: return [datetime.strptime(v.strip(),DATE_FORMATS[fmt]).date() for v in value.split(';')]
    except ValueError: return None

def mapped(row,settings): return {k:row.get(col,'').strip() for k,col in settings.mapping.items()}

def validate_settings(headers,s):
    if not s.mapping or set(s.mapping)-set(FIELDS): raise ValueError('Map at least one supported field.')
    if any(v not in headers for v in s.mapping.values()): raise ValueError('A mapped column is missing from this file.')
    if len(set(s.mapping.values()))!=len(s.mapping): raise ValueError('Each source column can map to only one field.')

def row_analysis(raw,s,index,duplicate=False):
    v=mapped(raw,s); flags=[]; actions=[]; calculations=[]
    def flag(text,action):
        flags.append(text)
        if action not in actions: actions.append(action)
    n={k:number(v.get(k,'')) for k in ['land_required','land_acquired','sanction_amount']}
    for k in n:
        if v.get(k) and n[k] is None: flag(f'Invalid nonnegative number: {FIELDS[k]}','Verify invalid numeric entries against source records.')
    d={k:date_list(v.get(k,''),s.date_format) for k in DATE_KEYS}
    for k in DATE_KEYS:
        if v.get(k) and d[k] is None: flag(f'Unreadable date: {FIELDS[k]}','Confirm the selected date format and source date values.')
        if d[k] and k not in ['date_3a','date_3A','date_3D'] and len(d[k])!=1:
            d[k]=None; flag(f'Expected one date: {FIELDS[k]}','Use one date for each snapshot, source, sanction or completion field.')
    required=['project_id','land_required','land_acquired','observation_date','source_date']
    if s.project_type=='highway': required+=['date_3a','date_3A','date_3D']
    missing=[FIELDS[k] for k in required if not v.get(k)]
    if missing: flag('Missing evidence: '+', '.join(missing),'Obtain missing evidence; absence in this file does not establish an incomplete stage.')
    if duplicate: flag('Possible duplicate project identifier or identical record','Resolve duplicates before portfolio aggregation or modeling.')
    req,acq=n['land_required'],n['land_acquired']
    valid=req is not None and acq is not None and req>0 and acq<=req
    if req==0: flag('Required land is zero; ratios suppressed','Verify required land and its unit before calculating ratios.')
    if req is not None and acq is not None and acq>req: flag('Acquired land exceeds required land; land indicators suppressed','Reconcile required and acquired land scope with the source.')
    indicators={'acquisition_progress_pct':100*acq/req if valid else None,
                'remaining_land':req-acq if valid else None,
                'remaining_land_pct':100*(req-acq)/req if valid else None,
                'sanction_inr_per_required_hectare':None}
    if valid:
        calculations.extend([
            {'name':'Acquisition progress (%)','formula':'acquired / required × 100','operands':f'{acq} / {req} × 100','value':indicators['acquisition_progress_pct']},
            {'name':f'Remaining land ({s.area_unit})','formula':'required − acquired','operands':f'{req} − {acq}','value':req-acq},
            {'name':'Remaining land (%)','formula':'(required − acquired) / required × 100','operands':f'({req} − {acq}) / {req} × 100','value':indicators['remaining_land_pct']}])
    if req is not None and req>0 and n['sanction_amount'] is not None:
        val=n['sanction_amount']*MONEY[s.amount_unit]/(req*FACTORS[s.area_unit])
        indicators['sanction_inr_per_required_hectare']=val
        calculations.append({'name':'Sanction INR per required hectare','formula':'amount × currency multiplier / (required × hectare conversion)','operands':f"{n['sanction_amount']} × {MONEY[s.amount_unit]} / ({req} × {FACTORS[s.area_unit]})",'value':val})
    stages=['sanction_date']+(['date_3a','date_3A','date_3D'] if s.project_type=='highway' else [])
    gaps=[]
    for left,right in zip(stages,stages[1:]):
        if d[left] and d[right]:
            gap=(min(d[right])-max(d[left])).days
            gaps.append({'from':FIELDS[left],'to':FIELDS[right],'days':gap,'formula':'earliest later-stage date − latest earlier-stage date','operands':f'{min(d[right]).isoformat()} − {max(d[left]).isoformat()}'})
            if gap<0: flag(f'Unusual recorded order: {FIELDS[right]} precedes {FIELDS[left]}','Verify timeline context; recorded order alone does not prove an error or legal violation.')
    if d['source_date'] and d['observation_date'] and d['source_date'][0]>d['observation_date'][0]:
        flag('Source date is after observation date','Confirm source availability at the observation date before any historical modeling.')
    for k in stages:
        if d[k] and d['observation_date'] and max(d[k])>d['observation_date'][0]:
            flag(f'{FIELDS[k]} occurs after observation date','Separate later information from the historical input snapshot.')
    if valid and req-acq>0: actions.append('Review the reported remaining land and confirm the next documented milestone with the responsible officer.')
    if not actions: actions.append('Review the source evidence and confirm the reported project status with the responsible officer.')
    for x in [*indicators.values(),*[c['value'] for c in calculations]]:
        if x is not None and not math.isfinite(x): raise ValueError('Values exceed the supported calculation range.')
    return {'index':index,'name':v.get('project_name') or v.get('project_id') or f'Uploaded row {index+1}',
            'original':raw,'mapped':v,'indicators':indicators,'calculations':calculations,'flags':flags,'actions':actions,
            'timeline':[{'stage':FIELDS[k],'dates':[x.isoformat() for x in d[k]] if d[k] else None} for k in stages],
            'gaps':gaps,'source_reference':v.get('source_reference',''),'missing_cells':sum(not x.strip() for x in raw.values()),
            'can_what_if':valid,'has_dates':any(d[k] for k in stages),'has_source_date':bool(d['source_date'])}

def analyze(raw,s):
    headers,rows=parse(raw);validate_settings(headers,s)
    ids=Counter(mapped(r,s).get('project_id','') for r in rows)
    signatures=Counter(tuple(r.values()) for r in rows)
    results=[row_analysis(r,s,i,(bool(mapped(r,s).get('project_id')) and ids[mapped(r,s)['project_id']]>1) or signatures[tuple(r.values())]>1) for i,r in enumerate(rows)]
    duplicates=any(any('duplicate' in flag for flag in r['flags']) for r in results)
    all_valid=all(r['can_what_if'] for r in results)
    can_total=s.comparable_scope and s.distinct_projects and not duplicates and all_valid
    totals=None
    if can_total:
        req=sum(number(r['mapped']['land_required']) for r in results)
        acq=sum(number(r['mapped']['land_acquired']) for r in results)
        totals={'required':req,'acquired':acq,'remaining':req-acq,'progress_pct':100*acq/req,'area_unit':s.area_unit}
        if any(isinstance(v,float) and not math.isfinite(v) for v in totals.values()): raise ValueError('Portfolio totals exceed the calculation range.')
    evidence={FIELDS[k]:sum(bool(mapped(r,s).get(k,'')) for r in rows) for k in ['project_id','land_required','land_acquired','observation_date','source_date','planned_completion','actual_completion']}
    review_queue=[{'row_index':r['index'],'project':r['name'],'review_flags':len(r['flags']),'first_action':r['actions'][0]} for r in sorted(results,key=lambda r:(-len(r['flags']),r['index']))]
    return {'evidence_coverage':evidence,'review_queue':review_queue,'headers':headers,'rows':results,'summary':{'record_count':len(rows),'flagged_records':sum(bool(r['flags']) for r in results),'valid_land_records':sum(r['can_what_if'] for r in results),'records_with_timeline_dates':sum(r['has_dates'] for r in results),'records_with_source_date':sum(r['has_source_date'] for r in results),'totals':totals,'aggregation_note':'Totals require valid land pairs in every row, confirmed compatible units/scopes and distinct projects, and no detected duplicates.'},'eligibility':{'prediction_enabled':False,'reason':'Descriptive analysis is available. Predictive evaluation requires explicit verification, sufficient historical records, and a successful temporal holdout check.'}}
