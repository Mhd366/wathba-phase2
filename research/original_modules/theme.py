"""
Design system — track paper.

Warm printed stock, tartan red, lane green, hard offset shadows, no glow.
The aesthetic is deliberately scientific-report rather than dashboard-SaaS:
this is an instrument presented to a federation and should read like one.
"""

from __future__ import annotations

# ═════════════════════════════════════════════════════════════════
#  Palette
# ═════════════════════════════════════════════════════════════════
INK = "#12100C"
INK2 = "#3A362E"
INK3 = "#7A7365"
BG = "#FAF8F3"
PAPER = "#FFFDF8"
SAND = "#F1EBDD"
LINE = "#DDD6C7"
LINE2 = "#C4BBA6"

TRACK = "#B8452E"      # tartan red
LANE = "#1B4D3E"       # lane green
GOLD = "#B8862F"
SKY = "#2E5C8A"
WARN = "#C4761A"

TIER_COLOR = {
    "developing":   INK3,
    "trained":      SKY,
    "national":     LANE,
    "world_class":  GOLD,
    "record":       TRACK,
    "above_record": TRACK,
    "unknown":      LINE2,
}

STATUS_COLOR = {
    "within": LANE, "above_band": LANE, "below_band": LANE,
    "below": TRACK, "above": TRACK,
    "missing": INK3, "excluded": INK3,
}

CONFIDENCE_COLOR = {"high": LANE, "medium": WARN, "low": TRACK, "excluded": INK3}


CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700;800&family=JetBrains+Mono:wght@400;500;700&family=IBM+Plex+Sans+Arabic:wght@400;600&display=swap');

:root{{
  --ink:{INK}; --ink2:{INK2}; --ink3:{INK3};
  --bg:{BG}; --paper:{PAPER}; --sand:{SAND};
  --line:{LINE}; --line2:{LINE2};
  --track:{TRACK}; --lane:{LANE}; --gold:{GOLD}; --sky:{SKY}; --warn:{WARN};
}}

.stApp{{
  background:var(--bg);
  background-image:repeating-linear-gradient(0deg,transparent,transparent 39px,
                   rgba(184,69,46,.02) 39px,rgba(184,69,46,.02) 40px);
}}
html,body,[class*="css"]{{font-family:'Sora',sans-serif;color:var(--ink)}}
#MainMenu,footer,header{{visibility:hidden}}
.block-container{{padding-top:1.8rem;padding-bottom:4rem;max-width:1440px}}
.ar{{font-family:'IBM Plex Sans Arabic',sans-serif;direction:rtl}}
.mono{{font-family:'JetBrains Mono',monospace}}

h1,h2,h3{{letter-spacing:-.6px;font-weight:700}}

/* ── masthead ── */
.mast{{display:flex;align-items:flex-end;gap:16px;border-bottom:3px solid var(--ink);
      padding-bottom:11px;margin-bottom:4px}}
.mast .word{{font-size:38px;font-weight:800;letter-spacing:-2.2px;line-height:.9}}
.mast .ar{{font-size:21px;color:var(--track);font-weight:600;padding-bottom:2px}}
.mast .tail{{margin-left:auto;font-family:'JetBrains Mono',monospace;font-size:9px;
            letter-spacing:2.2px;color:var(--ink3);text-transform:uppercase;
            padding-bottom:5px;text-align:right;line-height:1.7}}

.kicker{{font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:3px;
        color:var(--track);text-transform:uppercase;margin:22px 0 9px;
        display:flex;align-items:center;gap:10px}}
.kicker::after{{content:"";flex:1;height:1px;background:var(--line)}}

/* ── cards ── */
.card{{background:var(--paper);border:1.5px solid var(--ink);border-radius:2px;
      padding:15px 17px;box-shadow:3px 3px 0 var(--ink);margin-bottom:13px}}
.card.acc{{box-shadow:3px 3px 0 var(--track)}}
.card.gold{{box-shadow:3px 3px 0 var(--gold)}}
.card.lane{{box-shadow:3px 3px 0 var(--lane)}}
.card.soft{{border:1px solid var(--line2);box-shadow:none;background:var(--sand)}}
.card h4{{font-size:13px;font-weight:600;margin:0 0 5px}}
.card p{{font-size:11.5px;color:var(--ink2);line-height:1.6;margin:0}}
.sub{{font-size:11px;color:var(--ink3);line-height:1.55}}
.note{{font-size:9.5px;color:var(--ink3);line-height:1.5;font-style:italic}}

.chip{{display:inline-block;border:1px solid var(--ink);border-radius:2px;
      padding:2px 8px;font-size:9px;font-family:'JetBrains Mono',monospace;
      margin:2px 3px 2px 0;background:var(--paper);letter-spacing:.4px}}
.chip.r{{background:var(--track);color:#fff;border-color:var(--track)}}
.chip.g{{background:var(--lane);color:#fff;border-color:var(--lane)}}
.chip.y{{background:var(--gold);color:#fff;border-color:var(--gold)}}
.chip.o{{color:var(--ink3);border-color:var(--line2)}}

/* ── lane board ── */
.board{{background:var(--paper);border:1.5px solid var(--ink);box-shadow:4px 4px 0 var(--ink);
       padding:0;overflow:hidden;margin-bottom:16px}}
.board-hd{{background:var(--ink);color:var(--bg);padding:9px 16px;display:flex;
          align-items:baseline;gap:14px}}
.board-hd .t{{font-size:13px;font-weight:600;letter-spacing:-.3px}}
.board-hd .m{{font-family:'JetBrains Mono',monospace;font-size:9.5px;
             letter-spacing:1.6px;color:#B8B0A0;margin-left:auto}}

.lane-row{{display:grid;grid-template-columns:44px 1fr 78px 66px 96px 1fr 54px;
          align-items:center;gap:12px;padding:11px 16px;
          border-bottom:1px solid var(--line);position:relative}}
.lane-row:last-child{{border-bottom:none}}
.lane-row:nth-child(even){{background:rgba(241,235,221,.45)}}

.lane-no{{font-family:'JetBrains Mono',monospace;font-size:15px;font-weight:700;
         color:var(--paper);background:var(--ink);width:30px;height:30px;
         display:flex;align-items:center;justify-content:center;border-radius:2px}}
.lane-name{{font-size:13px;font-weight:600;line-height:1.25}}
.lane-name small{{display:block;font-size:9.5px;color:var(--ink3);font-weight:400;
                 font-family:'JetBrains Mono',monospace;margin-top:1px}}
.lane-num{{font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:700;
          text-align:right}}
.lane-num small{{display:block;font-size:8.5px;color:var(--ink3);font-weight:400;
                letter-spacing:.6px}}

.tier-pill{{display:inline-block;font-size:9px;font-family:'JetBrains Mono',monospace;
           padding:3px 8px;color:#fff;letter-spacing:.6px;white-space:nowrap}}

.mini-rail{{height:6px;background:var(--sand);border:1px solid var(--line2);
           position:relative;margin-top:3px}}
.mini-fill{{height:100%;position:absolute;left:0;top:0}}

.prio{{font-size:11px;line-height:1.3}}
.prio small{{display:block;font-size:9px;color:var(--ink3);
            font-family:'JetBrains Mono',monospace;margin-top:1px}}

/* ── tier rail ── */
.rail-wrap{{padding:32px 4px 40px;position:relative}}
.rail{{height:14px;border:1.5px solid var(--ink);position:relative;
      background:repeating-linear-gradient(90deg,var(--sand) 0 7px,var(--paper) 7px 14px)}}
.rail .seg{{position:absolute;top:0;bottom:0;border-right:1.5px solid var(--ink)}}
.rail .seg.meas{{background:rgba(184,134,47,.16)}}
.rail .lbl{{position:absolute;top:21px;transform:translateX(-50%);text-align:center;
           white-space:nowrap;font-family:'JetBrains Mono',monospace;font-size:8px;
           color:var(--ink3);letter-spacing:.5px}}
.rail .lbl b{{display:block;font-family:'Sora',sans-serif;font-size:10px;
             color:var(--ink);font-weight:600;letter-spacing:-.2px;margin-bottom:1px}}
.rail .you{{position:absolute;top:-29px;transform:translateX(-50%);text-align:center;z-index:3}}
.rail .you .flag{{background:var(--track);color:#fff;font-size:9.5px;padding:4px 10px;
                 font-family:'JetBrains Mono',monospace;white-space:nowrap}}
.rail .you .stem{{width:2px;height:17px;background:var(--track);margin:0 auto}}
.rail .gh{{position:absolute;top:-19px;transform:translateX(-50%);text-align:center;opacity:.6}}
.rail .gh .flag{{background:var(--paper);border:1px dashed var(--ink3);color:var(--ink3);
                font-size:8px;padding:2px 7px;font-family:'JetBrains Mono',monospace;
                white-space:nowrap}}
.rail .gh .stem{{width:1px;height:10px;margin:0 auto;
                background-image:linear-gradient(var(--ink3) 50%,transparent 50%);
                background-size:1px 4px}}

/* ── metric rows ── */
.mrow{{margin-bottom:10px}}
.mtop{{display:flex;justify-content:space-between;align-items:baseline;
      font-size:11px;margin-bottom:3px}}
.mtop .v{{font-family:'JetBrains Mono',monospace;font-weight:500}}
.mtrk{{height:8px;background:var(--sand);border:1px solid var(--line2);position:relative}}
.mband{{position:absolute;top:-1px;bottom:-1px;background:rgba(184,134,47,.22);
       border-left:1.5px solid var(--gold);border-right:1.5px solid var(--gold)}}
.mdot{{position:absolute;top:50%;width:12px;height:12px;border-radius:50%;
      transform:translate(-50%,-50%);border:2px solid var(--paper);z-index:2}}

/* ── verdict ── */
.vd{{border-left:4px solid;padding:12px 14px;background:var(--paper);
    border-top:1px solid var(--line2);border-right:1px solid var(--line2);
    border-bottom:1px solid var(--line2);margin-bottom:10px}}
.vd.ok{{border-left-color:var(--lane)}}
.vd.warn{{border-left-color:var(--warn)}}
.vd.mute{{border-left-color:var(--ink3);background:var(--sand);opacity:.82}}
.vd .hd{{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:5px}}
.vd .ttl{{font-size:12.5px;font-weight:600}}
.vd .bdg{{font-size:8px;font-family:'JetBrains Mono',monospace;letter-spacing:1.1px;
         padding:3px 8px;color:#fff}}
.bdg.ok{{background:var(--lane)}} .bdg.warn{{background:var(--warn)}}
.bdg.mute{{background:var(--ink3)}}

.delta{{display:flex;align-items:baseline;gap:8px;font-family:'JetBrains Mono',monospace;
       margin:7px 0}}
.delta .f{{font-size:14px;color:var(--ink3)}}
.delta .t{{font-size:20px;font-weight:700}}
.delta .g{{font-size:11px;color:var(--lane);font-weight:600}}

/* ── pips ── */
.pips{{display:inline-flex;gap:3px;vertical-align:middle}}
.pips i{{width:6px;height:6px;border-radius:50%;background:var(--line2);display:block}}

/* ── stat ── */
.stat{{background:var(--paper);border:1.5px solid var(--ink);padding:13px 11px;
      text-align:center;box-shadow:2px 2px 0 var(--ink)}}
.stat .v{{font-family:'JetBrains Mono',monospace;font-size:21px;font-weight:700;line-height:1}}
.stat .l{{font-size:9px;color:var(--ink3);line-height:1.35;margin-top:5px}}

/* ── rows ── */
.row{{display:flex;justify-content:space-between;padding:6px 0;
     border-bottom:1px solid var(--line);font-size:11.5px}}
.row:last-child{{border-bottom:none}}
.row .st{{font-family:'JetBrains Mono',monospace;font-size:10.5px;letter-spacing:.6px}}

/* ── refusal ── */
.refuse{{border:2px solid var(--track);background:var(--paper);padding:19px 22px;
        box-shadow:4px 4px 0 var(--track)}}
.refuse h3{{color:var(--track);margin:0 0 9px;font-size:17px}}

ul.d{{list-style:none;padding:0;margin:0}}
ul.d li{{font-size:11.5px;color:var(--ink2);line-height:1.65;padding-left:13px;
        position:relative}}
ul.d li::before{{content:"→";position:absolute;left:0;color:var(--track);
                font-family:'JetBrains Mono',monospace;font-size:10px}}

/* ── streamlit overrides ── */
section[data-testid="stSidebar"]{{background:var(--sand);border-right:1.5px solid var(--ink)}}
.stButton>button{{background:var(--ink);color:var(--bg);border:none;border-radius:2px;
                 font-family:'JetBrains Mono',monospace;font-size:10.5px;letter-spacing:1.3px;
                 padding:9px 18px;box-shadow:3px 3px 0 var(--track);font-weight:500}}
.stButton>button:hover{{background:var(--track);color:#fff;box-shadow:3px 3px 0 var(--ink)}}
.stTabs [data-baseweb="tab-list"]{{gap:2px;border-bottom:1.5px solid var(--ink)}}
.stTabs [data-baseweb="tab"]{{font-size:11.5px;padding:8px 15px;background:transparent}}
.stTabs [aria-selected="true"]{{color:var(--track);font-weight:600}}
</style>
"""


# ═════════════════════════════════════════════════════════════════
#  Fragment helpers
# ═════════════════════════════════════════════════════════════════
def masthead(subtitle: str = "") -> str:
    tail = subtitle or ("Sprint biomechanics<br>"
                        "London 2017 · Berlin 2009 · AthleticsPose")
    return (f'<div class="mast"><span class="word">WATHBA</span>'
            f'<span class="ar">وثبة</span>'
            f'<span class="tail">{tail}</span></div>')


def kicker(text: str) -> str:
    return f'<div class="kicker">{text}</div>'


def pips(score: float) -> str:
    filled = int(round((score or 0) * 5))
    color = (LANE if score >= 0.85 else WARN if score >= 0.60
             else TRACK if score > 0 else LINE2)
    return ('<span class="pips">' + "".join(
        f'<i style="background:{color}"></i>' if i < filled else "<i></i>"
        for i in range(5)) + "</span>")


def stat(value: str, label: str, color: str = INK, accent: str = INK) -> str:
    return (f'<div class="stat" style="box-shadow:2px 2px 0 {accent}">'
            f'<div class="v" style="color:{color}">{value}</div>'
            f'<div class="l">{label}</div></div>')


def row(left: str, right: str, right_color: str = INK3) -> str:
    return (f'<div class="row"><span>{left}</span>'
            f'<span class="st" style="color:{right_color}">{right}</span></div>')
