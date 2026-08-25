"""
UI components — pure functions returning HTML fragments.

Kept free of Streamlit calls so they can be tested, reused, and eventually
ported to a React frontend without rewriting the visual logic.
"""

from __future__ import annotations

from theme import (INK, INK3, TRACK, LANE, GOLD, SAND, LINE2, PAPER,
                   TIER_COLOR, STATUS_COLOR, CONFIDENCE_COLOR, pips, row)


# ═════════════════════════════════════════════════════════════════
#  Lane board — the signature coach screen
# ═════════════════════════════════════════════════════════════════
def lane_board(squad, ladder_max: float = 12.6) -> str:
    """Eight lanes, read at a glance, in the coach's own mental model."""
    summary = squad.squad_summary()

    head = (
        f'<div class="board-hd">'
        f'<span class="t">{squad.name}</span>'
        f'<span class="chip" style="background:transparent;border-color:#6A6355;'
        f'color:#C4BBA6">{squad.event}</span>'
        f'<span class="m">{summary["n_analysed"]}/{summary["n_athletes"]} ANALYSED'
        + (f' &nbsp;·&nbsp; SPREAD {summary["spread_s"]:.2f}s'
           if summary.get("spread_s") else "")
        + "</span></div>")

    rows = []
    for entry in squad.entries:
        color = TIER_COLOR.get(entry.tier_key, LINE2)

        # An athlete can be "ok" and still have no speed: without a scale
        # reference, step length is refused rather than guessed, so the whole
        # speed chain is unavailable. That is a correct outcome, not a bug,
        # and the board must render it as such.
        if entry.status != "ok" or entry.speed is None:
            if entry.status == "declined":
                pill, pill_bg = "DECLINED", TRACK
                note = "Clip refused — see the athlete view"
            elif entry.status == "unsupported_event":
                pill, pill_bg = "NOT CALIBRATED", LINE2
                note = "Event has no reference bands yet"
            elif entry.speed is None:
                pill, pill_bg = "NO SCALE", LINE2
                note = "Timing metrics only — no scale reference"
            else:
                pill, pill_bg = "PENDING", LINE2
                note = "Awaiting a clip"

            partial = ""
            if entry.status == "ok" and entry.report and entry.report.gaps:
                n = len(entry.report.gaps.flagged)
                partial = f"{n} flagged from timing metrics"

            rows.append(
                f'<div class="lane-row">'
                f'<div class="lane-no">{entry.lane}</div>'
                f'<div class="lane-name">{entry.athlete.display_name}'
                f'<small>{note}</small></div>'
                f'<div class="lane-num" style="color:{INK3}">—<small>M/S</small></div>'
                f'<div class="lane-num" style="color:{INK3}">—<small>EQ 100M</small></div>'
                f'<div><span class="tier-pill" style="background:{pill_bg}">'
                f'{pill}</span></div>'
                f'<div class="prio" style="color:{INK3}">'
                f'{entry.top_priority or "—"}<small>{partial}</small></div>'
                f'<div></div></div>')
            continue

        pos = (entry.speed or 0) / ladder_max * 100
        conf = entry.top_priority_confidence or "medium"

        rows.append(
            f'<div class="lane-row">'
            f'<div class="lane-no">{entry.lane}</div>'

            f'<div class="lane-name">{entry.athlete.display_name}'
            f'<small>{entry.athlete.height_m:.2f} m</small></div>'

            f'<div class="lane-num">{entry.speed:.2f}'
            f'<small>M/S</small></div>'

            f'<div class="lane-num">{entry.equivalent_time:.2f}'
            f'<small>EQ 100M</small></div>'

            f'<div><span class="tier-pill" style="background:{color}">'
            f'{entry.tier_label.upper()}</span>'
            f'<div class="mini-rail">'
            f'<div class="mini-fill" style="width:{min(pos,100):.1f}%;'
            f'background:{color}"></div></div></div>'

            f'<div class="prio">{entry.top_priority or "In band"}'
            f'<small>{entry.n_flagged} flagged · {conf} confidence</small></div>'

            f'<div style="text-align:right">'
            f'<span class="chip o" style="font-size:8px">'
            f'{(entry.next_stage or "—").upper()}</span></div>'
            f"</div>")

    return f'<div class="board">{head}{"".join(rows)}</div>'


# ═════════════════════════════════════════════════════════════════
#  Tier rail
# ═════════════════════════════════════════════════════════════════
def tier_rail(tier, stages, ladder) -> str:
    """The athlete's position, with the three anchors as ghost flags."""
    if not tier:
        return ""

    vmax = ladder[-1].high
    segs, labels = "", ""
    for band in ladder:
        left = band.low / vmax * 100
        width = (band.high - band.low) / vmax * 100
        cls = "seg meas" if band.basis == "measured" else "seg"
        segs += f'<div class="{cls}" style="left:{left}%;width:{width}%"></div>'
        labels += (f'<div class="lbl" style="left:{left + width/2}%">'
                   f'<b>{band.label}</b>{band.low:.1f} – {band.high:.1f}</div>')

    ghosts = ""
    for stage in stages:
        if abs(stage.speed - tier.speed) > 0.2:
            ghosts += (
                f'<div class="gh" style="left:{stage.speed/vmax*100:.1f}%">'
                f'<div class="flag">{stage.label.lower()} {stage.speed:.1f}</div>'
                f'<div class="stem"></div></div>')

    you = tier.speed / vmax * 100
    return (
        f'<div class="rail-wrap"><div class="rail">{segs}{labels}{ghosts}'
        f'<div class="you" style="left:{you:.1f}%">'
        f'<div class="flag">YOU · {tier.speed:.2f} m/s</div>'
        f'<div class="stem"></div></div></div></div>')


# ═════════════════════════════════════════════════════════════════
#  Metric band row
# ═════════════════════════════════════════════════════════════════
def band_row(gap) -> str:
    """One metric against its band. The shaded region is elite operating range."""
    if gap.value is None or gap.band_low is None:
        return ""

    lo, hi, val = gap.band_low, gap.band_high, gap.value
    span = max(hi - lo, 1e-9)
    pad = span * 0.7
    axis_lo, axis_hi = lo - pad, hi + pad

    def pct(x):
        return max(2.0, min(98.0, (x - axis_lo) / (axis_hi - axis_lo) * 100))

    color = STATUS_COLOR.get(gap.status, INK3)
    dim = ' <span class="note">·</span>' if gap.metric.startswith("norm_") else ""

    return (
        f'<div class="mrow"><div class="mtop">'
        f'<span>{gap.label}{dim}</span>'
        f'<span class="v" style="color:{color}">{val:.3g} {gap.unit}</span>'
        f'</div>'
        f'<div class="mtrk">'
        f'<div class="mband" style="left:{pct(lo):.1f}%;'
        f'width:{pct(hi)-pct(lo):.1f}%"></div>'
        f'<div class="mdot" style="left:{pct(val):.1f}%;background:{color}"></div>'
        f'</div>'
        f'<div class="note" style="margin-top:2px">band {lo:.3g} – {hi:.3g} · '
        f'{(gap.band_tier or "").replace("_"," ")}</div></div>')


# ═════════════════════════════════════════════════════════════════
#  Priority card
# ═════════════════════════════════════════════════════════════════
def priority_card(gap, rank: int) -> str:
    tone = "acc" if rank == 1 else ""
    conf_color = CONFIDENCE_COLOR.get(gap.confidence, INK3)
    direction = "Below" if gap.status == "below" else "Above"

    return (
        f'<div class="card {tone}">'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:baseline;margin-bottom:4px">'
        f'<span class="mono" style="font-size:9px;color:{TRACK};letter-spacing:1.2px">'
        f'PRIORITY {rank:02d}</span>'
        f'<span class="mono" style="font-size:9px;color:{INK3}">'
        f'score {gap.priority_score:.0f}</span></div>'
        f'<h4>{gap.label}</h4>'
        f'<p>{gap.value:.3g} {gap.unit} against a band of {gap.band_low:.3g} – '
        f'{gap.band_high:.3g}. {direction} by {gap.severity:.1f} band widths.</p>'
        f'<p class="note" style="margin-top:6px">{pips(gap.reliability)} '
        f'&nbsp;<span style="color:{conf_color}">{gap.confidence}</span> confidence — '
        f'{gap.reliability_reason.lower()}</p>'
        f'<p class="note" style="margin-top:4px;opacity:.75">{gap.band_source}</p>'
        f"</div>")


# ═════════════════════════════════════════════════════════════════
#  Stage verdict card
# ═════════════════════════════════════════════════════════════════
def stage_card(stage, verdict_style) -> str:
    style = verdict_style.get(stage.verdict, verdict_style["unknown"])

    if stage.is_cleared:
        body = (f'<div class="delta"><span class="t" style="color:{LANE}">'
                f'{stage.time_target_s:.2f} s</span>'
                f'<span class="g">cleared</span></div>'
                f'<p class="sub">This anchor is behind the athlete. '
                f'{stage.source}</p>')
    elif style["plan"]:
        body = (
            f'<div class="delta"><span class="f">{stage.time_now_s:.2f} s</span>'
            f'<span style="color:{INK3}">→</span>'
            f'<span class="t">{stage.time_target_s:.2f} s</span>'
            f'<span class="g">−{stage.time_gap_s:.2f}</span></div>'
            + row("Step frequency", f"+{stage.sf_change_pct:.1f}%", LANE)
            + row("Step length", f"+{stage.sl_change_pct:.1f}%", LANE)
            + f'<p class="note" style="margin-top:7px">'
              f'About {stage.years_estimated:.1f} years at this tier\'s '
              f'development rate. At the measured elite rate: '
              f'{stage.years_at_elite_rate:.1f} years — developing athletes '
              f'improve considerably faster.</p>')
    else:
        body = (
            f'<div class="delta"><span class="f">{stage.time_now_s:.2f} s</span>'
            f'<span style="color:{INK3}">→</span>'
            f'<span class="t" style="color:{INK3}">{stage.time_target_s:.2f} s</span>'
            f'<span style="color:{INK3};font-size:11px">−{stage.time_gap_s:.2f}</span>'
            f'</div>'
            f'<p class="sub">Shown so the landscape is visible. No plan is '
            f'attached — presenting this as a goal would be a promise the data '
            f'cannot support.</p>')

    return (f'<div class="vd {style["tone"]}"><div class="hd">'
            f'<span class="ttl">{stage.label}</span>'
            f'<span class="bdg {style["tone"]}">{style["label"]}</span></div>'
            f'{body}</div>')


# ═════════════════════════════════════════════════════════════════
#  Refusal panels
# ═════════════════════════════════════════════════════════════════
def refusal_panel(report) -> str:
    gates = (report.kpis.quality.gates if report.kpis else {}) or {}
    rows = "".join(
        row(name.replace("_", " ").title(),
            f'{"PASS" if g["pass"] else "FAIL"} · {g["value"]}',
            LANE if g["pass"] else TRACK)
        for name, g in gates.items())

    return (
        f'<div class="refuse"><h3>This clip cannot be measured accurately</h3>'
        f'<p class="sub" style="margin-bottom:11px">Every gate must pass before '
        f'a number is produced. A wrong measurement misleads a coach worse than '
        f'no measurement.</p>{rows}</div>')


def unsupported_panel(report, event_spec) -> str:
    return (
        f'<div class="refuse">'
        f'<h3>{event_spec.label} is not calibrated yet</h3>'
        f'<p class="sub">{report.message}</p></div>')


# ═════════════════════════════════════════════════════════════════
#  Group sessions
# ═════════════════════════════════════════════════════════════════
def group_session_card(session, metric_label: str) -> str:
    names = ", ".join(session["athletes"])
    return (
        f'<div class="card">'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:baseline;margin-bottom:4px">'
        f'<span class="mono" style="font-size:9px;color:{TRACK};letter-spacing:1.2px">'
        f'GROUP SESSION</span>'
        f'<span class="mono" style="font-size:9px;color:{INK3}">'
        f'{session["count"]} athletes</span></div>'
        f'<h4>{metric_label}</h4>'
        f'<p>{names}</p>'
        f'<p class="note" style="margin-top:6px">A limitation several athletes '
        f'share is one session, not several separate corrections.</p></div>')
