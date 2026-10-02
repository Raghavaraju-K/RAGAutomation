"""Tests for the visual automation dashboard builder (src/reporting/report_builder.py).

Follows the repo conventions: AAA (Arrange-Act-Assert) + tmp_path isolation +
the shared `unit` marker. These guard the report pipeline that `run_automation.py` uses.
"""
import json
import os

import pytest

from src.reporting import report_builder as RB

JUNIT_SAMPLE = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="4" failures="1" skipped="1" time="0.42">
    <testcase classname="tests.test_automation_rag" name="test_ask_ok" time="0.10"/>
    <testcase classname="tests.test_automation_rag" name="test_ask_bad" time="0.20">
      <failure message="AssertionError: boom">traceback here</failure>
    </testcase>
    <testcase classname="tests.bdd.test_bdd_ui_eval" name="test_negative__no_report" time="0.02">
      <skipped message="report missing"/>
    </testcase>
    <testcase classname="tests.test_units" name="test_kb_is_uk_only" time="0.10"/>
  </testsuite>
</testsuites>
"""


@pytest.fixture
def junit_file(tmp_path):
    p = tmp_path / "junit.xml"
    p.write_text(JUNIT_SAMPLE, encoding="utf-8")
    return str(p)


@pytest.fixture
def eval_file(tmp_path):
    rep = {
        "aggregate": {"n": 100, "recall@5": 0.99, "faithfulness": 1.0,
                      "answer_relevance": 0.979, "hallucination": 0.0,
                      "p95_latency_s": 0.0016, "precision@5": 0.198,
                      "mrr": 0.937, "hit@5": 0.99, "correctness": 0.963,
                      "p50_latency_s": 0.0011},
        "checks": {"recall_at_5": True, "faithfulness": True,
                   "answer_relevance": True, "hallucination": True,
                   "p95_latency_s": True},
        "verdict": "PASS",
    }
    p = tmp_path / "evaluation_report.json"
    p.write_text(json.dumps(rep), encoding="utf-8")
    return str(p)


@pytest.mark.unit
def test_junit_counts_pass_fail_skip(junit_file):
    summary, cases = RB.parse_junit(junit_file)
    # the tests.test_units case is developer-owned and excluded from the automation report
    assert summary["total"] == 3, summary
    assert summary["passed"] == 1, summary
    assert summary["failed"] == 1, summary
    assert summary["skipped"] == 1, summary
    assert summary["excluded_unit"] == 1, summary
    assert round(summary["pass_rate"], 1) == 33.3, summary
    assert summary["duration_s"] == 0.32, summary
    assert len(cases) == 3


@pytest.mark.unit
def test_unit_tests_excluded_by_default_but_available(junit_file):
    excluded, cases = RB.parse_junit(junit_file)
    assert excluded["excluded_unit"] == 1
    assert not any(c["is_unit"] for c in cases)
    assert all("test_units" not in c["nodeid"] for c in cases)
    # opt-in keeps them, and they are labelled as dev-owned
    included, cases2 = RB.parse_junit(junit_file, include_unit=True)
    assert included["total"] == 4
    assert included["excluded_unit"] == 0
    assert sum(1 for c in cases2 if c["is_unit"]) == 1
    assert any(c["category"] == "Unit Tests (dev-owned)" for c in cases2)


@pytest.mark.unit
def test_category_mapping_covers_uk_areas():
    assert RB.category_of("tests/test_automation_rag.py::x") == "RAG Q&A"
    assert RB.category_of("tests/bdd/test_bdd_rag.py::x") == "RAG Q&A"
    assert RB.category_of("tests/test_automation_extract.py::x") == "File Extraction"
    assert RB.category_of("tests/test_automation_ui.py::x") == "UI Automation"
    assert RB.category_of("tests/test_rag_gates.py::x") == "Eval Gates"
    assert RB.category_of("tests/unknown_thing.py::x") == "Other"
    # unit-test detection (by file name, marker-independent)
    assert RB.is_unit_test("tests/test_units.py::test_x")
    assert RB.is_unit_test("tests\\test_units.py::test_x")
    assert not RB.is_unit_test("tests/test_automation_ui.py::test_x")
    assert RB.category_of("tests/test_units.py::x") == "Unit Tests (dev-owned)"


@pytest.mark.unit
def test_verdict_requires_tests_and_eval_to_pass(junit_file, eval_file):
    summary, _ = RB.parse_junit(junit_file)
    good = RB.load_eval(eval_file)
    assert RB.verdict_of(summary, good)[0] == "FAIL"       # 1 test failing
    assert RB.verdict_of(summary, None)[0] == "FAIL"       # no eval report
    clean = {"total": 4, "passed": 4, "failed": 0, "skipped": 0,
             "duration_s": 1.0, "pass_rate": 100.0}
    assert RB.verdict_of(clean, good)[0] == "PASS"


@pytest.mark.unit
def test_build_writes_self_contained_dashboard(tmp_path, junit_file, eval_file):
    out = tmp_path / "dashboard.html"
    hist = tmp_path / "history.json"
    path = RB.build(junit_path=junit_file, out_html=str(out),
                    eval_path=eval_file, run_ts="20260101_000000",
                    history_path=str(hist))
    assert os.path.exists(path)
    html = out.read_text(encoding="utf-8")
    # no unsubstituted $placeholders and no external assets -> offline safe
    assert "$total" not in html and "$css" not in html and "$kpis" not in html
    assert "http://" not in html and "https://" not in html
    for token in ("donut", "kpi", "gauge", "run-card", "tc-table", "bar-row"):
        assert token in html, token
    # history persisted for the "last runs" trend
    saved = json.loads(hist.read_text(encoding="utf-8"))
    assert len(saved) == 1 and saved[0]["ts"] == "20260101_000000"
    assert saved[0]["total"] == 3 and saved[0]["verdict"] == "FAIL"


@pytest.mark.unit
def test_history_is_capped_and_deduplicated(tmp_path, junit_file, eval_file):
    hist = tmp_path / "history.json"
    summary, _ = RB.parse_junit(junit_file)
    for i in range(RB.HISTORY_KEEP + 3):
        RB.update_history(summary, None, f"20260101_{i:06d}", path=str(hist))
    saved = json.loads(hist.read_text(encoding="utf-8"))
    assert len(saved) <= RB.HISTORY_KEEP
    # re-running the same timestamp must not duplicate the entry
    before = len(saved)
    RB.update_history(summary, None, saved[-1]["ts"], path=str(hist))
    assert len(json.loads(hist.read_text(encoding="utf-8"))) == before


@pytest.mark.unit
def test_build_without_junit_or_eval_degrades_gracefully(tmp_path):
    out = tmp_path / "empty.html"
    path = RB.build(junit_path=str(tmp_path / "missing.xml"), out_html=str(out),
                    eval_path=str(tmp_path / "missing.json"),
                    run_ts="20260101_000000",
                    history_path=str(tmp_path / "h.json"))
    html = open(path, encoding="utf-8").read()
    assert "No RAG evaluation report found" in html
    assert "No test cases were collected" in html