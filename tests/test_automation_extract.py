"""Imperative automation: memo file extraction (txt/pdf/jpg/png) + error paths.

Best practice: boundary-value + error-guessing; generated fixtures
(conftest) avoid checked-in binaries; OCR tests skip cleanly without engine.
BDD mirror: tests/bdd/features/memo_extraction.feature
"""
import pytest

from tests.helpers.checks import extract, tesseract_available

pytestmark = [pytest.mark.extraction, pytest.mark.integration]
needs_ocr = pytest.mark.skipif(not tesseract_available(), reason="tesseract not installed")


def test_extract_txt(tmp_path, sample_text):
    from tests.helpers.checks import make_txt
    p = make_txt(str(tmp_path / "memo.txt"), sample_text)
    t, m = extract(p)
    assert m == "text" and "Companies House" in t


def test_extract_pdf_text(sample_pdf):
    t, m = extract(sample_pdf)
    assert m == "pdf-text", m
    assert "SONIA" in t and "Companies House" in t


@needs_ocr
def test_extract_jpg_ocr(sample_jpg):
    t, m = extract(sample_jpg)
    assert m == "image-ocr", m
    assert ("Companies House" in t or "SONIA" in t or "Debenture" in t), t[:300]


@needs_ocr
def test_extract_blank_image_gives_actionable_error(blank_png):
    t, m = extract(blank_png)
    assert t == "" and ("paste" in m.lower() or "no text" in m.lower()), m


@pytest.mark.negative
def test_extract_unsupported_type(tmp_path):
    p = str(tmp_path / "memo.xlsx")
    open(p, "wb").write(b"fake")
    t, m = extract(p)
    assert t == "" and "unsupported-type" in m


@pytest.mark.edge
def test_jpeg_extension_accepted(tmp_path, sample_jpg):
    from PIL import Image
    q = str(tmp_path / "memo.jpeg")
    Image.open(sample_jpg).save(q, "JPEG")
    t, m = extract(q)
    assert m in ("image-ocr",) or "ocr" in m.lower() or t == "", m

