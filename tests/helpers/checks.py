"""Single source of truth for test helpers.
BDD steps call these; imperative tests call these. No logic duplicated.
Follows DRY + AAA (Arrange-Act-Assert) + Given-When-Then naming.
"""
import os
import time

APP_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "app.py")

# ---------- RAG ----------

def index_uk_kb():
    from src.rag_pipeline import rebuild_index
    r = rebuild_index()
    assert r.chunks, "UK KB index is empty"
    return r


def ask_uk(question, k=5):
    from src.rag_pipeline import ask
    t0 = time.perf_counter()
    out = ask(question, k=k)
    return out, time.perf_counter() - t0


def search_uk(retriever, query, k=5):
    return retriever.search(query, k=k)


def assert_mentions(answer, *options):
    assert any(o in answer for o in options), answer[:600]


def assert_cites_uk(out):
    assert out["citations"], "answer must cite UK KB docs"
    assert all(c.startswith("uk_") for c in out["citations"]), out["citations"]


def faithfulness_of(out):
    from src.evaluation.metrics import faithfulness
    return faithfulness(out["answer"], out["contexts"])


# ---------- memo files ----------

def make_pdf(path, text):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(path, pagesize=A4)
    t = c.beginText(50, 800)
    for line in text.split(". "):
        t.textLine(line.strip() + ".")
    c.drawText(t)
    c.save()
    return path


def make_jpg(path, text, width=2000, height=900):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(im)
    words, lines, cur = text.split(), [], ""
    for w in words:
        cur = (cur + " " + w).strip()
        if len(cur) > 88:
            lines.append(cur)
            cur = ""
    if cur:
        lines.append(cur)
    y = 30
    for ln in lines[:22]:
        d.text((30, y), ln, fill="black")
        y += 34
    im.save(path, "JPEG")
    return path


def make_txt(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def make_blank_png(path):
    from PIL import Image
    Image.new("RGB", (800, 600), "white").save(path)
    return path


def extract(path):
    from src.memo_extract import extract_memo_text
    return extract_memo_text(path)


def tesseract_available():
    import shutil
    return shutil.which("tesseract") is not None or os.path.exists(
        r"C:\Program Files\Tesseract-OCR\tesseract.exe")


# ---------- memo analyser ----------

def analyse_text(text):
    from src.memo_analyser import analyse_memo
    return analyse_memo(text, is_text=True)


def analyse_file(path):
    from src.memo_analyser import analyse_memo
    return analyse_memo(path)


def assert_checklist_shape(res, n=8):
    assert len(res["checklist"]) == n, res
    for row in res["checklist"]:
        assert set(row) >= {"check", "score", "status", "found"}, row


def assert_evidence_cites_uk(res):
    for e in res["standards_evidence"]:
        assert e["cites"] and all(c.startswith("uk_") for c in e["cites"]), e


# ---------- UI ----------

def run_app():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(APP_PATH, default_timeout=120)
    at.run()
    assert not at.exception, at.exception
    return at


def tab_by_label(at, label):
    labels = [t.label for t in at.tabs]
    return at.tabs[labels.index(label)]


# ---------- eval gates ----------

def ensure_eval_report(k=5):
    import json
    from src.evaluation.runner import run
    p = os.path.join("data", "eval", "evaluation_report.json")
    if not os.path.exists(p):
        run(k=k)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def assert_release_gates(rep):
    a = rep["aggregate"]
    assert a["recall@5"] >= 0.90, a
    assert a["faithfulness"] >= 0.90, a
    assert a["answer_relevance"] >= 0.90, a
    assert a["hallucination"] <= 0.05, a
    assert a["p95_latency_s"] <= 3.0, a
    assert rep["verdict"] == "PASS", rep
