import csv
import io
from pathlib import Path
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from .schemas import Upload,Analysis,WhatIf,Export,Train,FIELDS
from .analysis import parse,analyze,row_analysis,number

app=FastAPI(title='BhuNiti AI · Team Nexora',version='3.0.0')
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],allow_methods=['GET','POST','DELETE'],allow_headers=['Content-Type','X-Access-Code'])
@app.middleware('http')
async def no_cache(request:Request,call_next):
    if request.url.path.startswith('/api'):
        declared=request.headers.get('content-length')
        if declared and int(declared)>6_000_000: return Response('Request too large',status_code=413)
    response=await call_next(request)
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    return response
from fastapi.exceptions import RequestValidationError
@app.exception_handler(RequestValidationError)
async def invalid_schema(request,exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=422,content={'detail':'Invalid request: confirm required settings, field types and size limits.'})
@app.exception_handler(ValueError)
async def invalid(request,exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=422,content={'detail':str(exc)})
@app.get('/api/health')
def health():return {'status':'ok','storage':'analysis: request memory; portals: expiring session memory (2 hours)'}
@app.get('/api/fields')
def fields():return FIELDS
@app.post('/api/inspect')
def inspect(req:Upload):
    headers,rows=parse(req.csv_text)
    return {'headers':headers,'row_count':len(rows),'preview':rows[:5]}
@app.post('/api/analyze')
def analysis(req:Analysis):return analyze(req.csv_text,req.settings)
@app.post('/api/what-if')
def whatif(req:WhatIf):
    baseline=analyze(req.csv_text,req.settings)
    if req.row_index>=len(baseline['rows']):raise ValueError('Row index is out of range.')
    row=baseline['rows'][req.row_index]
    if not row['can_what_if']:raise ValueError('Existing valid required and acquired land values are needed.')
    required=number(row['mapped']['land_required'])
    if req.acquired>required:raise ValueError('Acquired land cannot exceed required land.')
    changed=dict(row['original']);changed[req.settings.mapping['land_acquired']]=str(req.acquired)
    after=row_analysis(changed,req.settings,req.row_index)
    return {'baseline':row['indicators'],'changed':after['indicators'],'note':'User-entered assumption. Arithmetic only; original record unchanged. No delay reduction is inferred.'}
@app.post('/api/evaluate')
def evaluate(req:Train):
    from .modeling import train
    return train(req)
@app.post('/api/export')
def export(req:Export):
    result=analyze(req.csv_text,req.settings)
    fields=['acquisition_progress_pct','remaining_land','remaining_land_pct','sanction_inr_per_required_hectare']
    outputs=fields+['data_quality_flags','review_findings','recorded_date_gaps']+(['officer_notes'] if req.include_notes else [])
    headers=result['headers']; extra=[]
    for key in outputs:
        candidate='bhuniti_'+key
        while candidate in headers+extra:candidate='_'+candidate
        extra.append(candidate)
    stream=io.StringIO(newline='');writer=csv.writer(stream)
    def safe(v):
        text=str(v if v is not None else '')
        return "'"+text if text.lstrip().startswith(('=','+','-','@')) or text.startswith(('\t','\r')) else text
    writer.writerow([safe(v) for v in headers+extra])
    for row in result['rows']:
        vals=list(row['original'].values())+[row['indicators'][k] for k in fields]+[' | '.join(row['flags']),' | '.join(row['actions']),' | '.join(f"{g['from']} → {g['to']}: {g['days']} days" for g in row['gaps'])]
        if req.include_notes:vals.append(req.notes.get(str(row['index']),''))
        writer.writerow([safe(v) for v in vals])
    return Response('\ufeff'+stream.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="bhuniti_results.csv"'})
from .community import router as community_router
app.include_router(community_router)
frontend=Path(__file__).resolve().parents[2]/'frontend/dist'
if frontend.exists():app.mount('/',StaticFiles(directory=frontend,html=True),name='frontend')
