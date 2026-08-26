from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field

class EventCode(str, Enum):
    M100 = "100m"
    M200 = "200m"
    M400 = "400m"

class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WARNINGS = "completed_with_warnings"
    FAILED = "failed"

class ReferenceStatus(str, Enum):
    CALIBRATED = "calibrated"
    PENDING = "pending_reference_review"

class QualityWarning(BaseModel):
    code: str
    severity: Literal["info", "warning", "fatal"] = "warning"
    message: str
    fix: str | None = None

class CaptureQuality(BaseModel):
    score: float = Field(ge=0, le=1)
    fps: float | None = None
    frames_read: int = 0
    usable_keypoint_ratio: float = Field(default=0, ge=0, le=1)
    accepted: bool = True
    warnings: list[QualityWarning] = []

class MetricValue(BaseModel):
    key: str
    label: str
    value: float | None
    unit: str
    confidence: float = Field(ge=0, le=1)
    status: Literal["measured", "unavailable"] = "measured"

class StageComparison(BaseModel):
    key: str
    label: str
    target_speed_mps: float
    proximity_pct: float
    speed_gap_mps: float
    source: str

class DevelopmentPriority(BaseModel):
    metric_keys: list[str]
    title: str
    priority_score: float
    confidence: float
    integration_status: Literal["demo", "external_pending"] = "demo"

class AnalysisCreate(BaseModel):
    athlete_id: str = Field(min_length=2, max_length=100)
    athlete_name: str = Field(min_length=2, max_length=120)
    event: EventCode
    phase: str
    height_cm: float = Field(gt=120, lt=230)
    video_object_key: str = Field(min_length=3)
    lane: int | None = Field(default=None, ge=1, le=8)

class RaceAthleteCreate(BaseModel):
    athlete_id: str = Field(min_length=2, max_length=100)
    athlete_name: str = Field(min_length=2, max_length=120)
    height_cm: float = Field(gt=120, lt=230)
    lane: int = Field(ge=1, le=8)

class RaceAnalysisCreate(BaseModel):
    event: EventCode
    phase: str
    video_object_key: str = Field(min_length=3)
    athletes: list[RaceAthleteCreate] = Field(min_length=1, max_length=8)

class AnalysisResult(BaseModel):
    analysis_id: str
    athlete_id: str
    athlete_name: str
    lane: int | None = Field(default=None, ge=1, le=8)
    event: EventCode
    phase: str
    status: JobStatus
    reference_status: ReferenceStatus
    contract_version: str
    model_version: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    quality: CaptureQuality
    segment_speed_mps: float | None = None
    metrics: list[MetricValue] = []
    comparisons: list[StageComparison] = []
    priorities: list[DevelopmentPriority] = []
    message: str = ""

class RaceAnalysisResult(BaseModel):
    race_id: str
    status: JobStatus
    results: list[AnalysisResult]
    unmatched_lanes: list[int] = []
    message: str

class IntegrationContext(BaseModel):
    analysis_id: str
    event: EventCode
    athlete_summary: dict
    metric_gaps: list[dict]
    quality_warnings: list[QualityWarning]
