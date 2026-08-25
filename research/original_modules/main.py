"""
WATHBA — main application.

    streamlit run app/main.py

Reads the AthleteKPIs contract. It cannot tell whether the data came from the
pose model or a fixture, which is exactly what allowed the interface to be
built before the model was finished.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "app"))

from wathba.contracts import (AthleteKPIs, CaptureQuality, EVENTS,      # noqa: E402
                              SUPPORTED_EVENTS, METRICS, label)
from wathba.domain import (Squad, Athlete, TIER_LADDER, STAGES,         # noqa: E402
                           VERDICT_STYLE, CONSTANT_PROVENANCE,
                           citations, coverage, BAND_VERSION)
from wathba.services import analyse, DISCLAIMERS                        # noqa: E402
from wathba.services.narrative import (TemplateNarrativeService,        # noqa: E402
                                       StaticExerciseService,
                                       NOT_RECOMMENDED)

import theme                                                            # noqa: E402
import components as C                                                  # noqa: E402
from demo_data import build_demo_squad                                  # noqa: E402

st.set_page_config(page_title="WATHBA · Sprint Biomechanics",
                   page_icon="◼", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown(theme.CSS, unsafe_allow_html=True)

NARRATIVE = TemplateNarrativeService()
EXERCISES = StaticExerciseService()


@st.cache_resource
def get_squad() -> Squad:
    return build_demo_squad(NARRATIVE, EXERCISES)


squad = get_squad()

# ═════════════════════════════════════════════════════════════════
#  Sidebar
# ═════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(theme.kicker("View"), unsafe_allow_html=True)
    view = st.radio("View", ["Coach · Squad", "Athlete", "Analyse a clip",
                             "Reference"],
                    label_visibility="collapsed")

    st.markdown(theme.kicker("Event"), unsafe_allow_html=True)
    event = st.selectbox(
        "Event", list(EVENTS), index=0,
        format_func=lambda e: (f"{EVENTS[e].label}"
                               + ("" if e in SUPPORTED_EVENTS else "  · planned")),
        label_visibility="collapsed")

    if event not in SUPPORTED_EVENTS:
        st.markdown(
            f'<div class="card soft"><h4>Not calibrated</h4>'
            f'<p>{EVENTS[event].blocker}</p></div>', unsafe_allow_html=True)

    selected_athlete = None
    if view == "Athlete":
        st.markdown(theme.kicker("Athlete"), unsafe_allow_html=True)
        names = [e.athlete.display_name for e in squad.entries]
        pick = st.selectbox("Athlete", names, label_visibility="collapsed")
        selected_athlete = squad.by_athlete(
            next(e.athlete.athlete_id for e in squad.entries
                 if e.athlete.display_name == pick))

    st.markdown(theme.kicker("Recording guide"), unsafe_allow_html=True)
    st.markdown(
        '<p class="sub">Fixed camera, perpendicular to the lane.<br>'
        '60 fps if available, normal speed.<br>'
        'Whole body in frame, four steps minimum.<br>'
        'One runner only.</p>', unsafe_allow_html=True)


st.markdown(theme.masthead(), unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════
#  Coach · squad
# ═════════════════════════════════════════════════════════════════
def render_coach():
    summary = squad.squad_summary()

    cols = st.columns(5)
    cols[0].markdown(theme.stat(str(summary["n_analysed"]), "athletes analysed",
                                theme.TRACK, theme.TRACK), unsafe_allow_html=True)
    cols[1].markdown(theme.stat(f'{summary["speed_mean"]:.2f}', "squad mean m/s"),
                     unsafe_allow_html=True)
    cols[2].markdown(theme.stat(f'{summary["spread_s"]:.2f}', "spread, seconds"),
                     unsafe_allow_html=True)
    n_tiers = len(summary["tier_distribution"])
    cols[3].markdown(theme.stat(str(n_tiers), "tiers represented"),
                     unsafe_allow_html=True)
    shared = summary.get("shared_priority")
    cols[4].markdown(
        theme.stat(str(summary["shared_priority_count"]), "share a top priority",
                   theme.GOLD, theme.GOLD), unsafe_allow_html=True)

    st.markdown(theme.kicker("Lane board"), unsafe_allow_html=True)
    st.markdown(C.lane_board(squad), unsafe_allow_html=True)

    left, right = st.columns([1.1, 1])

    with left:
        st.markdown(theme.kicker("Group sessions"), unsafe_allow_html=True)
        sessions = squad.group_sessions()
        if not sessions:
            st.markdown(
                '<div class="card soft"><h4>No shared priorities</h4>'
                '<p>Every athlete in this squad has a different limiter. '
                'Individual sessions are the right call.</p></div>',
                unsafe_allow_html=True)
        for s in sessions[:3]:
            st.markdown(C.group_session_card(s, label(s["metric"])),
                        unsafe_allow_html=True)

    with right:
        st.markdown(theme.kicker("Ranking"), unsafe_allow_html=True)
        rows = "".join(
            theme.row(
                f'{i}. {e.athlete.display_name}',
                f'{e.speed:.2f} m/s · {e.equivalent_time:.2f}s',
                theme.TIER_COLOR.get(e.tier_key, theme.INK3))
            for i, e in enumerate(squad.ranked(), 1))
        st.markdown(f'<div class="card">{rows}</div>', unsafe_allow_html=True)

        dist = "".join(
            theme.row(tier, str(n),
                      theme.TIER_COLOR.get(tier.lower().replace(" ", "_"),
                                           theme.INK3))
            for tier, n in summary["tier_distribution"].items())
        st.markdown(
            f'<div class="card soft"><h4>Tier distribution</h4>{dist}'
            f'<p class="note" style="margin-top:7px">A squad spanning several '
            f'tiers needs differentiated work, not one session for everyone.'
            f'</p></div>', unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════
#  Athlete
# ═════════════════════════════════════════════════════════════════
def render_athlete(entry):
    report = entry.report

    if report.status == "declined":
        st.markdown(theme.kicker("Analysis declined"), unsafe_allow_html=True)
        a, b = st.columns([1.15, 1])
        a.markdown(C.refusal_panel(report), unsafe_allow_html=True)
        with b:
            st.markdown('<div class="card acc"><h4>How to fix it</h4></div>',
                        unsafe_allow_html=True)
            for i, fix in enumerate(report.fixes, 1):
                st.markdown(
                    f'<div class="card soft"><p><b class="mono" '
                    f'style="color:{theme.TRACK}">{i:02d}</b> &nbsp;{fix}</p>'
                    f'</div>', unsafe_allow_html=True)
        return

    if report.status == "unsupported_event":
        st.markdown(C.unsupported_panel(report, EVENTS[report.event]),
                    unsafe_allow_html=True)
        return

    tier, gaps, prog = report.tier, report.gaps, report.progression
    k = report.kpis

    cols = st.columns([1.5, 1, 1, 1, 1])
    cols[0].markdown(
        theme.stat(entry.athlete.display_name,
                   f"lane {entry.lane} · {EVENTS[report.event].label}",
                   theme.TRACK, theme.TRACK), unsafe_allow_html=True)
    cols[1].markdown(theme.stat(f"{k.speed:.2f}", "m/s"), unsafe_allow_html=True)
    cols[2].markdown(theme.stat(f"{tier.equivalent_time_s:.2f}",
                                "equivalent 100 m<br>simulation"),
                     unsafe_allow_html=True)
    cols[3].markdown(theme.stat(str(k.quality.n_steps), "steps detected"),
                     unsafe_allow_html=True)
    cols[4].markdown(
        theme.stat(f"{k.quality.fps:.0f}",
                   f"fps · ±{k.quality.timing_error_ms:.0f} ms"),
        unsafe_allow_html=True)

    t1, t2, t3, t4, t5 = st.tabs(
        ["  Position  ", "  Gaps  ", "  Path  ", "  Plan  ", "  Confidence  "])

    # ── position ──
    with t1:
        st.markdown(C.tier_rail(tier, STAGES[report.event],
                                TIER_LADDER[report.event]),
                    unsafe_allow_html=True)
        a, b = st.columns([1, 1])
        a.markdown(
            f'<div class="card acc"><h4>{tier.label} tier</h4>'
            f'<p>{tier.position_pct:.0f} percent through this band '
            f'({tier.band_low:.1f} – {tier.band_high:.1f} m/s). '
            f'{tier.remaining_pct:.0f} percent of it is still ahead — progress '
            f'inside a tier is still progress.</p>'
            f'<p class="note" style="margin-top:7px">Boundary basis: '
            f'{tier.basis}.</p></div>', unsafe_allow_html=True)
        if report.narrative:
            b.markdown(
                f'<div class="card"><h4>Summary</h4>'
                f'<p>{report.narrative.split(chr(10)+chr(10))[0]}</p></div>',
                unsafe_allow_html=True)

    # ── gaps ──
    with t2:
        left, right = st.columns([1.25, 1])
        with left:
            st.markdown(theme.kicker("Measured against reference band"),
                        unsafe_allow_html=True)
            for g in gaps.flagged + gaps.in_band:
                st.markdown(C.band_row(g), unsafe_allow_html=True)
            st.markdown(
                '<p class="note" style="margin-top:9px">The shaded region is the '
                'elite operating band. Sitting inside it is not a deficiency — '
                'Bolt ran 2.70 m steps and Su ran 2.26 m in the same final.</p>',
                unsafe_allow_html=True)

        with right:
            st.markdown(theme.kicker("Ranked priorities"), unsafe_allow_html=True)
            if not gaps.flagged:
                st.markdown(
                    f'<div class="card lane"><h4>No gaps at this reference level'
                    f'</h4><p>All {len(gaps.in_band)} measurable indicators sit '
                    f'inside their band. The limiter is more likely force '
                    f'production or race execution than the mechanics visible '
                    f'in this clip.</p></div>', unsafe_allow_html=True)
            for g in gaps.flagged:
                st.markdown(C.priority_card(g, g.rank), unsafe_allow_html=True)

            if gaps.unavailable:
                rows = "".join(
                    theme.row(g.label,
                              "not measured" if g.status == "missing" else "excluded")
                    for g in gaps.unavailable)
                st.markdown(
                    f'<div class="card soft"><h4>Not ranked</h4>{rows}'
                    f'<p class="note" style="margin-top:7px">Not measured, or not '
                    f'measured reliably enough to rank. No value was inferred to '
                    f'fill the gap.</p></div>', unsafe_allow_html=True)

    # ── path ──
    with t3:
        st.markdown(theme.kicker("The three anchors"), unsafe_allow_html=True)
        cols = st.columns(3)
        for col, stage in zip(cols, prog.stages):
            col.markdown(C.stage_card(stage, VERDICT_STYLE),
                         unsafe_allow_html=True)

        if prog.milestone:
            m = prog.milestone
            st.markdown(theme.kicker("Twelve-month target"), unsafe_allow_html=True)
            a, b = st.columns([1, 1.3])
            a.markdown(
                f'<div class="card gold">'
                f'<div class="delta"><span class="f">{tier.equivalent_time_s:.2f} s'
                f'</span><span style="color:{theme.INK3}">→</span>'
                f'<span class="t">{m["target_time_s"]:.2f} s</span>'
                f'<span class="g">−{m["time_gain_s"]:.2f}</span></div>'
                + theme.row("Step frequency", f'+{m["sf_change_pct"]:.1f}%', theme.LANE)
                + theme.row("Step length", f'+{m["sl_change_pct"]:.1f}%', theme.LANE)
                + f'<p class="note" style="margin-top:7px">{m["basis"]}.</p></div>',
                unsafe_allow_html=True)
            b.markdown(
                '<div class="card"><h4>Solved, not guessed</h4>'
                '<p><span class="mono">v = SL × SF</span> is an identity, so the '
                'required change is solved directly rather than estimated. The '
                'split between the two follows the 67/33 development ratio, '
                'stated in the IAAF report and independently reproduced from raw '
                'athlete progressions.</p>'
                '<p class="note" style="margin-top:7px">Targets needing more than '
                'five years are shown as reference points, never as goals with a '
                'plan attached.</p></div>', unsafe_allow_html=True)

    # ── plan ──
    with t4:
        if not report.exercises:
            st.markdown(
                '<div class="card soft"><h4>No prescription</h4>'
                '<p>No metric is outside its band with sufficient confidence to '
                'justify a training change.</p></div>', unsafe_allow_html=True)
        else:
            st.markdown(theme.kicker("Proposed plan · coach approval required"),
                        unsafe_allow_html=True)
            cols = st.columns(2)
            for i, ex in enumerate(report.exercises[:6]):
                cols[i % 2].markdown(
                    f'<div class="card">'
                    f'<div style="display:flex;justify-content:space-between;'
                    f'align-items:baseline;margin-bottom:3px">'
                    f'<span class="mono" style="font-size:9px;color:{theme.TRACK}">'
                    f'{i+1:02d}</span>'
                    f'<span class="chip r" style="font-size:8px">'
                    f'{label(ex.target_metric)}</span></div>'
                    f'<h4>{ex.name}</h4>'
                    f'<p>{ex.prescription} · {ex.frequency} · {ex.weeks} weeks</p>'
                    f'<p class="note" style="margin-top:5px">{ex.rationale}</p>'
                    f'</div>', unsafe_allow_html=True)

        st.markdown(theme.kicker("Never prescribed"), unsafe_allow_html=True)
        cols = st.columns(3)
        for col, (key, reason) in zip(cols, NOT_RECOMMENDED.items()):
            col.markdown(
                f'<div class="card soft"><h4 style="color:{theme.TRACK}">'
                f'{key.replace("_", " ").title()}</h4>'
                f'<p>{reason}</p></div>', unsafe_allow_html=True)

    # ── confidence ──
    with t5:
        left, right = st.columns([1.1, 1])
        with left:
            st.markdown(theme.kicker("Confidence per metric"), unsafe_allow_html=True)
            rows = "".join(
                f'<div class="row"><span>{g.label}</span><span>'
                f'{theme.pips(g.reliability or 0)}'
                f'<span class="st" style="color:{theme.INK3};margin-left:8px">'
                f'{g.confidence}</span></span></div>'
                for g in gaps.gaps)
            st.markdown(f'<div class="card">{rows}</div>', unsafe_allow_html=True)

        with right:
            st.markdown(theme.kicker("Capture quality"), unsafe_allow_html=True)
            q = k.quality
            items = [
                ("Frame rate", f"{q.fps:.0f} fps",
                 f"timing resolution ±{q.timing_error_ms:.0f} ms"),
                ("Camera angle", f"{q.camera_yaw_deg:.0f}°",
                 "side-on is best; beyond 40° distances and angles degrade"),
                ("Scale reference", "yes" if q.step_length_calibrated else "no",
                 q.calibration_method or "not supplied"),
                ("Steps detected", str(q.n_steps),
                 "more steps give a stabler median"),
            ]
            body = "".join(
                f'<div class="row"><span>{n}<br><span class="note">{note}</span>'
                f'</span><span class="st">{v}</span></div>'
                for n, v, note in items)
            st.markdown(f'<div class="card">{body}</div>', unsafe_allow_html=True)

        st.markdown(theme.kicker("What this analysis does not claim"),
                    unsafe_allow_html=True)
        cols = st.columns(len(DISCLAIMERS[:3]))
        for col, d in zip(cols, DISCLAIMERS[:3]):
            col.markdown(f'<div class="card soft"><p>{d}</p></div>',
                         unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════
#  Analyse a clip
# ═════════════════════════════════════════════════════════════════
def render_upload():
    st.markdown(theme.kicker("Analyse a clip"), unsafe_allow_html=True)

    left, right = st.columns([1, 1.2])
    with left:
        st.file_uploader("Sprint clip", type=["mp4", "mov", "avi"])
        c1, c2 = st.columns(2)
        c1.text_input("Athlete", "New athlete")
        c2.number_input("Height (m)", 1.40, 2.20, 1.78, 0.01)
        c1.selectbox("Event", sorted(SUPPORTED_EVENTS))
        c2.selectbox("Phase", ["max_velocity", "acceleration"])
        st.button("Run analysis", use_container_width=True)
        st.markdown(
            '<p class="note">The pose model is being trained by the team. The '
            'pipeline is wired and contract-tested; connect the service and '
            'this button becomes live without any other change.</p>',
            unsafe_allow_html=True)

    with right:
        st.markdown(theme.kicker("What happens to the clip"), unsafe_allow_html=True)
        steps = [
            ("Gate checks", "Six checks run before any measurement. A clip that "
                            "fails a hard gate is refused with instructions."),
            ("Pose estimation", "33 landmarks per frame, in metric 3D relative "
                                "to the hip centre."),
            ("Strike detection", "Foot strikes are the minima of foot height. "
                                 "Everything downstream depends on this."),
            ("KPI extraction", "Seven measured indicators, then nine "
                               "dimensionless ones that compare fairly across "
                               "body sizes."),
            ("Band comparison", "Each metric against its reference band, gated "
                                "by evidence, reliability and trainability."),
            ("Path and verdict", "The required change is solved from "
                                 "v = SL × SF, then checked for feasibility."),
        ]
        for i, (t, d) in enumerate(steps, 1):
            st.markdown(
                f'<div class="card soft" style="margin-bottom:8px">'
                f'<div style="display:flex;gap:10px">'
                f'<span class="mono" style="font-size:10px;color:{theme.TRACK}">'
                f'{i:02d}</span><div><h4>{t}</h4><p>{d}</p></div></div></div>',
                unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════
#  Reference
# ═════════════════════════════════════════════════════════════════
def render_reference():
    st.markdown(theme.kicker("Reference bands and sources"), unsafe_allow_html=True)

    left, right = st.columns([1.2, 1])

    with left:
        for source, metrics in citations("100m", "max_velocity").items():
            chips = "".join(f'<span class="chip o">{label(m)}</span>'
                            for m in metrics)
            st.markdown(
                f'<div class="card"><h4>{source}</h4>'
                f'<div style="margin-top:7px">{chips}</div></div>',
                unsafe_allow_html=True)

        st.markdown(theme.kicker("Event coverage"), unsafe_allow_html=True)
        rows = "".join(
            theme.row(
                f'{EVENTS[c].label} · {EVENTS[c].phases[0] if EVENTS[c].phases else ""}',
                "CALIBRATED" if c in SUPPORTED_EVENTS else "PLANNED",
                theme.LANE if c in SUPPORTED_EVENTS else theme.INK3)
            for c in EVENTS)
        st.markdown(
            f'<div class="card">{rows}'
            f'<p class="note" style="margin-top:8px">A missing band is a refusal, '
            f'never a fallback. Borrowing the 100 m band for a 400 m athlete '
            f'would rate a world-class runner as underdeveloped.</p></div>',
            unsafe_allow_html=True)

    with right:
        st.markdown(theme.kicker("Constants and provenance"), unsafe_allow_html=True)
        for name, prov in CONSTANT_PROVENANCE.items():
            tone = ("lane" if prov["status"].startswith("measured")
                    else "gold" if "part" in prov["status"] else "soft")
            caveat = prov.get("caveat", "")
            st.markdown(
                f'<div class="card {tone}"><h4>{name}</h4>'
                f'<p class="mono" style="font-size:10.5px">{prov["value"]}</p>'
                f'<p class="note" style="margin-top:5px">{prov["derived_from"]}</p>'
                f'<p class="note" style="margin-top:3px">'
                f'<b>{prov["status"]}</b>'
                + (f' — {caveat}' if caveat else '')
                + '</p></div>', unsafe_allow_html=True)

    st.markdown(theme.kicker("What this platform does not claim"),
                unsafe_allow_html=True)
    cols = st.columns(len(DISCLAIMERS))
    for col, d in zip(cols, DISCLAIMERS):
        col.markdown(f'<div class="card soft"><p>{d}</p></div>',
                     unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════
#  Router
# ═════════════════════════════════════════════════════════════════
if view == "Coach · Squad":
    render_coach()
elif view == "Athlete" and selected_athlete:
    render_athlete(selected_athlete)
elif view == "Analyse a clip":
    render_upload()
else:
    render_reference()

st.markdown(
    f'<div style="margin-top:40px;padding-top:13px;border-top:1px solid '
    f'{theme.LINE};font-family:\'JetBrains Mono\',monospace;font-size:8.5px;'
    f'letter-spacing:1.5px;color:{theme.INK3};text-transform:uppercase">'
    f'WATHBA · band version {BAND_VERSION} · Bissas et al. IAAF London 2017 · '
    f'Graubner &amp; Nixdorf 2011 · AthleticsPose CC BY-NC-SA 4.0</div>',
    unsafe_allow_html=True)
