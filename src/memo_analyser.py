"""User memo analysis against UK-standards-only KB."""
import os, re
from .rag_pipeline import ask
from .config import MEMO_DIR
from .memo_extract import extract_memo_text

CHECKLIST = [
 ("Consumer Duty + fair value outcome", ["consumer duty", "fair value", "good outcome", "price and value"]),
 ("Affordability (MCOB 11/CONC, ICR/LTI/DSCR stress)", ["affordab", "icr", "lti", "dscr", "stress", "mcob", "conc"]),
 ("IFRS 9 stage, ECL + coverage", ["ifrs 9", "stage", "ecl", "coverage", "sicr"]),
 ("Security: debenture + Companies House 21 days", ["debenture", "companies house", "21 days", "fixed and floating", "charge"]),
 ("Covenants + breach headroom", ["covenant", "dscr", "leverage", "headroom", "breach"]),
 ("Conduct: vulnerability, arrears, forbearance, FOS", ["vulnerab", "arrears", "forbearance", "breathing space", "ombudsman"]),
 ("Financial crime: MLR/KYC/OFSI/NCA", ["kyc", "aml", "ofsi", "nca", "money laundering", "sanction"]),
 ("Guarantees + independent advice", ["guarantee", "independent legal advice", "deed"]),
]

def _read_memo(path_or_text, is_text=False):
    if is_text:
        return path_or_text
    text, method = extract_memo_text(path_or_text)
    if text:
        return f"[extracted via {method}]\n" + text
    return ""

def _score(text, phrases):
    t = text.lower()
    hits = [p for p in phrases if p in t]
    return hits, (len(hits) / len(phrases)) if phrases else 1.0

def analyse_memo(path_or_text, is_text=False, top_k=5):
    text = _read_memo(path_or_text, is_text)
    if not text.strip():
        if not is_text:
            _, method = extract_memo_text(path_or_text)
            return {"error": f"Could not read text from file. ({method})"}
        return {"error": "Empty memo."}
    rows, gaps = [], []
    for label, phrases in CHECKLIST:
        hits, sc = _score(text, phrases)
        status = "PASS" if sc >= 0.5 else ("REVIEW" if sc >= 0.25 else "GAP")
        rows.append({"check": label, "score": round(sc, 2),
                     "status": status, "found": hits})
        if status == "GAP":
            gaps.append(label)
    # UK-grounded Q&A over the memo-relevant standards
    probes = ["Consumer Duty fair value assessment for this memo",
              "IFRS 9 stage and ECL coverage required",
              "Companies House debenture registration within 21 days",
              "Affordability ICR LTI DSCR stress for UK borrowers"]
    evidence = [ask(p, k=top_k) for p in probes]
    overall = round(sum(r["score"] for r in rows) / len(rows), 2)
    verdict = "READY FOR REVIEW" if overall >= 0.6 and len(gaps) <= 2 else "NEEDS WORK BEFORE COMMITTEE"
    return {"overall_score": overall, "verdict": verdict,
            "checklist": rows, "gaps": gaps,
            "standards_evidence": [{"q": e["query"], "a": e["answer"],
                                    "cites": e["citations"]} for e in evidence],
            "memo_chars": len(text)}
