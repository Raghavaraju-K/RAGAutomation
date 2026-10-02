"""BDD: memo extraction + analysis. Self-contained."""
import os
import pytest
from pytest_bdd import given, when, then, parsers, scenarios

scenarios("features/memo_extraction.feature")
scenarios("features/memo_analysis.feature")


@pytest.fixture
def bdd_file(tmp_path):
    return {"dir": str(tmp_path)}


@given("a generated digital PDF memo")
def gen_pdf(bdd_file, sample_text):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    p = os.path.join(bdd_file["dir"], "memo.pdf")
    c = canvas.Canvas(p, pagesize=A4)
    t = c.beginText(50, 800)
    for line in sample_text.split(". "):
        t.textLine(line.strip() + ".")
    c.drawText(t)
    c.save()
    bdd_file["path"] = p


@given("a generated JPG memo image")
def gen_jpg(bdd_file, sample_text):
    from PIL import Image, ImageDraw
    p = os.path.join(bdd_file["dir"], "memo.jpg")
    im = Image.new("RGB", (2000, 900), "white")
    d = ImageDraw.Draw(im)
    words, lines, cur = sample_text.split(), [], ""
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
    im.save(p, "JPEG")
    bdd_file["path"] = p


@given('a generated JPG memo image saved as ".jpeg"')
def gen_jpeg(bdd_file, sample_text):
    from PIL import Image, ImageDraw
    p = os.path.join(bdd_file["dir"], "memo.jpeg")
    im = Image.new("RGB", (2000, 900), "white")
    d = ImageDraw.Draw(im)
    d.text((30, 30), sample_text[:400], fill="black")
    im.save(p, "JPEG")
    bdd_file["path"] = p


@given("a generated TXT memo")
def gen_txt(bdd_file, sample_text):
    p = os.path.join(bdd_file["dir"], "memo.txt")
    open(p, "w", encoding="utf-8").write(sample_text)
    bdd_file["path"] = p


@given(parsers.parse('a file named "{name}" with fake bytes'))
def fake_file(bdd_file, name):
    p = os.path.join(bdd_file["dir"], name)
    open(p, "wb").write(b"fake")
    bdd_file["path"] = p


@given("a blank PNG image")
def blank_png_g(bdd_file):
    from PIL import Image
    p = os.path.join(bdd_file["dir"], "blank.png")
    Image.new("RGB", (800, 600), "white").save(p)
    bdd_file["path"] = p


@given("a strong UK memo text")
def strong_txt(bdd_file, sample_text):
    bdd_file["text"] = sample_text


@given("a weak memo text missing debenture and covenants")
def weak_txt(bdd_file, weak_text):
    bdd_file["text"] = weak_text


@given("an empty memo text")
def empty_txt(bdd_file):
    bdd_file["text"] = "   "


@given("a path to a memo file that does not exist")
def missing_path(bdd_file):
    bdd_file["path"] = os.path.join(bdd_file["dir"], "nope.pdf")


@when("I extract its text")
def do_extract(bdd_file):
    from src.memo_extract import extract_memo_text
    t, m = extract_memo_text(bdd_file["path"])
    bdd_file["text_out"], bdd_file["method"] = t, m


@when("I analyse the memo")
def do_analyse_text(bdd_file):
    from src.memo_analyser import analyse_memo
    bdd_file["res"] = analyse_memo(bdd_file["text"], is_text=True)


@when("I analyse the memo file")
def do_analyse_file(bdd_file):
    from src.memo_analyser import analyse_memo
    bdd_file["res"] = analyse_memo(bdd_file["path"])


@then(parsers.parse('the method is "{m}" and "{kw}" is present'))
def method_kw(bdd_file, m, kw):
    assert bdd_file["method"] == m, bdd_file["method"]
    assert kw in bdd_file["text_out"], bdd_file["text_out"][:300]


@then("the method is \"image-ocr\" and text is non-empty")
def ocr_nonempty(bdd_file):
    import shutil
    if shutil.which("tesseract") is None and not os.path.exists(
            r"C:\Program Files\Tesseract-OCR\tesseract.exe"):
        pytest.skip("tesseract not installed")
    assert bdd_file["method"] == "image-ocr", bdd_file["method"]
    assert len(bdd_file["text_out"].strip()) > 20


@then(parsers.parse('extraction fails with "{msg}"'))
def extraction_fails(bdd_file, msg):
    assert bdd_file["text_out"] == "", bdd_file["text_out"][:200]
    assert msg.lower() in bdd_file["method"].lower(), bdd_file["method"]


@then(parsers.parse('extraction fails with guidance to "{msg}" or clearer photo'))
def extraction_guidance(bdd_file, msg):
    import shutil
    if shutil.which("tesseract") is None and not os.path.exists(
            r"C:\Program Files\Tesseract-OCR\tesseract.exe"):
        pytest.skip("tesseract not installed")
    assert bdd_file["text_out"] == ""
    assert msg.lower() in bdd_file["method"].lower() or "clearer" in bdd_file["method"].lower()


@then("extraction succeeds or reports an OCR message")
def extraction_ok_or_msg(bdd_file):
    assert "ocr" in bdd_file["method"].lower() or bdd_file["text_out"] != ""


@then(parsers.parse('the verdict is "{v}"'))
def verdict_is(bdd_file, v):
    assert bdd_file["res"].get("verdict") == v, bdd_file["res"]


@then("all 8 checklist rows have check score and status")
def checklist_shape(bdd_file):
    rows = bdd_file["res"]["checklist"]
    assert len(rows) == 8
    assert all(set(r) >= {"check", "score", "status", "found"} for r in rows)


@then("standards evidence cites UK documents")
def evidence_uk(bdd_file):
    for e in bdd_file["res"]["standards_evidence"]:
        assert e["cites"] and all(c.startswith("uk_") for c in e["cites"])


@then(parsers.parse("a verdict is returned with overall score at least {s:f}"))
def verdict_score(bdd_file, s):
    assert "verdict" in bdd_file["res"], bdd_file["res"]
    assert bdd_file["res"]["overall_score"] >= s


@then(parsers.parse("at least {n:d} gaps are reported"))
def gaps_n(bdd_file, n):
    assert len(bdd_file["res"]["gaps"]) >= n, bdd_file["res"]


@then("an error is returned")
def error_returned(bdd_file):
    assert "error" in bdd_file["res"], bdd_file["res"]


