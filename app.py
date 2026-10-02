import streamlit as st
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.rag_pipeline import ask, rebuild_index, get_retriever
from src.evaluation.runner import run as run_eval
from src.memo_analyser import analyse_memo
from src.config import EVAL_DIR, KB_DIR, MEMO_DIR

st.set_page_config(page_title="UK Credit Memo RAG", layout="wide")
st.title("UK Credit Memo AI — Local RAG (FCA/PRA aligned)")
st.warning("Educational demo using public-summary UK standards (FCA Handbook, PRA Rulebook, MCOB/CONC, IFRS 9, MLR 2017). Not regulated advice. Verify against the current FCA Handbook / PRA Rulebook before any real lending decision.")

tabs = st.tabs(["Analyse My Memo", "Ask UK Standards", "Knowledge Base (UK only)", "Evaluation Dashboard", "Fine-tune"])

with tabs[0]:
    st.subheader("Analyse your credit memo against UK banking standards")
    st.caption("KB stays UK-standards-only. Your memo is stored in data/memos/ and is NEVER added to the KB index.")
    up = st.file_uploader("Upload your credit memo (PDF, JPG, JPEG, PNG, TXT, MD)",
                          type=["pdf", "jpg", "jpeg", "png", "txt", "md"])
    pasted = st.text_area("...or paste memo text", height=220)
    if up is not None and up.type.startswith("image"):
        st.image(up, caption="Uploaded memo image", width=420)
    if st.button("Analyse memo"):
        if up is not None:
            os.makedirs(MEMO_DIR, exist_ok=True)
            mp = os.path.join(MEMO_DIR, up.name)
            open(mp, "wb").write(up.getbuffer())
            with st.spinner("Extracting text + analysing..."):
                res = analyse_memo(mp)
            with st.expander("Extracted memo text (preview)"):
                from src.memo_extract import extract_memo_text as _ext
                _t, _m = _ext(mp)
                st.caption(f"Method: {_m} — {len(_t)} chars")
                st.text((_t or "(no text extracted)")[:4000])
        elif pasted.strip():
            res = analyse_memo(pasted, is_text=True)
        else:
            st.error("Upload or paste a memo first.")
            res = None
        if res and "error" not in res:
            st.metric("Overall UK-readiness", res["overall_score"])
            st.success(res["verdict"])
            if res["gaps"]:
                st.error("Gaps: " + "; ".join(res["gaps"]))
            st.table(res["checklist"])
            with st.expander("UK standards evidence"):
                for e in res["standards_evidence"]:
                    st.markdown(f"**Q: {e['q']}**")
                    st.write(e["a"])
                    st.caption("Sources: " + ", ".join(e["cites"]))
            dl = json.dumps(res, indent=2)
            st.download_button("Download analysis (JSON)", dl, "memo_uk_analysis.json")
        elif res:
            st.error(res["error"])

with tabs[1]:
    st.subheader("Ask about UK standards")
    q = st.text_input("Question", "What is the PRA minimum ICR and stressed rate for buy-to-let?")
    k = st.slider("Top-K", 1, 10, 5)
    if st.button("Ask"):
        t0 = time.perf_counter()
        out = ask(q, k=k)
        st.write(f"Latency: {out['latency_s']}s")
        st.success(out["answer"])
        st.caption("Citations: " + ", ".join(out["citations"]))
        st.info("UK check: verify against current FCA Handbook / PRA Rulebook; confirmed sources are listed in citations.")
        with st.expander("Retrieved context"):
            for c in out["contexts"]:
                st.markdown(f"**{c['doc']}** (score {c['score']})")
                st.text(c["text"][:1200])

with tabs[2]:
    st.subheader(f"UK-only knowledge base: {KB_DIR}")
    st.caption("Locked to uk_*.txt. User memos are NOT indexed.")
    files = sorted(f for f in os.listdir(KB_DIR) if f.startswith("uk_")) if os.path.exists(KB_DIR) else []
    st.write(f"{len(files)} UK standards documents (local)")
    for f in files:
        st.markdown(f"- {f}")

    if st.button("Rebuild UK index"):
        r = rebuild_index()
        st.success(f"Index rebuilt: {len(r.chunks)} chunks from UK KB only")

with tabs[3]:
    st.subheader("RAG Evaluation Framework — UK (100 questions)")
    st.text("Run RAG Pipeline -> Retrieval (Recall@K, Precision@K, MRR, Hit@K) + Generation (Faithfulness, Correctness, Relevance, Hallucination) -> Report -> Pass/Fail + Dashboard -> CI/CD Gate")
    if st.button("Run full evaluation"):
        with st.spinner("Running 100 questions..."):
            rep = run_eval(k=5)
        st.write(f"Verdict: {rep['verdict']}")
        st.json(rep["aggregate"])
        st.json(rep["checks"])
    rp = os.path.join(EVAL_DIR, "evaluation_report.json")
    if os.path.exists(rp):
        rep = json.load(open(rp, encoding="utf-8"))
        st.metric("Recall@5", round(rep["aggregate"]["recall@5"], 3))
        st.metric("Faithfulness", round(rep["aggregate"]["faithfulness"], 3))
        st.metric("Answer relevance", round(rep["aggregate"]["answer_relevance"], 3))
        st.metric("Hallucination", round(rep["aggregate"]["hallucination"], 3))
        st.metric("P95 latency (s)", round(rep["aggregate"]["p95_latency_s"], 3))
        st.bar_chart({"recall@5": rep["aggregate"]["recall@5"], "faithfulness": rep["aggregate"]["faithfulness"], "relevance": rep["aggregate"]["answer_relevance"], "correctness": rep["aggregate"]["correctness"]})

with tabs[4]:
    st.subheader("Fine-tune later (prep)")
    st.write("Log Q/A feedback locally for future fine-tuning. No cloud needed.")
    fq = st.text_input("Feedback question")
    fa = st.text_area("Corrected answer")
    if st.button("Save feedback"):
        fp = os.path.join(EVAL_DIR, "finetune_feedback.jsonl")
        open(fp, "a", encoding="utf-8").write(json.dumps({"q": fq, "a": fa}) + "\n")
        st.success(f"Saved to {fp}")

