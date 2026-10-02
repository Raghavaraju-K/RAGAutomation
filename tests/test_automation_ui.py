"""Automation: Streamlit UI smoke tests via AppTest (no browser needed)."""
import os

APP = os.path.join(os.path.dirname(__file__), "..", "app.py")


def _run_app():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    assert not at.exception, at.exception
    return at


def test_app_renders_all_tabs():
    at = _run_app()
    assert len(at.tabs) == 5
    labels = [t.label for t in at.tabs]
    assert labels == ["Analyse My Memo", "Ask UK Standards",
                      "Knowledge Base (UK only)", "Evaluation Dashboard",
                      "Fine-tune"], labels


def test_app_knowledge_base_lists_uk_docs():
    at = _run_app()
    kb_tab = at.tabs[2]
    md = " ".join(m.value for m in kb_tab.markdown)
    assert "uk_11_regulatory" in md or "UK standards documents" in md


def test_app_eval_dashboard_shows_metrics():
    at = _run_app()
    assert os.path.exists(os.path.join("data", "eval", "evaluation_report.json"))
    dash = at.tabs[3]
    metrics = {m.label: m.value for m in dash.metric}
    for k in ["Recall@5", "Faithfulness", "Answer relevance",
              "Hallucination", "P95 latency (s)"]:
        assert k in metrics, metrics
    assert float(metrics["Recall@5"]) >= 0.90


def test_app_memo_tab_has_uploader_and_paste_box():
    at = _run_app()
    memo_tab = at.tabs[0]
    assert len(memo_tab.file_uploader) >= 1
    assert len(memo_tab.text_area) >= 1


def test_app_ask_tab_has_question_box():
    at = _run_app()
    ask_tab = at.tabs[1]
    assert len(ask_tab.text_input) >= 1
    assert len(ask_tab.slider) >= 1
