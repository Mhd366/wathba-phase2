# WATHBA multi-runner model integration

This update replaces per-athlete repeated inference with one race-level request. The video is decoded once, YOLO Pose + ByteTrack produces runner tracks, tracks are mapped to the coach's lane roster, and one persisted analysis is returned per athlete.

## Apply on Windows

Place `WATHBA_MULTI_RUNNER_INTEGRATION.zip` in `D:\Projects\WATHBA_PHASE2`, then:

```powershell
cd D:\Projects\WATHBA_PHASE2
Expand-Archive -LiteralPath ".\WATHBA_MULTI_RUNNER_INTEGRATION.zip" -DestinationPath "." -Force

cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest
cd ..\frontend
npm.cmd run build
cd ..
```

The local model must be here for local testing:

```text
D:\Projects\WATHBA_PHASE2\backend\models\best.pt
```

Do not extract the supplied checkpoint internals. Copy/rename `best.pt.zip` to `best.pt` while preserving its bytes.

## Local backend environment

Add to `backend/.env`:

```text
MODEL_MODE=team
MODEL_PATH=./models/best.pt
MODEL_OBJECT_PATH=
MODEL_SHA256=0683621EC60D20218F137542808EB6E7EA09A77291C23866DF1F3B2BF87CBFB4
MODEL_SIZE_BYTES=118267057
MODEL_MAX_FRAMES=600
MINIMUM_TRACK_FRAMES=12
LANE_ORDER_TOP_TO_BOTTOM=true
```

For the first test, use one short side-view video and 2–4 visible runners. If lane 1 is at the bottom of the image rather than the top, change:

```text
LANE_ORDER_TOP_TO_BOTTOM=false
```

Then run:

```powershell
cd D:\Projects\WATHBA_PHASE2\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

In another PowerShell window:

```powershell
cd D:\Projects\WATHBA_PHASE2\frontend
npm.cmd run dev
```

## Production model storage

Supabase Storage:

```text
Bucket: model-artifacts (private)
Object: production/best.pt
```

Render environment:

```text
MODEL_MODE=team
MODEL_PATH=/tmp/wathba-pose-v1.pt
MODEL_BUCKET=model-artifacts
MODEL_OBJECT_PATH=production/best.pt
MODEL_SHA256=0683621EC60D20218F137542808EB6E7EA09A77291C23866DF1F3B2BF87CBFB4
MODEL_SIZE_BYTES=118267057
MODEL_CONFIDENCE=0.30
KEYPOINT_CONFIDENCE=0.35
MODEL_MAX_FRAMES=600
MINIMUM_TRACK_FRAMES=12
LANE_ORDER_TOP_TO_BOTTOM=true
VIDEO_BUCKET=race-videos
SUPABASE_URL=<project URL>
SUPABASE_SERVICE_ROLE_KEY=<server-only service role key>
PYTHON_VERSION=3.12.10
```

Keep the existing `DATABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, and `ALLOWED_ORIGINS` values. Never expose the service-role key in Vercel or a `NEXT_PUBLIC_*` variable.

## API contract

The frontend now calls only:

```text
POST /v1/races/analyse
```

Body:

```json
{
  "event": "100m",
  "phase": "max_velocity",
  "video_object_key": "user/session/video.mp4",
  "athletes": [
    {"athlete_id": "uuid-1", "athlete_name": "Omar", "height_cm": 178, "lane": 1},
    {"athlete_id": "uuid-2", "athlete_name": "Fahad", "height_cm": 181, "lane": 2}
  ]
}
```

The response includes `results[]`, one item per roster athlete. Each result has the lane, capture quality, six core metrics, confidence, and analysis ID. Each item is stored under the authenticated coach using the existing PostgreSQL persistence path.

## Honest measurement policy

Step length and metres-per-second speed remain unavailable until the capture supplies ground-plane or race-time calibration. The UI displays unavailable fields instead of demo numbers. Duty factor and contact/flight ratio are derived only when their measured inputs exist.

## Commit and deploy

```powershell
cd D:\Projects\WATHBA_PHASE2
git add backend frontend INSTALL_MULTI_RUNNER.md .gitignore
git commit -m "Integrate multi-runner YOLO pose analysis"
git push origin main
```

Deploy Render first. Confirm `/health`, then deploy Vercel so the frontend never points to a missing API route.
