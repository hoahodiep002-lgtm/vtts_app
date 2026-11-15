def extract(path: str) -> str:
    with open(path, "rb") as f:
        raw = f.read()
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        from charset_normalizer import from_bytes
        best = from_bytes(raw).best()
        return str(best) if best else raw.decode("utf-8", errors="replace")
