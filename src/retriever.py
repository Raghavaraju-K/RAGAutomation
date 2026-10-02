"""Local TF-IDF retriever. No internet, no API keys. Persists to data/index/."""
import os, re, math, json
from collections import Counter

TOKEN = re.compile(r"[a-z0-9]+")

def tokenize(t):
    return TOKEN.findall(t.lower())

class LocalRetriever:
    def __init__(self, chunk_size=900, overlap=150):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.chunks = []   # {id, doc, text}
        self.df = Counter()
        self.N = 0

    def chunk_text(self, text):
        out, i = [], 0
        while i < len(text):
            out.append(text[i:i+self.chunk_size])
            i += self.chunk_size - self.overlap
        return out

    def build(self, kb_dir):
        import fnmatch
        from .config import KB_GLOB
        self.chunks, self.df = [], Counter()
        for fn in sorted(os.listdir(kb_dir)):
            if not fnmatch.fnmatch(fn, KB_GLOB):
                continue
            p = os.path.join(kb_dir, fn)
            if not os.path.isfile(p):
                continue
            try:
                txt = open(p, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            for j, c in enumerate(self.chunk_text(txt)):
                cid = f"{fn}#c{j}"
                toks = set(tokenize(c))
                self.chunks.append({"id": cid, "doc": fn, "text": c,
                                    "tf": Counter(tokenize(c))})
                for t in toks:
                    self.df[t] += 1
        self.N = len(self.chunks)
        return self

    def idf(self, t):
        return math.log((1 + self.N) / (1 + self.df.get(t, 0))) + 1.0

    def search(self, query, k=5):
        qt = Counter(tokenize(query))
        qnorm = math.sqrt(sum(v*v for v in qt.values())) or 1.0
        scored = []
        for ch in self.chunks:
            s = 0.0
            for t, qv in qt.items():
                tf = ch["tf"].get(t, 0)
                if tf:
                    s += (qv/qnorm) * (1+math.log(tf)) * self.idf(t)
            scored.append((s, ch))
        scored.sort(key=lambda x: -x[0])
        res = []
        for s, ch in scored[:k]:
            res.append({"id": ch["id"], "doc": ch["doc"],
                        "text": ch["text"], "score": round(float(s), 4)})
        return res

    def save(self, d):
        os.makedirs(d, exist_ok=True)
        json.dump([{"id": c["id"], "doc": c["doc"], "text": c["text"]}
                   for c in self.chunks],
                  open(os.path.join(d, "chunks.json"), "w", encoding="utf-8"))
        json.dump({"df": dict(self.df), "N": self.N},
                  open(os.path.join(d, "df.json"), "w", encoding="utf-8"))

    def load(self, d):
        raw = json.load(open(os.path.join(d, "chunks.json"), encoding="utf-8"))
        meta = json.load(open(os.path.join(d, "df.json"), encoding="utf-8"))
        self.chunks = [{"id": r["id"], "doc": r["doc"], "text": r["text"],
                        "tf": Counter(tokenize(r["text"]))} for r in raw]
        self.df = Counter(meta["df"]); self.N = meta["N"]
        return self
