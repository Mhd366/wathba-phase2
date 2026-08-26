"""
Example FastAPI wrapper around the existing rag.py + llm.py.

Run with:
    pip install fastapi uvicorn
    uvicorn api_example:app --host 0.0.0.0 --port 8000

Send a request with:
    curl -X POST http://localhost:8000/ask \
      -H "Content-Type: application/json" \
      -H "X-API-Key: your-secret-key" \
      -d '{"question": "What is the typical ground contact time?", "model": "llama3.1:latest"}'
"""

import os
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, Dict, Any

from rag import retrieve
from llm import generate_answer

API_KEY = os.getenv("WATHBA_API_KEY")  # set this in the deployment .env

app = FastAPI(title="WATHBA RAG API")


# ------------------------------------------------------------------
# Request / response schemas
# ------------------------------------------------------------------

class AskRequest(BaseModel):
    question: str
    model: str = "llama3.1:latest"
    athlete_data: Optional[Dict[str, Any]] = None


class AskResponse(BaseModel):
    answer: str
    sources: list


# ------------------------------------------------------------------
# Simple API key check
# ------------------------------------------------------------------

def check_api_key(x_api_key: Optional[str]):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ------------------------------------------------------------------
# NOTE: because rag.py loads its models (dense_model, sparse_model,
# reranker) at import time as module-level globals, simply importing
# it here already loads them ONCE when the server starts — not per
# request. That part of your existing code is already correct for
# API use. Just don't re-import or reload rag.py per request.
# ------------------------------------------------------------------

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


@app.get("/health")
def health():
    return {"status": "ok"}