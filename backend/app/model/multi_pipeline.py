"""One-pass, multi-runner pose inference for the federation trial.

The model sees the video once. Persistent pose tracks are ranked as runners,
ordered by their image-plane lane position, and paired with the coach's lane
roster. Metric values remain unavailable when the video cannot support them.
"""

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from ..config import settings
from ..schemas import MetricValue
from .pipeline import KP, REQUIRED, _angle, _contact_mask, _runs, load_model


@dataclass(frozen=True)
class LaneTrack:
    lane: int
    track_id: int
    observations: list[tuple[int, np.ndarray, np.ndarray]]
    score: float


def _track_score(observations: list[tuple[int, np.ndarray, np.ndarray]]) -> float:
    points = np.asarray([row[1] for row in observations], dtype=float)
    confidence = np.asarray([row[2] for row in observations], dtype=float)
    if len(points) < settings.minimum_track_frames:
        return 0.0
    required = [KP[name] for name in REQUIRED]
    quality = float((confidence[:, required] >= settings.keypoint_confidence).mean())
    hips = np.nanmean(points[:, [KP["left_hip"], KP["right_hip"]], 0], axis=1)
    progress = float(np.nanquantile(hips, .90) - np.nanquantile(hips, .10)) if np.isfinite(hips).any() else 0.0
    ankles = points[:, [KP["left_ankle"], KP["right_ankle"]], 1]
    ankle_motion = float(np.nanquantile(ankles, .90) - np.nanquantile(ankles, .10)) if np.isfinite(ankles).any() else 0.0
    return len(observations) * max(quality, .05) * (1.0 + min(abs(progress), 500.0) / 500.0) * (1.0 + min(ankle_motion, 200.0) / 200.0)


def _lane_position(observations: list[tuple[int, np.ndarray, np.ndarray]]) -> float:
    points = np.asarray([row[1] for row in observations], dtype=float)
    hips_y = np.nanmean(points[:, [KP["left_hip"], KP["right_hip"]], 1], axis=1)
    return float(np.nanmedian(hips_y))


def _metrics(observations: list[tuple[int, np.ndarray, np.ndarray]], fps: float,
             height_cm: float) -> tuple[list[MetricValue], list[MetricValue], float, int]:
    frame_index = np.asarray([row[0] for row in observations], dtype=int)
    points = np.asarray([row[1] for row in observations], dtype=float)
    confidence = np.asarray([row[2] for row in observations], dtype=float)
    reliable = confidence >= settings.keypoint_confidence
    points[~reliable] = np.nan
    required = [KP[name] for name in REQUIRED]
    usable_ratio = float(np.isfinite(points[:, required, 0]).mean())

    left_contact = _contact_mask(points[:, KP["left_ankle"], 1])
    right_contact = _contact_mask(points[:, KP["right_ankle"], 1])
    left_runs, right_runs = _runs(left_contact), _runs(right_contact)
    contact_runs = left_runs + right_runs
    contact_events = sorted(
        [(start, "left") for start, _ in left_runs]
        + [(start, "right") for start, _ in right_runs]
    )
    contact_starts = [start for start, _ in contact_events]
    duration = max((frame_index[-1] - frame_index[0]) / fps, 1 / fps)
    step_frequency = len(contact_starts) / duration if len(contact_starts) >= 2 else None
    ground_contact = float(np.mean([(end - start) / fps for start, end in contact_runs])) if contact_runs else None
    valid_flights = [
        (end - start) / fps for start, end in _runs(~left_contact & ~right_contact)
        if (end - start) / fps <= .30
    ]
    flight_time = float(np.mean(valid_flights)) if valid_flights else None

    knees: list[float] = []
    all_knees: list[float] = []
    trunks: list[float] = []
    for index in contact_starts:
        for side in ("left", "right"):
            value = _angle(
                points[index, KP[f"{side}_hip"]],
                points[index, KP[f"{side}_knee"]],
                points[index, KP[f"{side}_ankle"]],
            )
            if value is not None:
                knees.append(value)
        shoulders = np.nanmean(points[index, [KP["left_shoulder"], KP["right_shoulder"]]], axis=0)
        hips = np.nanmean(points[index, [KP["left_hip"], KP["right_hip"]]], axis=0)
        if np.isfinite(shoulders).all() and np.isfinite(hips).all():
            trunks.append(float(np.degrees(np.arctan2(abs(shoulders[0] - hips[0]), abs(hips[1] - shoulders[1]) + 1e-8))))

    for index in range(len(points)):
        for side in ("left", "right"):
            value = _angle(
                points[index, KP[f"{side}_hip"]],
                points[index, KP[f"{side}_knee"]],
                points[index, KP[f"{side}_ankle"]],
            )
            if value is not None:
                all_knees.append(value)

    step_intervals: dict[str, list[float]] = {"left": [], "right": []}
    for previous, current in zip(contact_events, contact_events[1:]):
        previous_index, previous_side = previous
        current_index, current_side = current
        interval = (frame_index[current_index] - frame_index[previous_index]) / fps
        if current_side != previous_side and .12 <= interval <= .80:
            step_intervals[current_side].append(float(interval))
    left_step = float(np.median(step_intervals["left"])) if step_intervals["left"] else None
    right_step = float(np.median(step_intervals["right"])) if step_intervals["right"] else None
    step_asymmetry = None
    if left_step is not None and right_step is not None and (left_step + right_step) > 0:
        step_asymmetry = abs(left_step - right_step) / ((left_step + right_step) / 2.0) * 100.0

    knee_at_contact = float(np.mean(knees)) if knees else None
    minimum_knee = float(np.mean(sorted(all_knees)[:3])) if len(all_knees) >= 3 else None
    knee_delta = max(0.0, knee_at_contact - minimum_knee) if knee_at_contact is not None and minimum_knee is not None else None
    height_m = height_cm / 100.0
    normalised_sf = step_frequency * np.sqrt(height_m / 9.81) if step_frequency is not None and height_m > 0 else None
    duty_factor = ground_contact * step_frequency if ground_contact is not None and step_frequency is not None else None
    contact_flight = ground_contact / flight_time if ground_contact is not None and flight_time is not None and flight_time > 0 else None

    timing_confidence = float(min(1.0, fps / 100.0) * usable_ratio)
    values = [
        ("SF", "Step frequency", step_frequency, "Hz", timing_confidence),
        ("SL", "Step length", None, "m", 0.0),
        ("GCT", "Ground contact", ground_contact, "s", timing_confidence),
        ("FT", "Flight time", flight_time, "s", timing_confidence),
        ("KNEE", "Knee angle", knee_at_contact, "deg", usable_ratio),
        ("LEAN", "Trunk lean", float(np.mean(trunks)) if trunks else None, "deg", usable_ratio),
    ]
    metrics = [
        MetricValue(key=key, label=label, value=value, unit=unit,
                    confidence=float(conf), status="measured" if value is not None else "unavailable")
        for key, label, value, unit, conf in values
    ]
    derived_values = [
        ("DUTY", "Duty factor", duty_factor, "ratio", timing_confidence),
        ("CFR", "Contact / flight", contact_flight, "ratio", timing_confidence),
        ("RSL", "Relative step length", None, "ratio", 0.0),
        ("NSF", "Normalised step frequency", float(normalised_sf) if normalised_sf is not None else None, "dimensionless", timing_confidence),
        ("FROUDE", "Froude number", None, "dimensionless", 0.0),
        ("KDELTA", "Knee delta", knee_delta, "deg", usable_ratio),
        ("ASYM", "Step asymmetry", step_asymmetry, "%", timing_confidence),
    ]
    derived = [
        MetricValue(key=key, label=label, value=value, unit=unit,
                    confidence=float(conf), status="measured" if value is not None else "unavailable")
        for key, label, value, unit, conf in derived_values
    ]
    return metrics, derived, usable_ratio, len(contact_events)


def analyse_race_video(video_path: Path, model_path: Path,
                       athlete_heights: dict[int, float]) -> tuple[dict[int, dict], list[int]]:
    lanes = list(athlete_heights)
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError("The uploaded video could not be decoded")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
    model = load_model(str(model_path))
    tracks: dict[int, list[tuple[int, np.ndarray, np.ndarray]]] = {}
    frame_number = 0

    while frame_number < settings.model_max_frames:
        ok, frame = capture.read()
        if not ok:
            break
        frame_number += 1
        result = model.track(frame, persist=True, tracker="bytetrack.yaml",
                             conf=settings.model_confidence, verbose=False)[0]
        if result.boxes is None or result.boxes.id is None or result.keypoints is None:
            continue
        ids = result.boxes.id.int().cpu().numpy()
        points = result.keypoints.xy.cpu().numpy()
        confidences = result.keypoints.conf.cpu().numpy() if result.keypoints.conf is not None else np.ones(points.shape[:2])
        for index, track_id in enumerate(ids):
            tracks.setdefault(int(track_id), []).append((frame_number, points[index], confidences[index]))
    capture.release()

    if frame_number == 0:
        raise ValueError("The uploaded video contains no readable frames")

    candidates = [
        (track_id, observations, _track_score(observations))
        for track_id, observations in tracks.items()
        if len(observations) >= settings.minimum_track_frames
    ]
    candidates = sorted(candidates, key=lambda row: row[2], reverse=True)[:len(lanes)]
    candidates = sorted(candidates, key=lambda row: _lane_position(row[1]), reverse=not settings.lane_order_top_to_bottom)
    ordered_lanes = sorted(lanes)

    outputs: dict[int, dict] = {}
    for lane, (track_id, observations, score) in zip(ordered_lanes, candidates):
        metrics, derived, usable_ratio, valid_steps = _metrics(
            observations, fps, athlete_heights[lane]
        )
        outputs[lane] = {
            "frames_read": frame_number,
            "fps": fps,
            "usable_keypoint_ratio": usable_ratio,
            "body_visible_ratio": usable_ratio,
            "segment_speed_mps": None,
            "metrics": metrics,
            "derived_metrics": derived,
            "valid_steps": valid_steps,
            "track_id": track_id,
            "track_score": score,
        }
    unmatched = [lane for lane in ordered_lanes if lane not in outputs]
    return outputs, unmatched
