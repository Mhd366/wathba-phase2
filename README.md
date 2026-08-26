<div align="center">

<img src="logo 1.jpeg" alt="WATHBA Logo" width="500">

### AI-Powered Sprint Performance Gap Analysis

**Beyond race time — understanding why the gap exists.**

<br>

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![YOLO](https://img.shields.io/badge/YOLO11x--Pose-111F68)
![ByteTrack](https://img.shields.io/badge/Tracking-ByteTrack-6C63FF)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-5C3EE8?logo=opencv&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-Deep%20Learning-EE4C2C?logo=pytorch&logoColor=white)
![Ultralytics](https://img.shields.io/badge/Ultralytics-YOLO-111F68)
![NumPy](https://img.shields.io/badge/NumPy-Data%20Processing-013243?logo=numpy&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-Data%20Processing-150458?logo=pandas&logoColor=white)
![Roboflow](https://img.shields.io/badge/Roboflow-Dataset%20%26%20Annotation-6706CE)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-Frontend-61DAFB?logo=react&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-4169E1?logo=postgresql&logoColor=white)
![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Deployment-4285F4?logo=googlecloud&logoColor=white)
![RAG](https://img.shields.io/badge/RAG-AI%20Interpretation-8A2BE2)
![LLM](https://img.shields.io/badge/LLM-AI%20Interpretation-412991)

</div>

---

# WATHBA

## Project Overview

In sprinting, race time tells us **how large the performance gap is**, but it does not explain **why that gap exists**.

**WATHBA** is an AI-powered sprint performance analysis system designed to identify the biomechanical factors that may contribute to the performance gap between an athlete and elite or Olympic-level sprinters.

Using sprint videos, WATHBA combines pose estimation, athlete tracking, temporal analysis, and biomechanical measurements to transform race footage into athlete-specific performance insights.

> **Race time identifies the gap. WATHBA investigates what is behind it.**

---

## Problem Statement

The performance gap between Saudi sprinters and elite or Olympic-level athletes can be identified through race time, but **race time alone does not explain why this gap exists**.

Differences in performance may be influenced by biomechanical factors such as:

- Step and stride frequency
- Step and stride length
- Ground contact time
- Flight time
- Knee mechanics
- Trunk position

Traditional biomechanical analysis often requires specialized laboratories, motion-capture systems, force platforms, and high-speed cameras.

WATHBA explores a more accessible AI and video-based approach for identifying and interpreting the biomechanical factors that may contribute to sprint performance differences.

---

## Project Objective

WATHBA aims to support the reduction of the performance gap between developing athletes and elite or Olympic-level sprinters by:

- Analyzing sprint race videos.
- Detecting and tracking multiple athletes.
- Estimating 17 body keypoints.
- Extracting biomechanical performance indicators.
- Creating an individual biomechanical profile for each runner.
- Comparing athlete measurements with approved elite-level references.
- Identifying potential contributors to the performance gap.
- Providing interpretable performance insights for athletes and coaches.

---

# System Workflow

```text
Sprint Video
     │
     ▼
YOLO11x-Pose
     │
     ▼
17 Body Keypoints
     │
     ▼
ByteTrack
     │
     ▼
Runner IDs
     │
     ▼
Temporal Processing
     │
     ▼
Gait Event Detection
     │
     ▼
Biomechanical Metrics
     │
     ▼
Elite Reference Comparison
     │
     ▼
Performance Gap Analysis
     │
     ▼
Athlete Insights
```

---

# Dataset

The WATHBA dataset was personally collected from multiple sources, including YouTube, with a focus on sprinting and running videos.

The collected videos were converted into individual frames, and athlete poses were manually annotated using **Roboflow**.

Each athlete was annotated using **17 body keypoints** following the YOLO Pose keypoint format.

The original dataset contained **516 annotated images**, which was expanded to **1,442 images** through data augmentation.

| Dataset | Images |
|---|---:|
| Original | 516 |
| After Augmentation | 1,442 |
| Training | 1,153 |
| Validation | 144 |
| Testing | 145 |

The dataset was specifically developed to fine-tune YOLO11x-Pose for sprint-specific pose estimation and improve runner detection and keypoint stability.

---

# Pose Estimation Model

WATHBA uses **YOLO11x-Pose** for athlete pose estimation.

The project initially experimented with **YOLO11n-Pose** as a lightweight model for early pipeline development.

Because WATHBA's biomechanical calculations depend directly on accurate and stable body keypoints, the higher-capacity **YOLO11x-Pose** was later selected to prioritize pose quality over inference speed.

## Baseline

The COCO-pretrained YOLO11x-Pose was used as the baseline.

During sprint-video testing, two main limitations were observed:

- Some runners were not consistently detected.
- Keypoints showed instability across consecutive frames.

## Fine-Tuned Model

YOLO11x-Pose was fine-tuned on the custom WATHBA sprint dataset to better handle:

- Sprint-specific poses
- Rapid limb movement
- Multiple athletes
- Athlete overlap
- Partial occlusion
- Race-video conditions

The fine-tuned model produced more consistent runner detection and more stable keypoints for downstream biomechanical analysis.

---

# Model Evaluation

| Metric | Baseline | Fine-Tuned | Improvement |
|---|---:|---:|---:|
| **Precision** | 95.58% | **99.52%** | +3.94 pp |
| **Recall** | 92.86% | **98.71%** | +5.85 pp |
| **mAP@50** | 92.50% | **99.48%** | +6.98 pp |
| **mAP@50–95** | 56.31% | **86.38%** | **+30.08 pp** |

The largest improvement was observed in **mAP@50–95**, increasing from **56.31% to 86.38%**.

This provides a stronger pose-estimation foundation for the biomechanical analysis pipeline.

> **Note:** Model evaluation metrics measure pose-estimation performance and do not represent the accuracy of the biomechanical measurements themselves.

---

# Biomechanical Analysis

After pose estimation and athlete tracking, WATHBA converts body movement into biomechanical performance indicators.

| Metric | Description |
|---|---|
| **Step / Stride Frequency** | Running rhythm and cycle frequency |
| **Step / Stride Length** | Distance covered during the running cycle |
| **Ground Contact Time** | Time the foot remains in contact with the ground |
| **Flight Time** | Time during which the athlete is airborne |
| **Knee Angle** | Lower-limb mechanics during sprinting |
| **Trunk Lean** | Athlete trunk position during running |

Additional normalized and contextual measurements are calculated to support athlete comparison and result interpretation.

---

# Performance Gap Analysis

The purpose of WATHBA is not simply to determine that one athlete is slower than another.

```text
Athlete Performance
        │
        ▼
Biomechanical Profile
        │
        ▼
Elite Reference
        │
        ▼
Identify Differences
        │
        ▼
Potential Contributors
        │
        ▼
Performance Development Insights
```

WATHBA uses biomechanical measurements to investigate **which movement characteristics may be contributing to the observed performance gap**.

> **The time shows the gap. The biomechanics help explain the gap.**

---

# WATHBA Phase 2 — Federation Trial

Following the development and validation of the core analysis pipeline, WATHBA is being extended into a **production foundation for a 3–4 week federation trial**.

Phase 2 moves the project from a research-oriented analysis pipeline toward a deployable coach and athlete platform.

## Production Architecture

- **Frontend:** React / TypeScript responsive coach and athlete workspace.
- **Backend:** FastAPI with a versioned JSON contract.
- **AI Model:** Adapter-based model boundary, allowing the approved team model to replace the mock model without changing the frontend.
- **Storage:** Private object storage for uploaded videos and PostgreSQL for athletes, analysis jobs, and results.
- **Reports:** Server-generated federation PDF reports.
- **RAG / LLM:** Maintained as a separate evidence and interpretation component with read-only integration context.

---


## Repository Structure

```text
backend/
  app/                 FastAPI, quality policy, model adapter, PDF
  tests/               Contract and event-safety tests
  Dockerfile

research/
  original_modules/    Research and domain-analysis modules

docs/
  ARCHITECTURE.md
```

---

## API

The Phase 2 backend exposes a versioned analysis API:

```text
GET  /health
GET  /v1/capabilities
POST /v1/analyses
GET  /v1/analyses/{analysis_id}
GET  /v1/analyses/{analysis_id}/report.pdf
GET  /v1/analyses/{analysis_id}/integration-context
```

The included in-memory store supports the initial contract trial and is intended to be replaced with **PostgreSQL** before multi-instance production deployment.

---

## Cloud Deployment

Phase 2 is designed for cloud deployment using:

**GitHub → Google Cloud Run → FastAPI Backend → Private Video Storage → Analysis Model**

During continued model development, the backend can operate using:

```text
MODEL_MODE=mock
```

Once the approved model artifact is ready, the backend can switch to:

```text
MODEL_MODE=team
```

without requiring changes to the frontend API contract.

---


# WATHBA Team

- **Aljuhara**
- **Dalia**
- **Mohammed**
- **Nawaf**
- **Abdulaziz**

---

<div align="center">

### WATHBA

**From knowing the time to understanding the performance behind it.**

</div>
