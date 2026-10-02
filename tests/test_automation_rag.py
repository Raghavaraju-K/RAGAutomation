"""Imperative automation: UK RAG pipeline (ask/search/answer + latency + citations).

Industry practice: Arrange-Act-Assert, one behaviour per test,
explicit assertions on grounded facts, citations and latency SLO.
BDD mirrors: tests/bdd/features/rag_qa.feature + ai_patterns.feature
"""
import pytest

from tests.helpers.checks import (
    index_uk_kb, ask_uk, search_uk, assert_mentions, assert_cites_uk,
    faithfulness_of,
)

pytestmark = [pytest.mark.rag, pytest.mark.integration]


def test_ask_returns_grounded_answer_with_citations():
    # Arrange: indexed UK KB. Act: ask ICR question. Assert: facts + cites.
    index_uk_kb()
    out, _ = ask_uk("What is the PRA minimum ICR and stressed rate for buy-to-let?", k=5)
    assert out["answer"] and len(out["answer"]) > 50
    assert_mentions(out["answer"], "125 percent", "5.5 percent")
    assert_cites_uk(out)
    assert len(out["contexts"]) == 5


def test_ask_sonia_not_sofr():
    index_uk_kb()
    out, _ = ask_uk("What reference rate replaces SOFR for UK pricing?", k=5)
    assert "SONIA" in out["answer"]


def test_ask_ifrs9_stage2():
    index_uk_kb()
    out, _ = ask_uk("What is Stage 2 under IFRS 9?", k=5)
    a = out["answer"]
    assert ("lifetime ECL" in a or "SICR" in a
            or "significant increase" in a.lower()), a[:400]


def test_ask_latency_under_threshold():
    from src.config import THRESHOLDS
    index_uk_kb()
    lats = [ask_uk(q, k=5)[1]
            for q in ["What is SONIA?", "What is ICR?", "What is IFRS 9 Stage 1?"]]
    assert max(lats) < THRESHOLDS["p95_latency_s"], lats


def test_retriever_only_searches_uk_kb():
    r = index_uk_kb()
    assert all(c["doc"].startswith("uk_") for c in r.chunks)
    hits = search_uk(r, "Consumer Duty fair value", k=5)
    assert hits and hits[0]["doc"].startswith("uk_")


def test_rebuild_index_idempotent():
    from src.rag_pipeline import rebuild_index, get_retriever
    n1 = len(rebuild_index().chunks)
    n2 = len(get_retriever().chunks)
    assert n1 == n2 and n1 > 0


# ---- AI-pattern edge cases (imperative side of ai_patterns.feature) ----

@pytest.mark.negative
def test_gibberish_question_does_not_hallucinate_rule():
    index_uk_kb()
    out, _ = ask_uk("zzzqqq blorpt flimflam wobble 99999", k=5)
    assert "FCA Handbook section 999" not in out["answer"]


@pytest.mark.edge
def test_empty_question_safe_fallback():
    index_uk_kb()
    out, _ = ask_uk("", k=5)
    assert out["answer"] and (out["citations"] or "don't have" in out["answer"])


@pytest.mark.edge
def test_paraphrase_consistent_answer_metamorphic():
    index_uk_kb()
    a1, _ = ask_uk("What is the PRA minimum ICR and stressed rate for buy-to-let?", k=5)
    a2, _ = ask_uk("PRA minimum ICR stressed rate BTL?", k=5)
    assert_mentions(a1["answer"], "125 percent", "5.5 percent")
    assert_mentions(a2["answer"], "125 percent", "5.5 percent")


@pytest.mark.ai_pattern
def test_gold_document_recalled_top5():
    r = index_uk_kb()
    ids = [h["doc"] for h in search_uk(r, "PRA SS13/16 ICR 125 percent 5.5 percent")]
    assert "uk_12_affordability_btl.txt" in ids, ids


@pytest.mark.ai_pattern
def test_answer_faithfulness_is_perfect():
    index_uk_kb()
    out, _ = ask_uk("What is the PRA minimum ICR and stressed rate for buy-to-let?", k=5)
    assert faithfulness_of(out) == 1.0


@pytest.mark.ai_pattern
def test_user_memos_never_indexed_no_leakage():
    r = index_uk_kb()
    docs = {c["doc"] for c in r.chunks}
    assert docs and all(d.startswith("uk_") for d in docs)


@pytest.mark.ai_pattern
def test_typo_question_still_answers_robustness():
    index_uk_kb()
    out, _ = ask_uk("What is teh PRA minimun ICR for buy-to-lett?", k=5)
    assert_mentions(out["answer"], "125 percent", "5.5 percent")


@pytest.mark.ai_pattern
def test_vulnerable_customer_gets_conduct_guidance():
    index_uk_kb()
    out, _ = ask_uk("How should vulnerable customers in arrears be treated?", k=5)
    assert_mentions(out["answer"], "forbearance", "Breathing Space", "vulnerable")


@pytest.mark.ai_pattern
def test_same_question_twice_same_citations_determinism():
    index_uk_kb()
    o1, _ = ask_uk("What is Stage 2 under IFRS 9?", k=5)
    o2, _ = ask_uk("What is Stage 2 under IFRS 9?", k=5)
    assert o1["citations"] == o2["citations"]

