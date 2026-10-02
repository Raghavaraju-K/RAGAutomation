"""BDD: UK RAG QA + AI testing patterns. Self-contained (steps + scenarios)."""
import os
import pytest
from pytest_bdd import given, when, then, parsers, scenarios

scenarios("features/rag_qa.feature")
scenarios("features/ai_patterns.feature")


@pytest.fixture
def bdd_ctx():
    return {}


@given("the UK knowledge base is indexed")
def uk_indexed(bdd_ctx):
    from src.rag_pipeline import rebuild_index
    bdd_ctx["retriever"] = rebuild_index()
    assert bdd_ctx["retriever"].chunks


@when(parsers.parse('I ask "{q}"'))
def ask_q(bdd_ctx, q):
    import time
    from src.rag_pipeline import ask
    t0 = time.perf_counter()
    bdd_ctx["out"] = ask(q, k=5)
    bdd_ctx["latency"] = time.perf_counter() - t0
    bdd_ctx["question"] = q


@when(parsers.parse('I ask "{q}" twice'))
def ask_twice(bdd_ctx, q):
    from src.rag_pipeline import ask
    bdd_ctx["out"] = ask(q, k=5)
    bdd_ctx["out2"] = ask(q, k=5)


@when(parsers.parse('I search "{q}"'))
def search_q(bdd_ctx, q):
    bdd_ctx["hits"] = bdd_ctx["retriever"].search(q, k=5)


@then(parsers.parse('the answer mentions "{a}" or "{b}"'))
def mentions_either(bdd_ctx, a, b):
    ans = bdd_ctx["out"]["answer"]
    assert a in ans or b in ans, ans[:500]


@then(parsers.parse('the answer mentions "{a}"'))
def mentions(bdd_ctx, a):
    assert a in bdd_ctx["out"]["answer"], bdd_ctx["out"]["answer"][:500]


@then("the answer cites a UK standards document")
def cites_uk(bdd_ctx):
    assert bdd_ctx["out"]["citations"]
    assert all(c.startswith("uk_") for c in bdd_ctx["out"]["citations"])


@then("the latency is under 3 seconds")
def latency_ok(bdd_ctx):
    assert bdd_ctx["latency"] < 3.0


@then(parsers.parse('the answer does not invent "{phrase}"'))
def no_invent(bdd_ctx, phrase):
    assert phrase not in bdd_ctx["out"]["answer"]


@then("an answer is still returned with citations or a safe fallback")
def fallback_ok(bdd_ctx):
    out = bdd_ctx["out"]
    assert out["answer"] and (out["citations"] or "don't have" in out["answer"])


@then(parsers.parse('both answers mention "{a}" or "{b}"'))
def both_mention(bdd_ctx, a, b):
    from src.rag_pipeline import ask
    second = ask("PRA minimum ICR stressed rate BTL?", k=5)
    for o in (bdd_ctx["out"], second):
        assert a in o["answer"] or b in o["answer"], o["answer"][:400]


@when("I ask an empty question")
def ask_empty(bdd_ctx):
    import time
    from src.rag_pipeline import ask
    t0 = time.perf_counter()
    bdd_ctx["out"] = ask("", k=5)
    bdd_ctx["latency"] = time.perf_counter() - t0


@then(parsers.parse('"{doc}" is in the top 5'))
def doc_in_top5(bdd_ctx, doc):
    ids = [h["doc"] for h in bdd_ctx["hits"]]
    assert doc in ids, ids


@then("faithfulness of the answer to its contexts is 1.0")
def faith_one(bdd_ctx):
    from src.evaluation.metrics import faithfulness
    out = bdd_ctx["out"]
    assert faithfulness(out["answer"], out["contexts"]) == 1.0


@then("the index contains only UK standards documents")
def index_uk_only(bdd_ctx):
    docs = {c["doc"] for c in bdd_ctx["retriever"].chunks}
    assert docs and all(d.startswith("uk_") for d in docs)


@then('"data/memos" files are absent from the index')
def memos_absent(bdd_ctx):
    docs = {c["doc"] for c in bdd_ctx["retriever"].chunks}
    assert not any("memo" in d.lower() and not d.startswith("uk_") for d in docs)


@then("both runs cite the same documents")
def same_cites(bdd_ctx):
    assert bdd_ctx["out"]["citations"] == bdd_ctx["out2"]["citations"]



