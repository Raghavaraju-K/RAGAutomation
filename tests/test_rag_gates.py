"""Pytest gate: Recall@5>=90%, Faithfulness>=90%, Relevance>=90%, Hall<=5%, p95<=3s."""
import os, json

def load_report():
    p = os.path.join("data", "eval", "evaluation_report.json")
    assert os.path.exists(p), "Run: python -m src.evaluation.runner first (or via Streamlit dashboard)"
    return json.load(open(p, encoding="utf-8"))

def test_recall_at_5():
    r = load_report()
    assert r["aggregate"]["recall@5"] >= 0.90, r["aggregate"]

def test_faithfulness():
    r = load_report()
    assert r["aggregate"]["faithfulness"] >= 0.90, r["aggregate"]

def test_answer_relevance():
    r = load_report()
    assert r["aggregate"]["answer_relevance"] >= 0.90, r["aggregate"]

def test_hallucination():
    r = load_report()
    assert r["aggregate"]["hallucination"] <= 0.05, r["aggregate"]

def test_p95_latency():
    r = load_report()
    assert r["aggregate"]["p95_latency_s"] <= 3.0, r["aggregate"]

def test_ci_gate_verdict():
    r = load_report()
    assert r["verdict"] == "PASS", r
