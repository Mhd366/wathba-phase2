"""
Parses the actual WATHBA computer-vision output: running_summary.csv

This file contains one row per detected runner (track_id) in a video,
already in correct units (seconds, degrees, Hz) — no unit conversion
needed. It also includes built-in data-quality flags that must be
respected: a row marked "review / reject timing" should not be treated
as a confident measurement.
"""

import io
import pandas as pd


def parse_running_summary_csv(csv_bytes: bytes, track_id=None) -> dict:
    """
    Args:
        csv_bytes: raw bytes of the uploaded running_summary.csv.
        track_id: which runner to extract (matches the CSV's track_id
            column). If None, picks the first row flagged "usable";
            falls back to the first row overall if none are usable.

    Returns:
        dict shaped for llm.py's generate_answer(athlete_data=...),
        including an optional "data_quality_note" the prompt should
        surface as a caveat rather than a confident fact.
    """
    df = pd.read_csv(io.BytesIO(csv_bytes))

    if df.empty:
        raise ValueError("CSV file is empty")

    if track_id is not None:
        matches = df[df["track_id"] == int(track_id)]
        if matches.empty:
            raise ValueError(f"No runner found with track_id={track_id}")
        row = matches.iloc[0]
    else:
        usable = df[df["biomechanics_quality"] == "usable"]
        row = usable.iloc[0] if not usable.empty else df.iloc[0]

    # --- Data quality caveat (file-level + row-level) ---
    quality_notes = []

    fps = row.get("video_fps")
    if fps is not None and fps < 30:
        quality_notes.append(
            f"Video recorded at {fps:.0f} FPS — contact/flight timing values "
            "are estimates, not precise lab-grade measurements."
        )

    if row.get("biomechanics_quality") != "usable":
        reasons = row.get("quality_rejection_reasons", "unspecified")
        quality_notes.append(
            f"This runner's data is flagged '{row.get('biomechanics_quality')}' "
            f"(reasons: {reasons}). Treat these measurements as low-confidence."
        )

    # --- Core metrics (already in correct units — no conversion needed) ---
    metrics = {
        "stride_frequency_hz": round(float(row["stride_frequency_hz"]), 3),
        "step_frequency_hz": round(float(row["step_frequency_hz"]), 3),
        "cadence_steps_per_min": round(float(row["cadence_steps_per_min"]), 1),
        "ground_contact_time_s": round(float(row["gct_s"]), 4),
        "flight_time_s": round(float(row["ft_s"]), 4),
        "duty_factor": round(float(row["duty_factor"]), 3),
        "knee_angle_at_initial_contact_deg": round(float(row["knee_angle_at_initial_contact_deg"]), 1),
        "minimum_knee_angle_deg": round(float(row["minimum_knee_angle_deg"]), 1),
        "trunk_lean_at_initial_contact_deg": round(float(row["trunk_lean_at_initial_contact_deg"]), 1),
        "detected_strides": int(row["detected_strides"]),
    }

    return {
        "athlete_name": f"Runner (track_id {int(row['track_id'])})",
        "clip_id": f"track_{int(row['track_id'])}",
        "phase": "N/A",  # not present in this CSV — set manually if known
        "metrics": metrics,
        "data_quality_note": " ".join(quality_notes) if quality_notes else None,
    }


def list_available_runners(csv_bytes: bytes) -> list:
    """
    Utility for the frontend: returns a quick summary of every runner in
    the file so the user can pick which track_id to analyze.
    """
    df = pd.read_csv(io.BytesIO(csv_bytes))
    return [
        {
            "track_id": int(row["track_id"]),
            "quality": row["biomechanics_quality"],
            "detected_strides": int(row["detected_strides"]),
        }
        for _, row in df.iterrows()
]
