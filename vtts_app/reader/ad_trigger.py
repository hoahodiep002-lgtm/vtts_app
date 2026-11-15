"""Thuat toan chen quang cao am thanh (tinh THEO TUNG VAN BAN).

Quy tac:
- Van ban < 1000 tu: chen 1 quang cao khi DOC XONG.
- Van ban >= 1000 tu: cu moi 1000 tu chen 1 quang cao, tai dau ket thuc cau
  dau tien sau moc (1000, 2000, ...). Dai/ngan quyet dinh so lan (1 hay nhieu).
  Phan cuoi chua du 1000 tu thi KHONG chen them o cuoi bai.
- Chi dem khi TTS doc XONG (onDone); doc lai cung cau khong bi dem trung.
- Phan du duoc giu lai; 1 cau rat dai vuot nhieu moc -> chi 1 quang cao o cuoi cau.
- Chunk giua cau dai (sentence_end=False) khong kich hoat quang cao.
- Pro: bo qua hoan toan.
- Bo dem reset khi bat dau doc van ban tu dau (start_idx == 0); khi doc tiep
  (resume) bo dem duoc giu.
"""
from typing import Protocol

from core.config import AD_WORD_THRESHOLD
from reader.chunker import count_words


class CounterStore(Protocol):
    words: int


class MemoryStore:
    def __init__(self, words: int = 0):
        self.words = words


class AdTrigger:
    def __init__(self, store: CounterStore, is_pro: bool = False,
                 threshold: int = AD_WORD_THRESHOLD):
        self.store = store
        self.is_pro = is_pro
        self.threshold = threshold
        self._counted: set[tuple[str, int]] = set()

    def reset(self) -> None:
        """Bat dau mot van ban moi: dem lai tu 0."""
        self.store.words = 0
        self._counted.clear()

    def should_play_end_ad(self, total_words: int) -> bool:
        """Van ban ngan (< dinh muc): chen 1 quang cao khi doc xong."""
        return (not self.is_pro) and 0 < total_words < self.threshold

    def words_until_ad(self) -> float:
        """So tu con thieu de cham dinh muc (<=0: da du, chen o dau cau ke tiep). Pro: vo han."""
        return float("inf") if self.is_pro else self.threshold - self.store.words

    def on_chunk_finished(self, doc_id: str, idx: int, text: str,
                          sentence_end: bool = True) -> bool:
        """True = can phat quang cao truoc doan ke tiep.
        Tu luon duoc dem. Nhung chunk nam GIUA mot cau dai (sentence_end=False)
        khong duoc kich hoat quang cao; bo dem giu nguyen nen se kich hoat o
        chunk cuoi cua cau."""
        if self.is_pro or (doc_id, idx) in self._counted:
            return False
        self._counted.add((doc_id, idx))
        self.store.words += count_words(text)
        return sentence_end and self.store.words >= self.threshold

    def on_ad_played(self) -> None:
        # Giu phan du nhung chi tinh 1 quang cao moi lan kich hoat:
        # cau rat dai lam bo dem vuot nhieu moc -> khong phat quang cao lien tiep.
        self.store.words %= self.threshold
