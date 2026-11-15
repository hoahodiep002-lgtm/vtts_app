import re
from typing import NamedTuple

from core.config import CHUNK_MAX_WORDS

WORD_RE = re.compile(r"\w+", re.UNICODE)       # tieng Viet tach bang khoang trang
SENT_RE = re.compile(r"(?<=[.!?…])\s+|\n+")


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text))


MAX_CHARS = 3000   # Android TextToSpeech.getMaxSpeechInputLength() thuong = 4000


def _split_long(sentence: str, max_chars: int = MAX_CHARS) -> list[str]:
    """Cau khong dau cau + rat dai -> cat theo tu de khong vuot gioi han TTS."""
    if len(sentence) <= max_chars:
        return [sentence]
    parts, buf, size = [], [], 0
    for w in sentence.split():
        if buf and size + len(w) + 1 > max_chars:
            parts.append(" ".join(buf)); buf, size = [], 0
        buf.append(w); size += len(w) + 1
    if buf:
        parts.append(" ".join(buf))
    return parts


class Chunk(NamedTuple):
    text: str
    sentence_end: bool      # True = chunk nay ket thuc o ranh gioi cau (an toan de chen quang cao)


def split_units(text: str) -> list[Chunk]:
    """Tach thanh don vi nho nhat: moi cau 1 don vi (sentence_end=True).
    Cau qua dai bi cat: cac manh dau sentence_end=False, manh cuoi True."""
    units: list[Chunk] = []
    for sentence in filter(None, (s.strip() for s in SENT_RE.split(text))):
        pieces = _split_long(sentence)
        units += [Chunk(p, False) for p in pieces[:-1]]
        units.append(Chunk(pieces[-1], True))
    return units


def plan_batch(units: list[Chunk], start: int, need: float = float("inf"),
               max_words: int = CHUNK_MAX_WORDS) -> int:
    """Chon cac don vi doc lien tiep trong 1 lan speak, tra ve chi so ket thuc (loai tru).

    - Gom cac cau tron ven toi da ~max_words tu (cho giong doc muot).
    - DUNG ngay sau cau co dau ket thuc ma so tu tich luy da dat `need`
      (need = so tu con thieu de cham dinh muc quang cao). Nho vay quang cao
      duoc chen dung o dau cham dau tien sau tu thu 1000.
    - Manh giua cau dai (sentence_end=False) luon doc rieng, khong gom them.
    """
    j, n = start, 0
    while j < len(units):
        u = units[j]
        w = count_words(u.text)
        if j > start and (not u.sentence_end or n + w > max_words):
            break
        n += w
        j += 1
        if not u.sentence_end or n >= need:
            break
    return j


def chunk_text_ex(text: str, max_words: int = CHUNK_MAX_WORDS) -> list[Chunk]:
    units, out, i = split_units(text), [], 0
    while i < len(units):
        j = plan_batch(units, i, max_words=max_words)
        out.append(Chunk(" ".join(u.text for u in units[i:j]), units[j - 1].sentence_end))
        i = j
    return out


def chunk_text(text: str, max_words: int = CHUNK_MAX_WORDS) -> list[str]:
    return [c.text for c in chunk_text_ex(text, max_words)]
