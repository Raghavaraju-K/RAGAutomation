# Automation Strategy

> Audience: automation testers and QA leads. Explains the **approach**, the **types of testing**
> covered, the **evaluation checks**, and the **release gates**.

## 1. Purpose and scope

The automation suite proves that the UK Credit Memo RAG app **retrieves the right UK standards,
answers with grounded citations, extracts memos from every supported format, scores them against
an 8-point UK checklist, and renders a working UI** — and that it does so within quality gates.

**In scope (automation report):**

- Functional/behavioural automation for RAG Q&A, file extraction, memo analysis, UI and gates.
- BDD/Gherkin acceptance tests (business-readable).
- RAG/AI evaluation checks over a 100-question golden dataset.

**Out of scope (stays in the repo, not in the report):**

- Developer-owned **unit tests** (`tests/test_units.py`, `unit` marker).
- Tests of the report builder itself (`tests/test_automation_report.py`, `unit` marker).

> The automation report is for automation testers; unit tests are the developers' responsibility.
> Unit tests remain runnable with `pytest -q` and are excluded from the report via `-m "not unit"`.

## 2. Quality goals

| Goal | Measure | Gate |
|---|---|---|
| Correct retrieval | Recall@5 | >= 0.90 |
| Grounded answers | Faithfulness | >= 0.90 |
| Answer relevance | Answer relevance | >= 0.90 |
| No invention | Hallucination | <= 0.05 |
| Responsiveness | p95 latency | <= 3.0 s |
| Overall | Eval verdict | PASS |
| Stability | Automation suite | 0 failures |

## 3. Automation approach

- **AAA (Arrange-Act-Assert)** — every test is a short, readable arrange/act/assert.
- **Given-When-Then** — the same scenarios are also expressed in Gherkin (`tests/bdd/features/*`).
- **DRY / single source of truth** — BDD steps and imperative tests both call
  `tests/helpers/checks.py`; no logic is duplicated between the two styles.
- **Deterministic & offline** — no LLM judge, no network; results are reproducible run-to-run.
- **Markers for selection** — `unit`, `rag`, `extraction`, `analyser`, `ui`, `gates`, `bdd`,
  `negative`, `edge`, `ai_pattern` (see `pytest.ini`).
- **Isolated test data** — fixtures generate PDFs/JPGs at runtime (`tmp_path`); no committed binaries needed.
- **Report-first** — every run produces a visual dashboard, machine-readable Cucumber JSON and an eval report.

## 4. Types of testing covered

| # | Type | What it validates | Where |
|---|---|---|---|
| 1 | Functional (RAG Q&A) | Grounded answer + UK citation + latency SLO | `test_automation_rag.py`, `test_bdd_rag.py` |
| 2 | Functional (file extraction) | PDF/JPG/JPEG/PNG/TXT/MD extraction + actionable errors | `test_automation_extract.py`, `test_bdd_memo.py` |
| 3 | Functional (memo analysis) | 8-point UK checklist, verdict, gaps, UK evidence | `test_automation_analyser.py`, `test_bdd_memo.py` |
| 4 | BDD acceptance | Business-readable Given/When/Then over all areas | `tests/bdd/features/*` |
| 5 | UI automation | Streamlit app renders 5 tabs, uploader, Q box, KB list, gates — headless | `test_automation_ui.py`, `test_bdd_ui_eval.py` |
| 6 | Integration / end-to-end | Multi-component paths (extract -> analyse -> evidence) | `test_automation_analyser.py`, `test_bdd_memo.py` |
| 7 | Data/regression (evaluation) | 100-Q metrics + per-question rows for regression diffing | `test_automation_eval.py`, `runner.py` |
| 8 | Release gates | Thresholds enforced as tests | `test_rag_gates.py`, `test_bdd_ui_eval.py` |
| 9 | AI-specific patterns | Grounding, hallucination guard, metamorphic, robustness, no-leakage, bias, determinism | `ai_patterns.feature`, `test_automation_rag.py` |
| 10 | Negative / error handling | Unsupported types, blank images, empty input, missing files, gibberish | `*_negative*` tests + `negative` marker |
| 11 | Edge cases | `.jpeg` vs `.jpg`, empty question, paraphrase consistency, missing report | `*_edge*` tests + `edge` marker |

**Automation case counts (85 total, current run):**

| Area | Cases | Files |
|---|---|---|
| RAG Q&A | 15 | `test_automation_rag.py` |
| RAG Q&A (BDD) | 12 | `test_bdd_rag.py` |
| File Extraction | 6 | `test_automation_extract.py` |
| Memo Extraction & Analysis (BDD) | 11 | `test_bdd_memo.py` |
| Memo Analysis | 12 | `test_automation_analyser.py` |
| UI Automation | 5 | `test_automation_ui.py` |
| UI & Eval Gates (BDD) | 13 | `test_bdd_ui_eval.py` |
| Eval Gates | 5 | `test_automation_eval.py` |
| Eval Gates | 6 | `test_rag_gates.py` |
| **Total** | **85** | |

## 5. Coverage matrix (positive / negative / edge)

| Area | Feature / file | Positive | Negative | Edge |
|---|---|---|---|---|
| RAG Q&A | `rag_qa.feature` + `test_automation_rag.py` + `test_bdd_rag.py` | ICR/SONIA/Stage-2 answered + cited, latency < 3s | gibberish Q does not invent an FCA section | empty Q safe fallback; paraphrase consistency (metamorphic) |
| File extraction | `memo_extraction.feature` + `test_automation_extract.py` | digital PDF text; JPG OCR; TXT direct | xlsx unsupported-type; blank PNG paste-guidance | `.jpeg` alias; scanned-PDF OCR path |
| Memo analysis | `memo_analysis.feature` + `test_automation_analyser.py` | strong memo READY; PDF end-to-end; evidence cites `uk_*` | weak memo NEEDS WORK + >=3 gaps; empty memo error | missing file error |
| Streamlit UI | `ui_tabs.feature` + `test_automation_ui.py` | 5 tabs render; uploader + paste; Q box + Top-K; UK-only KB list; gates shown | dashboard still loads with no report | zero exceptions on load |
| Eval gates | `eval_gates.feature` + `test_rag_gates.py` + `test_automation_eval.py` | Recall>=.90, Faith>=.90, Rel>=.90, Hall<=.05, p95<=3s, PASS | gate failures block release | 100 per-question rows for regression |
| AI patterns | `ai_patterns.feature` + `test_automation_rag.py` | gold doc in top-5; faithfulness 1.0; determinism | no-leakage: memos never indexed | typo robustness; bias/fairness conduct guidance |

## 6. Evaluation checks (RAG/AI)

The 100-question golden dataset (`uk_q1` 35 core credit/regulatory, `uk_q2` 35 affordability/IFRS 9/
conduct/crime, `uk_q3` 30 paraphrases + UK-ised covenants/policy) is run end-to-end by
`src/evaluation/runner.py`, which writes `data/eval/evaluation_report.json`.

**Retrieval metrics** (per question, aggregated):
- **Recall@5** — is the gold document in the top-5 chunks?
- **Precision@5**, **MRR**, **Hit@5**.

**Generation metrics:**
- **Faithfulness** — fraction of answer sentences supported by retrieved context (word overlap).
- **Hallucination** = 1 - Faithfulness.
- **Answer relevance** — stemmed keyword-recall of question concepts (with UK synonyms).
- **Correctness** — coverage of expected keywords for the question.

**Latency:** p50 and p95 per query.

**Release gates** (from `src/config.py` `THRESHOLDS`):

| Metric | Threshold | Direction |
|---|---|---|
| Recall@5 | >= 0.90 | higher is better |
| Faithfulness | >= 0.90 | higher is better |
| Answer relevance | >= 0.90 | higher is better |
| Hallucination | <= 0.05 | lower is better |
| p95 latency | <= 3.0 s | lower is better |

Latest result: Recall@5 0.99, Faithfulness 1.00, Relevance 0.979, Hallucination 0.00, p95 ~0.0016s -> **PASS**.

## 7. AI-app testing patterns used

| Pattern | Check | Where |
|---|---|---|
| Grounding / faithfulness | Extractive answers; faithfulness == 1.0 | `ai_patterns.feature`, `test_automation_eval.py` |
| Retrieval quality | Recall@5 / Precision / MRR / Hit@K on 100 golden Qs | `runner.py`, `eval_gates.feature` |
| Hallucination guard | Gibberish-Q probe; hallucination = 1 - faithfulness, gate <= 5% | `rag_qa.feature` |
| Metamorphic consistency | Paraphrased ICR question -> same facts | `rag_qa.feature` |
| Robustness | Typo question still answers | `ai_patterns.feature` |
| No-leakage | User memos excluded from the index | `ai_patterns.feature` |
| Bias / fairness | Vulnerable-customer Q -> conduct/forbearance guidance | `ai_patterns.feature` |
| Determinism | Same Q twice -> same citations | `ai_patterns.feature` |
| Latency SLO | Per-query + p95 <= 3 s | `test_automation_rag.py`, gates |
| Golden dataset / regression | 100 Qs pinned; per-question rows stored for diffing | `uk_q1/q2/q3.py`, eval report |


## 8. Test data strategy

- **Fixtures** (`tests/conftest.py`): `sample_text` (strong memo), `weak_text`, `sample_pdf`
  (generated with reportlab), `sample_jpg` (generated with Pillow), `blank_png`. Generated at
  runtime via `tmp_path`/`tmp_path_factory` — no committed test binaries.
- **Golden dataset**: 100 UK questions with gold document + expected keywords, pinned in
  `src/evaluation/uk_q*.py`; materialised to `data/eval/test_dataset_100.json`.
- **KB corpus**: `data/knowledge_base/uk_*.txt` (15 docs). The `uk_` glob guarantees the index is
  UK-standards-only.
- **No-leakage rule**: `data/memos/` (user memos) is *never* indexed — asserted by tests.

## 9. Test environment and tooling

| Concern | Tooling |
|---|---|
| Test runner | `pytest` 8.x, `pytest-bdd` (Gherkin), `pytest-html`, `pytest-metadata` |
| Reporting | `src/reporting/report_builder.py` (inline-SVG dashboard), `--cucumberjson`, `--junitxml` |
| UI automation | `streamlit.testing.v1.AppTest` (headless, no browser) |
| OCR | Tesseract at `C:\Program Files\Tesseract-OCR` + `pytesseract`, `pypdfium2`, `Pillow` |
| PDF/text | `pypdf`, `reportlab` |
| Python | 3.11+ (CI) / 3.14 (local) |

## 10. Execution model

**Local — one command (recommended):**
```
python run_automation.py
```
Runs `run_eval.py` -> `pytest -q -m "not unit"` (with HTML/Cucumber/JUnit) -> `build_report.py`,
then opens `reports/automation_dashboard.html`.

**Selective runs:**
```
pytest -q                     # ALL tests incl. unit (developer use)
pytest -q -m "not unit"       # automation tests only
pytest tests/bdd -q           # BDD/Gherkin only
pytest -q -m ui               # only UI automation
pytest -q -m "negative or edge"
```

**CI** (`.github/workflows/rag-gate.yml`): on push/PR -> install deps + Tesseract -> `run_eval.py`
-> `pytest -m "not unit"` (HTML/Cucumber/JUnit) -> `build_report.py` -> upload `reports/` artifact.

## 11. Reporting and dashboards

- `reports/automation_dashboard.html` — **the automation report**: donut/pie of Pass/Fail/Skipped,
  KPI cards (total, passed, failed, skipped, duration), RAG metric gauges with gate chips,
  pass-rate-by-area bars, **last 3 runs** trend, and a searchable/filterable table of automation cases.
- `reports/history.json` — rolling run history (keeps last 20) that powers the last-3-runs view.
- `reports/automation_report_<ts>.html` — pytest-html per-test detail.
- `reports/cucumber_<ts>.json` — Cucumber-compatible JSON for CI dashboards.
- `data/eval/evaluation_report.json` — 100-Q metrics, per-question rows, PASS/FAIL verdict.

## 12. Entry / exit criteria

**Entry:** dependencies installed; Tesseract present for OCR tests; `data/knowledge_base/uk_*.txt`
present; eval report generated before gate tests (`run_eval.py` first).

**Exit (release gate):** all automation tests pass AND eval verdict == PASS
(Recall>=0.90, Faith>=0.90, Rel>=0.90, Hall<=0.05, p95<=3s). Any failing gate blocks release.

## 13. Risks, limitations and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| OCR engine missing | Image/scanned-PDF tests fail or skip | Tesseract installed + `needs_ocr`/skip guards; clear actionable errors |
| Lexical metrics misgrade nuance | False confidence/negatives | Tuned UK synonyms + golden keywords; gates are conservative |
| Paraphrase recall (TF-IDF) | Missed retrieval on reworded Qs | `uk_q3` paraphrase bank + metamorphic tests |
| Eval report missing | Gate tests error | Runner generates it first; tests call `ensure_eval_report()` |
| Unit tests leaking into report | Report scope violation | `-m "not unit"` + `is_unit_test()` filter + report test asserting exclusion |
| Flaky UI/AppTest | Intermittent failures | Headless `AppTest` with `default_timeout=120`, zero-exception assertions |

## 14. Conventions checklist for a new automation test

- [ ] Put it in `tests/test_automation_<area>.py` or a `.feature` under `tests/bdd/features/`.
- [ ] Reuse a helper from `tests/helpers/checks.py` (add one there if missing — do not duplicate logic).
- [ ] Use an existing marker (`rag`, `extraction`, `analyser`, `ui`, `gates`, `negative`, `edge`, `ai_pattern`).
- [ ] Cover at least one **negative** or **edge** case where meaningful.
- [ ] Do **not** tag it `unit` (that would exclude it from the automation report).
- [ ] If it is a new area, add a `_CATEGORY_RULES` entry in `src/reporting/report_builder.py`.
- [ ] Run `python run_automation.py` and confirm it appears in `reports/automation_dashboard.html`.

