from uuid import uuid4
from .config import settings
from .events import EVENTS, STAGES_100M
from .model_adapter import MockPoseModelAdapter, TeamPoseModelAdapter
from .quality import evaluate_capture
from .schemas import (AnalysisCreate, AnalysisResult, DevelopmentPriority,
                      JobStatus, ReferenceStatus, StageComparison)

def run_analysis(request: AnalysisCreate) -> AnalysisResult:
    adapter = MockPoseModelAdapter() if settings.model_mode == "mock" else TeamPoseModelAdapter(settings.model_path)
    raw = adapter.analyse(request)
    quality = evaluate_capture(frames_read=raw["frames_read"], fps=raw.get("fps"),
        usable_keypoint_ratio=raw.get("usable_keypoint_ratio", 0), camera_yaw_deg=raw.get("camera_yaw_deg"),
        body_visible_ratio=raw.get("body_visible_ratio"))
    if not quality.accepted:
        return AnalysisResult(analysis_id=f"WTH-{uuid4().hex[:10].upper()}", athlete_id=request.athlete_id,
            athlete_name=request.athlete_name, event=request.event, phase=request.phase, status=JobStatus.FAILED,
            reference_status=EVENTS[request.event]["reference_status"], contract_version=settings.contract_version,
            model_version=settings.model_version, quality=quality, message="The file could not be decoded. No measurements were produced.")

    speed = raw.get("segment_speed_mps")
    comparisons: list[StageComparison] = []
    priorities: list[DevelopmentPriority] = []
    if request.event == "100m" and speed:
        comparisons = [StageComparison(key=k,label=label,target_speed_mps=target,
            proximity_pct=round(min(100,speed/target*100),1),speed_gap_mps=round(max(0,target-speed),3),source=source)
            for k,label,target,source in STAGES_100M]
        priorities = [DevelopmentPriority(metric_keys=["GCT","FT"],title="Ground-contact efficiency",
            priority_score=.91,confidence=.88,integration_status="demo")]

    status = JobStatus.COMPLETED_WARNINGS if quality.warnings else JobStatus.COMPLETED
    reference_status = EVENTS[request.event]["reference_status"]
    message = ("Analysis completed. Comparative bands are awaiting federation reference approval."
               if reference_status == ReferenceStatus.PENDING else "Analysis and calibrated comparisons completed.")
    return AnalysisResult(analysis_id=f"WTH-{uuid4().hex[:10].upper()}", athlete_id=request.athlete_id,
        athlete_name=request.athlete_name, event=request.event, phase=request.phase, status=status,
        reference_status=reference_status, contract_version=settings.contract_version,
        model_version=settings.model_version, quality=quality, segment_speed_mps=speed,
        metrics=raw["metrics"], comparisons=comparisons, priorities=priorities, message=message)

