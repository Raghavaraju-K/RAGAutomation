"""Extractive grounded generator: only emits sentences from retrieved context.
This keeps faithfulness high and hallucination low by construction."""
import re

SENT = re.compile(r"(?<=[.!?])\s+")

def split_sentences(t):
    return [s.strip() for s in SENT.split(t.strip()) if len(s.strip()) > 20]

def overlap(a, b):
    sa = set(re.findall(r"[a-z0-9]+", a.lower()))
    sb = set(re.findall(r"[a-z0-9]+", b.lower()))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)

STOP = set("what which when where who whom whose why how is are was were be been being do does did done have has had having will would shall should may might must can could ought i you he she it we they them this that these those a an the and or but if then than so such as of at by for with about into through during before after over under again once here there all any both each few more most other some no nor not only own same too very just don list name give tell explain describe contain".split())

def qtoks(q):
    t = [x for x in re.findall(r"[a-z0-9]+", q.lower()) if x not in STOP and len(x) > 2]
    return t or re.findall(r"[a-z0-9]+", q.lower())

def sscore(qts, sent):
    st = set(re.findall(r"[a-z0-9]+", sent.lower()))
    hits = sum(1 for q in qts if q in st)
    rec = hits / max(1, len(set(qts)))
    bonus = 0.0
    if re.search(r"\d", sent):
        bonus += 0.3
    if any(u in sent.lower() for u in ["minimum", "maximum", "required", "must", "equals", "percent", "bps", "mm", "not a guarantee"]):
        bonus += 0.15
    return rec + bonus * 0.2


def generate_answer(query, contexts, max_sents=5):
    qts = qtoks(query)
    cands = []
    for c in contexts:
        for s in split_sentences(c["text"]):
            cands.append((sscore(qts, s), s, c["doc"]))
    if not cands:
        return {"answer": "I don't have that in the credit policy KB.",
                "citations": []}
    cands.sort(key=lambda x: -x[0])
    # greedy cover of query tokens
    picked, used, covered_all = [], set(), set()
    for _ in range(max_sents):
        best_i, best_key = -1, None
        for i, (sc, s, d) in enumerate(cands):
            if i in used:
                continue
            new = len(set(re.findall(r"[a-z0-9]+", s.lower())) & (set(qts) - covered_all))
            key = (new, sc)
            if best_key is None or key > best_key:
                best_key, best_i = key, i
        if best_i < 0:
            break
        used.add(best_i)
        picked.append(cands[best_i])
        covered_all |= set(re.findall(r"[a-z0-9]+", cands[best_i][1].lower()))
    ans = " ".join(s for _, s, _ in picked)
    cites = sorted(set(d for _, _, d in picked))
    return {"answer": ans, "citations": cites}
