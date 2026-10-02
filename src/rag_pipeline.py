"""RAG pipeline: retrieve locally then generate grounded answer."""
import os, time
from .config import KB_DIR, INDEX_DIR, TOP_K, CHUNK_SIZE, CHUNK_OVERLAP
from .retriever import LocalRetriever
from .generator import generate_answer

_retriever = None

def get_retriever():
    global _retriever
    if _retriever is not None:
        return _retriever
    r = LocalRetriever(CHUNK_SIZE, CHUNK_OVERLAP)
    idx_c = os.path.join(INDEX_DIR, "chunks.json")
    if os.path.exists(idx_c):
        try:
            r.load(INDEX_DIR)
            if r.chunks:
                _retriever = r
                return r
        except Exception:
            pass
    r.build(KB_DIR)
    try:
        r.save(INDEX_DIR)
    except Exception:
        pass
    _retriever = r
    return r

def rebuild_index():
    global _retriever
    r = LocalRetriever(CHUNK_SIZE, CHUNK_OVERLAP).build(KB_DIR)
    r.save(INDEX_DIR)
    _retriever = r
    return r

def ask(query, k=TOP_K):
    t0 = time.perf_counter()
    r = get_retriever()
    ctx = r.search(query, k=k)
    g = generate_answer(query, ctx)
    dt = time.perf_counter() - t0
    return {"query": query, "answer": g["answer"],
            "citations": g["citations"], "contexts": ctx,
            "latency_s": round(dt, 3)}
