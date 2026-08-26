from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from .config import settings
from .auth import require_user
from .database import load_analysis, save_analysis
from .events import EVENTS
from .report import build_pdf
from .schemas import (AnalysisCreate, AnalysisResult, IntegrationContext,
                      RaceAnalysisCreate, RaceAnalysisResult)
from .service import run_analysis, run_race_analysis

app=FastAPI(title=settings.app_name,version=settings.contract_version)
app.add_middleware(CORSMiddleware,allow_origins=settings.allowed_origins.split(","),allow_credentials=True,
                   allow_methods=["GET","POST"],allow_headers=["Authorization","Content-Type"])
@app.get("/health")
def health(): return {"status":"ok","contract_version":settings.contract_version,"model_mode":settings.model_mode}

@app.get("/v1/capabilities")
def capabilities():
    return {"events":[{"code":code.value,**data} for code,data in EVENTS.items()],
            "integrations":{"chat":"ready_for_external_api","recommendations":"ready_for_external_api"}}

@app.post("/v1/analyses",response_model=AnalysisResult,status_code=201)
def create_analysis(payload:AnalysisCreate,user:dict=Depends(require_user)):
    if payload.phase not in EVENTS[payload.event]["phases"]:
        raise HTTPException(422,f"Valid phases: {EVENTS[payload.event]['phases']}")
    result=run_analysis(payload); save_analysis(user["id"],payload,result); return result

@app.post("/v1/races/analyse",response_model=RaceAnalysisResult,status_code=201)
def create_race_analysis(payload:RaceAnalysisCreate,user:dict=Depends(require_user)):
    if payload.phase not in EVENTS[payload.event]["phases"]:
        raise HTTPException(422,f"Valid phases: {EVENTS[payload.event]['phases']}")
    try:
        batch, requests = run_race_analysis(payload)
    except ValueError as error:
        raise HTTPException(422,str(error)) from error
    except RuntimeError as error:
        raise HTTPException(503,str(error)) from error
    for request, result in zip(requests, batch.results):
        save_analysis(user["id"],request,result)
    return batch

@app.get("/v1/analyses/{analysis_id}",response_model=AnalysisResult)
def get_analysis(analysis_id:str,user:dict=Depends(require_user)):
    result=load_analysis(user["id"],analysis_id)
    if result is None: raise HTTPException(404,"Analysis not found")
    return result

@app.get("/v1/analyses/{analysis_id}/report.pdf")
def export_report(analysis_id:str,user:dict=Depends(require_user)):
    result=load_analysis(user["id"],analysis_id)
    if result is None: raise HTTPException(404,"Analysis not found")
    return Response(build_pdf(result),media_type="application/pdf",
                    headers={"Content-Disposition":f'attachment; filename="{analysis_id}.pdf"'})

@app.get("/v1/analyses/{analysis_id}/integration-context",response_model=IntegrationContext)
def integration_context(analysis_id:str,user:dict=Depends(require_user)):
    r=load_analysis(user["id"],analysis_id)
    if r is None: raise HTTPException(404,"Analysis not found")
    return IntegrationContext(analysis_id=r.analysis_id,event=r.event,
        athlete_summary={"athlete_id":r.athlete_id,"athlete_name":r.athlete_name,"speed_mps":r.segment_speed_mps},
        metric_gaps=[p.model_dump() for p in r.priorities],quality_warnings=r.quality.warnings)
