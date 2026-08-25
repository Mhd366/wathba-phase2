"""
Contract tests — the safety net.

These encode the guarantees the whole system rests on. If any of them fails,
a number somewhere in the interface is lying to a coach.

    pytest
"""

from __future__ import annotations
import math
import pytest

from wathba.contracts import AthleteKPIs, CaptureQuality, EVENTS, SUPPORTED_EVENTS
from wathba.contracts.events import UnsupportedEvent, require_supported
from wathba.domain import (classify, solve_path, feasibility, build_progression,
                           analyse_gaps, get_bands, validate_registry,
                           TIER_LADDER, STAGES, VERDICT_STYLE, Squad, Athlete)
from wathba.domain.bands import NoBandsAvailable
from wathba.services import analyse


def make_kpis(**over) -> AthleteKPIs:
    base = dict(
        athlete_id="TEST", event="100m", phase="max_velocity", height_m=1.80,
        step_frequency=4.50, step_length=1.95,
        ground_contact_time=0.128, flight_time=0.094,
        knee_angle_strike=152.0, knee_angle_min=136.0, trunk_lean=11.0,
        source="mediapipe_video",
    )
    quality = dict(fps=60, camera_yaw_deg=10, n_steps=8,
                   step_length_calibrated=True)
    quality.update(over.pop("quality", {}))
    base.update(over)
    return AthleteKPIs(quality=CaptureQuality(**quality), **base).derive()


# ═════════════════════════════════════════════════════════════════
#  Physical identities — if these break, the path solver is meaningless
# ═════════════════════════════════════════════════════════════════
def test_speed_is_the_product_of_length_and_frequency():
    k = make_kpis(step_length=1.95, step_frequency=4.50)
    assert k.speed == pytest.approx(1.95 * 4.50, rel=1e-12)


def test_solved_path_hits_its_target_exactly():
    for target in (9.0, 10.5, 11.584, 12.215):
        p = solve_path(1.88, 4.32, target)
        assert p["check_speed"] == pytest.approx(target, rel=1e-9)


def test_path_to_an_already_achieved_target_requires_no_change():
    p = solve_path(2.10, 5.00, 8.0)
    assert p["achieved"] is True
    assert p["sf_change_pct"] == 0.0 and p["sl_change_pct"] == 0.0


def test_duty_factor_and_contact_flight_ratio_are_consistent():
    k = make_kpis(ground_contact_time=0.120, flight_time=0.080)
    assert k.derived["duty_factor"] == pytest.approx(0.120 / 0.200)
    assert k.derived["contact_flight_ratio"] == pytest.approx(0.120 / 0.080)


# ═════════════════════════════════════════════════════════════════
#  No band borrowing across events — the most dangerous failure mode
# ═════════════════════════════════════════════════════════════════
def test_unsupported_event_raises_rather_than_falling_back():
    for code in ("200m", "400m"):
        with pytest.raises(UnsupportedEvent):
            require_supported(code)


def test_unsupported_event_returns_a_refusal_not_a_report():
    k = make_kpis(event="400m")
    r = analyse(k)
    assert r.status == "unsupported_event"
    assert r.gaps is None and r.tier is None
    assert r.message


def test_missing_phase_bands_refuse():
    with pytest.raises(NoBandsAvailable):
        get_bands("100m", "curve")


def test_every_supported_event_has_bands():
    for code in SUPPORTED_EVENTS:
        for phase in EVENTS[code].phases:
            try:
                assert get_bands(code, phase)
            except NoBandsAvailable:
                pytest.fail(f"{code}/{phase} declared supported but has no bands")


# ═════════════════════════════════════════════════════════════════
#  Nothing is ever invented
# ═════════════════════════════════════════════════════════════════
def test_uncalibrated_step_length_is_excluded_not_estimated():
    k = make_kpis(step_length=None,
                  quality={"step_length_calibrated": False})
    r = analyse_gaps(k)
    sl = r.by_metric("norm_step_length")
    assert sl.status in {"missing", "excluded"}
    assert sl.priority_score is None
    assert sl.metric not in [g.metric for g in r.flagged]


def test_missing_metrics_are_never_scored():
    k = make_kpis(knee_angle_strike=None, knee_angle_min=None)
    r = analyse_gaps(k)
    for g in r.gaps:
        if g.status == "missing":
            assert g.priority_score is None
            assert g.value is None


def test_metrics_inside_their_band_score_zero():
    k = make_kpis()
    r = analyse_gaps(k)
    for g in r.in_band:
        assert (g.priority_score or 0) == 0


# ═════════════════════════════════════════════════════════════════
#  Feasibility honesty
# ═════════════════════════════════════════════════════════════════
def test_unreachable_targets_carry_no_training_plan():
    k = make_kpis(step_frequency=4.0, step_length=1.70)
    prog = build_progression(k)
    for stage in prog.stages:
        if stage.verdict == "reference_only":
            assert stage.show_training_plan is False


def test_both_adjusted_and_elite_rate_are_reported():
    k = make_kpis(step_frequency=4.32, step_length=1.88)
    prog = build_progression(k)
    for stage in prog.stages:
        if stage.years_estimated is not None:
            assert stage.years_at_elite_rate is not None
            assert stage.rate_basis
            # the adjustment must never make a target look harder than reality
            assert stage.years_estimated <= stage.years_at_elite_rate + 1e-9


def test_developing_athletes_are_not_held_to_the_elite_rate():
    dev = feasibility(6.0, 3.0, tier="developing")
    elite = feasibility(6.0, 3.0, tier="world_class")
    assert dev["years"] < elite["years"]
    assert dev["multiplier"] > elite["multiplier"]


# ═════════════════════════════════════════════════════════════════
#  Three-stage progression
# ═════════════════════════════════════════════════════════════════
def test_progression_has_exactly_three_ordered_stages():
    prog = build_progression(make_kpis())
    assert len(prog.stages) == 3
    assert [s.order for s in prog.stages] == [1, 2, 3]
    assert [s.stage for s in prog.stages] == [
        "trained", "world_class", "record"]


def test_cleared_stages_are_marked_and_next_stage_is_the_first_open_one():
    fast = make_kpis(step_frequency=4.80, step_length=1.95)   # ~9.36 m/s
    prog = build_progression(fast)
    assert prog.stages[0].is_cleared is True
    assert prog.next_stage.stage == "world_class"


def test_time_gap_is_always_reported_alongside_the_percentage():
    prog = build_progression(make_kpis())
    for stage in prog.stages:
        assert stage.time_gap_s is not None
        assert 0 <= stage.achievement_pct <= 100


# ═════════════════════════════════════════════════════════════════
#  Tier classification
# ═════════════════════════════════════════════════════════════════
def test_classification_reports_position_not_just_a_label():
    t = classify(9.0)
    assert t.tier == "trained"
    assert 0 <= t.position_pct <= 100
    assert t.position_pct + t.remaining_pct == pytest.approx(100.0)


def test_tier_boundaries_are_contiguous_and_labelled():
    for event, ladder in TIER_LADDER.items():
        for a, b in zip(ladder, ladder[1:]):
            assert a.high == b.low, f"{event}: gap between {a.key} and {b.key}"
        for band in ladder:
            assert band.basis in {"measured", "interpolated"}


def test_speed_above_the_ladder_is_flagged_as_extrapolated():
    t = classify(14.0)
    assert t.basis == "extrapolated"


# ═════════════════════════════════════════════════════════════════
#  Refusals
# ═════════════════════════════════════════════════════════════════
def test_declined_clips_produce_fixes_not_numbers():
    k = AthleteKPIs(athlete_id="X", status="declined",
                    fixes=["Use a fixed camera."],
                    message="Cannot measure.")
    r = analyse(k)
    assert r.status == "declined"
    assert r.fixes and r.gaps is None and r.tier is None


def test_too_few_steps_is_surfaced_as_a_problem():
    k = make_kpis(quality={"n_steps": 3})
    assert any("steps" in p for p in k.validate())


def test_implausible_step_frequency_is_surfaced():
    assert any("double detection" in p for p in make_kpis(step_frequency=8.5).validate())
    assert any("slow-motion" in p for p in make_kpis(step_frequency=1.2).validate())


# ═════════════════════════════════════════════════════════════════
#  Reference registry integrity
# ═════════════════════════════════════════════════════════════════
def test_band_registry_is_structurally_sound():
    assert validate_registry() == []


def test_every_band_carries_a_citation():
    for phase in ("max_velocity", "acceleration"):
        for band in get_bands("100m", phase).values():
            assert band.source, f"{band.metric} has no citation"


# ═════════════════════════════════════════════════════════════════
#  Squad
# ═════════════════════════════════════════════════════════════════
def test_lanes_are_unique_and_bounded():
    sq = Squad("S", "Test", "100m")
    sq.assign(Athlete("A", "A"), 1)
    with pytest.raises(ValueError):
        sq.assign(Athlete("B", "B"), 1)
    with pytest.raises(ValueError):
        sq.assign(Athlete("C", "C"), 9)


def test_squad_survives_athletes_without_a_speed():
    sq = Squad("S", "Test", "100m")
    sq.assign(Athlete("A", "A", height_m=1.8), 1, analyse(make_kpis()))
    no_scale = make_kpis(step_length=None,
                         quality={"step_length_calibrated": False})
    sq.assign(Athlete("B", "B", height_m=1.8), 2, analyse(no_scale))
    s = sq.squad_summary()
    assert s["n_analysed"] == 2
    assert s["speed_mean"] is not None


# ═════════════════════════════════════════════════════════════════
#  Serialisation
# ═════════════════════════════════════════════════════════════════
def test_report_round_trips_to_json():
    import json
    r = analyse(make_kpis())
    payload = json.dumps(r.to_dict(), default=str)
    assert len(payload) > 500
    back = json.loads(payload)
    assert back["status"] == "ok"
    assert back["citations"]
    assert back["disclaimers"]


def test_kpis_round_trip_through_the_flat_notebook_shape():
    flat = {
        "athlete_id": "NB", "event": "100m", "phase": "max_velocity",
        "height_m": 1.80, "step_frequency": 4.5, "step_length": 1.95,
        "ground_contact_time": 0.128, "flight_time": 0.094,
        "n_steps": 8, "fps": 60.0, "step_length_calibrated": True,
        "source": "mediapipe_video",
    }
    k = AthleteKPIs.from_dict(flat)
    assert k.quality.n_steps == 8
    assert k.quality.fps == 60.0
    assert k.speed == pytest.approx(4.5 * 1.95)
