"""Tests for the presentation-grade Automation Strategy document builder.

Developer-owned (unit marker): guards the doc pipeline that `build_strategy_doc.py` uses.
"""
import json
import os

import pytest

from src.reporting import strategy_doc as SD

JUNIT_SAMPLE = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="3" failures="0" skipped="0" time="0.30">
    <testcase classname="tests.test_automation_rag" name="test_ask_ok" time="0.10"/>
    <testcase classname="tests.test_automation_ui" name="test_tabs" time="0.10"/>
    <testcase classname="tests.test_units" name="test_dev_only" time="0.10"/>
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
    rep = {"aggregate": {"n": 100, "recall@5": 0.99, "faithfulness": 1.0,
                         "answer_relevance": 0.979, "hallucination": 0.0,
                         "p95_latency_s": 0.0016, "precision@5": 0.198,
                         "mrr": 0.937, "correctness": 0.963},
           "checks": {"recall_at_5": True, "faithfulness": True,
                      "answer_relevance": True, "hallucination": True,
                      "p95_latency_s": True},
           "verdict": "PASS"}
    p = tmp_path / "evaluation_report.json"
    p.write_text(json.dumps(rep), encoding="utf-8")
    return str(p)


@pytest.mark.unit
def test_build_renders_self_contained_deck(tmp_path, junit_file, eval_file, monkeypatch):
    # keep the shared run history out of the repo during the test
    monkeypatch.setattr(SD.RB, "HISTORY_FILE", str(tmp_path / "history.json"))
    out = tmp_path / "doc.html"
    path = SD.build(out_html=str(out), junit_path=junit_file, eval_path=eval_file)
    assert os.path.exists(path)
    html = open(path, encoding="utf-8").read()

    # no unsubstituted placeholders and no external assets -> offline safe
    assert "$css" not in html and "$total" not in html and "$area_bars" not in html
    assert "http://" not in html and "https://" not in html

    # all presentation sections present
    for token in ('class="hero"', 'class="kpis"', 'class="ring"', "type-card",
                  'table class="matrix"', "pat-grid", 'class="step"',
                  'class="area"', 'class="artifacts"', "@media print"):
        assert token in html, token

    # automation scope: unit test excluded from the counts
    assert "test_dev_only" not in html
    assert SD.gather(junit_file, eval_file)["summary"]["total"] == 2


@pytest.mark.unit
def test_gather_pulls_live_gate_and_area_numbers(tmp_path, junit_file, eval_file, monkeypatch):
    monkeypatch.setattr(SD.RB, "HISTORY_FILE", str(tmp_path / "history.json"))
    g = SD.gather(junit_file, eval_file)
    assert g["summary"]["total"] == 2
    assert g["summary"]["excluded_unit"] == 1
    assert g["gates_passed"] == 5 and g["gates_total"] == 5
    assert g["verdict"] == "PASS"
    assert "RAG Q&A" in g["by_area"] and "UI Automation" in g["by_area"]


@pytest.mark.unit
def test_deck_degrades_gracefully_without_data(tmp_path, monkeypatch):
    monkeypatch.setattr(SD.RB, "HISTORY_FILE", str(tmp_path / "history.json"))
    out = tmp_path / "empty.html"
    path = SD.build(out_html=str(out),
                    junit_path=str(tmp_path / "missing.xml"),
                    eval_path=str(tmp_path / "missing.json"))
    html = open(path, encoding="utf-8").read()
    assert "No automation cases collected" in html
    assert "Run <code>python run_eval.py</code>" in html