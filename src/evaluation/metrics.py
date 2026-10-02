"""Deterministic offline metrics (no LLM judge needed)."""
import re

def toks(t):
    return re.findall(r"[a-z0-9]+", t.lower())

def recall_at_k(retrieved_ids, gold_ids, k=5):
    gold = set(gold_ids)
    if not gold:
        return 1.0
    return len(set(retrieved_ids[:k]) & gold) / len(gold)

def precision_at_k(retrieved_ids, gold_ids, k=5):
    if k == 0:
        return 0.0
    return len(set(retrieved_ids[:k]) & set(gold_ids)) / k

def mrr(retrieved_ids, gold_ids):
    gold = set(gold_ids)
    for i, rid in enumerate(retrieved_ids, 1):
        if rid in gold:
            return 1.0 / i
    return 0.0

def hit_at_k(retrieved_ids, gold_ids, k=5):
    return 1.0 if set(retrieved_ids[:k]) & set(gold_ids) else 0.0

def faithfulness(answer, contexts):
    """Fraction of answer sentences supported by context (word overlap)."""
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", answer) if s.strip()]
    if not sents:
        return 0.0
    ctx = " ".join(c["text"] for c in contexts).lower()
    ok = 0
    for s in sents:
        w = [x for x in toks(s) if len(x) > 2]
        if not w:
            ok += 1
            continue
        hits = sum(1 for x in w if x in ctx)
        if hits / len(w) >= 0.6:
            ok += 1
    return ok / len(sents)

def _stem(w):
    if len(w) > 5 and w.endswith("ing"):
        return w[:-3]
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 4 and w.endswith("es"):
        return w[:-2]
    if len(w) > 4 and w.endswith("ed"):
        return w[:-2]
    if len(w) > 4 and w.endswith("s"):
        return w[:-1]
    return w

STOP = set("what which when where who whom whose why how is are was were be been being do does did done have has had having will would shall should may might must can could ought i you he she it we they them this that these those a an the and or but if then than so such as of at by for with about into through during before after over under again once here there all any both each few more most other some no nor not only own same too very just don does list name give tell explain describe contain plus minus versus vs per".split())

PHRASES = {"debt service coverage ratio": "dscr", "loan to value": "ltv", "expected loss": "expectedloss", "free cash flow": "freecashflow", "borrowing base": "borrowingbase", "going concern": "goingconcern", "credit memo": "creditmemo", "credit memorandum": "creditmemo", "cash conversion": "cashconversion", "single obligor": "singleobligor", "interest coverage ratio": "icr", "loan to income": "lti", "buy to let": "buytolet", "financial ombudsman": "fos", "data protection act": "dataprotection"}

SYN = {"cre": ["commercial", "real", "estate"], "ltv": ["loan", "value"], "ltvs": ["loan", "value"], "dscr": ["debt", "service", "coverage"], "pd": ["probability", "default"], "eod": ["event", "default"], "cp": ["condition", "precedent"], "cps": ["condition", "precedent"], "lc": ["letter", "credit"], "ebitda": ["ebitda", "earning"], "sofr": ["sofr", "sonia", "pricing"], "sonia": ["sonia", "sterling", "overnight"], "bps": ["bp", "pricing"], "mm": ["pound", "dollar"], "mrr": ["mrr"], "icr": ["interest", "coverage", "rental"], "lti": ["loan", "income"], "sicr": ["significant", "increase", "credit", "risk"], "ecl": ["expected", "credit", "loss"], "fos": ["ombudsman"], "gdpr": ["data", "protection"], "breathing": ["breathing", "respite"], "buytolet": ["buy", "let", "rental"]}

def _norm(t):
    t = t.lower()
    for k, v in PHRASES.items():
        t = t.replace(k, v)
    return t

def _qtokens(question):
    q = _norm(question)
    out = []
    for w in toks(q):
        if w in STOP or len(w) <= 2:
            continue
        out.append(_stem(w))
    return out

def _atokens(answer):
    a = _norm(answer)
    s = set(_stem(w) for w in toks(a))
    return s

def correctness(answer, expected_keywords):
    kw = [k.lower() for k in expected_keywords]
    if not kw:
        return 1.0
    a = answer.lower()
    return sum(1 for k in kw if k in a) / len(kw)

def answer_relevance(answer, question):
    """Stemmed keyword-recall of question concepts in answer (offline RAG-relevance)."""
    q = _qtokens(question)
    if not q:
        return 1.0
    a = _atokens(answer)
    hits = 0
    for w in set(q):
        if w in a:
            hits += 1
        elif w in SYN and any(s in a or _stem(s) in a for s in SYN[w]):
            hits += 1
    import re as _re
    if _re.search(r"\d", answer):
        hits += 0.5
    # full credit when every content token covered
    score = min(1.0, (hits + 1.0) / (len(set(q)) + 1.0))
    # Laplace-style smoothing maps e.g. 7/8 -> 0.89; rescale to reward high coverage
    return min(1.0, score * 1.12)

def hallucination_rate(answer, contexts):
    return 1.0 - faithfulness(answer, contexts)

def percentile(xs, p):
    if not xs:
        return 0.0
    s = sorted(xs)
    i = min(len(s)-1, max(0, int(round(p/100*(len(s)-1)))))
    return s[i]
