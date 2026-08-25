"""
Reference band registry.

Every band is keyed by (event, phase, metric). A missing band is a hard
refusal, never a fallback to another event: borrowing the 100 m band for a
400 m athlete would rate a world-class runner as underdeveloped.

Every band carries its source citation. A coach must be able to trace any
number the system shows back to a published report.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import csv

from ..contracts.events import require_supported
from ..contracts.metrics import METRICS

BAND_VERSION = "2017-london-v1"


@dataclass(frozen=True)
class Band:
    event: str
    phase: str
    metric: str
    low: float
    high: float
    mean: float | None
    direction: str            # higher | lower | band
    evidence: float           # strength of the reference, 0-1
    tier: str                 # which population the band describes
    source: str               # citation a coach can check
    note: str = ""

    @property
    def width(self) -> float:
        return max(self.high - self.low, 1e-9)

    def contains(self, value: float) -> bool:
        return self.low <= value <= self.high

    def to_dict(self) -> dict:
        return asdict(self)


LONDON = "Bissas et al. (2018), IAAF Biomechanical Report, Men's 100 m, London 2017"
ATHPOSE = "AthleticsPose sprint clips, 8-camera motion capture (CC BY-NC-SA 4.0)"
BERLIN = "Graubner & Nixdorf (2011), New Studies in Athletics 26(1/2):19-53"


def _b(metric, low, high, mean, direction, evidence, tier, source, note=""):
    return Band("100m", "max_velocity", metric, low, high, mean,
                direction, evidence, tier, source, note)


# ═════════════════════════════════════════════════════════════════
#  100 m · maximum velocity
# ═════════════════════════════════════════════════════════════════
_MAX_VELOCITY_100M = [
    # ── world-class bands, measured per athlete (n=8) ──
    _b("norm_step_length", 1.30, 1.38, 1.334, "higher", 0.90, "world_class", LONDON,
       "Height-normalised. Raw step length never ranks athletes of different "
       "heights — height correlates with step length at r = 0.976."),
    _b("norm_step_freq", 1.857, 2.122, 2.062, "band", 0.90, "world_class", LONDON,
       "Pendulum-scaled. Read jointly with step length, never maximised alone."),
    _b("step_frequency", 4.39, 5.00, 4.799, "band", 0.90, "world_class", LONDON,
       "Bolt held the LOWEST step rate in this final and finished third. "
       "Frequency alone does not rank athletes."),
    _b("knee_angle_strike", 147.7, 167.1, 156.6, "band", 0.75, "world_class", LONDON,
       "Projected from video; confidence falls sharply off-axis."),
    _b("knee_angle_min", 128.2, 146.0, 139.0, "higher", 0.75, "world_class", LONDON,
       "A higher minimum means better maintenance through stance. Medallists "
       "held their knee angle better than the rest of the field."),
    _b("knee_delta", 8.6, 25.2, 17.0, "lower", 0.70, "world_class", LONDON,
       "Knee collapse under load. A strength indicator, not mobility."),
    _b("trunk_lean", 2.9, 17.5, 9.9, "band", 0.65, "world_class", LONDON,
       "Converted from the report's horizontal convention via abs(90 - angle). "
       "Comparing conventions directly would create a phantom 60-degree gap."),

    # ── published range, not a per-athlete distribution ──
    _b("ground_contact_time", 0.084, 0.104, 0.094, "lower", 0.75,
       "world_class_range", LONDON,
       "The report states this range explicitly. It is not a reconstructed "
       "distribution, so no standard deviation is available."),

    # ── metrics only the motion-capture reference provides ──
    _b("duty_factor", 0.547, 0.620, 0.581, "lower", 0.80, "trained", ATHPOSE,
       "Internal step ratio. Does not scale with running speed the way step "
       "length does, so no speed matching is required."),
    _b("contact_flight_ratio", 1.200, 1.630, 1.370, "lower", 0.80, "trained", ATHPOSE,
       "Described in the literature as the key determinant of step structure."),
    _b("flight_time", 0.079, 0.110, 0.095, "band", 0.70, "trained", ATHPOSE,
       "Not chased independently of speed."),
    _b("asym_step_time", 1.0, 6.0, 3.1, "lower", 0.60, "trained", ATHPOSE,
       "Descriptive in the 100 m. Becomes diagnostic on curved events."),
]

# ═════════════════════════════════════════════════════════════════
#  100 m · acceleration — a different mechanical regime
# ═════════════════════════════════════════════════════════════════
_ACCELERATION_100M = [
    Band("100m", "acceleration", "step_frequency", 3.60, 4.60, 3.89,
         "band", 0.70, "record", BERLIN,
         "Bolt's 0-20 m phase. Acceleration mechanics differ fundamentally "
         "from maximum velocity — the two are never mixed."),
    Band("100m", "acceleration", "step_length", 1.55, 2.10, 1.78,
         "higher", 0.70, "record", BERLIN,
         "Step length grows with distance travelled during acceleration."),
    Band("100m", "acceleration", "ground_contact_time", 0.100, 0.160, 0.130,
         "lower", 0.60, "trained", ATHPOSE,
         "Longer ground contact is expected and correct during acceleration."),
]

_REGISTRY: dict[tuple[str, str], dict[str, Band]] = {}
for band in _MAX_VELOCITY_100M + _ACCELERATION_100M:
    _REGISTRY.setdefault((band.event, band.phase), {})[band.metric] = band


class NoBandsAvailable(Exception):
    """Raised when no calibrated bands exist for an event/phase combination."""


def get_bands(event: str = "100m", phase: str = "max_velocity") -> dict[str, Band]:
    """
    Bands for one event and phase.

    Refuses rather than substituting. Silent fallback to another event's band
    is the single most dangerous failure mode this system could have.
    """
    require_supported(event)
    bands = _REGISTRY.get((event, phase))
    if not bands:
        raise NoBandsAvailable(
            f"No reference bands calibrated for {event} / {phase}. "
            f"Available: {sorted(set(_REGISTRY))}"
        )
    return bands


def get_band(metric: str, event: str = "100m",
             phase: str = "max_velocity") -> Band | None:
    return get_bands(event, phase).get(metric)


def citations(event: str = "100m", phase: str = "max_velocity") -> dict[str, list[str]]:
    """Every source backing this event, grouped. For the reference page."""
    out: dict[str, list[str]] = {}
    for band in get_bands(event, phase).values():
        out.setdefault(band.source, []).append(band.metric)
    return out


def coverage() -> list[dict]:
    """Which event/phase combinations are calibrated, and how completely."""
    rows = []
    for (event, phase), bands in sorted(_REGISTRY.items()):
        rows.append({
            "event": event, "phase": phase,
            "metrics": len(bands),
            "band_version": BAND_VERSION,
            "sources": sorted({b.source.split(",")[0] for b in bands.values()}),
        })
    return rows


def export_csv(path: str | Path) -> None:
    """Write the registry out. Federation review needs an auditable artefact."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "event", "phase", "metric", "low", "high", "mean", "direction",
            "evidence", "tier", "source", "note", "band_version"])
        w.writeheader()
        for bands in _REGISTRY.values():
            for b in bands.values():
                row = b.to_dict()
                row["band_version"] = BAND_VERSION
                w.writerow(row)


def validate_registry() -> list[str]:
    """Structural problems. Empty means the registry is sound."""
    problems = []
    for (event, phase), bands in _REGISTRY.items():
        for metric, b in bands.items():
            if metric not in METRICS:
                problems.append(f"{event}/{phase}: unknown metric '{metric}'")
            if b.low >= b.high:
                problems.append(f"{event}/{phase}/{metric}: low >= high")
            if not (0 < b.evidence <= 1):
                problems.append(f"{event}/{phase}/{metric}: evidence out of range")
            if b.mean is not None and not (b.low <= b.mean <= b.high):
                problems.append(f"{event}/{phase}/{metric}: mean outside band")
            if not b.source:
                problems.append(f"{event}/{phase}/{metric}: missing citation")
    return problems
