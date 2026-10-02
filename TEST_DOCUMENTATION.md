# Automation test documentation — what is tested, how, and where

## 1. How to run (one command each)
```
pip install -r requirements.txt
python run_automation.py        # AUTOMATION tests only + eval + HTML + Cucumber + dashboard, opens it
python run_eval.py              # 100-Q RAG eval only
pytest -q                       # ALL tests incl. unit (developer use)
pytest -q -m "not unit"         # automation tests only
pytest tests/bdd -q             # BDD/Gherkin only
pytest --html reports/x.html --self-contained-html --cucumberjson reports/x.json --junitxml reports/.internal/x.xml -m "not unit" -q
python build_report.py          # build the automation dashboard from the newest JUnit feed
streamlit run app.py            # manual UI testing
```

### Report scope (important)
- The automation report is for **automation testers**: it contains automation tests only
  (RAG Q&A, file extraction, memo analysis, **UI automation**, BDD and release-gate checks).
- **Developer-owned unit tests** (`tests/test_units.py`, tagged with the `unit` marker) stay in the
  codebase and remain runnable via `pytest -q`, but are **excluded from the automation report**.
  The runner selects `-m "not unit"` and the report builder filters them out by default
  (`--include-unit` opts back in). The dashboard shows a "Scope" note with the excluded count.

## 2. Reports
- `reports/automation_dashboard.html` — **visual dashboard** (open this one): donut/pie chart of
  Pass / Fail / Skipped, KPI cards (total, passed, failed, skipped, duration), radial gauges for the
  100-Q RAG metrics, pass-rate-by-area bars, **last 3 runs** trend, and a searchable/filterable
  table of every automation test case. Fully self-contained (inline SVG + CSS, no CDN, offline).
- `reports/history.json` — rolling run history the dashboard reads to render the last 3 runs
  (keeps the most recent 20).
- `reports/automation_report_<ts>.html` — pytest-html: per-test PASS/FAIL/SKIP, durations, suite summary.
- `reports/cucumber_<ts>.json` — `--cucumberjson`: Cucumber-compatible JSON (features/scenarios/steps) for CI dashboards.
- `reports/.internal/junit_<ts>.xml` — machine-readable feed consumed by the dashboard (not a deliverable).
- `data/eval/evaluation_report.json` — 100-Q RAG metrics + per-question rows + PASS/FAIL verdict.
- `docs/automation_strategy.html` — presentation-grade strategy deck: hero, KPIs, gate gauges, test-type grid, coverage matrix, pipeline. Self-contained; rebuild with `python build_strategy_doc.py` (also written by `python run_automation.py`); `Ctrl+P` saves a PDF.
- CI gate: `.github/workflows/rag-gate.yml` runs eval + the automation suite on push/PR.

## 2b. Related documentation
- [docs/automation_strategy.html](docs/automation_strategy.html) — visual strategy deck (presentable / printable).
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system, test and reporting architecture (with diagrams).
- [docs/AUTOMATION_STRATEGY.md](docs/AUTOMATION_STRATEGY.md) — automation approach, test types, evaluation checks, gates.
- [docs/ONBOARDING.md](docs/ONBOARDING.md) — onboarding guide for automation testers.
- [docs/README.md](docs/README.md) — documentation index.

## 3. Coverage matrix (positive / negative / edge)

| Area | Feature / file | Positive | Negative | Edge |
|---|---|---|---|---|
| RAG Q&A | `bdd/features/rag_qa.feature` + `test_automation_rag.py` + `test_bdd_rag.py` | ICR/SONIA/Stage-2 answered + cited, latency < 3s | gibberish Q does not invent FCA section | empty Q safe fallback; paraphrase consistency (metamorphic) |
| File extraction (PDF/JPG/JPEG/PNG/TXT/MD) | `memo_extraction.feature` + `test_automation_extract.py` | digital PDF text; JPG OCR; TXT direct | xlsx unsupported-type; blank PNG paste-guidance | .jpeg alias; scanned-PDF OCR path |
| Memo analysis (8 UK checks) | `memo_analysis.feature` + `test_automation_analyser.py` | strong memo READY; PDF end-to-end; evidence cites uk_* | weak memo NEEDS WORK + 3 gaps; empty memo error | missing file error |
| Streamlit UI (5 tabs) | `ui_tabs.feature` + `test_automation_ui.py` | 5 tabs render; uploader+paste; Q box+Top-K; UK-only KB list; gates shown | dashboard still loads with no report | zero exceptions on load |
| Eval gates (100 Qs) | `eval_gates.feature` + `test_rag_gates.py` + `test_automation_eval.py` | Recall≥.90 Faith≥.90 Rel≥.90 Hall≤.05 p95≤3s PASS | — (gate failures block release) | — |
| KB integrity | `test_units.py` + `test_automation_rag.py` | index is uk_* only; rebuild idempotent | `data/memos` never indexed | — |

## 4. AI-app testing patterns used (and where)
- **Grounding/faithfulness**: extractive answers + `faithfulness==1.0` (`ai_patterns.feature`, `test_automation_eval.py`).
- **Retrieval quality**: Recall@5/Precision/MRR/Hit@K on 100 golden Qs (`runner.py`, `eval_gates.feature`).
- **Hallucination guard**: gibberish-Q probe; hallucination = 1 − faithfulness, gate ≤ 5%.
- **Metamorphic consistency**: paraphrased ICR question → same facts (`rag_qa.feature`).
- **Robustness**: typo question still answers (`ai_patterns.feature`).
- **No-leakage**: user memos excluded from index (`ai_patterns.feature`).
- **Bias/fairness**: vulnerable-customer Q → conduct/forbearance guidance (`ai_patterns.feature`).
- **Determinism**: same Q twice → same citations (`ai_patterns.feature`).
- **Latency SLO**: per-query + p95 ≤ 3 s (`test_automation_rag.py`, gates).
- **Golden dataset**: 100 UK Qs pinned in `uk_q1/q2/q3.py`; eval report stores per-question rows for regression diff.
