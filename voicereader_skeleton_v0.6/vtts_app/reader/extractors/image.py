"""OCR anh. pytesseract KHONG chay tren Android -> dung ML Kit qua pyjnius.
Tren PC co the cam backend khac de test."""
_backend = None


def set_backend(fn) -> None:
    global _backend
    _backend = fn


def extract(path: str) -> str:
    if _backend is None:
        raise NotImplementedError("Chua cam OCR backend (ML Kit tren Android)")
    return _backend(path)
