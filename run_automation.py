"""One-command automation: RAG eval + automation pytest suite + BDD + Cucumber + HTML + dashboard.

Scope: automation tests only. Unit tests (marker ``unit``, e.g. tests/test_units.py) are
developer-owned and remain in the repo for `pytest -q`, but are excluded here via
`-m "not unit"` so the automation report never shows them.
"""
import subprocess, sys, os, datetime, webbrowser

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
os.makedirs("reports", exist_ok=True)
os.makedirs(os.path.join("reports", ".internal"), exist_ok=True)  # machine-readable feed (not a deliverable)
HTML = f"reports/automation_report_{TS}.html"
CUCUMBER = f"reports/cucumber_{TS}.json"
JUNIT = f"reports/.internal/junit_{TS}.xml"
DASHBOARD = "reports/automation_dashboard.html"
STRATEGY_DOC = "docs/automation_strategy.html"

cmds = [
    # 1. 100-question RAG evaluation -> data/eval/evaluation_report.json (gate tests read it)
    [sys.executable, "run_eval.py"],
    # 2. Automation suite only (unit tests excluded) + pytest-html + Cucumber JSON + JUnit feed
    [sys.executable, "-m", "pytest", "-q", "-m", "not unit",
     "--html", HTML, "--self-contained-html",
     "--cucumberjson", CUCUMBER, "--junitxml", JUNIT],
    # 3. Visual dashboard (pie chart, KPIs, last 3 runs) built from the JUnit feed + eval report
    [sys.executable, "build_report.py", "--junit", JUNIT, "--html", DASHBOARD,
     "--run-ts", TS],
    # 4. Presentation-grade strategy deck (self-contained, for sharing / printing to PDF)
    [sys.executable, "build_strategy_doc.py", "--junit", JUNIT,
     "--html", STRATEGY_DOC],
]

rc = 0
for c in cmds:
    print("+", " ".join(c))
    r = subprocess.run(c)
    if r.returncode != 0:
        # Keep going so the dashboard is always produced, but remember the failure.
        rc = rc or r.returncode
        print(f"FAILED ({r.returncode}): {' '.join(c)}")

print(f"\nDashboard    : {DASHBOARD}")
print(f"Strategy doc : {STRATEGY_DOC}")
print(f"pytest-html  : {HTML}")
print(f"Cucumber JSON: {CUCUMBER}")
try:
    webbrowser.open("file://" + os.path.abspath(DASHBOARD))
except Exception:
    pass
sys.exit(rc)
