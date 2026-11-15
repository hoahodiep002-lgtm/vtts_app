def extract(path: str) -> str:
    from docx import Document
    return "\n".join(p.text for p in Document(path).paragraphs if p.text.strip())
