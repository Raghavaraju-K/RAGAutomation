"""Developer-owned UNIT tests.

They stay in the codebase for fast local feedback (`pytest -q`,
`pytest tests/test_units.py`) but are deliberately EXCLUDED from the
automation report: the automation runner selects `-m "not unit"` and the
report builder also filters unit tests out by default.
"""
import pytest

pytestmark = pytest.mark.unit


def test_kb_is_uk_only():
    import os
    from src.config import KB_DIR
    files = os.listdir(KB_DIR)
    assert files, "KB empty"
    assert all(f.startswith("uk_") for f in files), files

def test_pdf_text_extraction():
    from src.memo_extract import extract_memo_text
    t, m = extract_memo_text("data/memos/_sample_memo.pdf")
    assert m == "pdf-text" and len(t) > 200, (m, len(t))

def test_image_ocr_if_available():
    import shutil
    from src.memo_extract import extract_memo_text
    if shutil.which("tesseract") is None:
        import os as _os
        if not _os.path.exists(r"C:\Program Files\Tesseract-OCR\tesseract.exe"):
            import pytest
            pytest.skip("tesseract not installed")
    t, m = extract_memo_text("data/memos/_sample_memo.png")
    assert len(t.strip()) > 50, (m, t[:200])

def test_memo_analyser_runs():
    from src.memo_analyser import analyse_memo
    txt = ("Borrower ABC Ltd Companies House 12345678 seeks 2MM pounds term loan at SONIA plus 250 bps. "
           "DSCR 1.35x, ICR 150 percent at 5.5 percent stress, LTI 3x. Debenture with fixed and floating charges "
           "to be registered at Companies House within 21 days. IFRS 9 Stage 1 with ECL coverage 1 percent. "
           "Consumer Duty fair value assessed, good outcome. Covenants include DSCR 1.20x and leverage 3.5x. "
           "OFSI sanctions clear, MLR KYC done, NCA no SAR. Guarantee by parent as deed with independent legal advice. "
           "Forbearance none, arrears none, vulnerability assessed, Financial Ombudsman rights explained.")
    r = analyse_memo(txt, is_text=True)
    assert r["overall_score"] >= 0.6, r
    assert "verdict" in r and "checklist" in r

def test_memo_analyser_pdf():
    from src.memo_analyser import analyse_memo
    r = analyse_memo("data/memos/_sample_memo.pdf")
    assert "verdict" in r, r
    assert r["overall_score"] >= 0.5, r
