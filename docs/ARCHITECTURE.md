# Federation-trial architecture

```text
React product
  ├─ Athlete workspace
  ├─ Eight-lane coach board
  ├─ 100m calibrated module
  ├─ 200m reference-review module
  ├─ 400m reference-review module
  └─ PDF + chatbot surfaces
          │
          ▼
FastAPI contract v2
  ├─ authentication boundary
  ├─ analysis job API
  ├─ tolerant capture-quality policy
  ├─ event capability registry
  ├─ PDF export
  └─ integration context endpoint
          │
          ▼
Pose model adapter
  ├─ mock contract fixture now
  └─ team model later
          │
          ▼
Shared kinematics + event bands
  ├─ 100m: calibrated comparisons
  ├─ 200m: raw analysis, bands locked
  └─ 400m: raw analysis, bands locked
```

## Video acceptance policy

The former all-or-nothing refusal is replaced with three outcomes:

1. `completed`: usable clip with no material warning.
2. `completed_with_warnings`: analysis continues, affected metrics receive lower confidence or become unavailable.
3. `failed`: only when no frames can be decoded or no usable person/keypoints can be obtained.

This is smoother for the athlete without silently manufacturing measurements.

## Model handoff contract

The model team returns frames/keypoints to `TeamPoseModelAdapter`. The adapter must emit:

- frames read, fps, usable keypoint ratio;
- optional camera/body visibility estimates;
- segment speed when calibration exists;
- six metric values with per-metric confidence.

No UI change is permitted when swapping mock and team adapters.

## External AI integration

RAG, recommendations and LLM chat are separate services. They consume `GET /v1/analyses/{id}/integration-context`. They do not receive raw video and cannot overwrite measured KPIs, event bands or capture quality.

