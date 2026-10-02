"""UK 100-question dataset + runner + report per framework image."""
import json, os, time
from .uk_q1 import UK_Q1
from .uk_q2 import UK_Q2
from .uk_q3 import UK_Q3
from . import metrics as M
from ..rag_pipeline import ask
from ..config import EVAL_DIR, THRESHOLDS
ALL = UK_Q1 + UK_Q2 + UK_Q3

def dataset_path():
    return os.path.join(EVAL_DIR, "test_dataset_100.json")

def ensure_dataset():
    os.makedirs(EVAL_DIR, exist_ok=True)
    rows = [{"id": f"q{i+1:03d}", "question": q, "gold_doc": d,
             "expected_keywords": kw} for i, (q, d, kw) in enumerate(ALL)]
    assert len(rows) == 100, len(rows)
    json.dump(rows, open(dataset_path(), "w", encoding="utf-8"), indent=1)
    return dataset_path()

def run(k=5):
    ensure_dataset()
    rows = json.load(open(dataset_path(), encoding="utf-8"))
    per_q, lats = [], []
    for r in rows:
        t0 = time.perf_counter()
        out = ask(r["question"], k=k)
        dt = time.perf_counter() - t0
        lats.append(dt)
        ret_ids = [c["doc"] for c in out["contexts"]]
        rec = M.recall_at_k(ret_ids, [r["gold_doc"]], k)
        prec = M.precision_at_k(ret_ids, [r["gold_doc"]], k)
        mrr = M.mrr(ret_ids, [r["gold_doc"]])
        hit = M.hit_at_k(ret_ids, [r["gold_doc"]], k)
        faith = M.faithfulness(out["answer"], out["contexts"])
        rel = M.answer_relevance(out["answer"], r["question"])
        corr = M.correctness(out["answer"], r["expected_keywords"])
        hall = 1.0 - faith
        per_q.append({"id": r["id"], "question": r["question"],
                      "gold_doc": r["gold_doc"], "retrieved": ret_ids,
                      "answer": out["answer"], "recall@k": rec,
                      "precision@k": prec, "mrr": mrr, "hit@k": hit,
                      "faithfulness": faith, "relevance": rel,
                      "correctness": corr, "hallucination": hall,
                      "latency_s": round(dt, 3)})
    agg = {"n": len(per_q),
           "recall@5": sum(x["recall@k"] for x in per_q)/len(per_q),
           "precision@5": sum(x["precision@k"] for x in per_q)/len(per_q),
           "mrr": sum(x["mrr"] for x in per_q)/len(per_q),
           "hit@5": sum(x["hit@k"] for x in per_q)/len(per_q),
           "faithfulness": sum(x["faithfulness"] for x in per_q)/len(per_q),
           "answer_relevance": sum(x["relevance"] for x in per_q)/len(per_q),
           "correctness": sum(x["correctness"] for x in per_q)/len(per_q),
           "hallucination": sum(x["hallucination"] for x in per_q)/len(per_q),
           "p50_latency_s": M.percentile(lats, 50),
           "p95_latency_s": M.percentile(lats, 95)}
    checks = {"recall_at_5": agg["recall@5"] >= THRESHOLDS["recall_at_5"],
              "faithfulness": agg["faithfulness"] >= THRESHOLDS["faithfulness"],
              "answer_relevance": agg["answer_relevance"] >= THRESHOLDS["answer_relevance"],
              "hallucination": agg["hallucination"] <= THRESHOLDS["hallucination"],
              "p95_latency_s": agg["p95_latency_s"] <= THRESHOLDS["p95_latency_s"]}
    verdict = "PASS" if all(checks.values()) else "FAIL"
    report = {"aggregate": agg, "checks": checks, "verdict": verdict,
              "thresholds": THRESHOLDS, "per_question": per_q}
    os.makedirs(EVAL_DIR, exist_ok=True)
    json.dump(report, open(os.path.join(EVAL_DIR, "evaluation_report.json"),
                           "w", encoding="utf-8"), indent=1)
    return report
