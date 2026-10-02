# Onboarding Guide — Automation Tester

> Audience: a new automation tester joining the UK Credit Memo AI project.
> Goal: go from zero to running the suite and adding your first automated test in under 30 minutes.

## 1. What you are testing

A **local, offline RAG app** for UK credit memos (FCA/PRA aligned). It:

- Answers questions over a **UK-standards knowledge base** with grounded, cited answers.
- **Extracts** text from memos (PDF/JPG/JPEG/PNG/TXT/MD) and **scores** them against an
  8-point UK checklist.

Everything runs offline: local TF-IDF retrieval + an **extractive** generator (no LLM, no API keys).
That is why results are **deterministic** and testable.

## 2. Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | local dev used 3.14; CI uses 3.11 |
| `pip install -r requirements.txt` | pytest, pytest-bdd, pytest-html, streamlit, pypdf, pypdfium2, pillow, pytesseract, reportlab, pandas, numpy, pyyaml |
| Tesseract OCR | Install at `C:\Program Files\Tesseract-OCR\tesseract.exe` (Windows). Needed for image/scanned-PDF tests; without it those tests skip with a clear message. |

Install once:
```powershell
pip install -r requirements.txt
```

## 3. 10-minute quickstart

```powershell
# 1. See everything work (eval + automation tests + reports + dashboard)
python run_automation.py
```

This runs, in order:
1. `run_eval.py` — 100-question RAG evaluation -> `data/eval/evaluation_report.json`
2. `pytest -q -m "not unit"` — automation suite -> pytest-html, Cucumber JSON, JUnit feed
3. `build_report.py` — the visual dashboard

Then open **`reports/automation_dashboard.html`** (it opens automatically): pie chart, KPI cards,
RAG gauges, last 3 runs, searchable test table.

**Selective runs:**
```powershell
pytest -q                     # ALL tests incl. unit (developer use) -> ~97 passed
pytest -q -m "not unit"       # automation tests only -> ~85 passed, 12 deselected
pytest tests/bdd -q           # BDD/Gherkin only
pytest -q -m ui               # only UI automation
pytest -q -m "negative or edge"
pytest -q -m rag
```

## 4. Repo tour (where everything lives)

```
app.py                     Streamlit UI (5 tabs) — the app under test
run_eval.py                RAG evaluation only
run_automation.py          one-command automation (start here)
build_report.py            builds reports/automation_dashboard.html
pytest.ini                 markers + testpaths

src/                       application code under test
  retriever.py             TF-IDF retriever
  generator.py             extractive generator
  rag_pipeline.py          ask() / rebuild_index()
  memo_extract.py          PDF/image/text extraction (+OCR)
  memo_analyser.py         8-point UK checklist
  evaluation/              100-Q dataset + metrics + runner
  reporting/               report_builder.py (dashboard generator)

tests/
  conftest.py              fixtures: sample_text, weak_text, sample_pdf, sample_jpg, blank_png
  helpers/checks.py        SINGLE SOURCE OF TRUTH for test helpers  <-- read this
  test_automation_*.py     automation tests (rag/extract/analyser/ui/eval)
  test_rag_gates.py        release gates
  bdd/features/*.feature   Gherkin scenarios
  bdd/test_bdd_*.py        step definitions
  test_units.py            developer UNIT tests (unit marker) — NOT in the automation report

data/knowledge_base/       uk_*.txt (15 UK standards docs)
data/memos/                user memos (NEVER indexed)
data/eval/                 evaluation_report.json
reports/                   automation_dashboard.html, history.json, pytest-html, cucumber
reports/.internal/         junit feed (machine-readable, not a deliverable)
docs/                      this documentation set
```

## 5. How the test suite is organised

Two styles, **one shared helper layer**:

- **Imperative** tests (`tests/test_automation_*.py`) — AAA, one behaviour per test.
- **BDD** tests (`tests/bdd/`) — Gherkin `Given/When/Then` in `.feature` files, steps in `test_bdd_*.py`.

Both call the same helpers in `tests/helpers/checks.py` (`index_uk_kb`, `ask_uk`, `analyse_file`,
`assert_cites_uk`, `run_app`, `ensure_eval_report`, ...). **Never duplicate logic — add a helper.**

## 6. Writing your first automation test

Example — an imperative test (add to `tests/test_automation_rag.py` or a new
`tests/test_automation_<area>.py`):

```python
import pytest
from tests.helpers.checks import index_uk_kb, ask_uk, assert_mentions, assert_cites_uk

pytestmark = pytest.mark.rag


def test_ask_covenant_breach_headroom_is_explained():
    # Arrange
    index_uk_kb()
    # Act
    out, _ = ask_uk("What happens if a covenant is breached?", k=5)
    # Assert
    assert_mentions(out["answer"], "headroom", "waiver", "breach")
    assert_cites_uk(out)
```

Example — a BDD scenario. Add to a feature file (`tests/bdd/features/rag_qa.feature`):

```gherkin
Scenario: Positive - covenant breach question is answered with citation
  Given the UK knowledge base is indexed
  When I ask "What happens if a covenant is breached?"
  Then the answer cites a UK standards document
```

Then provide/reuse a step in the matching `tests/bdd/test_bdd_*.py`:
```python
@then("the answer cites a UK standards document")
def cites_uk(bdd_ctx):
    assert bdd_ctx["out"]["citations"]
    assert all(c.startswith("uk_") for c in bdd_ctx["out"]["citations"])
```

> **Do not** tag your automation test with the `unit` marker — that excludes it from the
> automation report. `unit` is reserved for developer-owned tests.

## 7. Markers (selection + intent)

Defined in `pytest.ini`: `unit`, `integration`, `rag`, `extraction`, `analyser`, `ui`, `gates`,
`bdd`, `negative`, `edge`, `ai_pattern`.

## 8. Reports: what you produce

| Artifact | What it is |
|---|---|
| `reports/automation_dashboard.html` | The visual automation report (open this) |
| `reports/history.json` | Rolling history powering the last-3-runs trend |
| `reports/automation_report_<ts>.html` | pytest-html per-test detail |
| `reports/cucumber_<ts>.json` | Cucumber JSON for CI dashboards |
| `data/eval/evaluation_report.json` | 100-Q RAG metrics + PASS/FAIL verdict |

The dashboard excludes developer-owned unit tests (shows a "Scope" note with the excluded count).
## 9. Troubleshooting

| Symptom | Fix |
|---|---|
| Image/scanned-PDF tests skipped "tesseract not installed" | Install Tesseract at `C:\Program Files\Tesseract-OCR` and `pip install pytesseract` |
| Gate tests fail "file not found" | Run `python run_eval.py` first (generates the eval report) |
| Dashboard shows 0 tests | Ensure the JUnit feed exists at `reports/.internal/junit_*.xml`; rerun `run_automation.py` |
| My new test is missing from the report | It may be tagged `unit`; otherwise check `_CATEGORY_RULES` in `src/reporting/report_builder.py` |
| Test flakiness on UI | `AppTest.from_file(..., default_timeout=120)`; assert `not at.exception` |
| `reports/.internal` missing (CI) | It is kept by `reports/.internal/.gitkeep`; create the folder if absent |

## 10. First-PR checklist

- [ ] Test lives in `tests/test_automation_<area>.py` (or a `.feature` + steps).
- [ ] Uses a helper from `tests/helpers/checks.py` (extend it if needed).
- [ ] Tagged with an appropriate marker; **not** `unit`.
- [ ] Includes a negative and/or edge case where meaningful.
- [ ] `pytest -q -m "not unit"` passes locally.
- [ ] `python run_automation.py` shows the case in `reports/automation_dashboard.html`.
- [ ] Docs updated if you added a new area/metric (see `docs/AUTOMATION_STRATEGY.md`).

## 11. Where to read more

- [ARCHITECTURE.md](ARCHITECTURE.md) — system + test + reporting architecture.
- [AUTOMATION_STRATEGY.md](AUTOMATION_STRATEGY.md) — approach, test types, evaluation checks, gates.
- [../TEST_DOCUMENTATION.md](../TEST_DOCUMENTATION.md) — run commands + coverage matrix.
- [../README.md](../README.md) — product overview.