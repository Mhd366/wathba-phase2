# WATHBA advanced metrics update

This update adds backend-computed derived metrics to each new race analysis:

- Duty factor
- Contact/flight ratio
- Normalised step frequency using the submitted athlete height
- Knee delta using contact versus minimum observed knee angle
- Left/right step-timing asymmetry
- Valid detected step count

Step length, relative step length, speed, and Froude number remain unavailable until distance or race-time calibration exists.

## Install

```powershell
cd D:\Projects\WATHBA_PHASE2
Expand-Archive -LiteralPath ".\WATHBA_ADVANCED_METRICS_UPDATE.zip" -DestinationPath "." -Force

cd backend
.\.venv\Scripts\python.exe -m pytest
cd ..\frontend
npm.cmd run build
cd ..

git add backend frontend INSTALL_ADVANCED_METRICS.md
git commit -m "Add advanced biomechanical metrics"
git pull --rebase origin main
git push origin main
```

Deploy Render first, then redeploy Vercel. Run a new video analysis; previously stored analyses do not contain the new `derived_metrics` fields.
