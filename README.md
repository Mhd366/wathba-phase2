# WATHBA Phase 2 — Federation Trial

Production foundation for a 3–4 week federation trial.

## Stack decision

- **Frontend:** React/TypeScript. The deployed product is a responsive coach and athlete workspace, not Streamlit.
- **Backend:** FastAPI with a versioned JSON contract.
- **Model:** adapter boundary; the team model can replace the mock adapter without changing the frontend.
- **Storage:** private object storage for video; PostgreSQL for athletes, jobs and results.
- **PDF:** server-generated federation report.
- **RAG/LLM:** owned by the responsible team. WATHBA exposes a read-only integration-context endpoint only.

## Repository map

```text
backend/
  app/                 FastAPI, quality policy, model adapter, PDF
  tests/               contract and event-safety tests
  Dockerfile
research/
  original_modules/    supplied Streamlit/domain files preserved as evidence
docs/
  ARCHITECTURE.md
```

## Important scientific rule

100m is calibrated. 200m and 400m accept video and may expose raw model measurements, but comparisons, tier labels and development claims remain locked until their event-specific reports are approved. The system never borrows 100m bands.

## Cloud-only deployment

1. Push this project to GitHub.
2. Connect the `backend/` directory to Google Cloud Run continuous deployment.
3. Set `MODEL_MODE=mock` while training continues.
4. Store uploaded videos in a private bucket and pass only `video_object_key` to the API.
5. Set the React environment variable `NEXT_PUBLIC_ANALYSIS_API_URL` to the Cloud Run URL.
6. When the model is approved, upload its versioned ONNX/TorchScript artifact and switch `MODEL_MODE=team`.

## API routes

- `GET /health`
- `GET /v1/capabilities`
- `POST /v1/analyses`
- `GET /v1/analyses/{analysis_id}`
- `GET /v1/analyses/{analysis_id}/report.pdf`
- `GET /v1/analyses/{analysis_id}/integration-context`

The included in-memory store is for the contract trial. Replace it with PostgreSQL before multi-instance production traffic.

