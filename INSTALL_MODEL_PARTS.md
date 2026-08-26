# WATHBA split-model loader

Apply this small update after uploading these private Supabase objects:

```text
model-artifacts/production/best.pt.part000
model-artifacts/production/best.pt.part001
model-artifacts/production/best.pt.part002
```

## Install

```powershell
cd D:\Projects\WATHBA_PHASE2
Expand-Archive -LiteralPath ".\WATHBA_MODEL_PARTS_UPDATE.zip" -DestinationPath "." -Force
```

## Render variables

```text
MODEL_PATH=/tmp/wathba-pose-final.pt
MODEL_BUCKET=model-artifacts
MODEL_OBJECT_PATH=
MODEL_OBJECT_PARTS=production/best.pt.part000,production/best.pt.part001,production/best.pt.part002
MODEL_SIZE_BYTES=118267057
MODEL_SHA256=0683621EC60D20218F137542808EB6E7EA09A77291C23866DF1F3B2BF87CBFB4
```

Keep the existing Supabase service-role credentials. `MODEL_OBJECT_PARTS` is a single comma-separated value with no line breaks.

The backend downloads each part sequentially, appends it to a temporary file, deletes the downloaded part, verifies final size and SHA-256, and only then allows Ultralytics to load the model.

## Verify and deploy

```powershell
cd D:\Projects\WATHBA_PHASE2\backend
.\.venv\Scripts\python.exe -m pytest
cd ..
git add backend INSTALL_MODEL_PARTS.md
git commit -m "Support split model artifact download"
git push origin main
```

Then deploy the latest commit on Render. A successful first analysis creates `/tmp/wathba-pose-final.pt`; subsequent analyses on the same running instance reuse it.
