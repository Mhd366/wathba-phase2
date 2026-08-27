"""
WATHBA RAG + LLM API

Endpoints:
  POST /ask                  — pure research question (JSON body)
  POST /ask-with-athlete-csv — question + athlete prediction CSV upload
  GET  /health                — health check

Run locally:
    uvicorn api_example:app --host 0.0.0.0 --port 8000

Run on Render:
    Start Command: uvicorn api_example:app --host 0.0.0.0 --port $PORT
"""

import os
import io
from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, Dict, Any

from rag import retrieve
from llm import generate_answer
from csv_parser import parse_running_summary_csv, list_available_runners

API_KEY = os.getenv("WATHBA_API_KEY")  # set this in Render's Environment Variables

app = FastAPI(title="WATHBA RAG API")


# ------------------------------------------------------------------
# Shared helpers
# ------------------------------------------------------------------

def check_api_key(x_api_key: Optional[str]):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ------------------------------------------------------------------
# /ask — pure research question, no athlete data (JSON body)
# ------------------------------------------------------------------

class AskRequest(BaseModel):
    question: str
    model: str = "llama3.1:latest"
    athlete_data: Optional[Dict[str, Any]] = None


class AskResponse(BaseModel):
    answer: str
    sources: list


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest, x_api_key: Optional[str] = Header(None)):
    check_api_key(x_api_key)

    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        top_docs, context_text = retrieve(request.question)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Retrieval failed: {e}")

    try:
        answer = generate_answer(
            question=request.question,
            context_text=context_text,
            model=request.model,
            athlete_data=request.athlete_data,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"LLM generation failed: {e}")

    sources = [
        {"source": d["source"], "page": d["page"], "rerank_score": d["rerank_score"]}
        for d in top_docs
    ]

    return AskResponse(answer=answer, sources=sources)


# ------------------------------------------------------------------
# /ask-with-athlete-csv — question + a WATHBA prediction CSV upload
# (multipart/form-data, not JSON, because it includes a file)
# ------------------------------------------------------------------

@app.post("/ask-with-athlete-csv")
async def ask_with_athlete_csv(
    question: str = Form(...),
    model: str = Form("llama3.1:latest"),
    athlete_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    x_api_key: Optional[str] = Header(None),
):
    check_api_key(x_api_key)

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    csv_bytes = await file.read()

    try:
        track_id = int(athlete_id) if athlete_id is not None else None
        athlete_data = parse_running_summary_csv(csv_bytes, track_id=track_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")

    try:
        top_docs, context_text = retrieve(question)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Retrieval failed: {e}")

    try:
        answer = generate_answer(
            question=question,
            context_text=context_text,
            model=model,
            athlete_data=athlete_data,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"LLM generation failed: {e}")

    return {
        "answer": answer,
        "athlete_data_used": athlete_data,
        "sources": [{"source": d["source"], "page": d["page"]} for d in top_docs],
    }


@app.post("/list-runners")
async def list_runners(file: UploadFile = File(...)):
    """
    Lets the frontend show a picker (e.g. 'Runner 4 — usable', 'Runner 1 —
    review/reject') before the user commits to analyzing one of them.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    csv_bytes = await file.read()

    try:
        return {"runners": list_available_runners(csv_bytes)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")


@app.get("/health")
def health():
    return {"status": "ok"}
