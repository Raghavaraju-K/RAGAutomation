# Documentation

Start here depending on what you need:

| Document | Audience | What it covers |
|---|---|---|
| [automation_strategy.html](automation_strategy.html) | Anyone you present to | **Visual strategy deck**: hero + KPIs, quality gates, test types, coverage matrix, AI patterns, pipeline, entry/exit criteria. Open it, share it, or `Ctrl+P` to save a PDF |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Engineers, reviewers, new joiners | System + test + reporting architecture, component responsibilities, data flows, design decisions |
| [AUTOMATION_STRATEGY.md](AUTOMATION_STRATEGY.md) | Automation testers, QA leads | Automation approach, test types, coverage matrix, RAG/AI evaluation checks, gates, test data, entry/exit criteria |
| [ONBOARDING.md](ONBOARDING.md) | New automation testers | Prerequisites, 10-minute quickstart, repo tour, how to add tests, troubleshooting, first-PR checklist |

## TL;DR

```
pip install -r requirements.txt
python run_automation.py     # runs RAG eval + automation suite, builds the visual dashboard
```

Open **`reports/automation_dashboard.html`** — pie chart of Pass/Fail/Skipped, KPI totals,
RAG metric gauges, last 3 runs, and a searchable table of every **automation** test case.

- **Automation report scope:** automation tests only (85 cases). Developer-owned **unit tests**
  (`tests/test_units.py`, `unit` marker) stay in the code and run with `pytest -q` but are
  **excluded** from the automation report.
- Also generated: `reports/automation_report_<ts>.html` (pytest-html), `reports/cucumber_<ts>.json`
  (Cucumber JSON), `data/eval/evaluation_report.json` (100-Q RAG metrics).

See also the repo root [README.md](../README.md) and [TEST_DOCUMENTATION.md](../TEST_DOCUMENTATION.md).
