from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

from ..config import settings
from ..schemas import MetricValue

KEYPOINT_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
]
KP = {name: index for index, name in enumerate(KEYPOINT_NAMES)}
REQUIRED = ["left_shoulder", "right_shoulder", "left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle"]


@lru_cache(maxsize=1)
def load_model(model_path: str):
    from ultralytics import YOLO
    model = YOLO(model_path)
    keypoint_shape = getattr(getattr(model, "model", None), "kpt_shape", None)
    if keypoint_shape and int(keypoint_shape[0]) != 17:
        raise RuntimeError(f"Expected 17 keypoints, model reports {keypoint_shape[0]}")
    return model


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    start = None
    for index, value in enumerate(mask.astype(bool)):
        if value and start is None:
            start = index
        elif not value and start is not None:
            if index - start >= 2:
                runs.append((start, index))
            start = None
    if start is not None and len(mask) - start >= 2:
        runs.append((start, len(mask)))
    return runs


def _angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float | None:
    if np.isnan(np.concatenate([a, b, c])).any():
        return None
    ba, bc = a - b, c - b
    denominator = np.linalg.norm(ba) * np.linalg.norm(bc)
    if denominator < 1e-8:
        return None
    cosine = np.clip(np.dot(ba, bc) / denominator, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine)))


def _contact_mask(ankle_y: np.ndarray) -> np.ndarray:
    valid = np.isfinite(ankle_y)
    if valid.sum() < 5:
        return np.zeros(len(ankle_y), dtype=bool)
    filled = ankle_y.copy()
    filled[~valid] = np.interp(np.flatnonzero(~valid), np.flatnonzero(valid), filled[valid])
    velocity = np.abs(np.gradient(filled))
    return valid & (filled >= np.quantile(filled[valid], 0.65)) & (velocity <= np.quantile(velocity[valid], 0.70))


def analyse_video(video_path: Path, model_path: Path) -> dict:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        return {"frames_read": 0, "fps": None, "usable_keypoint_ratio": 0.0, "body_visible_ratio": 0.0, "segment_speed_mps": None, "metrics": []}
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
    model = load_model(str(model_path))
    tracks: dict[int, list[tuple[int, np.ndarray, np.ndarray]]] = {}
    frame_number = 0
    while frame_number < settings.model_max_frames:
        ok, frame = capture.read()
        if not ok:
            break
        frame_number += 1
        result = model.track(frame, persist=True, tracker="bytetrack.yaml", conf=settings.model_confidence, verbose=False)[0]
        if result.boxes is None or result.boxes.id is None or result.keypoints is None:
            continue
        track_ids = result.boxes.id.int().cpu().numpy()
        points = result.keypoints.xy.cpu().numpy()
        confidences = result.keypoints.conf.cpu().numpy() if result.keypoints.conf is not None else np.ones(points.shape[:2])
        for detection_index, track_id in enumerate(track_ids):
            tracks.setdefault(int(track_id), []).append((frame_number, points[detection_index], confidences[detection_index]))
    capture.release()

    if not tracks:
        return {"frames_read": frame_number, "fps": fps, "usable_keypoint_ratio": 0.0, "body_visible_ratio": 0.0, "segment_speed_mps": None, "metrics": []}

    # MVP: one-runner demo. Select the most persistent track; lane mapping follows next.
    track_id, observations = max(tracks.items(), key=lambda item: len(item[1]))
    frame_index = np.array([row[0] for row in observations], dtype=int)
    points = np.array([row[1] for row in observations], dtype=float)
    confidence = np.array([row[2] for row in observations], dtype=float)
    reliable = confidence >= settings.keypoint_confidence
    points[~reliable] = np.nan
    required_indexes = [KP[name] for name in REQUIRED]
    usable_ratio = float(np.isfinite(points[:, required_indexes, 0]).mean())

    left_contact = _contact_mask(points[:, KP["left_ankle"], 1])
    right_contact = _contact_mask(points[:, KP["right_ankle"], 1])
    left_runs, right_runs = _runs(left_contact), _runs(right_contact)
    contact_runs = left_runs + right_runs
    contact_starts = sorted([start for start, _ in contact_runs])
    duration = max((frame_index[-1] - frame_index[0]) / fps, 1 / fps)
    step_frequency = len(contact_starts) / duration if len(contact_starts) >= 2 else None
    ground_contact = float(np.mean([(end - start) / fps for start, end in contact_runs])) if contact_runs else None
    flight_runs = _runs(~left_contact & ~right_contact)
    valid_flights = [(end - start) / fps for start, end in flight_runs if (end - start) / fps <= 0.30]
    flight_time = float(np.mean(valid_flights)) if valid_flights else None

    knee_angles: list[float] = []
    trunk_angles: list[float] = []
    for index in contact_starts:
        for side in ("left", "right"):
            value = _angle(points[index, KP[f"{side}_hip"]], points[index, KP[f"{side}_knee"]], points[index, KP[f"{side}_ankle"]])
            if value is not None:
                knee_angles.append(value)
        shoulders = np.nanmean(points[index, [KP["left_shoulder"], KP["right_shoulder"]]], axis=0)
        hips = np.nanmean(points[index, [KP["left_hip"], KP["right_hip"]]], axis=0)
        if np.isfinite(shoulders).all() and np.isfinite(hips).all():
            trunk_angles.append(float(np.degrees(np.arctan2(abs(shoulders[0] - hips[0]), abs(hips[1] - shoulders[1]) + 1e-8))))

    timing_confidence = min(1.0, fps / 100.0) * usable_ratio
    angle_confidence = usable_ratio
    metrics = [
        MetricValue(key="SF", label="Step frequency", value=step_frequency, unit="Hz", confidence=timing_confidence, status="measured" if step_frequency is not None else "unavailable"),
        MetricValue(key="SL", label="Step length", value=None, unit="m", confidence=0.0, status="unavailable"),
        MetricValue(key="GCT", label="Ground contact", value=ground_contact, unit="s", confidence=timing_confidence, status="measured" if ground_contact is not None else "unavailable"),
        MetricValue(key="FT", label="Flight time", value=flight_time, unit="s", confidence=timing_confidence, status="measured" if flight_time is not None else "unavailable"),
        MetricValue(key="KNEE", label="Knee angle", value=float(np.mean(knee_angles)) if knee_angles else None, unit="deg", confidence=angle_confidence, status="measured" if knee_angles else "unavailable"),
        MetricValue(key="LEAN", label="Trunk lean", value=float(np.mean(trunk_angles)) if trunk_angles else None, unit="deg", confidence=angle_confidence, status="measured" if trunk_angles else "unavailable"),
    ]
    return {"frames_read": frame_number, "fps": fps, "usable_keypoint_ratio": usable_ratio, "body_visible_ratio": usable_ratio, "segment_speed_mps": None, "metrics": metrics, "track_id": track_id}
