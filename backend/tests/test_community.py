"""Test-only contract fixtures; never loaded into the application workspace."""
import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.community import SESSIONS,LOCK
client=TestClient(app)
@pytest.fixture(autouse=True)
def isolated():
    with LOCK:SESSIONS.clear()
    yield
    with LOCK:SESSIONS.clear()
def register(ready=False):
    return 'project_id,parcel_id,citizen_id,area_name,approval_status,acquisition_status,compensation_due_inr,compensation_paid_inr,status_date,source_reference\nP1,L1,C1,North,'+('approved' if ready else 'pending')+',pending,100,'+('100' if ready else '40')+',2025-01-01,test-only\nP1,L2,C2,North,approved,pending,200,200,2025-01-01,test-only\nP2,L3,C3,North,unknown,unknown,,,,\n'
def setup(ready=False,geo=None):
    r=client.post('/api/community/sessions',json={'csv_text':register(ready),'verified_register':True,'geojson':geo});assert r.status_code==200,r.text
    a=r.json();b='/api/community/'+a['session_id'];o={'X-Access-Code':a['access_code']}
    c={i['citizen_id']:{'X-Access-Code':i['access_code']} for i in client.get(b+'/invitations',headers=o).json()}
    return b,o,c
def issue(b,c,parcel='L1',category='compensation'):
    return client.post(b+'/reports',headers=c['C1'],json={'project_id':'P1','parcel_id':parcel,'category':category,'description':'Please review the recorded status.'})
def options():
    return {'project_id':'P1','acquire_now':{'schedule_days':10,'incremental_cost_inr':20,'disrupted_citizens':1},'wait':{'schedule_days':20,'incremental_cost_inr':10,'disrupted_citizens':0},'schedule_weight':1,'cost_weight':0,'citizen_weight':0,'schedule_scale_days':100,'cost_scale_inr':100,'basis':'user_assumptions','source_note':'Test-only milestone comparison','procedures_confirmed':True,'officer':'Test officer'}
def choice(ev,kind='wait_and_resolve'):
    return {'evaluation_id':ev['id'],'choice':kind,'reason':'Test review reasoning','officer':'Test officer'}
def test_roles_and_private_exports():
    b,o,c=setup()
    for cid in c:
        d=client.get(b,headers=c[cid]).json();assert d['role']=='citizen'
        assert all(p['citizen_id']==cid for p in d['parcels'])
        assert 'area_summary' not in d and 'decisions' not in d
        assert client.get(b+'/invitations',headers=c[cid]).status_code==403
        assert client.delete(b,headers=c[cid]).status_code==403
        assert client.post(b+'/evaluate-decision',headers=c[cid],json=options()).status_code==403
        exp=client.get(b+'/export',headers=c[cid]);assert 'access_code' not in exp.text and 'official_token' not in exp.text
    assert client.get(b).status_code==403
    assert client.get(b,headers={'X-Access-Code':'wrong'}).status_code==403
    assert client.get(b,headers=o).headers['cache-control']=='no-store'
def test_report_ownership_counts_and_response():
    b,o,c=setup();assert issue(b,c,'L2').status_code==403
    r=issue(b,c);assert r.status_code==200
    assert issue(b,c).status_code==409
    assert issue(b,c,category='approval').status_code==200
    d=client.get(b,headers=o).json();a=next(x for x in d['area_summary'] if x['project_id']=='P1')
    assert (a['report_count'],a['reporting_citizens'],a['registered_citizens'],a['reporting_share_pct'])==(2,1,2,50)
    assert next(x for x in d['area_summary'] if x['project_id']=='P2')['report_count']==0
    assert client.get(b,headers=c['C2']).json()['reports']==[]
    path=b+'/reports/'+r.json()['id']+'/response';body={'status':'resolved','message':'Status checked against the register','officer':'Test officer'}
    assert client.post(path,headers=c['C1'],json=body).status_code==403
    assert client.post(path,headers=o,json=body).status_code==200
    assert client.get(b,headers=c['C1']).json()['reports'][0]['responses'][0]['message']==body['message']
    assert client.get(b,headers=o).json()['area_summary'][0]['unresolved_reports']==1

def test_missing_compensation_stays_unknown():
    b,o,c=setup();d=client.get(b,headers=o).json()['impact']
    assert d['compensation_pending_inr'] is None and d['known_compensation_pending_subtotal_inr']==60
    assert d['compensation_unknown_parcels']==1
    assert client.get(b,headers=c['C3']).json()['parcels'][0]['compensation_pending_inr'] is None

def test_timing_formula_gates_audit_and_staleness():
    b,o,c=setup();r=client.post(b+'/evaluate-decision',headers=o,json=options());assert r.status_code==200,r.text
    d=r.json();assert d['acquire_now']['score']==90 and d['wait']['score']==80
    assert d['gates'] and d['inputs']['basis']=='user_assumptions'
    assert client.post(b+'/decisions',headers=o,json=choice(d,'acquire_now_review')).status_code==422
    assert client.post(b+'/decisions',headers=o,json=choice(d)).status_code==200
    audit=client.get(b+'/export',headers=o).json()['decisions'][0]['evaluation']
    assert len(audit['parcel_snapshot'])==2 and 'reported_impact' in audit
    issue(b,c);assert client.post(b+'/decisions',headers=o,json=choice(d)).status_code==422

def test_ready_comparison_and_invalid_estimates():
    b,o,c=setup(True);d=client.post(b+'/evaluate-decision',headers=o,json=options()).json();assert d['gates']==[]
    assert client.post(b+'/decisions',headers=o,json=choice(d,'acquire_now_review')).status_code==200
    for changes in [{'schedule_scale_days':5},{'schedule_weight':0},{'basis':'unverified_kind'}]:
        assert client.post(b+'/evaluate-decision',headers=o,json={**options(),**changes}).status_code==422
    p=options();p['acquire_now']['disrupted_citizens']=3
    assert client.post(b+'/evaluate-decision',headers=o,json=p).status_code==422

def test_sourced_status_update_and_stale_decision():
    b,o,c=setup();ev=client.post(b+'/evaluate-decision',headers=o,json=options()).json()
    u={'project_id':'P1','parcel_id':'L1','acquisition_status':'pending','approval_status':'approved','compensation_due_inr':100,'compensation_paid_inr':100,'status_date':'2025-02-01','source_reference':'test-source','officer':'Test officer','reason':'Test correction'}
    assert client.post(b+'/parcel-update',headers=c['C1'],json=u).status_code==403
    assert client.post(b+'/parcel-update',headers=o,json={**u,'compensation_paid_inr':101}).status_code==422
    assert client.post(b+'/parcel-update',headers=o,json=u).status_code==200
    assert client.post(b+'/parcel-update',headers=o,json={**u,'status_date':'2024-01-01'}).status_code==422
    d=client.get(b,headers=c['C1']).json();assert d['parcels'][0]['compensation_pending_inr']==0
    assert d['updates'][0]['before']['compensation_pending_inr']==60
    assert client.get(b,headers=c['C2']).json()['updates']==[]
    assert client.post(b+'/decisions',headers=o,json=choice(ev)).status_code==422

def test_geometry_validation_and_scope():
    g={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'project_id':'P1','stage':'planned','source_reference':'test-only'},'geometry':{'type':'LineString','coordinates':[[70,20],[71,21]]}}]}
    b,o,c=setup(geo=g)
    assert len(client.get(b,headers=c['C1']).json()['geometry']['features'])==1
    assert client.get(b,headers=c['C3']).json()['geometry']['features']==[]
    for bad in [None,[],{'type':'Feature','properties':[],'geometry':{}},{'type':'Feature','properties':{'project_id':'P1'},'geometry':{'type':'Point','coordinates':[999,20]}}]:
        r=client.post('/api/community/sessions',json={'csv_text':register(),'verified_register':True,'geojson':{'type':'FeatureCollection','features':[bad]}})
        assert r.status_code==422,r.text

def test_close_expiry_and_import_validation():
    for t in [register().replace('P1,L2,C2','P1,L1,C2'),register().replace('100,40','100,140'),register().replace('100,40','1e308,40')]:
        assert client.post('/api/community/sessions',json={'csv_text':t,'verified_register':True}).status_code==422
    assert client.post('/api/community/sessions',json={'csv_text':register()}).status_code==422
    b,o,c=setup();assert client.delete(b,headers=o).status_code==200
    assert client.get(b,headers=c['C1']).status_code==410
    b,o,c=setup()
    with LOCK:SESSIONS[b.split('/')[-1]]['expires']=time.time()-1
    assert client.get(b,headers=o).status_code==410
