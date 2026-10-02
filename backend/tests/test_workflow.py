import csv,io
from datetime import date,timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import Settings
from app.analysis import analyze
client=TestClient(app)

def payload():
    return {'csv_text':'ID,Name,Required,Acquired,Sanction,Start,Lower,Upper,Final,Observed,Source\nA,Record A,200,50,400000,2020-01-01,2020-02-01,2020-03-01,,2021-01-01,2020-12-01\n',
      'settings':{'mapping':{'project_id':'ID','project_name':'Name','land_required':'Required','land_acquired':'Acquired','sanction_amount':'Sanction','sanction_date':'Start','date_3a':'Lower','date_3A':'Upper','date_3D':'Final','observation_date':'Observed','source_date':'Source'},'area_unit':'hectares','amount_unit':'INR','date_format':'ISO','project_type':'highway','comparable_scope':True,'distinct_projects':True}}

def test_empty_app_and_structure():
    assert client.get('/api/health').json()['storage'].startswith('analysis: request memory')
    for text in ['','A,A\n1,2','A,B\n1','A,B\n']:
        assert client.post('/api/inspect',json={'csv_text':text}).status_code==422
    assert client.get('/api/projects').status_code==404

def test_calculations_and_timeline():
    r=client.post('/api/analyze',json=payload());assert r.status_code==200
    data=r.json(); row=data['rows'][0]
    assert row['indicators']['acquisition_progress_pct']==25
    assert row['indicators']['remaining_land']==150
    assert row['indicators']['sanction_inr_per_required_hectare']==2000
    assert row['gaps'][1]['days']==29
    assert row['timeline'][-1]['dates'] is None
    assert data['summary']['totals']['progress_pct']==25
    assert data['eligibility']['prediction_enabled'] is False
    assert r.headers['cache-control']=='no-store'

def test_invalid_missing_and_duplicate_suppression():
    p=payload();p['csv_text']=p['csv_text'].replace(',200,50,',',200,300,');r=client.post('/api/analyze',json=p).json()
    assert r['rows'][0]['indicators']['remaining_land'] is None
    p=payload();p['csv_text']+=p['csv_text'].splitlines()[1]+'\n'
    r=client.post('/api/analyze',json=p).json();assert r['summary']['totals'] is None
    p=payload();p['csv_text']=p['csv_text'].replace(',200,50,',',0,NaN,')
    assert client.post('/api/analyze',json=p).json()['rows'][0]['indicators']['acquisition_progress_pct'] is None

def test_scope_units_and_date_format():
    p=payload();p['settings']['project_type']='other'
    r=client.post('/api/analyze',json=p).json();assert len(r['rows'][0]['timeline'])==1
    p['settings']['comparable_scope']=False
    assert client.post('/api/analyze',json=p).json()['summary']['totals'] is None
    p['settings']['mapping']['land_acquired']='Required'
    assert client.post('/api/analyze',json=p).status_code==422
    p=payload();p['settings']['date_format']='DMY'
    assert any('Unreadable' in f for f in client.post('/api/analyze',json=p).json()['rows'][0]['flags'])

def test_whatif_does_not_mutate():
    p=payload();before=client.post('/api/analyze',json=p).json()
    result=client.post('/api/what-if',json={**p,'row_index':0,'acquired':100}).json()
    assert result['baseline']['acquisition_progress_pct']==25
    assert result['changed']['acquisition_progress_pct']==50
    assert client.post('/api/analyze',json=p).json()==before
    assert client.post('/api/what-if',json={**p,'row_index':0,'acquired':250}).status_code==422

def test_export_inclusion_and_safe_cells():
    p=payload();p['csv_text']=p['csv_text'].replace('Record A','=2+2')
    response=client.post('/api/export',json={**p,'notes':{'0':'Officer note'},'include_notes':False})
    rows=list(csv.reader(io.StringIO(response.text.lstrip('\ufeff'))))
    assert rows[1][1]=="'=2+2";assert 'Officer note' not in response.text
    assert 'Officer note' in client.post('/api/export',json={**p,'notes':{'0':'Officer note'},'include_notes':True}).text

def test_model_gate_rejects_unverified_and_small():
    assert client.post('/api/evaluate',json=payload()).status_code==422
    p={**payload(),'verified_outcomes':True,'verified_snapshot_inputs':True,'verified_plan_at_snapshot':True,'verification_note':'Checked source'}
    assert client.post('/api/evaluate',json=p).status_code==422

def historical_contract():
    stream=io.StringIO();w=csv.writer(stream)
    w.writerow(['id','required','acquired','obs','source','planned','actual','reference'])
    # Test-only boundary fixture: distinct cohorts whose outcomes precede subsequent cohorts.
    for i in range(120):
        start=date(1980,1,1)+timedelta(days=i*100)
        late=i%2
        w.writerow([str(i),100,10 if late else 90,start,start-timedelta(days=1),start+timedelta(days=20),start+timedelta(days=30 if late else 10),'test-source'])
    return {'csv_text':stream.getvalue(),'settings':{'mapping':{'project_id':'id','land_required':'required','land_acquired':'acquired','observation_date':'obs','source_date':'source','planned_completion':'planned','actual_completion':'actual','source_reference':'reference'},'area_unit':'hectares','amount_unit':'INR','date_format':'ISO','project_type':'other'},'verified_outcomes':True,'verified_snapshot_inputs':True,'verified_plan_at_snapshot':True,'verification_note':'Test-only contract verification'}

def test_temporal_model_contract_and_leakage_gate():
    p=historical_contract();r=client.post('/api/evaluate',json=p)
    assert r.status_code==200,r.text
    d=r.json();assert sum(d['split']['counts'])==120
    assert len(d['split']['counts'])==4
    assert len(d['validation_candidates'])==4
    assert 'XGBoost' in d['validation_candidates']
    assert 0 <= d['validation_candidates']['XGBoost']['brier'] <= 1
    assert len(d['features'])==4
    assert len(d['heldout_predictions'][0]['local_sensitivity'])==4
    assert len(d['uncertainty']['brier_95_percent_bootstrap_interval'])==2
    assert d['prediction_enabled'] is True
    assert d['heldout_predictions'][0]['row_index']>=96
    assert d['test_metrics']['brier']<d['test_baseline']['brier']
    p['csv_text']=p['csv_text'].replace('1980-01-11','2010-01-11')
    assert client.post('/api/evaluate',json=p).status_code==422

def test_test_outcomes_do_not_select_or_calibrate_model():
    p=historical_contract(); first=client.post('/api/evaluate',json=p).json()
    rows=list(csv.reader(io.StringIO(p['csv_text'])))
    for i,row in enumerate(rows[1:]):
        if i>=96:
            obs=date.fromisoformat(row[3]);row[6]=str(obs+timedelta(days=10 if i%2 else 30))
    stream=io.StringIO();csv.writer(stream).writerows(rows);p['csv_text']=stream.getvalue()
    second=client.post('/api/evaluate',json=p).json()
    assert first['selected_model']==second['selected_model']
    assert first['validation_candidates']==second['validation_candidates']
    assert first['calibration']['mean_probability']==second['calibration']['mean_probability']
    assert second['prediction_enabled'] is False
