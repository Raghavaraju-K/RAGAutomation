# UK Credit Memo AI — Local RAG (FCA/PRA aligned)
[![rag-gate](https://github.com/Raghavaraju-K/RAGAutomation/actions/workflows/rag-gate.yml/badge.svg)](https://github.com/Raghavaraju-K/RAGAutomation/actions/workflows/rag-gate.yml)

> **RAG application with automation coverage** — a local UK credit-memo RAG app together with its
> full test strategy, visual reports and CI gate.

KB is UK-standards-only: `data/knowledge_base/uk_*.txt` (15 docs, no cloud).
User credit memos go to `data/memos/` and are NEVER indexed — they are analysed against the UK KB.

## Tabs
1. Analyse My Memo — upload PDF / JPG / JPEG / PNG / TXT / MD or paste text -> extracted-text preview, UK-readiness score, PASS/REVIEW/GAP checklist, UK evidence with citations, JSON download.
2. Ask UK Standards — Q&A over UK KB only.
3. Knowledge Base (UK only) — locked view, Rebuild UK index.
4. Evaluation Dashboard — UK 100 Qs.
5. Fine-tune — feedback logger.

## File support
- Digital PDF: embedded text via pypdf (instant, offline).
- Scanned PDF + JPG/JPEG/PNG: OCR via Tesseract (installed at C:\Program Files\Tesseract-OCR) + pytesseract + pypdfium2 rendering.
- If OCR finds nothing, the app shows a clear message and asks you to paste text instead.

## Run
```
pip install -r requirements.txt
streamlit run app.py
python run_eval.py
pytest -q                  # ALL tests incl. unit (developer use)
python run_automation.py   # AUTOMATION tests only + visual dashboard -> reports/automation_dashboard.html
```
Latest: Recall@5 0.99, Faithfulness 1.00, Relevance 0.979, Hallucination 0.00, p95 ~0.002s -> PASS. Automation tests: 85 passed.

## Reports (automation scope)
The report is for **automation testers**: automation tests only (RAG Q&A, file extraction, memo
analysis, UI automation, BDD, release gates). Developer-owned **unit tests** (`tests/test_units.py`)
stay in the code and run with `pytest -q`, but are excluded from the automation report (`-m "not unit"`;
`build_report.py --include-unit` opts back in).
- `reports/automation_dashboard.html` — visual dashboard: pie chart of Pass/Fail/Skipped, KPI totals, RAG metric gauges, last 3 runs, searchable test table (self-contained, offline).
- `reports/automation_report_<ts>.html` — pytest-html per-test detail.
- `reports/cucumber_<ts>.json` — CI-friendly Cucumber JSON. (`reports/.internal/junit_*.xml` is the internal feed.)
- `data/eval/evaluation_report.json` — 100-Q RAG metrics + PASS/FAIL verdict.
- `docs/automation_strategy.html` — presentation-grade strategy deck (self-contained; open and `Ctrl+P` to save as PDF). Rebuild with `python build_strategy_doc.py`.

## Documentation
- [docs/README.md](docs/README.md) — documentation index.
- [docs/automation_strategy.html](docs/automation_strategy.html) — **visual strategy deck** (presentable / printable).
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system, test and reporting architecture.
- [docs/AUTOMATION_STRATEGY.md](docs/AUTOMATION_STRATEGY.md) — automation approach, test types, evaluation checks, gates.
- [docs/ONBOARDING.md](docs/ONBOARDING.md) — onboarding guide for automation testers.
- [TEST_DOCUMENTATION.md](TEST_DOCUMENTATION.md) — run commands + coverage matrix.

## Compliance note
Demo summarises public UK standards; not regulated advice. Verify against current FCA Handbook / PRA Rulebook with compliance/legal sign-off.



