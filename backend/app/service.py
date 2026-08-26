from uuid import uuid4
from pathlib import Path
from tempfile import gettempdir
from .config import settings
from .events import EVENTS, STAGES_100M
from .model_adapter import MockPoseModelAdapter, TeamPoseModelAdapter
from .model.artifact import download_race_video, ensure_model_artifact
from .model.multi_pipeline import analyse_race_video
from .quality import evaluate_capture
from .schemas import (AnalysisCreate, AnalysisResult, DevelopmentPriority,
                      JobStatus, RaceAnalysisCreate, RaceAnalysisResult,
                      ReferenceStatus, StageComparison)

def _build_result(request: AnalysisCreate, raw: dict) -> AnalysisResult:
    quality = evaluate_capture(frames_read=raw["frames_read"], fps=raw.get("fps"),
        usable_keypoint_ratio=raw.get("usable_keypoint_ratio", 0), camera_yaw_deg=raw.get("camera_yaw_deg"),
        body_visible_ratio=raw.get("body_visible_ratio"))
    if not quality.accepted:
        return AnalysisResult(analysis_id=f"WTH-{uuid4().hex[:10].upper()}", athlete_id=request.athlete_id,
            athlete_name=request.athlete_name, lane=request.lane, event=request.event, phase=request.phase, status=JobStatus.FAILED,
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
        athlete_name=request.athlete_name, lane=request.lane, event=request.event, phase=request.phase, status=status,
        reference_status=reference_status, contract_version=settings.contract_version,
        model_version=settings.model_version, quality=quality, segment_speed_mps=speed,
        metrics=raw.get("metrics", []), derived_metrics=raw.get("derived_metrics", []),
        valid_steps=raw.get("valid_steps", 0), comparisons=comparisons,
        priorities=priorities, message=message)

def run_analysis(request: AnalysisCreate) -> AnalysisResult:
    adapter = MockPoseModelAdapter() if settings.model_mode == "mock" else TeamPoseModelAdapter(settings.model_path)
    raw = adapter.analyse(request)
    return _build_result(request, raw)

def run_race_analysis(request: RaceAnalysisCreate) -> tuple[RaceAnalysisResult, list[AnalysisCreate]]:
    lanes = [athlete.lane for athlete in request.athletes]
    if len(lanes) != len(set(lanes)):
        raise ValueError("Each athlete must be assigned to a unique lane")
    race_id = f"RACE-{uuid4().hex[:10].upper()}"
    local_video = Path(gettempdir()) / f"wathba-{race_id}.mp4"
    model_path = ensure_model_artifact()
    download_race_video(request.video_object_key, local_video)
    try:
        by_lane, unmatched = analyse_race_video(
            local_video, model_path,
            {athlete.lane: athlete.height_cm for athlete in request.athletes},
        )
    finally:
        local_video.unlink(missing_ok=True)

    results: list[AnalysisResult] = []
    individual_requests: list[AnalysisCreate] = []
    for athlete in request.athletes:
        individual = AnalysisCreate(
            athlete_id=athlete.athlete_id, athlete_name=athlete.athlete_name,
            event=request.event, phase=request.phase, height_cm=athlete.height_cm,
            video_object_key=request.video_object_key, lane=athlete.lane,
        )
        individual_requests.append(individual)
        raw = by_lane.get(athlete.lane, {
            "frames_read": 1, "fps": None, "usable_keypoint_ratio": 0,
            "body_visible_ratio": 0, "segment_speed_mps": None, "metrics": [],
        })
        results.append(_build_result(individual, raw))
    batch_status = JobStatus.COMPLETED_WARNINGS if unmatched or any(r.quality.warnings for r in results) else JobStatus.COMPLETED
    message = f"Analysed one video for {len(results)} athlete(s)."
    if unmatched:
        message += f" No stable runner track was found for lane(s): {', '.join(map(str, unmatched))}."
    return RaceAnalysisResult(race_id=race_id, status=batch_status, results=results,
                              unmatched_lanes=unmatched, message=message), individual_requests
