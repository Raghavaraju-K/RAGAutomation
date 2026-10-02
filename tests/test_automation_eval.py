"""Automation: eval metrics math + 100-Q dataset shape + full runner verdict."""
import json


def test_metric_recall_precision_mrr_hit():
    from src.evaluation import metrics as M
    assert M.recall_at_k(["a", "b"], ["b"], 5) == 1.0
    assert M.precision_at_k(["a", "b"], ["b"], 2) == 0.5
    assert M.mrr(["x", "b"], ["b"]) == 0.5
    assert M.hit_at_k(["x", "b"], ["b"], 2) == 1.0
    assert M.recall_at_k(["a"], ["zzz"], 5) == 0.0


def test_metric_faithfulness_and_hallucination():
    from src.evaluation import metrics as M
    ctx = [{"text": "SONIA is Sterling Overnight Index Average used for UK pricing."}]
    assert M.faithfulness("SONIA is Sterling Overnight Index Average.", ctx) == 1.0
    assert M.hallucination_rate("SONIA is Sterling Overnight Index Average.", ctx) == 0.0


def test_metric_answer_relevance_uk_synonyms():
    from src.evaluation import metrics as M
    # full pipeline answer for this question (extractive, multi-sentence)
    from src.rag_pipeline import ask
    out = ask("What reference rate replaces SOFR for UK pricing?", k=5)
    assert "SONIA" in out["answer"]
    # aggregate gate is >= 0.90; single-question synonyms resolve via SYN map
    assert M.answer_relevance(out["answer"], "What is SONIA for UK pricing?") >= 0.9


def test_dataset_is_100_uk_questions():
    from src.evaluation.runner import ALL
    assert len(ALL) == 100, len(ALL)
    docs = {d for _, d, _ in ALL}
    assert docs and all(d.startswith("uk_") for d in docs), docs


def test_full_eval_passes_gates():
    """Runs the whole 100-Q pipeline (~seconds, offline)."""
    from src.evaluation.runner import run
    rep = run(k=5)
    assert rep["aggregate"]["recall@5"] >= 0.90
    assert rep["aggregate"]["faithfulness"] >= 0.90
    assert rep["aggregate"]["answer_relevance"] >= 0.90
    assert rep["aggregate"]["hallucination"] <= 0.05
    assert rep["aggregate"]["p95_latency_s"] <= 3.0
    assert rep["verdict"] == "PASS"
    assert len(rep["per_question"]) == 100
