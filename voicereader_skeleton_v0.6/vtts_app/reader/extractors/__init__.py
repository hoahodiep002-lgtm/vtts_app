from pathlib import Path

from reader.extractors import docx, image, pdf, txt

_BY_EXT = {
    ".txt": txt.extract,
    ".pdf": pdf.extract,
    ".docx": docx.extract,
    ".png": image.extract, ".jpg": image.extract, ".jpeg": image.extract,
}


def extract_text(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext not in _BY_EXT:
        raise ValueError(f"Dinh dang chua ho tro: {ext}")
    return _BY_EXT[ext](path)
