"""Builds a presentation-grade, self-contained HTML version of the Automation Strategy.

Reuses the dashboard's data layer (JUnit feed + RAG evaluation report + run history)
so every number in the deck is live and consistent with reports/automation_dashboard.html.

Output: one .html file (inline SVG + CSS, no CDN) that opens offline, presents well on a
projector, and prints cleanly to PDF (Ctrl+P).

Usage:
    python build_strategy_doc.py
    python -m src.reporting.strategy_doc --open
"""
import argparse
import datetime
import html as _html
import os
from string import Template

from src.reporting import report_builder as RB

DEFAULT_HTML = os.path.join("docs", "automation_strategy.html")

AUTHOR = "Automation QA"

# Business areas shown in the deck (order matters for presentation).
AREA_ORDER = [
    "RAG Q&A", "File Extraction", "Memo Extraction & Analysis", "Memo Analysis",
    "UI Automation", "UI & Eval Gates", "Eval Gates",
]

# Types of testing covered: (title, icon, blurb, where)
TEST_TYPES = [
    ("Functional - RAG Q&A", "chat",
     "Grounded answers with UK citations and a latency SLO on every response.",
     "test_automation_rag.py, test_bdd_rag.py"),
    ("Functional - File Extraction", "file",
     "PDF / JPG / JPEG / PNG / TXT / MD extraction, with actionable error messages.",
     "test_automation_extract.py, test_bdd_memo.py"),
    ("Functional - Memo Analysis", "clipboard",
     "8-point UK checklist scoring, verdict, gaps and UK-cited evidence.",
     "test_automation_analyser.py, test_bdd_memo.py"),
    ("BDD Acceptance", "gears",
     "Business-readable Given / When / Then scenarios across every area.",
     "tests/bdd/features/*.feature"),
    ("UI Automation", "window",
     "Headless Streamlit UI: 5 tabs, uploader, Q box, KB list, gates - no browser.",
     "test_automation_ui.py, test_bdd_ui_eval.py"),
    ("Integration / E2E", "link",
     "Multi-component paths: extract -> analyse -> standards evidence.",
     "test_automation_analyser.py, test_bdd_memo.py"),
    ("Data & Regression", "chart",
     "100-question evaluation with per-question rows for regression diffing.",
     "test_automation_eval.py, runner.py"),
    ("Release Gates", "gate",
     "Quality thresholds enforced as failing tests.",
     "test_rag_gates.py, test_bdd_ui_eval.py"),
    ("AI-Specific Patterns", "spark",
     "Grounding, hallucination guard, metamorphic, robustness, no-leakage, bias, determinism.",
     "ai_patterns.feature, test_automation_rag.py"),
    ("Negative / Error Handling", "shield",
     "Unsupported types, blank images, empty input, missing files, gibberish queries.",
     "*_negative* tests + negative marker"),
    ("Edge Cases", "repeat",
     ".jpeg vs .jpg, empty question, paraphrase consistency, missing report.",
     "*_edge* tests + edge marker"),
]

# Coverage matrix rows: (area, positive, negative, edge)
COVERAGE = [
    ("RAG Q&A",
     "ICR / SONIA / Stage-2 answered &amp; cited; latency &lt; 3s",
     "Gibberish question does not invent an FCA section",
     "Empty question safe fallback; paraphrase (metamorphic) consistency"),
    ("File Extraction",
     "Digital PDF text; JPG OCR; TXT direct",
     ".xlsx unsupported-type; blank PNG paste-guidance",
     ".jpeg alias; scanned-PDF OCR path"),
    ("Memo Analysis",
     "Strong memo READY; PDF end-to-end; evidence cites uk_*",
     "Weak memo NEEDS WORK + &ge; 3 gaps; empty memo error",
     "Missing file error"),
    ("Streamlit UI",
     "5 tabs render; uploader + paste; Q box + Top-K; UK-only KB list",
     "Dashboard still loads with no eval report",
     "Zero exceptions on load"),
    ("Eval Gates",
     "Recall &ge; .90, Faith &ge; .90, Rel &ge; .90, Hall &le; .05, p95 &le; 3s, PASS",
     "Gate failures block the release",
     "100 per-question rows for regression"),
    ("AI Patterns",
     "Gold doc in top-5; faithfulness 1.0; determinism",
     "No-leakage: user memos never indexed",
     "Typo robustness; bias/fairness conduct guidance"),
]
# AI testing patterns: (name, detail)
PATTERNS = [
    ("Grounding", "Extractive answers keep faithfulness at 1.0"),
    ("Retrieval quality", "Recall@5 / Precision / MRR / Hit@K on 100 golden Qs"),
    ("Hallucination guard", "Gibberish probe; hallucination = 1 - faithfulness, gate &le; 5%"),
    ("Metamorphic", "Paraphrased ICR question returns the same facts"),
    ("Robustness", "Typo-laden question still answered"),
    ("No-leakage", "User memos excluded from the UK index"),
    ("Bias / fairness", "Vulnerable-customer question gets conduct guidance"),
    ("Determinism", "Same question twice returns the same citations"),
    ("Latency SLO", "Per-query and p95 latency within budget"),
    ("Golden dataset", "100 pinned UK questions; rows stored for diffing"),
]

# Execution pipeline: (step number, title, detail)
PIPELINE = [
    ("1", "Evaluate", "run_eval.py runs the 100-question RAG evaluation"),
    ("2", "Automate", "pytest -m &quot;not unit&quot; runs the automation suite"),
    ("3", "Report", "build_report.py renders the visual dashboard"),
    ("4", "Decide", "PASS / FAIL verdict gates the release"),
]

# Reports produced: (artifact, purpose)
ARTIFACTS = [
    ("reports/automation_dashboard.html", "Visual automation report - the one to open"),
    ("reports/history.json", "Rolling history powering the last-3-runs trend"),
    ("reports/automation_report_&lt;ts&gt;.html", "pytest-html per-test detail"),
    ("reports/cucumber_&lt;ts&gt;.json", "Cucumber JSON for CI dashboards"),
    ("data/eval/evaluation_report.json", "100-Q metrics + per-question rows + verdict"),
]

_ICONS = {
    "chat": "M4 5h16v10H8l-4 4z",
    "file": "M7 3h7l4 4v13H7zM14 3v4h4",
    "clipboard": "M9 3h6v3H9zM7 6h10v14H7zM9 11h6M9 15h6",
    "gears": "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM12 2v3M12 19v3M2 12h3M19 12h3",
    "window": "M3 5h18v14H3zM3 9h18M7 7h.01",
    "link": "M9 15l6-6M8 7l-3 3a4 4 0 0 0 6 6M16 17l3-3a4 4 0 0 0-6-6",
    "chart": "M4 20V10M10 20V4M16 20v-7M22 20H2",
    "gate": "M5 21V4h14v17M9 9h6M9 13h6M9 17h6",
    "spark": "M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2z",
    "shield": "M12 3l8 3v6c0 5-4 8-8 9-4-1-8-4-8-9V6z",
    "repeat": "M4 9a6 6 0 0 1 10-4l3 3M20 15a6 6 0 0 1-10 4l-3-3M17 5v3h-3M7 19v-3h3",
    "clock": "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 7v5l3 2",
    "check": "M20 6 9 17l-5-5",
    "target": "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10zM12 11a1 1 0 1 0 0 2 1 1 0 0 0 0-2z",
}


def _esc(t):
    return _html.escape(str(t), quote=True)


def icon(name, cls="ic"):
    return (f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">'
            f'<path d="{_ICONS.get(name, _ICONS["check"])}"/></svg>')
def _pretty_ts(ts):
    try:
        return datetime.datetime.strptime(ts, "%Y%m%d_%H%M%S").strftime("%d %b %Y, %H:%M")
    except (ValueError, TypeError):
        return str(ts)


def gather(junit_path=None, eval_path=None):
    """Collect live numbers used across the deck (automation scope only)."""
    summary, cases = RB.parse_junit(junit_path or RB.newest_junit())
    eval_rep = RB.load_eval(eval_path or RB.EVAL_REPORT) or {}
    hist = RB.load_history()

    by_area = {}
    for c in cases:
        row = by_area.setdefault(c["category"], {"total": 0, "passed": 0,
                                                 "failed": 0, "skipped": 0})
        row["total"] += 1
        row[c["status"]] += 1

    agg = eval_rep.get("aggregate", {})
    checks = eval_rep.get("checks", {})
    gates_passed = sum(1 for v in checks.values() if v)
    verdict = RB.verdict_of(summary, eval_rep if eval_rep else None)

    return {
        "summary": summary,
        "cases": cases,
        "eval": eval_rep,
        "agg": agg,
        "checks": checks,
        "history": hist,
        "by_area": by_area,
        "gates_passed": gates_passed,
        "gates_total": len(checks),
        "verdict": verdict[0],
        "verdict_class": verdict[1],
        "verdict_sub": verdict[2],
        "generated": datetime.datetime.now().strftime("%d %b %Y %H:%M"),
        "latest_run": _pretty_ts(hist[-1]["ts"]) if hist else "-",
        "runs": len(hist),
    }


def area_bars(by_area):
    """Area cards with a mini pass-rate bar (automation areas only)."""
    if not by_area:
        return '<p class="muted">No automation cases collected.</p>'
    rows = []
    for name in AREA_ORDER + [k for k in by_area if k not in AREA_ORDER]:
        if name not in by_area:
            continue
        c = by_area[name]
        t = c["total"] or 1
        rate = 100.0 * c["passed"] / t
        ok = c["failed"] == 0
        rows.append(
            f'<div class="area">'
            f'<div class="area-top"><span class="area-name">{_esc(name)}</span>'
            f'<span class="area-count">{c["passed"]}/{c["total"]}</span></div>'
            f'<div class="area-track">'
            f'<span class="area-fill {"ok" if ok else "bad"}" style="width:{rate:.1f}%"></span>'
            f'</div>'
            f'<span class="area-chip {"ok" if ok else "bad"}">'
            f'{"100%" if ok else f"{rate:.0f}%"}</span></div>')
    return "".join(rows)


def ring_gauge(label, value_text, arc, passed, sub, size=132, stroke=11):
    """Circular gate gauge with a PASS/FAIL chip."""
    import math
    r = (size - stroke) / 2.0
    cx = cy = size / 2.0
    circ = 2 * math.pi * r
    arc = max(0.0, min(1.0, arc))
    color = "#34d399" if passed else "#fb7185"
    track = (f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" fill="none" '
             f'stroke="rgba(148,163,184,.18)" stroke-width="{stroke:g}"/>')
    fill = (f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" fill="none" stroke="{color}" '
            f'stroke-width="{stroke:g}" stroke-linecap="round" '
            f'stroke-dasharray="{arc * circ:.3f} {circ:.3f}" '
            f'transform="rotate(-90 {cx:g} {cy:g})"/>')
    txt = (f'<text x="{cx:g}" y="{cy + 3:g}" text-anchor="middle" class="ring-val">'
           f'{_esc(value_text)}</text>'
           f'<text x="{cx:g}" y="{cy + 22:g}" text-anchor="middle" class="ring-sub">'
           f'{_esc(sub)}</text>')
    chip = "chip-pass" if passed else "chip-fail"
    return (f'<div class="ring-box"><svg class="ring" viewBox="0 0 {size} {size}" '
            f'role="img" aria-label="{_esc(label)}">{track}{fill}{txt}</svg>'
            f'<div class="ring-label">{_esc(label)}</div>'
            f'<span class="chip {chip}">{"PASS" if passed else "FAIL"}</span></div>')
GATES = [
    ("recall@5", "Recall@5", "higher", "recall_at_5", "{:.2f}", "target &ge; 0.90"),
    ("faithfulness", "Faithfulness", "higher", "faithfulness", "{:.2f}", "target &ge; 0.90"),
    ("answer_relevance", "Answer Relevance", "higher", "answer_relevance", "{:.2f}", "target &ge; 0.90"),
    ("hallucination", "Hallucination", "lower", "hallucination", "{:.2f}", "target &le; 0.05"),
    ("p95_latency_s", "p95 Latency", "seconds", "p95_latency_s", "{:.3f}s", "target &le; 3.0s"),
]


def gates_section(g):
    agg, checks = g["agg"], g["checks"]
    if not agg:
        return '<div class="empty">Run <code>python run_eval.py</code> to populate the gates.</div>'
    out = []
    for key, label, direction, gate_key, fmt, sub in GATES:
        if key not in agg:
            continue
        val = float(agg[key])
        passed = bool(checks.get(gate_key, True))
        if direction == "seconds":
            arc = max(0.0, min(1.0, 1.0 - val / 3.0))
        elif direction == "higher":
            arc = max(0.0, min(1.0, val))
        else:
            arc = max(0.0, min(1.0, 1.0 - val))
        out.append(ring_gauge(label, fmt.format(val), arc, passed, sub))
    return f'<div class="rings">{"".join(out)}</div>'


def test_type_cards(g):
    cards = []
    for title, ic, blurb, where in TEST_TYPES:
        cards.append(
            f'<article class="type-card">'
            f'<div class="type-ic">{icon(ic)}</div>'
            f'<h4>{_esc(title)}</h4>'
            f'<p>{_esc(blurb)}</p>'
            f'<div class="type-where">{_esc(where)}</div>'
            f'</article>')
    return f'<div class="type-grid">{"".join(cards)}</div>'


def coverage_table():
    rows = []
    for area, pos, neg, edge in COVERAGE:
        rows.append(
            f'<tr><th class="cov-area">{_esc(area)}</th>'
            f'<td class="cov-pos"><span class="cov-dot pos"></span>{pos}</td>'
            f'<td class="cov-neg"><span class="cov-dot neg"></span>{neg}</td>'
            f'<td class="cov-edge"><span class="cov-dot edge"></span>{edge}</td></tr>')
    return (
        '<div class="table-wrap"><table class="matrix"><thead><tr>'
        '<th>Area</th><th>Positive checks</th><th>Negative checks</th><th>Edge checks</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def pattern_cards():
    cards = []
    for name, detail in PATTERNS:
        cards.append(
            f'<div class="pat"><div class="pat-ic">{icon("check")}</div>'
            f'<div><b>{_esc(name)}</b><span>{detail}</span></div></div>')
    return f'<div class="pat-grid">{"".join(cards)}</div>'


def pipeline_flow():
    steps = []
    for n, title, detail in PIPELINE:
        steps.append(
            f'<div class="step"><div class="step-n">{_esc(n)}</div>'
            f'<h4>{title}</h4><p>{_esc(detail)}</p></div>')
    return (f'<div class="pipeline">{"".join(steps)}</div>'
            f'<div class="pipeline-cmd">python run_automation.py &nbsp;&rarr;&nbsp; '
            f'reports/automation_dashboard.html</div>')


def artifact_list():
    rows = []
    for name, purpose in ARTIFACTS:
        rows.append(f'<li><code>{name}</code><span>{_esc(purpose)}</span></li>')
    return f'<ul class="artifacts">{"".join(rows)}</ul>'


def history_strip(hist):
    recent = list(reversed(hist))[:RB.HISTORY_SHOW]
    if not recent:
        return '<span class="muted small">No run history yet.</span>'
    chips = []
    for i, h in enumerate(recent):
        cls = "pass" if h.get("verdict") == "PASS" else "fail"
        tag = "latest" if i == 0 else f"-{i}"
        chips.append(
            f'<span class="hist {cls}"><b>{h.get("total", 0)}</b> tests '
            f'&middot; {h.get("pass_rate", 0):.0f}% &middot; {_esc(tag)}</span>')
    return "".join(chips)
_CSS_1 = """
:root{
  --bg:#060912;--card:rgba(18,27,47,.74);--card2:rgba(11,18,33,.72);--line:#233254;
  --txt:#eaf0ff;--muted:#94a6c6;--green:#34d399;--red:#fb7185;--amber:#fbbf24;
  --blue:#60a5fa;--violet:#a78bfa;--cyan:#22d3ee;--pink:#f472b6;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--txt);line-height:1.5;overflow-x:hidden;
  font-family:"Segoe UI",system-ui,-apple-system,Roboto,Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased}
body::before{content:"";position:fixed;inset:0;z-index:0;pointer-events:none;
  background:
    radial-gradient(58rem 40rem at 10% -10%,rgba(96,165,250,.22),transparent 60%),
    radial-gradient(48rem 36rem at 95% 0%,rgba(167,139,250,.20),transparent 62%),
    radial-gradient(52rem 40rem at 60% 110%,rgba(34,211,238,.16),transparent 60%),
    radial-gradient(40rem 30rem at 85% 70%,rgba(244,114,182,.10),transparent 60%);
  animation:aurora 18s ease-in-out infinite alternate}
@keyframes aurora{from{transform:translate3d(0,0,0) scale(1)}to{transform:translate3d(0,-18px,0) scale(1.03)}}
.deck{position:relative;z-index:1;max-width:1180px;margin:0 auto;padding:30px 22px 70px}
h1,h2,h3,h4{margin:0;font-weight:800;letter-spacing:.2px}
code{font-family:Consolas,Monaco,monospace;font-size:12.4px;color:#d5e5ff;
  background:rgba(8,14,26,.85);border:1px solid var(--line);border-radius:6px;padding:1px 6px}
.muted{color:var(--muted)}.small{font-size:12.5px}

/* ---------- sticky nav ---------- */
.nav{position:sticky;top:0;z-index:20;display:flex;flex-wrap:wrap;gap:8px;
  padding:12px 14px;margin-bottom:20px;border-radius:16px;
  background:rgba(9,15,28,.82);border:1px solid var(--line);backdrop-filter:blur(12px)}
.nav a{color:#c7d6f2;text-decoration:none;font-size:12.5px;font-weight:600;
  padding:6px 12px;border-radius:20px;border:1px solid transparent;transition:.18s}
.nav a:hover{color:#fff;background:rgba(96,165,250,.16);border-color:rgba(96,165,250,.4)}
.nav .spacer{flex:1}
.nav button{cursor:pointer;font:inherit;font-size:12.5px;font-weight:700;color:#04121f;
  background:linear-gradient(135deg,#22d3ee,#60a5fa);border:0;border-radius:20px;padding:7px 14px}
.nav button:hover{filter:brightness(1.08)}

/* ---------- hero ---------- */
.hero{position:relative;overflow:hidden;border-radius:26px;padding:40px 40px 34px;
  background:linear-gradient(140deg,rgba(30,46,84,.95),rgba(10,16,30,.94));
  border:1px solid var(--line);box-shadow:0 30px 80px rgba(2,6,20,.6)}
.hero::after{content:"";position:absolute;inset:-2px;border-radius:26px;pointer-events:none;
  background:linear-gradient(120deg,rgba(34,211,238,.5),rgba(167,139,250,.4),rgba(96,165,250,.4));
  -webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);
  mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);
  -webkit-mask-composite:xor;mask-composite:exclude;padding:1.2px}
.eyebrow{display:inline-block;font-size:12px;letter-spacing:2px;text-transform:uppercase;
  color:var(--cyan);font-weight:800;margin-bottom:12px}
.hero h1{font-size:44px;line-height:1.05;letter-spacing:-.5px;
  background:linear-gradient(92deg,#ffffff,#b8d0ff 50%,#7ef0e0);
  -webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
.hero .lede{color:#c2d2ee;font-size:15.5px;max-width:760px;margin-top:14px}
.hero-meta{display:flex;flex-wrap:wrap;gap:10px;margin-top:22px}
.badge{display:inline-flex;align-items:center;gap:7px;font-size:12px;font-weight:700;
  padding:6px 13px;border-radius:20px;background:rgba(9,15,28,.7);border:1px solid var(--line);
  color:#cadcf7}
.badge .dot{width:8px;height:8px;border-radius:50%;background:currentColor}
.badge.pass{color:#6ee7b7;border-color:rgba(52,211,153,.4);background:rgba(52,211,153,.12)}
.badge.fail{color:#fda4af;border-color:rgba(251,113,133,.4);background:rgba(251,113,133,.12)}
.hero-byline{margin-top:20px;color:var(--muted);font-size:12.5px}

/* ---------- KPI strip ---------- */
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:16px;margin:22px 0}
.kpi{position:relative;overflow:hidden;padding:18px 18px 16px;border-radius:18px;
  background:var(--card);border:1px solid var(--line);backdrop-filter:blur(10px);transition:.2s}
.kpi:hover{transform:translateY(-4px);box-shadow:0 20px 46px rgba(2,6,20,.55)}
.kpi .bar{position:absolute;left:0;top:0;bottom:0;width:4px;
  background:linear-gradient(180deg,var(--cyan),var(--violet))}
.kpi .v{font-size:32px;font-weight:900;line-height:1}
.kpi .l{font-size:12px;color:#c7d6f2;font-weight:600;margin-top:4px}
.kpi .s{font-size:11px;color:var(--muted)}
.kpi.g .v{color:var(--green)}.kpi.b .v{color:var(--red)}.kpi.c .v{color:var(--cyan)}
.kpi.v2 .v{color:var(--violet)}.kpi.a .v{color:var(--amber)}
"""
_CSS_2 = """
/* ---------- sections ---------- */
.section{margin-top:34px;scroll-margin-top:80px}
.sec-head{display:flex;align-items:center;gap:13px;margin-bottom:16px}
.sec-num{flex:0 0 auto;width:34px;height:34px;border-radius:11px;display:grid;place-items:center;
  font-size:15px;font-weight:900;color:#04121f;
  background:linear-gradient(135deg,var(--cyan),var(--blue));box-shadow:0 8px 22px rgba(34,211,238,.3)}
.sec-head h2{font-size:22px}
.sec-head .sub{color:var(--muted);font-size:13px;margin-top:2px}
.card{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:22px 24px;
  backdrop-filter:blur(10px);box-shadow:0 18px 46px rgba(2,6,20,.42)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
@media(max-width:900px){.grid2,.grid3{grid-template-columns:1fr}}
.card h3{font-size:15px;color:#dbe7ff;margin-bottom:10px}
.card p{color:#bccde9;font-size:13.6px;margin:6px 0}
.card ul{margin:8px 0 0;padding-left:18px;color:#bccde9;font-size:13.4px}
.lead{color:#c9d8f2;font-size:14.5px;line-height:1.6}
.empty{padding:20px;border:1px dashed var(--line);border-radius:14px;color:var(--muted);
  text-align:center;font-size:13.5px}

/* ---------- gates (rings) ---------- */
.rings{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px}
.ring-box{display:flex;flex-direction:column;align-items:center;gap:6px;padding:16px 8px;
  border-radius:18px;background:var(--card2);border:1px solid var(--line)}
.ring{width:132px;height:132px}
.ring circle{transition:stroke-dasharray 1s cubic-bezier(.3,1,.4,1)}
.ring-val{font-size:23px;font-weight:900;fill:#f3f8ff}
.ring-sub{font-size:9.5px;fill:#8ea3c6}
.ring-label{font-size:12.5px;font-weight:700;color:#d6e2fa;text-align:center}
.chip{font-size:10px;font-weight:900;letter-spacing:1.2px;padding:3px 11px;border-radius:20px}
.chip-pass{background:rgba(52,211,153,.18);color:#6ee7b7}
.chip-fail{background:rgba(251,113,133,.18);color:#fda4af}

/* ---------- areas ---------- */
.areas{display:grid;grid-template-columns:repeat(auto-fit,minmax(212px,1fr));gap:12px}
.area{position:relative;padding:13px 14px 15px;border-radius:14px;
  background:var(--card2);border:1px solid var(--line)}
.area-top{display:flex;justify-content:space-between;gap:8px;font-size:12.6px;margin-bottom:8px}
.area-name{color:#d6e2fa;font-weight:600}
.area-count{color:var(--muted);font-weight:700}
.area-track{height:9px;border-radius:6px;background:rgba(148,163,184,.14);overflow:hidden}
.area-fill{display:block;height:100%;border-radius:6px}
.area-fill.ok{background:linear-gradient(90deg,#10b981,#34d399)}
.area-fill.bad{background:linear-gradient(90deg,#e11d48,#fb7185)}
.area-chip{position:absolute;top:11px;right:12px;font-size:10px;font-weight:900;
  padding:1px 8px;border-radius:20px}
.area-chip.ok{background:rgba(52,211,153,.16);color:#6ee7b7}
.area-chip.bad{background:rgba(251,113,133,.16);color:#fda4af}

/* ---------- test type cards ---------- */
.type-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px}
.type-card{position:relative;padding:20px;border-radius:18px;background:var(--card);
  border:1px solid var(--line);transition:.2s;overflow:hidden}
.type-card::before{content:"";position:absolute;inset:0;opacity:0;transition:.25s;
  background:radial-gradient(24rem 12rem at 20% -20%,rgba(96,165,250,.16),transparent 70%)}
.type-card:hover{transform:translateY(-4px);box-shadow:0 22px 50px rgba(2,6,20,.55)}
.type-card:hover::before{opacity:1}
.type-ic{width:42px;height:42px;border-radius:13px;display:grid;place-items:center;
  background:rgba(96,165,250,.14);color:#8ec5ff;margin-bottom:12px}
.type-ic .ic{width:22px;height:22px}
.type-card h4{font-size:14.6px;color:#e6eeff;margin-bottom:6px}
.type-card p{color:#b4c6e4;font-size:13px;margin:0}
.type-where{margin-top:12px;font-family:Consolas,Monaco,monospace;font-size:11.2px;
  color:#7fe3d6;word-break:break-word}
"""
_CSS_3 = """
/* ---------- matrix table ---------- */
.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:16px}
table.matrix{border-collapse:collapse;width:100%;font-size:12.8px;min-width:840px}
table.matrix thead th{position:sticky;top:0;background:#111c33;text-align:left;padding:12px 14px;
  color:#a9c0e6;font-size:11px;letter-spacing:1.1px;text-transform:uppercase;
  border-bottom:1px solid var(--line)}
table.matrix tbody td{padding:12px 14px;border-bottom:1px solid rgba(35,50,84,.6);
  color:#c3d3ef;vertical-align:top;line-height:1.5}
table.matrix tbody tr:hover{background:rgba(96,165,250,.07)}
th.cov-area{text-align:left;padding:12px 14px;font-size:12.8px;color:#e2ebff;
  white-space:nowrap;border-bottom:1px solid rgba(35,50,84,.6)}
.cov-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:8px;
  vertical-align:middle}
.cov-dot.pos{background:var(--green);box-shadow:0 0 10px rgba(52,211,153,.65)}
.cov-dot.neg{background:var(--red);box-shadow:0 0 10px rgba(251,113,133,.65)}
.cov-dot.edge{background:var(--amber);box-shadow:0 0 10px rgba(251,191,36,.65)}

/* ---------- patterns ---------- */
.pat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(268px,1fr));gap:12px}
.pat{display:flex;gap:12px;align-items:flex-start;padding:14px 15px;border-radius:14px;
  background:var(--card2);border:1px solid var(--line)}
.pat-ic{flex:0 0 26px;width:26px;height:26px;border-radius:9px;display:grid;place-items:center;
  background:rgba(52,211,153,.14);color:#6ee7b7}
.pat-ic .ic{width:15px;height:15px}
.pat b{display:block;font-size:13.4px;color:#e6eeff}
.pat span{font-size:12.4px;color:#a9bde0}

/* ---------- pipeline ---------- */
.pipeline{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;position:relative}
@media(max-width:900px){.pipeline{grid-template-columns:1fr 1fr}}
.step{position:relative;padding:18px 16px;border-radius:16px;background:var(--card2);
  border:1px solid var(--line);text-align:center}
.step-n{width:32px;height:32px;margin:0 auto 10px;border-radius:50%;display:grid;place-items:center;
  font-weight:900;color:#04121f;background:linear-gradient(135deg,var(--cyan),var(--violet))}
.step h4{font-size:14px;color:#e6eeff}
.step p{font-size:12.4px;color:#a9bde0;margin:6px 0 0}
.pipeline-cmd{margin-top:14px;text-align:center;font-family:Consolas,Monaco,monospace;
  font-size:12.8px;color:#7fe3d6;background:rgba(8,14,26,.8);border:1px dashed var(--line);
  border-radius:12px;padding:12px}

/* ---------- artifacts / history ---------- */
.artifacts{list-style:none;margin:0;padding:0}
.artifacts li{display:flex;gap:12px;align-items:baseline;padding:11px 0;
  border-bottom:1px dashed rgba(35,50,84,.75);font-size:13px}
.artifacts li:last-child{border-bottom:0}
.artifacts span{color:var(--muted);font-size:12.5px}
.hist-strip{display:flex;flex-wrap:wrap;gap:10px}
.hist{font-size:12.4px;padding:8px 13px;border-radius:12px;border:1px solid var(--line);
  background:var(--card2);color:#c7d6f2}
.hist b{color:#eaf0ff;font-size:14px}
.hist.pass{border-color:rgba(52,211,153,.4)}
.hist.fail{border-color:rgba(251,113,133,.4)}

/* ---------- footer + print ---------- */
.foot{margin-top:40px;padding-top:20px;border-top:1px solid var(--line);text-align:center;
  color:var(--muted);font-size:12px;line-height:1.9}
.foot b{color:#cddbf5}
@media print{
  body{background:#fff;color:#111}
  body::before,.nav{display:none!important}
  .deck{max-width:100%;padding:0}
  .hero,.card,.type-card,.kpi,.ring-box,.area,.pat,.step,.table-wrap
    {background:#fff!important;border:1px solid #d5dced!important;box-shadow:none!important}
  .hero h1{-webkit-text-fill-color:#0f172a;background:none;color:#0f172a}
  .eyebrow,.sec-head .sub,.muted,.card p,.card ul,.pat span,.step p,.type-card p
    {color:#475569!important}
  h1,h2,h3,h4,.kpi .v,.ring-val,.type-card h4,.pat b,.step h4,.area-name,th.cov-area
    {color:#0f172a!important}
  .section,.card,.type-card,.ring-box,.area,.pat,.step,.kpi{break-inside:avoid;page-break-inside:avoid}
  .section{page-break-before:auto}
}
"""
_CSS = _CSS_1 + _CSS_2 + _CSS_3

_JS = """
(function(){
  var printBtn = document.getElementById('btn-print');
  if (printBtn) { printBtn.addEventListener('click', function(){ window.print(); }); }
  var rings = document.querySelectorAll('.ring');
  rings.forEach(function(r, i){
    var arc = r.querySelector('circle:nth-child(2)');
    if(!arc){return;}
    var d = arc.getAttribute('stroke-dasharray');
    if(!d){return;}
    arc.style.strokeDasharray = '0 ' + d.split(' ')[1];
    setTimeout(function(){ arc.style.strokeDasharray = d; }, 90 * i + 120);
  });
})();
"""

_TEMPLATE_A = Template("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Automation Strategy - UK Credit Memo AI</title>
<style>$css</style>
</head>
<body>
<div class="deck">

  <nav class="nav">
    <a href="#purpose">1 Purpose</a>
    <a href="#gates">2 Gates</a>
    <a href="#types">3 Test Types</a>
    <a href="#coverage">4 Coverage</a>
    <a href="#eval">5 Evaluation</a>
    <a href="#patterns">6 AI Patterns</a>
    <a href="#run">7 Execution</a>
    <a href="#areas">8 Areas</a>
    <a href="#reports">9 Reports</a>
    <a href="#criteria">10 Criteria</a>
    <span class="spacer"></span>
    <button id="btn-print" type="button">Print / Save PDF</button>
  </nav>

  <header class="hero">
    <div class="eyebrow">Automation Strategy &middot; QA Engineering</div>
    <h1>Automated Quality Assurance for the<br/>UK Credit Memo RAG Platform</h1>
    <p class="lede">A deterministic, offline automation programme that proves the RAG app retrieves
      the right UK standards, answers with grounded citations, extracts memos from every supported
      format, scores them against an 8-point UK checklist, renders a working UI, and stays inside
      quality gates on every run.</p>
    <div class="hero-meta">
      <span class="badge $verdict_class"><span class="dot"></span>Release verdict: $verdict_text</span>
      <span class="badge"><span class="dot"></span>$total automation test cases</span>
      <span class="badge"><span class="dot"></span>Gates passed: $gates</span>
      <span class="badge"><span class="dot"></span>Offline &amp; deterministic (no LLM, no keys)</span>
    </div>
    <div class="hero-byline">Prepared by <b>$author</b> &middot; generated $generated &middot;
      latest run $latest_run ($runs runs recorded)</div>
  </header>

  <section class="kpis">
    <div class="kpi g"><span class="bar"></span><div class="v">$total</div>
      <div class="l">Automation test cases</div><div class="s">$pass_rate% pass rate</div></div>
    <div class="kpi c"><span class="bar"></span><div class="v">$gates</div>
      <div class="l">Release gates passed</div><div class="s">Recall, Faith, Rel, Hall, p95</div></div>
    <div class="kpi v2"><span class="bar"></span><div class="v">$golden_n</div>
      <div class="l">Golden evaluation questions</div><div class="s">UK standards dataset</div></div>
    <div class="kpi b"><span class="bar"></span><div class="v">$excluded_unit</div>
      <div class="l">Unit tests excluded</div><div class="s">developer-owned, not in report</div></div>
    <div class="kpi a"><span class="bar"></span><div class="v">$p95</div>
      <div class="l">p95 latency</div><div class="s">target &le; 3.0s</div></div>
  </section>

  <section id="purpose" class="section">
    <div class="sec-head"><div class="sec-num">1</div>
      <div><h2>Purpose &amp; Scope</h2>
        <div class="sub">What this programme proves, and what it deliberately leaves out</div></div>
    </div>
    <div class="grid2">
      <div class="card">
        <h3>Purpose</h3>
        <p class="lead">Give the business a trustworthy, repeatable signal that the UK Credit Memo
          AI behaves correctly &mdash; grounded, cited, fast and safe &mdash; before every release.</p>
        <ul>
          <li>Correct retrieval of UK standards for real credit questions.</li>
          <li>Answers grounded in retrieved context, with UK citations.</li>
          <li>Robust extraction across PDF, image and text memos.</li>
          <li>Consistent UK-readiness scoring with evidence.</li>
          <li>Working UI and enforced release gates.</li>
        </ul>
      </div>
      <div class="card">
        <h3>Scope</h3>
        <p><b>In scope (automation report):</b> functional, BDD, UI automation, integration/E2E,
          regression, release gates and AI-specific checks &mdash; $total cases.</p>
        <p><b>Out of scope (kept in the codebase):</b> developer-owned <b>unit tests</b>
          (<code>test_units.py</code>, <code>unit</code> marker). They run with
          <code>pytest -q</code> but are excluded from the automation report via
          <code>-m &quot;not unit&quot;</code>.</p>
        <p class="muted small">This keeps the report meaningful for automation testers and respects
          the developers' ownership of unit tests.</p>
      </div>
    </div>
  </section>

  <section id="gates" class="section">
    <div class="sec-head"><div class="sec-num">2</div>
      <div><h2>Quality Goals &amp; Release Gates</h2>
        <div class="sub">Every gate is enforced as a failing test - a red gate blocks the release</div></div>
    </div>
    <div class="card">
      $gates_section
      <div style="margin-top:18px"><div class="small muted" style="margin-bottom:8px">Recent runs</div>
        <div class="hist-strip">$history_strip</div></div>
    </div>
  </section>

  <section id="types" class="section">
    <div class="sec-head"><div class="sec-num">3</div>
      <div><h2>Types of Testing Covered</h2>
        <div class="sub">Eleven automation disciplines across function, behaviour and AI quality</div></div>
    </div>
    $type_cards
  </section>
""")
_TEMPLATE_B = Template("""
  <section id="coverage" class="section">
    <div class="sec-head"><div class="sec-num">4</div>
      <div><h2>Coverage Matrix</h2>
        <div class="sub">Positive, negative and edge checks mapped to every business area</div></div>
    </div>
    $coverage_table
  </section>

  <section id="eval" class="section">
    <div class="sec-head"><div class="sec-num">5</div>
      <div><h2>Evaluation Checks</h2>
        <div class="sub">A 100-question golden dataset scored end-to-end, offline and deterministically</div></div>
    </div>
    <div class="grid2">
      <div class="card">
        <h3>The golden dataset</h3>
        <p><b>$golden_n UK questions</b> with a gold document and expected keywords each:
          <b>35</b> core credit &amp; regulatory, <b>35</b> affordability / IFRS 9 / conduct /
          financial crime, <b>30</b> paraphrases and UK-ised covenants &amp; policy.</p>
        <p class="muted small">Per-question rows are stored so regressions can be diffed run over run.</p>
        <h3 style="margin-top:16px">Retrieval &amp; generation metrics</h3>
        <ul>
          <li><b>Retrieval:</b> Recall@5, Precision@5, MRR, Hit@5</li>
          <li><b>Generation:</b> Faithfulness, Hallucination, Answer relevance, Correctness</li>
          <li><b>Performance:</b> p50 and p95 latency per query</li>
        </ul>
      </div>
      <div class="card">
        <h3>Latest measured results</h3>
        <div class="pat-grid" style="grid-template-columns:1fr 1fr">
          $eval_stats
        </div>
        <p class="muted small" style="margin-top:14px">Metrics are lexical heuristics (no LLM judge),
          which keeps them reproducible and free of API keys.</p>
      </div>
    </div>
  </section>

  <section id="patterns" class="section">
    <div class="sec-head"><div class="sec-num">6</div>
      <div><h2>AI-Specific Testing Patterns</h2>
        <div class="sub">What makes testing a non-deterministic RAG system meaningful</div></div>
    </div>
    <div class="card">$pattern_cards</div>
  </section>

  <section id="run" class="section">
    <div class="sec-head"><div class="sec-num">7</div>
      <div><h2>How It Runs</h2>
        <div class="sub">One command, four stages - locally and in CI</div></div>
    </div>
    <div class="card">$pipeline_flow</div>
  </section>

  <section id="areas" class="section">
    <div class="sec-head"><div class="sec-num">8</div>
      <div><h2>Automation by Area</h2>
        <div class="sub">Where the $total automation cases live, with live pass rates</div></div>
    </div>
    <div class="card"><div class="areas">$area_bars</div></div>
  </section>

  <section id="reports" class="section">
    <div class="sec-head"><div class="sec-num">9</div>
      <div><h2>Reports Produced</h2>
        <div class="sub">Visual, machine-readable and audit-friendly outputs on every run</div></div>
    </div>
    <div class="card">$artifact_list</div>
  </section>

  <section id="criteria" class="section">
    <div class="sec-head"><div class="sec-num">10</div>
      <div><h2>Entry / Exit Criteria &amp; Risk</h2>
        <div class="sub">When the suite may run, and when a release may ship</div></div>
    </div>
    <div class="grid3">
      <div class="card">
        <h3>Entry criteria</h3>
        <ul>
          <li>Dependencies installed; Tesseract present for OCR tests.</li>
          <li>UK knowledge base present (<code>uk_*.txt</code>).</li>
          <li>Evaluation report generated before the gate tests.</li>
        </ul>
      </div>
      <div class="card">
        <h3>Exit criteria</h3>
        <ul>
          <li>All $total automation cases pass.</li>
          <li>Evaluation verdict is <b>PASS</b>.</li>
          <li>Recall &ge; .90, Faith &ge; .90, Rel &ge; .90, Hall &le; .05, p95 &le; 3s.</li>
          <li>Any failing gate blocks the release.</li>
        </ul>
      </div>
      <div class="card">
        <h3>Key risks &amp; mitigations</h3>
        <ul>
          <li><b>OCR missing</b> &rarr; skip guards + actionable errors.</li>
          <li><b>Lexical metrics</b> &rarr; tuned UK synonyms + conservative gates.</li>
          <li><b>Paraphrase recall</b> &rarr; paraphrase bank + metamorphic tests.</li>
          <li><b>Unit leakage</b> &rarr; marker + filter + a test that asserts exclusion.</li>
        </ul>
      </div>
    </div>
  </section>

  <footer class="foot">
    <div><b>Automation Strategy</b> &middot; UK Credit Memo AI (FCA/PRA aligned) &middot;
      generated $generated</div>
    <div>Regenerate with <code>python build_strategy_doc.py</code> &middot;
      live dashboard at <code>reports/automation_dashboard.html</code></div>
    <div>Educational demo summarising public UK standards &mdash; not regulated advice.</div>
  </footer>

</div>
<script>$js</script>
</body>
</html>
""")
def eval_stats(g):
    """Small metric cards for the latest evaluation results."""
    agg = g["agg"]
    if not agg:
        return '<p class="muted small">No evaluation report found.</p>'
    items = [
        ("Recall@5", f"{agg.get('recall@5', 0):.2f}"),
        ("Faithfulness", f"{agg.get('faithfulness', 0):.2f}"),
        ("Answer relevance", f"{agg.get('answer_relevance', 0):.3f}"),
        ("Hallucination", f"{agg.get('hallucination', 0):.2f}"),
        ("Correctness", f"{agg.get('correctness', 0):.3f}"),
        ("MRR", f"{agg.get('mrr', 0):.3f}"),
        ("Precision@5", f"{agg.get('precision@5', 0):.3f}"),
        ("p95 latency", f"{agg.get('p95_latency_s', 0):.4f}s"),
    ]
    out = []
    for label, value in items:
        out.append(
            f'<div class="pat"><div class="pat-ic">{icon("target")}</div>'
            f'<div><b>{_esc(value)}</b><span>{_esc(label)}</span></div></div>')
    return "".join(out)


def build(out_html=DEFAULT_HTML, junit_path=None, eval_path=None, open_browser=False):
    """Render the presentation-grade strategy deck and return the path written."""
    g = gather(junit_path=junit_path, eval_path=eval_path)
    summary = g["summary"]
    agg = g["agg"]

    html_out = (_TEMPLATE_A.substitute(
        css=_CSS,
        author=_esc(AUTHOR),
        generated=_esc(g["generated"]),
        latest_run=_esc(g["latest_run"]),
        runs=g["runs"],
        verdict_class=g["verdict_class"],
        verdict_text=g["verdict"],
        total=summary["total"],
        pass_rate=f'{summary["pass_rate"]:.0f}',
        gates=f'{g["gates_passed"]}/{g["gates_total"]}' if g["gates_total"] else "-",
        golden_n=agg.get("n", 0),
        excluded_unit=summary.get("excluded_unit", 0),
        p95=f'{agg.get("p95_latency_s", 0):.3f}s' if agg else "-",
        gates_section=gates_section(g),
        history_strip=history_strip(g["history"]),
        type_cards=test_type_cards(g),
    ) + _TEMPLATE_B.substitute(
        coverage_table=coverage_table(),
        golden_n=agg.get("n", 0),
        eval_stats=eval_stats(g),
        pattern_cards=pattern_cards(),
        pipeline_flow=pipeline_flow(),
        total=summary["total"],
        area_bars=area_bars(g["by_area"]),
        artifact_list=artifact_list(),
        generated=_esc(g["generated"]),
        js=_JS,
    ))

    os.makedirs(os.path.dirname(out_html) or ".", exist_ok=True)
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html_out)

    if open_browser:
        try:
            import webbrowser
            webbrowser.open("file://" + os.path.abspath(out_html))
        except Exception:
            pass
    return out_html


def main():
    ap = argparse.ArgumentParser(
        description="Build the presentation-grade Automation Strategy document.")
    ap.add_argument("--html", default=DEFAULT_HTML, help=f"output HTML (default {DEFAULT_HTML})")
    ap.add_argument("--junit", default=None, help="JUnit feed (default: newest reports/.internal)")
    ap.add_argument("--eval", dest="eval_path", default=None, help="RAG evaluation JSON")
    ap.add_argument("--open", action="store_true", help="open in the browser")
    args = ap.parse_args()
    out = build(out_html=args.html, junit_path=args.junit, eval_path=args.eval_path,
                open_browser=args.open)
    print(f"Strategy doc: {out}")


if __name__ == "__main__":
    main()