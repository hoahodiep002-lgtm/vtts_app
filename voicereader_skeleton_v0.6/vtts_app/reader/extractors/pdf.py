def extract(path: str) -> str:
    """pypdf (thuan Python) thay pdfplumber de de build tren Android.
    PDF scan (khong co text) -> can dua qua OCR."""
    from pypdf import PdfReader
    pages = (p.extract_text() or "" for p in PdfReader(path).pages)
    text = "\n".join(pages).strip()
    if not text:
        raise ValueError("PDF khong co lop text (co the la ban scan) - can OCR")
    return text
