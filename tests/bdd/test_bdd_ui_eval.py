"""BDD: UI tabs + eval gates. Self-contained."""
import os
import pytest
from pytest_bdd import given, when, then, parsers, scenarios

scenarios("features/ui_tabs.feature")
scenarios("features/eval_gates.feature")

APP = os.path.join(os.path.dirname(__file__), "..", "..", "app.py")


@pytest.fixture
def ui():
    return {}


@given("the Streamlit app loads")
def app_loads(ui):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    assert not at.exception, at.exception
    ui["at"] = at


@given("the Streamlit app loads with an evaluation report")
def app_with_report(ui):
    assert os.path.exists(os.path.join("data", "eval", "evaluation_report.json"))
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    assert not at.exception, at.exception
    ui["at"] = at


@given("no evaluation report exists")
def no_report(ui, tmp_path):
    import shutil
    src = os.path.join("data", "eval", "evaluation_report.json")
    bak = str(tmp_path / "report_backup.json")
    moved = False
    if os.path.exists(src):
        shutil.move(src, bak)
        moved = True
    ui["restore"] = (src, bak, moved)


@given("a completed 100-question evaluation report")
def completed_report(ui):
    import json
    from src.evaluation.runner import run
    p = os.path.join("data", "eval", "evaluation_report.json")
    if not os.path.exists(p):
        run(k=5)
    ui["rep"] = json.load(open(p, encoding="utf-8"))


@when(parsers.parse('I open the "{tab}" tab'))
def open_tab(ui, tab):
    labels = [t.label for t in ui["at"].tabs]
    ui["tab"] = ui["at"].tabs[labels.index(tab)]


@then("5 tabs render named Analyse My Memo, Ask UK Standards, Knowledge Base, Evaluation Dashboard and Fine-tune")
def five_tabs(ui):
    labels = [t.label for t in ui["at"].tabs]
    assert labels == ["Analyse My Memo", "Ask UK Standards",
                      "Knowledge Base (UK only)", "Evaluation Dashboard",
                      "Fine-tune"], labels


@then("a memo file uploader is visible")
def uploader_visible(ui):
    assert len(ui["tab"].file_uploader) >= 1


@then("a paste-text box is visible")
def paste_visible(ui):
    assert len(ui["tab"].text_area) >= 1


@then("a question box is visible")
def qbox_visible(ui):
    assert len(ui["tab"].text_input) >= 1


@then("a Top-K control is visible")
def topk_visible(ui):
    assert len(ui["tab"].slider) >= 1


@then("only UK standards documents are listed")
def uk_only_listed(ui):
    md = " ".join(m.value for m in ui["tab"].markdown)
    assert "uk_" in md


@then(parsers.parse("{metric} is at least {val:f}"))
def metric_gte(ui, metric, val):
    if "rep" in ui:
        key = {"Recall@5": "recall@5", "Faithfulness": "faithfulness",
               "Answer relevance": "answer_relevance"}[metric]
        assert ui["rep"]["aggregate"][key] >= val
    else:
        vals = {m.label: float(m.value) for m in ui["tab"].metric}
        assert vals[metric] >= val, vals


@then(parsers.parse("{metric} is at most {val:f}"))
@then(parsers.parse("{metric} is at most {val:f} seconds"))
def metric_lte(ui, metric, val):
    if "rep" in ui:
        key = {"Hallucination": "hallucination", "P95 latency": "p95_latency_s"}[metric]
        assert ui["rep"]["aggregate"][key] <= val
    else:
        vals = {m.label: float(m.value) for m in ui["tab"].metric}
        assert vals[metric] <= val, vals


@then("the app still loads without crashing")
def still_loads(ui):
    assert not ui["at"].exception


@then("no exception is raised")
def no_exc(ui):
    assert not ui["at"].exception


@then(parsers.parse('the verdict is "{v}" with 100 per-question rows'))
def verdict_rows(ui, v):
    assert ui["rep"]["verdict"] == v
    assert len(ui["rep"]["per_question"]) == 100


