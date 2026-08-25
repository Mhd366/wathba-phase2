"""
Tier ladder and the three-stage progression.

The three stages are the spine of the athlete's story:

    TRAINED  ──▶  WORLD_CLASS  ──▶  RECORD
    (mocap)       (London 2017)     (Bolt, Berlin 2009)
     n=8           n=8               n=1

Each stage carries its own distance, its own solved path, and its own honest
verdict on whether it is reachable. Only reachable stages carry a plan.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict, field

from ..contracts.events import EVENTS, require_supported


# ═════════════════════════════════════════════════════════════════
#  Constants — derived in notebook 03, provenance carried here
# ═════════════════════════════════════════════════════════════════
ACCEL_FACTOR = 0.8598          # race-average / max velocity, London 2017 n=8
ACCEL_FACTOR_SD = 0.0052

DEV_WEIGHTS = {"step_frequency": 0.67, "step_length": 0.33}
ANNUAL_FEASIBLE_PCT = {"step_frequency": 0.62, "step_length": 0.25}

FEASIBILITY_YEARS = {"realistic": 2.0, "ambitious": 5.0}

# Development rates above were measured on MATURE ELITE athletes moving from a
# U20 personal best to a lifetime peak. A developing athlete improves far
# faster: the same 5% frequency gain that takes a world-class sprinter most of
# a career is a normal season for someone early in development.
#
# These multipliers are ASSUMED, not measured — we hold no developing-athlete
# progression dataset. They are declared here, carried in CONSTANT_PROVENANCE,
# and both the adjusted and the raw elite figure are shown to the user so the
# assumption is never hidden behind a single confident number.
TIER_DEVELOPMENT_MULTIPLIER = {
    "developing":  4.0,
    "trained":     2.5,
    "national":    1.5,
    "world_class": 1.0,     # the measured elite rate
    "record":      1.0,
    "above_record": 1.0,
}

CONSTANT_PROVENANCE = {
    "ACCEL_FACTOR": {
        "value": ACCEL_FACTOR,
        "sd": ACCEL_FACTOR_SD,
        "derived_from": "London 2017 finalists: (100/race_time) / cm_velocity",
        "n": 8,
        "status": "measured",
    },
    "DEV_WEIGHTS": {
        "value": DEV_WEIGHTS,
        "derived_from": "IAAF London 2017 report; independently reproduced from "
                        "raw U20-to-PB progressions in notebook 02b",
        "status": "measured and replicated",
    },
    "ANNUAL_FEASIBLE_PCT": {
        "value": ANNUAL_FEASIBLE_PCT,
        "derived_from": "median U20-to-PB gain / assumed five-year window",
        "status": "part-measured, part-assumed",
        "caveat": "The development window is assumed, not measured. It is the "
                  "largest single source of uncertainty in the feasibility "
                  "verdict; a sensitivity analysis is run in notebook 03.",
    },
    "TIER_DEVELOPMENT_MULTIPLIER": {
        "value": TIER_DEVELOPMENT_MULTIPLIER,
        "derived_from": "Not derived. Coaching-practice estimate of how much "
                        "faster a developing athlete improves than a mature "
                        "elite one.",
        "status": "assumed",
        "caveat": "No developing-athlete progression dataset exists in this "
                  "project. Every feasibility verdict therefore reports both "
                  "the tier-adjusted estimate and the raw elite-rate figure, "
                  "so the reader can see exactly what the assumption bought.",
    },
}


# ═════════════════════════════════════════════════════════════════
#  Ladder
# ═════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class TierBand:
    key: str
    label: str
    label_ar: str
    low: float
    high: float
    basis: str                 # "measured" | "interpolated"


TIER_LADDER: dict[str, tuple[TierBand, ...]] = {
    "100m": (
        TierBand("developing",  "Developing",  "قيد التطوير", 0.0,  8.2,  "interpolated"),
        TierBand("trained",     "Trained",     "مدرَّب",       8.2,  9.8,  "measured"),
        TierBand("national",    "National",    "وطني",        9.8,  10.9, "interpolated"),
        TierBand("world_class", "World class", "نخبة عالمية",  10.9, 11.9, "measured"),
        TierBand("record",      "Record",      "قياسي",       11.9, 12.6, "measured"),
    ),
}


@dataclass(frozen=True)
class Stage:
    """One of the three measured anchors."""
    key: str
    label: str
    label_ar: str
    speed: float
    step_frequency: float
    step_length: float
    rel_step_length: float
    source: str
    n: int
    order: int


STAGES: dict[str, tuple[Stage, ...]] = {
    "100m": (
        Stage("trained", "Trained", "المدرَّبون",
              speed=8.819, step_frequency=4.4672, step_length=1.9742,
              rel_step_length=1.163,
              source="AthleticsPose sprint clips, motion capture", n=8, order=1),
        Stage("world_class", "World class", "النخبة العالمية",
              speed=11.584, step_frequency=4.799, step_length=2.424,
              rel_step_length=1.334,
              source="IAAF London 2017 men's 100 m final", n=8, order=2),
        Stage("record", "Record", "الرقم القياسي",
              speed=12.215, step_frequency=4.490, step_length=2.720,
              rel_step_length=1.395,
              source="Bolt, Berlin 2009, max-velocity phases", n=1, order=3),
    ),
}


# ═════════════════════════════════════════════════════════════════
#  Results
# ═════════════════════════════════════════════════════════════════
@dataclass
class TierPosition:
    tier: str
    label: str
    label_ar: str
    band_low: float
    band_high: float | None
    position_pct: float
    remaining_pct: float
    basis: str
    speed: float
    equivalent_time_s: float | None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class StageProgress:
    """Distance to one anchor, plus the solved path and its verdict."""
    stage: str
    label: str
    label_ar: str
    source: str
    n: int
    order: int

    athlete_speed: float
    target_speed: float
    achievement_pct: float          # speed ratio — compresses differences
    speed_gap_ms: float
    time_now_s: float
    time_target_s: float
    time_gap_s: float               # the number the interface leads with

    sf_now: float | None = None
    sf_target: float | None = None
    sf_change_pct: float | None = None
    sl_now: float | None = None
    sl_target: float | None = None
    sl_change_pct: float | None = None

    years_estimated: float | None = None
    years_at_elite_rate: float | None = None
    rate_basis: str | None = None
    verdict: str = "unknown"
    show_training_plan: bool = False
    is_current_stage: bool = False
    is_cleared: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProgressionLadder:
    """The full three-stage story, in order."""
    stages: list[StageProgress] = field(default_factory=list)
    current_stage_index: int = 0
    next_stage: StageProgress | None = None
    milestone: dict | None = None

    def to_dict(self) -> dict:
        return {
            "stages": [s.to_dict() for s in self.stages],
            "current_stage_index": self.current_stage_index,
            "next_stage": self.next_stage.to_dict() if self.next_stage else None,
            "milestone": self.milestone,
        }


# ═════════════════════════════════════════════════════════════════
#  Functions
# ═════════════════════════════════════════════════════════════════
def equivalent_time(speed: float | None, event: str = "100m",
                    accel_factor: float = ACCEL_FACTOR) -> float | None:
    """
    Max-velocity speed to an equivalent race time.

    A SIMULATION, not a prediction. Maximum velocity is not average race
    velocity — the athlete accelerates from rest and decelerates at the end.
    """
    if not speed or speed <= 0:
        return None
    distance = EVENTS[event].distance_m if event in EVENTS else 100.0
    return distance / (speed * accel_factor)


def classify(speed: float | None, event: str = "100m") -> TierPosition | None:
    """Position on the ladder — a location, not just a label."""
    if not speed or speed <= 0 or event not in TIER_LADDER:
        return None

    for band in TIER_LADDER[event]:
        if band.low <= speed < band.high:
            pos = (speed - band.low) / (band.high - band.low) * 100
            return TierPosition(
                tier=band.key, label=band.label, label_ar=band.label_ar,
                band_low=band.low, band_high=band.high,
                position_pct=round(pos, 1), remaining_pct=round(100 - pos, 1),
                basis=band.basis, speed=round(speed, 3),
                equivalent_time_s=round(equivalent_time(speed, event) or 0, 2),
            )

    last = TIER_LADDER[event][-1]
    return TierPosition(
        tier="above_record", label="Above calibrated range",
        label_ar="فوق النطاق المعاير",
        band_low=last.high, band_high=None,
        position_pct=100.0, remaining_pct=0.0, basis="extrapolated",
        speed=round(speed, 3),
        equivalent_time_s=round(equivalent_time(speed, event) or 0, 2),
    )


def solve_path(step_length: float, step_frequency: float,
               target_speed: float, weights: dict | None = None) -> dict:
    """
    v = SL × SF is an identity, so the required change is solved, not guessed.

    The split between the two follows the 67/33 development ratio, which is
    stated in the IAAF report and was independently reproduced.
    """
    w = weights or DEV_WEIGHTS
    current = step_length * step_frequency

    if target_speed <= current:
        return {"sf_target": step_frequency, "sl_target": step_length,
                "sf_change_pct": 0.0, "sl_change_pct": 0.0,
                "check_speed": current, "achieved": True}

    growth = target_speed / current
    sf_t = step_frequency * growth ** w["step_frequency"]
    sl_t = step_length * growth ** w["step_length"]

    return {
        "sf_target": sf_t, "sl_target": sl_t,
        "sf_change_pct": (sf_t / step_frequency - 1) * 100,
        "sl_change_pct": (sl_t / step_length - 1) * 100,
        "check_speed": sf_t * sl_t,      # equals target_speed by construction
        "achieved": False,
    }


def feasibility(sf_change_pct: float, sl_change_pct: float,
                tier: str = "trained",
                annual: dict | None = None) -> dict:
    """
    Years required to reach a target, and the resulting verdict.

    Returns BOTH figures deliberately:
      years            tier-adjusted, the number the plan is built on
      years_elite_rate raw measured elite rate, for transparency

    A developing athlete is not held to a world-class sprinter's rate of
    improvement. Doing so would mark the very next stage unreachable, which
    is both demoralising and wrong.
    """
    a = annual or ANNUAL_FEASIBLE_PCT
    mult = TIER_DEVELOPMENT_MULTIPLIER.get(tier, 1.0)

    if sf_change_pct <= 0 and sl_change_pct <= 0:
        return {"years": 0.0, "years_elite_rate": 0.0, "verdict": "achieved",
                "multiplier": mult, "rate_basis": "already cleared"}

    elite_years = max(sf_change_pct / a["step_frequency"],
                      sl_change_pct / a["step_length"])
    years = elite_years / mult

    if years <= FEASIBILITY_YEARS["realistic"]:
        verdict = "realistic"
    elif years <= FEASIBILITY_YEARS["ambitious"]:
        verdict = "ambitious"
    else:
        verdict = "reference_only"

    return {
        "years": years,
        "years_elite_rate": elite_years,
        "verdict": verdict,
        "multiplier": mult,
        "rate_basis": (f"{tier} development rate, {mult:.1f}x the measured "
                       f"elite rate (assumed multiplier)"),
    }


VERDICT_STYLE = {
    "achieved":       {"label": "CLEARED",        "tone": "ok",   "plan": True},
    "realistic":      {"label": "REALISTIC",      "tone": "ok",   "plan": True},
    "ambitious":      {"label": "AMBITIOUS",      "tone": "warn", "plan": True},
    "reference_only": {"label": "REFERENCE ONLY", "tone": "mute", "plan": False},
    "unknown":        {"label": "UNKNOWN",        "tone": "mute", "plan": False},
}


def build_progression(kpis, event: str = "100m") -> ProgressionLadder:
    """
    The three-stage ladder for one athlete.

    Stages the athlete has already passed are marked cleared. The first stage
    still ahead is the next target, and it is the only one the interface
    foregrounds with a plan.
    """
    require_supported(event)

    speed = kpis.speed
    sl, sf = kpis.step_length, kpis.step_frequency
    if not speed:
        return ProgressionLadder()

    t_now = equivalent_time(speed, event) or 0.0
    position = classify(speed, event)
    tier_key = position.tier if position else "trained"

    ladder = ProgressionLadder()
    current_index = 0

    for stage in STAGES.get(event, ()):
        t_target = equivalent_time(stage.speed, event) or 0.0
        cleared = speed >= stage.speed

        sp = StageProgress(
            stage=stage.key, label=stage.label, label_ar=stage.label_ar,
            source=stage.source, n=stage.n, order=stage.order,
            athlete_speed=round(speed, 3),
            target_speed=round(stage.speed, 3),
            achievement_pct=round(min(speed / stage.speed * 100, 100.0), 1),
            speed_gap_ms=round(max(stage.speed - speed, 0.0), 3),
            time_now_s=round(t_now, 2),
            time_target_s=round(t_target, 2),
            time_gap_s=round(max(t_now - t_target, 0.0), 2),
            is_cleared=cleared,
        )

        if sl and sf:
            p = solve_path(sl, sf, stage.speed)
            f = feasibility(p["sf_change_pct"], p["sl_change_pct"], tier=tier_key)
            sp.sf_now = round(sf, 3)
            sp.sf_target = round(p["sf_target"], 3)
            sp.sf_change_pct = round(p["sf_change_pct"], 1)
            sp.sl_now = round(sl, 3)
            sp.sl_target = round(p["sl_target"], 3)
            sp.sl_change_pct = round(p["sl_change_pct"], 1)
            sp.years_estimated = round(f["years"], 1)
            sp.years_at_elite_rate = round(f["years_elite_rate"], 1)
            sp.rate_basis = f["rate_basis"]
            sp.verdict = f["verdict"]
            sp.show_training_plan = VERDICT_STYLE[f["verdict"]]["plan"]

        if cleared:
            current_index = stage.order
        ladder.stages.append(sp)

    ladder.current_stage_index = current_index
    ladder.next_stage = next((s for s in ladder.stages if not s.is_cleared), None)
    if ladder.next_stage:
        ladder.next_stage.is_current_stage = True

    # ── the 12-month milestone: the only target that always carries a plan ──
    if sl and sf:
        mult = TIER_DEVELOPMENT_MULTIPLIER.get(tier_key, 1.0)
        annual_growth = ((1 + ANNUAL_FEASIBLE_PCT["step_frequency"] * mult / 100)
                         * (1 + ANNUAL_FEASIBLE_PCT["step_length"] * mult / 100) - 1)
        ms_speed = speed * (1 + annual_growth)
        p = solve_path(sl, sf, ms_speed)
        ms_time = equivalent_time(ms_speed, event) or 0.0
        ladder.milestone = {
            "horizon": "12 months",
            "target_speed": round(ms_speed, 3),
            "target_time_s": round(ms_time, 2),
            "time_gain_s": round(t_now - ms_time, 2),
            "sf_change_pct": round(p["sf_change_pct"], 1),
            "sl_change_pct": round(p["sl_change_pct"], 1),
            "basis": (f"median observed annual progression, compounded, "
                      f"scaled {mult:.1f}x for the {tier_key} tier"),
            "multiplier": mult,
        }

    return ladder
