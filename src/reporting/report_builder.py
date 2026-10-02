"""Builds a self-contained, visual HTML **automation** dashboard.

Audience: automation testers. The dashboard reports automation test cases only
(functional/BDD/UI/RAG/extraction/gate checks). Developer-owned **unit tests**
are excluded by default so the report never mixes them in — pass
``include_unit=True`` (CLI: ``--include-unit``) if you really want them.

Inputs  : JUnit XML (``pytest --junitxml``) + RAG evaluation JSON.
Outputs : one .html file (no external assets, opens offline) + a rolling history JSON
          so the dashboard can show the last N runs (default 3).

Usage:
    python build_report.py
    python -m src.reporting.report_builder --junit reports/.internal/junit.xml --html reports/dashboard.html
"""
import argparse
import datetime
import glob
import html as _html
import json
import math
import os
import xml.etree.ElementTree as ET
from string import Template

REPORTS_DIR = "reports"
INTERNAL_DIR = os.path.join(REPORTS_DIR, ".internal")
HISTORY_FILE = os.path.join(REPORTS_DIR, "history.json")
EVAL_REPORT = os.path.join("data", "eval", "evaluation_report.json")
DEFAULT_HTML = os.path.join(REPORTS_DIR, "automation_dashboard.html")
HISTORY_KEEP = 20   # how many runs to persist
HISTORY_SHOW = 3    # how many recent runs to display

# Test file stem -> business-friendly area (mirrors TEST_DOCUMENTATION.md coverage matrix).
_CATEGORY_RULES = [
    ("test_automation_rag", "RAG Q&A"),
    ("test_bdd_rag", "RAG Q&A"),
    ("test_automation_extract", "File Extraction"),
    ("test_bdd_memo", "Memo Extraction & Analysis"),
    ("test_automation_analyser", "Memo Analysis"),
    ("test_automation_ui", "UI Automation"),
    ("test_bdd_ui_eval", "UI & Eval Gates"),
    ("test_automation_eval", "Eval Gates"),
    ("test_rag_gates", "Eval Gates"),
    ("test_units", "Unit Tests (dev-owned)"),
]

# Evaluation metric presentation: key -> (label, unit, higher_is_better, format)
_EVAL_METRICS = [
    ("recall@5", "Recall@5", "ratio", True, "{:.2f}"),
    ("faithfulness", "Faithfulness", "ratio", True, "{:.2f}"),
    ("answer_relevance", "Answer Relevance", "ratio", True, "{:.2f}"),
    ("hallucination", "Hallucination", "ratio", False, "{:.2f}"),
    ("p95_latency_s", "p95 Latency", "seconds", False, "{:.3f}s"),
]
_GATE_KEYS = {
    "recall@5": "recall_at_5",
    "faithfulness": "faithfulness",
    "answer_relevance": "answer_relevance",
    "hallucination": "hallucination",
    "p95_latency_s": "p95_latency_s",
}


def category_of(nodeid):
    """Map a test node id to a business area label."""
    for stem, label in _CATEGORY_RULES:
        if stem in nodeid:
            return label
    return "Other"


def is_unit_test(nodeid):
    """True for developer-owned unit tests (e.g. tests/test_units.py).

    Identified by file name so it works even when the ``unit`` marker is not
    carried into the JUnit XML.
    """
    path = nodeid.split("::")[0].replace("\\", "/").lower()
    return path.rsplit("/", 1)[-1].startswith("test_unit")


def parse_junit(path, include_unit=False):
    """Parse a JUnit XML file -> (summary dict, list of test-case dicts).

    By default unit tests are filtered out so the automation report stays
    automation-only. ``summary["excluded_unit"]`` records how many were dropped.
    """
    empty = {"total": 0, "passed": 0, "failed": 0, "skipped": 0,
             "duration_s": 0.0, "pass_rate": 0.0, "excluded_unit": 0}
    if not path or not os.path.exists(path):
        return empty, []
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root)
    cases = []
    for suite in suites:
        for tc in suite.iter("testcase"):
            cls = tc.get("classname", "") or ""
            name = tc.get("name", "") or ""
            nodeid = (cls.replace(".", "/") + "::" + name) if cls else name
            status, detail = "passed", ""
            for child in tc:
                if child.tag in ("failure", "error"):
                    status = "failed"
                    detail = (child.get("message") or child.text or "").strip()
                    break
                if child.tag == "skipped":
                    status = "skipped"
                    detail = (child.get("message") or "").strip()
                    break
            cases.append({
                "nodeid": nodeid,
                "module": cls,
                "name": name,
                "status": status,
                "time": float(tc.get("time") or 0.0),
                "detail": " ".join(detail.split())[:400],
                "category": category_of(nodeid),
                "is_unit": is_unit_test(nodeid),
            })
    excluded = 0 if include_unit else sum(1 for c in cases if c["is_unit"])
    if not include_unit:
        cases = [c for c in cases if not c["is_unit"]]
    counts = {k: sum(1 for c in cases if c["status"] == k)
              for k in ("passed", "failed", "skipped")}
    summary = {
        "total": len(cases),
        "passed": counts["passed"],
        "failed": counts["failed"],
        "skipped": counts["skipped"],
        "duration_s": round(sum(c["time"] for c in cases), 2),
        "excluded_unit": excluded,
    }
    summary["pass_rate"] = (round(100.0 * summary["passed"] / summary["total"], 1)
                            if summary["total"] else 0.0)
    return summary, cases


def load_eval(path=EVAL_REPORT):
    """Load the RAG evaluation report, or None when it has not been generated."""
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def load_history(path=HISTORY_FILE):
    if path and os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (ValueError, OSError):
            return []
    return []


def verdict_of(summary, eval_rep):
    """Overall release verdict -> (label, css class, one-line explanation)."""
    tests_ok = summary["total"] > 0 and summary["failed"] == 0
    eval_ok = bool(eval_rep and eval_rep.get("verdict") == "PASS")
    if tests_ok and eval_ok:
        return "PASS", "pass", "All test cases passed and every RAG release gate is green."
    reasons = []
    if not tests_ok:
        reasons.append(f"{summary['failed']} test(s) failing")
    if eval_rep is None:
        reasons.append("RAG evaluation report missing")
    elif not eval_ok:
        reasons.append("one or more RAG release gates failed")
    return "FAIL", "fail", "; ".join(reasons).capitalize() + "."


def update_history(summary, eval_rep, run_ts, path=HISTORY_FILE):
    """Append the current run to the rolling history and return the full list."""
    label, _, _ = verdict_of(summary, eval_rep)
    hist = [h for h in load_history(path) if h.get("ts") != run_ts]
    hist.append({
        "ts": run_ts,
        "total": summary["total"],
        "passed": summary["passed"],
        "failed": summary["failed"],
        "skipped": summary["skipped"],
        "pass_rate": summary["pass_rate"],
        "duration_s": summary["duration_s"],
        "verdict": label,
    })
    hist = hist[-HISTORY_KEEP:]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(hist, f, indent=1)
    return hist


def newest_junit(reports_dir=REPORTS_DIR):
    """Return the most recently written JUnit XML (searches reports/ and reports/.internal/)."""
    files = glob.glob(os.path.join(reports_dir, "junit_*.xml"))
    files += glob.glob(os.path.join(reports_dir, ".internal", "junit_*.xml"))
    if not files:
        return None
    return max(files, key=os.path.getmtime)

# --------------------------------------------------------------------------- #
# Chart / fragment renderers (inline SVG, no external libraries)              #
# --------------------------------------------------------------------------- #

def _esc(text):
    return _html.escape(str(text), quote=True)


def donut_chart(segments, size=240, stroke=32, center_top="TOTAL", center_big=""):
    """Render an SVG donut (pie) chart. `segments` = list of label/value/color."""
    r = (size - stroke) / 2.0
    cx = cy = size / 2.0
    circ = 2 * math.pi * r
    total = sum(s["value"] for s in segments) or 1
    arcs = [f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" fill="none" '
            f'stroke="#22304a" stroke-width="{stroke:g}"/>']
    offset = 0.0
    for seg in segments:
        frac = seg["value"] / total
        if frac <= 0:
            continue
        dash = frac * circ
        arcs.append(
            f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" fill="none" '
            f'stroke="{seg["color"]}" stroke-width="{stroke:g}" '
            f'stroke-dasharray="{dash:.3f} {circ - dash:.3f}" '
            f'stroke-dashoffset="{-offset:.3f}" transform="rotate(-90 {cx:g} {cy:g})" '
            f'stroke-linecap="butt">'
            f'<title>{_esc(seg["label"])}: {seg["value"]}</title></circle>')
        offset += dash
    big = center_big if center_big != "" else str(total)
    center = (f'<text x="{cx:g}" y="{cy - 2:g}" text-anchor="middle" '
              f'class="donut-big">{_esc(big)}</text>'
              f'<text x="{cx:g}" y="{cy + 22:g}" text-anchor="middle" '
              f'class="donut-cap">{_esc(center_top)}</text>')
    return (f'<svg class="donut" viewBox="0 0 {size} {size}" role="img" '
            f'aria-label="test outcome distribution">'
            f'{"".join(arcs)}{center}</svg>')


def donut_legend(segments):
    rows = []
    for seg in segments:
        rows.append(
            f'<li><span class="dot" style="background:{seg["color"]}"></span>'
            f'<span class="lg-label">{_esc(seg["label"])}</span>'
            f'<span class="lg-value">{seg["value"]}</span></li>')
    return f'<ul class="legend">{"".join(rows)}</ul>'


def radial_gauge(label, value_text, arc, passed, sub="", size=132, stroke=11):
    """Small circular gauge. `arc` is 0..1 of the ring to fill."""
    r = (size - stroke) / 2.0
    cx = cy = size / 2.0
    circ = 2 * math.pi * r
    arc = max(0.0, min(1.0, arc))
    color = "#22c55e" if passed else "#ef4444"
    track = f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" fill="none" ' \
            f'stroke="#22304a" stroke-width="{stroke:g}"/>'
    fill = (f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" fill="none" stroke="{color}" '
            f'stroke-width="{stroke:g}" stroke-linecap="round" '
            f'stroke-dasharray="{arc * circ:.3f} {circ:.3f}" '
            f'transform="rotate(-90 {cx:g} {cy:g})"/>')
    txt = (f'<text x="{cx:g}" y="{cy + 4:g}" text-anchor="middle" class="gauge-val">'
           f'{_esc(value_text)}</text>'
           f'<text x="{cx:g}" y="{cy + 22:g}" text-anchor="middle" class="gauge-sub">'
           f'{_esc(sub)}</text>')
    chip = "chip-pass" if passed else "chip-fail"
    chip_txt = "PASS" if passed else "FAIL"
    return (f'<div class="gauge-box"><svg class="gauge" viewBox="0 0 {size} {size}" '
            f'role="img" aria-label="{_esc(label)} gauge">{track}{fill}{txt}</svg>'
            f'<div class="gauge-label">{_esc(label)}</div>'
            f'<span class="chip {chip}">{chip_txt}</span></div>')


def category_bars(summary_by_cat, total):
    """Horizontal bars: passed / failed / skipped per business area."""
    if not summary_by_cat:
        return '<p class="muted">No test cases found.</p>'
    rows = []
    for cat, c in sorted(summary_by_cat.items(), key=lambda kv: -kv[1]["total"]):
        t = c["total"] or 1
        p_pct = 100.0 * c["passed"] / t
        f_pct = 100.0 * c["failed"] / t
        s_pct = 100.0 * c["skipped"] / t
        rate = 100.0 * c["passed"] / t
        badge = "b-ok" if c["failed"] == 0 else "b-bad"
        rows.append(
            f'<div class="bar-row">'
            f'<div class="bar-head"><span class="bar-name">{_esc(cat)}</span>'
            f'<span class="bar-meta">{c["passed"]}/{c["total"]} '
            f'<span class="rate {badge}">{rate:.0f}%</span></span></div>'
            f'<div class="bar-track">'
            f'<span class="bar-seg s-pass" style="width:{p_pct:.2f}%"></span>'
            f'<span class="bar-seg s-fail" style="width:{f_pct:.2f}%"></span>'
            f'<span class="bar-seg s-skip" style="width:{s_pct:.2f}%"></span>'
            f'</div></div>')
    return "".join(rows)

def eval_section(eval_rep):
    """Radial gauges for the 100-question RAG evaluation."""
    if not eval_rep:
        return ('<div class="empty">No RAG evaluation report found. Run '
                '<code>python run_eval.py</code> to generate '
                '<code>data/eval/evaluation_report.json</code>.</div>')
    agg = eval_rep.get("aggregate", {})
    checks = eval_rep.get("checks", {})
    gates = []
    for key, label, unit, higher, fmt in _EVAL_METRICS:
        if key not in agg:
            continue
        val = float(agg[key])
        gate_key = _GATE_KEYS.get(key)
        passed = bool(checks.get(gate_key, True))
        if unit == "seconds":
            arc = max(0.0, min(1.0, 1.0 - val / 3.0))
            sub = "target <=3.0s"
        elif higher:
            arc = max(0.0, min(1.0, val))
            sub = "higher is better"
        else:
            arc = max(0.0, min(1.0, 1.0 - val))
            sub = "lower is better"
        gates.append(radial_gauge(label, fmt.format(val), arc, passed, sub))
    n = agg.get("n", 0)
    extra = [
        ("Questions", n),
        ("Precision@5", f"{agg.get('precision@5', 0):.3f}"),
        ("MRR", f"{agg.get('mrr', 0):.3f}"),
        ("Hit@5", f"{agg.get('hit@5', 0):.3f}"),
        ("Correctness", f"{agg.get('correctness', 0):.3f}"),
        ("p50 Latency", f"{agg.get('p50_latency_s', 0):.4f}s"),
    ]
    chips = "".join(f'<span class="mini-stat"><b>{_esc(v)}</b>{_esc(k)}</span>'
                    for k, v in extra)
    return (f'<div class="gauges">{"".join(gates)}</div>'
            f'<div class="mini-stats">{chips}</div>')


def _fmt_ts(ts):
    try:
        return datetime.datetime.strptime(ts, "%Y%m%d_%H%M%S").strftime("%d %b %Y, %H:%M:%S")
    except (ValueError, TypeError):
        return str(ts)


def recent_runs_section(hist):
    """Cards for the last N runs + a stacked-bar trend chart."""
    recent = list(reversed(hist))[:HISTORY_SHOW]
    if not recent:
        return '<div class="empty">No run history yet.</div>'
    cards = []
    max_total = max((r["total"] for r in recent), default=1) or 1
    for i, r in enumerate(recent):
        hp = 150.0 * r.get("passed", 0) / max_total
        hf = 150.0 * r.get("failed", 0) / max_total
        hs = 150.0 * r.get("skipped", 0) / max_total
        v_cls = "pass" if r.get("verdict") == "PASS" else "fail"
        tag = "Latest run" if i == 0 else f"{i + 1} runs ago"
        cards.append(
            f'<div class="run-card{" latest" if i == 0 else ""}">'
            f'<div class="run-top"><span class="run-tag">{_esc(tag)}</span>'
            f'<span class="pill {v_cls}">{_esc(r.get("verdict", "?"))}</span></div>'
            f'<div class="run-when">{_esc(_fmt_ts(r.get("ts", "")))}</div>'
            f'<div class="run-bars">'
            f'<span class="vb s-pass" style="height:{hp:.1f}px" '
            f'title="passed {r.get("passed", 0)}"></span>'
            f'<span class="vb s-fail" style="height:{hf:.1f}px" '
            f'title="failed {r.get("failed", 0)}"></span>'
            f'<span class="vb s-skip" style="height:{hs:.1f}px" '
            f'title="skipped {r.get("skipped", 0)}"></span>'
            f'</div>'
            f'<div class="run-stats">'
            f'<span><b>{r.get("total", 0)}</b>total</span>'
            f'<span class="ok"><b>{r.get("passed", 0)}</b>pass</span>'
            f'<span class="bad"><b>{r.get("failed", 0)}</b>fail</span>'
            f'<span class="warn"><b>{r.get("skipped", 0)}</b>skip</span>'
            f'</div>'
            f'<div class="run-foot">{r.get("pass_rate", 0):.1f}% pass rate'
            f' &middot; {r.get("duration_s", 0)}s</div>'
            f'</div>')
    return (f'<div class="run-grid">{"".join(cards)}</div>'
            f'<p class="muted small">Stacked bars are scaled to the largest run '
            f'({max_total} tests). Green = passed, red = failed, amber = skipped.</p>')
def kpi_cards(summary, eval_rep):
    total = summary["total"]
    rate = summary["pass_rate"]
    avg = (summary["duration_s"] / total) if total else 0.0
    cards = [
        ("clipboard", "Total Test Cases", f"{total}", "collected in this run", ""),
        ("check", "Passed", f"{summary['passed']}", f"{rate:.1f}% pass rate", "ok"),
        ("x", "Failed", f"{summary['failed']}",
         "needs attention" if summary["failed"] else "none", "bad" if summary["failed"] else ""),
        ("pause", "Skipped", f"{summary['skipped']}",
         "not executed" if summary["skipped"] else "none", "warn" if summary["skipped"] else ""),
        ("clock", "Duration", f"{summary['duration_s']}s", f"{avg:.3f}s avg/test", ""),
    ]
    html_cards = []
    for icon, label, value, sub, cls in cards:
        html_cards.append(
            f'<div class="kpi {cls}">'
            f'<div class="kpi-ic ic-{cls or "base"}">{_ICONS[icon]}</div>'
            f'<div class="kpi-body"><div class="kpi-val">{_esc(value)}</div>'
            f'<div class="kpi-lbl">{_esc(label)}</div>'
            f'<div class="kpi-sub">{_esc(sub)}</div></div></div>')
    return "".join(html_cards)


def test_table(cases):
    if not cases:
        return '<p class="muted">No test cases were collected.</p>'
    stat_cls = {"passed": "st-pass", "failed": "st-fail", "skipped": "st-skip"}
    rows = []
    for c in cases:
        detail = (f'<div class="tc-detail">{_esc(c["detail"])}</div>'
                  if c["detail"] else "")
        rows.append(
            f'<tr data-id="{_esc(c["nodeid"])}" data-status="{c["status"]}">'
            f'<td><span class="status-dot {stat_cls[c["status"]]}"></span>'
            f'{c["status"].upper()}</td>'
            f'<td class="tc-area">{_esc(c["category"])}</td>'
            f'<td class="tc-name">{_esc(c["nodeid"])}{detail}</td>'
            f'<td class="num">{c["time"]:.3f}s</td></tr>')
    return (
        f'<div class="tc-controls">'
        f'<input id="tc-search" type="search" placeholder="Search test name..."/>'
        f'<select id="tc-filter">'
        f'<option value="all">All statuses</option>'
        f'<option value="passed">Passed</option>'
        f'<option value="failed">Failed</option>'
        f'<option value="skipped">Skipped</option>'
        f'</select>'
        f'<span id="tc-count" class="muted small"></span></div>'
        f'<div class="table-wrap"><table id="tc-table"><thead><tr>'
        f'<th>Result</th><th>Area</th><th>Test case</th><th class="num">Time</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


_ICONS = {
    "clipboard": '<svg viewBox="0 0 24 24"><path d="M9 2h6a2 2 0 0 1 2 2h1a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h1a2 2 0 0 1 2-2z"/><path d="M9 4v2h6V4"/></svg>',
    "check": '<svg viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5"/></svg>',
    "x": '<svg viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12"/></svg>',
    "pause": '<svg viewBox="0 0 24 24"><path d="M8 5v14M16 5v14"/></svg>',
    "clock": '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
}
_CSS_1 = """
:root{
  --bg:#070b16;--panel:rgba(17,25,44,.72);--panel2:#111a2c;--line:#22304a;
  --txt:#e8eefc;--muted:#93a3c0;--green:#22c55e;--red:#ef4444;--amber:#f59e0b;
  --blue:#3b82f6;--violet:#8b5cf6;--cyan:#22d3ee;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  background:var(--bg);color:var(--txt);min-height:100vh;
  font-family:"Segoe UI",system-ui,-apple-system,Roboto,Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased;line-height:1.45;overflow-x:hidden;
}
body::before{
  content:"";position:fixed;inset:0;z-index:0;pointer-events:none;
  background:
    radial-gradient(60rem 40rem at 12% -8%,rgba(59,130,246,.20),transparent 60%),
    radial-gradient(48rem 34rem at 92% 4%,rgba(139,92,246,.18),transparent 62%),
    radial-gradient(52rem 38rem at 70% 108%,rgba(34,211,238,.14),transparent 60%);
}
.wrap{position:relative;z-index:1;max-width:1220px;margin:0 auto;padding:30px 22px 60px}
a{color:var(--cyan)}
h1,h2,h3{margin:0;font-weight:800;letter-spacing:.2px}
.muted{color:var(--muted)}
.small{font-size:12.5px}
code{background:#0b1424;border:1px solid var(--line);border-radius:6px;
  padding:1px 6px;font-family:Consolas,Monaco,monospace;font-size:12.5px;color:#cfe0ff}

/* ---------- hero ---------- */
.hero{
  display:flex;flex-wrap:wrap;gap:22px;align-items:center;justify-content:space-between;
  padding:26px 30px;border-radius:22px;
  background:linear-gradient(135deg,rgba(29,44,80,.92),rgba(12,19,35,.92));
  border:1px solid var(--line);box-shadow:0 24px 60px rgba(2,6,20,.55);
  position:relative;overflow:hidden;
}
.hero::after{
  content:"";position:absolute;inset:-2px;border-radius:22px;pointer-events:none;
  background:linear-gradient(120deg,rgba(34,211,238,.45),rgba(139,92,246,.35),rgba(59,130,246,.35));
  -webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);
  mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);
  -webkit-mask-composite:xor;mask-composite:exclude;padding:1px;opacity:.9;
}
.brand{display:inline-block;font-size:12.5px;letter-spacing:1.6px;text-transform:uppercase;
  color:var(--cyan);font-weight:700;margin-bottom:8px}
.hero h1{font-size:34px;line-height:1.1;
  background:linear-gradient(90deg,#ffffff,#a9c6ff 55%,#7ef0e0);
  -webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
.hero .sub{color:var(--muted);font-size:13.5px;margin-top:10px}
.hero .sub b{color:#dbe7ff}
.verdict{font-size:34px;font-weight:900;letter-spacing:2px;padding:6px 22px;border-radius:16px;
  display:inline-block;line-height:1.25}
.verdict.pass{color:#062b12;background:linear-gradient(135deg,#34d399,#22c55e);
  box-shadow:0 0 0 1px rgba(34,197,94,.5),0 12px 40px rgba(34,197,94,.35)}
.verdict.fail{color:#2b0606;background:linear-gradient(135deg,#fb7185,#ef4444);
  box-shadow:0 0 0 1px rgba(239,68,68,.5),0 12px 40px rgba(239,68,68,.35)}
.verdict-sub{color:var(--muted);font-size:12.5px;margin-top:10px;max-width:290px}
.scope-note{color:#9fb2d4;font-size:12px;margin-top:10px}
.scope-note code{font-size:11.5px}

/* ---------- kpis ---------- */
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin:22px 0}
.kpi{display:flex;gap:14px;align-items:center;padding:18px;border-radius:18px;
  background:var(--panel);border:1px solid var(--line);backdrop-filter:blur(9px);
  transition:transform .18s ease,box-shadow .18s ease}
.kpi:hover{transform:translateY(-3px);box-shadow:0 18px 42px rgba(2,6,20,.5)}
.kpi-ic{width:46px;height:46px;flex:0 0 46px;border-radius:14px;display:grid;place-items:center}
.kpi-ic svg{width:24px;height:24px;fill:none;stroke-width:2.1;stroke-linecap:round;stroke-linejoin:round}
.ic-base{background:rgba(59,130,246,.16);stroke:var(--blue)}
.ic-base svg{stroke:var(--blue)}
.ic-ok{background:rgba(34,197,94,.16)} .ic-ok svg{stroke:var(--green)}
.ic-bad{background:rgba(239,68,68,.16)} .ic-bad svg{stroke:var(--red)}
.ic-warn{background:rgba(245,158,11,.16)} .ic-warn svg{stroke:var(--amber)}
.kpi-val{font-size:30px;font-weight:900;line-height:1}
.kpi-lbl{font-size:12.5px;color:#c7d6f2;font-weight:600;margin-top:2px}
.kpi-sub{font-size:11.5px;color:var(--muted)}
.kpi.ok .kpi-val{color:var(--green)} .kpi.bad .kpi-val{color:var(--red)}
.kpi.warn .kpi-val{color:var(--amber)}
"""
_CSS_2 = """
/* ---------- layout cards ---------- */
.grid2{display:grid;grid-template-columns:minmax(300px,1.05fr) minmax(320px,1.4fr);gap:18px}
@media(max-width:880px){.grid2{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:22px 24px;
  backdrop-filter:blur(9px);box-shadow:0 18px 46px rgba(2,6,20,.4);margin-top:18px}
.card h2{font-size:16.5px;display:flex;align-items:center;gap:10px;margin-bottom:16px}
.card h2::before{content:"";width:5px;height:19px;border-radius:3px;
  background:linear-gradient(180deg,var(--cyan),var(--violet))}
.card .hint{color:var(--muted);font-size:12.5px;margin:-8px 0 14px}
.empty{padding:22px;border:1px dashed var(--line);border-radius:14px;color:var(--muted);
  text-align:center;font-size:13.5px}

/* ---------- donut ---------- */
.donut-holder{display:flex;gap:26px;align-items:center;flex-wrap:wrap;justify-content:center}
.donut{width:240px;height:240px;filter:drop-shadow(0 12px 30px rgba(2,6,20,.55))}
.donut circle{transition:stroke-dashoffset .8s cubic-bezier(.3,1,.4,1)}
.donut-big{font-size:34px;font-weight:900;fill:#eaf1ff}
.donut-cap{font-size:12px;font-weight:700;letter-spacing:1.6px;fill:#8ea3c6}
.legend{list-style:none;margin:0;padding:0;min-width:180px}
.legend li{display:flex;align-items:center;gap:10px;padding:9px 0;font-size:14px;
  border-bottom:1px dashed rgba(34,48,74,.8)}
.legend li:last-child{border-bottom:0}
.dot{width:12px;height:12px;border-radius:50%;flex:0 0 12px}
.lg-label{flex:1;color:#cddbf5}
.lg-value{font-weight:800;font-size:16px}

/* ---------- category bars ---------- */
.bar-row{margin-bottom:14px}
.bar-head{display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px}
.bar-name{color:#d6e2fa;font-weight:600}
.bar-meta{color:var(--muted)}
.rate{font-weight:800;padding:1px 8px;border-radius:20px;margin-left:6px;font-size:11.5px}
.b-ok{background:rgba(34,197,94,.15);color:#4ade80}
.b-bad{background:rgba(239,68,68,.15);color:#fca5a5}
.bar-track{display:flex;height:13px;border-radius:8px;overflow:hidden;background:#0c1526;
  border:1px solid var(--line)}
.bar-seg{display:block;height:100%}
.s-pass{background:linear-gradient(90deg,#16a34a,#4ade80)}
.s-fail{background:linear-gradient(90deg,#b91c1c,#f87171)}
.s-skip{background:linear-gradient(90deg,#b45309,#fbbf24)}

/* ---------- gauges ---------- */
.gauges{display:grid;grid-template-columns:repeat(auto-fit,minmax(148px,1fr));gap:14px}
.gauge-box{display:flex;flex-direction:column;align-items:center;gap:6px;padding:14px 8px;
  border-radius:16px;background:rgba(9,15,28,.6);border:1px solid var(--line)}
.gauge{width:132px;height:132px}
.gauge circle{transition:stroke-dasharray .9s cubic-bezier(.3,1,.4,1)}
.gauge-val{font-size:22px;font-weight:900;fill:#f2f7ff}
.gauge-sub{font-size:9.5px;fill:#8ea3c6}
.gauge-label{font-size:12.5px;font-weight:700;color:#d6e2fa;text-align:center}
.chip{font-size:10px;font-weight:800;letter-spacing:1px;padding:2px 10px;border-radius:20px}
.chip-pass{background:rgba(34,197,94,.18);color:#4ade80}
.chip-fail{background:rgba(239,68,68,.18);color:#fca5a5}
.mini-stats{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}
.mini-stat{background:rgba(9,15,28,.7);border:1px solid var(--line);border-radius:12px;
  padding:9px 14px;font-size:11.5px;color:var(--muted);display:flex;flex-direction:column}
.mini-stat b{color:#e8eefc;font-size:15px;font-weight:800}
"""
_CSS_3 = """
/* ---------- recent runs ---------- */
.run-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}
.run-card{background:rgba(9,15,28,.62);border:1px solid var(--line);border-radius:18px;padding:16px}
.run-card.latest{border-color:rgba(34,211,238,.55);box-shadow:0 0 0 1px rgba(34,211,238,.25)}
.run-top{display:flex;justify-content:space-between;align-items:center}
.run-tag{font-size:11px;letter-spacing:1.3px;text-transform:uppercase;color:var(--cyan);font-weight:700}
.pill{font-size:10.5px;font-weight:800;letter-spacing:1px;padding:3px 10px;border-radius:20px}
.pill.pass{background:rgba(34,197,94,.18);color:#4ade80}
.pill.fail{background:rgba(239,68,68,.18);color:#fca5a5}
.run-when{font-size:12px;color:var(--muted);margin:6px 0 12px}
.run-bars{display:flex;align-items:flex-end;gap:6px;height:152px;padding-bottom:6px;
  border-bottom:1px solid var(--line)}
.vb{width:100%;border-radius:6px 6px 0 0;min-height:3px}
.run-stats{display:flex;flex-wrap:wrap;gap:10px;margin-top:12px;font-size:11px;color:var(--muted)}
.run-stats b{display:block;font-size:16px;color:#e8eefc}
.run-stats .ok b{color:#4ade80}.run-stats .bad b{color:#fca5a5}.run-stats .warn b{color:#fbbf24}
.run-foot{margin-top:12px;font-size:12px;color:#bcd0f0;font-weight:600}

/* ---------- test table ---------- */
.tc-controls{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
.tc-controls input,.tc-controls select{background:#0b1424;border:1px solid var(--line);
  color:var(--txt);border-radius:10px;padding:9px 13px;font-size:13px;min-width:190px;outline:none}
.tc-controls input:focus,.tc-controls select:focus{border-color:var(--cyan)}
.table-wrap{max-height:620px;overflow:auto;border:1px solid var(--line);border-radius:14px}
table{border-collapse:collapse;width:100%;font-size:12.8px}
thead th{position:sticky;top:0;background:#101a2e;text-align:left;padding:11px 14px;
  color:#a9c0e6;font-weight:700;font-size:11.5px;letter-spacing:1px;text-transform:uppercase;
  border-bottom:1px solid var(--line);z-index:2}
tbody td{padding:10px 14px;border-bottom:1px solid rgba(34,48,74,.55);vertical-align:top}
tbody tr:hover{background:rgba(59,130,246,.07)}
.num{text-align:right;color:#bcd0f0;white-space:nowrap}
.tc-area{color:#a9bde0;white-space:nowrap}
.tc-name{font-family:Consolas,Monaco,monospace;font-size:12px;color:#dbe7ff;word-break:break-word}
.tc-detail{margin-top:5px;color:#fca5a5;font-size:11.5px}
.status-dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:8px}
.st-pass{background:var(--green);box-shadow:0 0 10px rgba(34,197,94,.7)}
.st-fail{background:var(--red);box-shadow:0 0 10px rgba(239,68,68,.7)}
.st-skip{background:var(--amber);box-shadow:0 0 10px rgba(245,158,11,.7)}
td:first-child{white-space:nowrap;font-weight:700;font-size:11.5px;color:#c7d6f2}
"""
_CSS = _CSS_1 + _CSS_2 + _CSS_3

_JS = """
(function(){
  var search=document.getElementById('tc-search');
  var filter=document.getElementById('tc-filter');
  var counter=document.getElementById('tc-count');
  var rows=Array.prototype.slice.call(document.querySelectorAll('#tc-table tbody tr'));
  function apply(){
    var q=(search.value||'').toLowerCase();
    var f=filter.value;
    var shown=0;
    rows.forEach(function(r){
      var okQ=r.getAttribute('data-id').toLowerCase().indexOf(q)!==-1;
      var okF=(f==='all')||(r.getAttribute('data-status')===f);
      var vis=okQ&&okF;
      r.style.display=vis?'':'none';
      if(vis){shown++;}
    });
    counter.textContent=shown+' / '+rows.length+' shown';
  }
  search.addEventListener('input',apply);
  filter.addEventListener('change',apply);
  apply();
  var donut=document.querySelector('.donut');
  if(donut){
    var arcs=donut.querySelectorAll('circle');
    arcs.forEach(function(c,i){
      var d=c.getAttribute('stroke-dasharray');
      if(!d){return;}
      c.style.strokeDasharray='0 '+d.split(' ')[1];
      setTimeout(function(){c.style.strokeDasharray=d;},60*i+80);
    });
  }
})();
"""

_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>UK Credit Memo AI - Automation Dashboard</title>
<style>$css</style>
</head>
<body>
<div class="wrap">

  <header class="hero">
    <div class="hero-left">
      <div class="brand">UK Credit Memo AI &middot; Local RAG (FCA/PRA aligned)</div>
      <h1>Automation Test Dashboard</h1>
      <div class="sub">Run <b>$run_ts_pretty</b> &middot; generated $generated<br/>
        Source: <b>$total</b> automation test cases + <b>$eval_n</b>-question RAG evaluation</div>
      <div class="scope-note">$scope_note</div>
    </div>
    <div class="hero-right">
      <div class="verdict $verdict_class">$verdict_text</div>
      <div class="verdict-sub">$verdict_sub</div>
    </div>
  </header>

  <section class="kpis">$kpis</section>

  <section class="grid2">
    <div class="card">
      <h2>Test Outcome Distribution</h2>
      <div class="donut-holder">
        $donut
        $legend
      </div>
    </div>
    <div class="card">
      <h2>Pass Rate by Area</h2>
      <p class="hint">Grouped by business area; segments show passed / failed / skipped.</p>
      $category_bars
    </div>
  </section>

  <section class="card">
    <h2>RAG Evaluation &mdash; 100 UK Questions</h2>
    <p class="hint">Each gauge fills with the "goodness" of the metric; chip shows the release gate.</p>
    $eval_section
  </section>

  <section class="card">
    <h2>Last $history_show Runs</h2>
    $recent_runs
  </section>

  <section class="card">
    <h2>All Test Cases ($total)</h2>
    $test_table
  </section>

</div>
<script>$js</script>
</body>
</html>
""")
def _pretty_ts(ts):
    try:
        dt = datetime.datetime.strptime(ts, "%Y%m%d_%H%M%S")
        return dt.strftime("%d %b %Y at %H:%M:%S")
    except (ValueError, TypeError):
        return str(ts)


def build(junit_path=None, out_html=DEFAULT_HTML, eval_path=None,
          run_ts=None, history_path=None, open_browser=False, include_unit=False):
    """Render the dashboard and return the HTML path written."""
    junit_path = junit_path or newest_junit()
    eval_path = eval_path or EVAL_REPORT
    history_path = history_path or HISTORY_FILE
    run_ts = run_ts or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    summary, cases = parse_junit(junit_path, include_unit=include_unit)
    eval_rep = load_eval(eval_path)
    hist = update_history(summary, eval_rep, run_ts, path=history_path)

    label, v_class, v_sub = verdict_of(summary, eval_rep)

    # Donut: draw only non-zero slices (keeps the ring clean), but always list all
    # three outcome categories in the legend so Passed / Failed / Skipped are explicit.
    all_segments = [
        {"label": "Passed", "value": summary["passed"], "color": "#22c55e"},
        {"label": "Failed", "value": summary["failed"], "color": "#ef4444"},
        {"label": "Skipped", "value": summary["skipped"], "color": "#f59e0b"},
    ]
    donut_segments = [s for s in all_segments if s["value"] > 0]
    if not donut_segments:
        donut_segments = [{"label": "No tests", "value": 1, "color": "#334155"}]
    donut = donut_chart(donut_segments, center_big=str(summary["total"]))

    by_cat = {}
    for c in cases:
        row = by_cat.setdefault(c["category"], {"total": 0, "passed": 0,
                                                "failed": 0, "skipped": 0})
        row["total"] += 1
        row[c["status"]] += 1

    eval_n = (eval_rep or {}).get("aggregate", {}).get("n", 0)

    if include_unit:
        scope_note = "Scope: automation tests (+ unit tests included via --include-unit)."
    elif summary["excluded_unit"]:
        scope_note = (f"Scope: automation tests only &mdash; {summary['excluded_unit']} "
                      f"developer-owned unit test(s) excluded from this report "
                      f"(they remain in the code and run with <code>pytest -q</code>).")
    else:
        scope_note = "Scope: automation tests only (developer-owned unit tests excluded)."

    html_out = _TEMPLATE.substitute(
        css=_CSS,
        js=_JS,
        run_ts_pretty=_esc(_pretty_ts(run_ts)),
        generated=_esc(datetime.datetime.now().strftime("%d %b %Y %H:%M:%S")),
        total=summary["total"],
        eval_n=eval_n,
        scope_note=scope_note,
        verdict_class=v_class,
        verdict_text=label,
        verdict_sub=_esc(v_sub),
        kpis=kpi_cards(summary, eval_rep),
        donut=donut,
        legend=donut_legend(all_segments),
        category_bars=category_bars(by_cat, summary["total"]),
        eval_section=eval_section(eval_rep),
        history_show=HISTORY_SHOW,
        recent_runs=recent_runs_section(hist),
        test_table=test_table(cases),
    )

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
        description="Build the visual, self-contained RAG automation dashboard.")
    ap.add_argument("--junit", default=None,
                    help="JUnit XML produced by pytest --junitxml")
    ap.add_argument("--html", default=DEFAULT_HTML, help="output HTML path")
    ap.add_argument("--eval", dest="eval_path", default=None,
                    help="RAG evaluation JSON (default data/eval/evaluation_report.json)")
    ap.add_argument("--history", default=None, help="rolling history JSON path")
    ap.add_argument("--run-ts", dest="run_ts", default=None,
                    help="run timestamp YYYYMMDD_HHMMSS (defaults to now)")
    ap.add_argument("--open", action="store_true", help="open the report in a browser")
    ap.add_argument("--include-unit", dest="include_unit", action="store_true",
                    help="also include developer-owned unit tests (excluded by default)")
    args = ap.parse_args()
    out = build(junit_path=args.junit, out_html=args.html, eval_path=args.eval_path,
                run_ts=args.run_ts, history_path=args.history, open_browser=args.open,
                include_unit=args.include_unit)
    print(f"Dashboard: {out}")


if __name__ == "__main__":
    main()