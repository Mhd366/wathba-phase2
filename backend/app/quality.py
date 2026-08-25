from .schemas import CaptureQuality, QualityWarning

def evaluate_capture(*, frames_read: int, fps: float | None,
                     usable_keypoint_ratio: float, camera_yaw_deg: float | None = None,
                     body_visible_ratio: float | None = None) -> CaptureQuality:
    """Tolerant intake: degrade confidence before rejecting the whole clip."""
    warnings: list[QualityWarning] = []
    if frames_read <= 0:
        warnings.append(QualityWarning(code="unreadable_video", severity="fatal", message="No readable video frames were found.", fix="Re-export the clip as MP4/H.264."))
    if fps is None:
        warnings.append(QualityWarning(code="fps_unknown", message="Frame rate could not be confirmed.", fix="Keep the original video metadata."))
    elif fps < 30:
        warnings.append(QualityWarning(code="low_fps", message="Timing precision is reduced below 30 fps.", fix="Use 60 fps when available."))
    if usable_keypoint_ratio < .55:
        warnings.append(QualityWarning(code="sparse_keypoints", message="Some frames have incomplete keypoints.", fix="Keep the full body visible and reduce occlusion."))
    if camera_yaw_deg is not None and camera_yaw_deg > 40:
        warnings.append(QualityWarning(code="camera_angle", message="The view is far from side-on; projected angles have lower confidence.", fix="Record perpendicular to the lane when possible."))
    if body_visible_ratio is not None and body_visible_ratio < .65:
        warnings.append(QualityWarning(code="partial_body", message="The full body is not visible in part of the clip.", fix="Increase camera distance."))

    penalty = sum(.18 if w.severity == "warning" else 0 for w in warnings)
    score = max(.15, min(1.0, usable_keypoint_ratio - penalty))
    accepted = not any(w.severity == "fatal" for w in warnings)
    return CaptureQuality(score=round(score, 3), fps=fps, frames_read=frames_read,
                          usable_keypoint_ratio=usable_keypoint_ratio,
                          accepted=accepted, warnings=warnings)

