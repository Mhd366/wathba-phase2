from abc import ABC, abstractmethod
from .schemas import AnalysisCreate, MetricValue

class PoseModelAdapter(ABC):
    @abstractmethod
    def analyse(self, request: AnalysisCreate) -> dict: ...

class MockPoseModelAdapter(PoseModelAdapter):
    """Contract fixture used until the team's model artifact is approved."""
    def analyse(self, request: AnalysisCreate) -> dict:
        return {
            "frames_read": 486, "fps": 60.0, "usable_keypoint_ratio": .94,
            "camera_yaw_deg": 14.0, "body_visible_ratio": .91,
            "segment_speed_mps": 8.86,
            "metrics": [
                MetricValue(key="SF", label="Step frequency", value=4.32, unit="Hz", confidence=.94),
                MetricValue(key="SL", label="Step length", value=2.05, unit="m", confidence=.89),
                MetricValue(key="GCT", label="Ground contact", value=.118, unit="s", confidence=.91),
                MetricValue(key="FT", label="Flight time", value=.113, unit="s", confidence=.90),
                MetricValue(key="KNEE", label="Knee angle", value=148, unit="deg", confidence=.86),
                MetricValue(key="LEAN", label="Trunk lean", value=11.4, unit="deg", confidence=.72),
            ],
        }

class TeamPoseModelAdapter(PoseModelAdapter):
    def __init__(self, model_path: str):
        self.model_path = model_path
        # Load the approved ONNX/TorchScript model once at process startup.

    def analyse(self, request: AnalysisCreate) -> dict:
        # Integration boundary:
        # video_object_key -> decoded frames -> team keypoints -> shared
        # kinematics.py -> exact dictionary returned by MockPoseModelAdapter.
        raise NotImplementedError("Connect the team's versioned model artifact here")

