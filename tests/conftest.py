"""Shared pytest fixtures: sample memo text, generated PDF/JPG, paths."""
import os
import pytest

SAMPLE_TEXT = (
    "Borrower ABC Ltd Companies House 12345678 seeks 2MM pounds term loan "
    "at SONIA plus 250 bps. DSCR 1.35x, ICR 150 percent at 5.5 percent stress, "
    "LTI 3x. Debenture with fixed and floating charges to be registered at "
    "Companies House within 21 days. IFRS 9 Stage 1 with ECL coverage 1 percent. "
    "Consumer Duty fair value assessed, good outcome. Covenants include DSCR 1.20x "
    "and leverage 3.5x with headroom and no breach. "
    "OFSI sanctions clear, MLR KYC done, NCA no SAR, money laundering checks passed. "
    "Guarantee by parent as deed with independent legal advice. "
    "Forbearance none, arrears none, vulnerability assessed, "
    "breathing space considered, Financial Ombudsman rights explained."
)

WEAK_TEXT = (
    "Borrower XYZ Ltd seeks loan. DSCR 1.1x weak. No debenture yet. "
    "No covenants stated."
)

SAMPLE_QUESTIONS = [
    "What is the PRA minimum ICR and stressed rate for buy-to-let?",
    "What reference rate replaces SOFR for UK pricing?",
    "What is Stage 2 under IFRS 9?",
]


@pytest.fixture(scope="session")
def sample_text():
    return SAMPLE_TEXT


@pytest.fixture(scope="session")
def weak_text():
    return WEAK_TEXT


@pytest.fixture(scope="session")
def sample_pdf(tmp_path_factory):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    p = str(tmp_path_factory.mktemp("memos") / "memo.pdf")
    c = canvas.Canvas(p, pagesize=A4)
    t = c.beginText(50, 800)
    for line in SAMPLE_TEXT.split(". "):
        t.textLine(line.strip() + ".")
    c.drawText(t)
    c.save()
    assert os.path.exists(p)
    return p


@pytest.fixture(scope="session")
def sample_jpg(tmp_path_factory):
    from PIL import Image, ImageDraw
    p = str(tmp_path_factory.mktemp("memos") / "memo.jpg")
    im = Image.new("RGB", (2000, 900), "white")
    d = ImageDraw.Draw(im)
    words, lines, cur = SAMPLE_TEXT.split(), [], ""
    for w in words:
        if len(cur) + len(w) < 90:
            cur += " " + w
        else:
            lines.append(cur.strip())
            cur = w
    lines.append(cur.strip())
    y = 30
    for ln in lines[:22]:
        d.text((30, y), ln, fill="black")
        y += 34
    im.save(p, "JPEG")
    return p


@pytest.fixture(scope="session")
def blank_png(tmp_path_factory):
    from PIL import Image
    p = str(tmp_path_factory.mktemp("memos") / "blank.png")
    Image.new("RGB", (800, 600), "white").save(p)
    return p
