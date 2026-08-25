"""
Gap scoring and priority ranking.

Three multipliers gate every score, so a confident recommendation can only
come from a metric that is well referenced, well measured, and trainable:

    priority = min(severity, 3) x evidence x reliability x trainability x 100

A metric that fails any one of those is not ranked. It is shown as
unavailable rather than silently filled with a guess.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict, field

from ..contracts.athlete_kpis import AthleteKPIs, finite
from ..contracts.metrics import METRICS, label
from .bands import Band, get_bands

SEVERITY_CAP = 3.0


# ═════════════════════════════════════════════════════════════════
#  Measurement reliability — how much we trust THIS measurement
# ═════════════════════════════════════════════════════════════════
def measurement_reliability(metric: str, kpis: AthleteKPIs) -> tuple[float, str]:
    """Returns (score 0-1, a reason a coach can read)."""
    q = kpis.quality
    is_mocap = "mocap" in kpis.source or "athleticspose" in kpis.source

    if metric in {"step_length", "norm_step_length", "norm_speed", "froude_number"}:
        if not q.step_length_calibrated:
            return 0.0, "No scale reference supplied — excluded from ranking."
        if finite(q.camera_yaw_deg) and q.camera_yaw_deg > 40:
            return 0.45, (f"Camera {q.camera_yaw_deg:.0f}° off-axis degrades "
                          f"distance measurement.")
        if is_mocap:
            return 0.90, "Motion capture."
        return 0.75, "Scaled from stature on a near side-on view."

    if metric in {"knee_angle_strike", "knee_angle_min", "knee_delta", "trunk_lean"}:
        if is_mocap:
            return 0.90, "Motion capture."
        if finite(q.camera_yaw_deg) and q.camera_yaw_deg > 40:
            return 0.35, (f"Projected angle at {q.camera_yaw_deg:.0f}° is "
                          f"unreliable.")
        return 0.65, "Projected angle from a single camera."

    if metric in {"ground_contact_time", "flight_time",
                  "duty_factor", "contact_flight_ratio"}:
        if finite(q.fps):
            err = 1000.0 / q.fps
            if q.fps < 30:
                return 0.40, f"{q.fps:.0f} fps — timing error near ±{err:.0f} ms."
            if q.fps < 60:
                return 0.70, f"{q.fps:.0f} fps — timing error near ±{err:.0f} ms."
            return 0.90, f"{q.fps:.0f} fps — timing error near ±{err:.0f} ms."
        return 0.75, "Frame rate unknown."

    # step count stabilises any median
    if finite(q.n_steps) and q.n_steps < 6:
        return 0.75, f"Only {q.n_steps} steps — median is less stable."
    return 0.90, "Derived from strike timing."


def confidence_label(score: float) -> str:
    if score >= 0.85:
        return "high"
    if score >= 0.60:
        return "medium"
    if score > 0:
        return "low"
    return "excluded"


# ═════════════════════════════════════════════════════════════════
#  Band evaluation
# ═════════════════════════════════════════════════════════════════
def evaluate(value: float, band: Band) -> tuple[str, float, float]:
    """
    Returns (status, severity in band widths, the boundary that was missed).

    Note the asymmetry: for a 'higher is better' metric, exceeding the band is
    not a problem. Bolt exceeded the field's relative step length and it was a
    strength, not a deviation to correct.
    """
    w = band.width
    if band.direction == "higher":
        if value < band.low:
            return "below", (band.low - value) / w, band.low
        return ("within" if value <= band.high else "above_band"), 0.0, band.low

    if band.direction == "lower":
        if value > band.high:
            return "above", (value - band.high) / w, band.high
        return ("within" if value >= band.low else "below_band"), 0.0, band.high

    if value < band.low:
        return "below", (band.low - value) / w, band.low
    if value > band.high:
        return "above", (value - band.high) / w, band.high
    return "within", 0.0, (band.low + band.high) / 2


# ═════════════════════════════════════════════════════════════════
#  Results
# ═════════════════════════════════════════════════════════════════
@dataclass
class MetricGap:
    metric: str
    label: str
    value: float | None
    unit: str

    band_low: float | None = None
    band_high: float | None = None
    band_mean: float | None = None
    band_tier: str | None = None
    band_source: str | None = None
    band_note: str = ""
    direction: str | None = None

    status: str = "missing"          # within | below | above | missing | excluded
    severity: float | None = None
    gap_pct: float | None = None
    priority_score: float | None = None

    evidence: float | None = None
    reliability: float | None = None
    reliability_reason: str = ""
    confidence: str = "excluded"
    trainability: float | None = None
    rank: int | None = None

    @property
    def is_flagged(self) -> bool:
        return self.status in {"below", "above"}

    @property
    def in_band(self) -> bool:
        return self.status in {"within", "above_band", "below_band"}

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GapReport:
    athlete_id: str
    event: str
    phase: str
    gaps: list[MetricGap] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def flagged(self) -> list[MetricGap]:
        return [g for g in self.gaps if g.is_flagged and g.priority_score]

    @property
    def in_band(self) -> list[MetricGap]:
        return [g for g in self.gaps if g.in_band]

    @property
    def unavailable(self) -> list[MetricGap]:
        return [g for g in self.gaps if g.status in {"missing", "excluded"}]

    @property
    def top_priority(self) -> MetricGap | None:
        return self.flagged[0] if self.flagged else None

    def by_metric(self, metric: str) -> MetricGap | None:
        return next((g for g in self.gaps if g.metric == metric), None)

    def to_dict(self) -> dict:
        return {
            "athlete_id": self.athlete_id,
            "event": self.event,
            "phase": self.phase,
            "gaps": [g.to_dict() for g in self.gaps],
            "problems": self.problems,
            "summary": {
                "flagged": len(self.flagged),
                "in_band": len(self.in_band),
                "unavailable": len(self.unavailable),
            },
        }


# ═════════════════════════════════════════════════════════════════
#  Entry point
# ═════════════════════════════════════════════════════════════════
def analyse_gaps(kpis: AthleteKPIs, event: str | None = None,
                 phase: str | None = None) -> GapReport:
    """Score every metric against its band and rank what is actionable."""
    event = event or kpis.event
    phase = phase or kpis.phase
    bands = get_bands(event, phase)

    report = GapReport(athlete_id=kpis.athlete_id, event=event, phase=phase,
                       problems=kpis.validate())

    for metric, band in bands.items():
        spec = METRICS.get(metric)
        gap = MetricGap(
            metric=metric,
            label=label(metric),
            value=None,
            unit=spec.unit if spec else "",
            band_low=band.low, band_high=band.high, band_mean=band.mean,
            band_tier=band.tier, band_source=band.source, band_note=band.note,
            direction=band.direction, evidence=band.evidence,
            trainability=spec.trainability if spec else 0.5,
        )

        value = kpis.get(metric)
        if not finite(value):
            gap.status = "missing"
            gap.reliability = 0.0
            gap.reliability_reason = "Not measured in this clip."
            report.gaps.append(gap)
            continue

        gap.value = float(value)
        reliability, reason = measurement_reliability(metric, kpis)
        gap.reliability = reliability
        gap.reliability_reason = reason
        gap.confidence = confidence_label(reliability)

        if reliability == 0.0:
            gap.status = "excluded"
            report.gaps.append(gap)
            continue

        status, severity, boundary = evaluate(gap.value, band)
        gap.status = status
        gap.severity = round(severity, 3)
        if boundary:
            gap.gap_pct = round((gap.value - boundary) / boundary * 100, 1)

        gap.priority_score = round(
            min(severity, SEVERITY_CAP) * band.evidence * reliability
            * (spec.trainability if spec else 0.5) * 100, 1)

        report.gaps.append(gap)

    # rank the actionable ones
    report.gaps.sort(
        key=lambda g: (g.priority_score is None, -(g.priority_score or 0)))
    for i, g in enumerate(report.flagged, 1):
        g.rank = i

    return report
