"""Extract text from user-uploaded memos: .txt/.md/.pdf/.jpg/.jpeg/.png.
PDF: embedded text via pypdf; scanned pages via OCR if available.
Images: OCR if available. KB stays UK-only; memos never indexed."""
import os

TESSERACT_EXE = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def _ensure_tesseract():
    try:
        import pytesseract
        if os.path.exists(TESSERACT_EXE):
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE
    except Exception:
        pass

def _pdf_text_embedded(path):
    try:
        from pypdf import PdfReader
        r = PdfReader(path)
        out = []
        for p in r.pages:
            try:
                out.append(p.extract_text() or "")
            except Exception:
                out.append("")
        return "\n".join(out).strip()
    except Exception:
        return ""

def _ocr_available():
    try:
        import pytesseract  # noqa
        from PIL import Image  # noqa
        return True
    except Exception:
        return False

def _ocr_image(path):
    _ensure_tesseract()
    import pytesseract
    from PIL import Image
    img = Image.open(path)
    if img.mode != "RGB":
        img = img.convert("RGB")
    # upscale small images for OCR
    w, h = img.size
    if max(w, h) < 1500:
        s = 1500 / max(w, h)
        img = img.resize((int(w*s), int(h*s)))
    return pytesseract.image_to_string(img).strip()

def _ocr_pdf(path):
    """Render PDF pages with pypdfium2 then OCR each page."""
    _ensure_tesseract()
    import pypdfium2 as pdfium
    from PIL import Image
    import pytesseract
    pdf = pdfium.PdfDocument(path)
    texts = []
    for i in range(len(pdf)):
        page = pdf[i]
        bitmap = page.render(scale=2.5).to_pil()
        if bitmap.mode != "RGB":
            bitmap = bitmap.convert("RGB")
        texts.append(pytesseract.image_to_string(bitmap))
    return "\n".join(texts).strip()

def extract_memo_text(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".txt", ".md", ".text", ".csv"):
        for enc in ("utf-8", "latin-1"):
            try:
                return open(path, encoding=enc).read(), "text"
            except Exception:
                continue
        return "", "text"
    if ext == ".pdf":
        t = _pdf_text_embedded(path)
        if len(t.strip()) >= 50:
            return t.strip(), "pdf-text"
        if _ocr_available():
            try:
                t2 = _ocr_pdf(path)
                if t2.strip():
                    return t2, "pdf-ocr"
            except Exception as e:
                return "", f"pdf-ocr-failed: {e}. Install Tesseract (see README) or paste text."
        return "", ("no-extractable-text: scanned PDF with no OCR engine. "
                    "Install Tesseract OCR (https://github.com/UB-Mannheim/tesseract/wiki) "
                    "+ pip install pytesseract, or paste the memo text.")
    if ext in (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"):
        if _ocr_available():
            try:
                t = _ocr_image(path)
                if t.strip():
                    return t, "image-ocr"
                return "", "image-ocr-empty: OCR found no text. Try a clearer photo or paste text."
            except Exception as e:
                return "", f"image-ocr-failed: {e}"
        return "", ("no-ocr-engine: install Tesseract OCR "
                    "(https://github.com/UB-Mannheim/tesseract/wiki) + pip install pytesseract, "
                    "or paste the memo text.")
    return "", f"unsupported-type: {ext}"
