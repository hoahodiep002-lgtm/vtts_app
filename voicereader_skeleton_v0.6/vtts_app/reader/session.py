"""Vong lap doc: TTS + chen quang cao. Nhan TTS/AdPlayer qua interface -> test duoc bang fake.

Don vi vi tri = CAU (chi so trong split_units). Moi lan speak gom 1+ cau lien tiep,
nhung luon dung dung tai cau ma tong so tu cham dinh muc.

Quy tac quang cao (xem ad_trigger.py):
  < 1000 tu  : 1 quang cao khi doc xong.
  >= 1000 tu : moi 1000 tu 1 quang cao, tai dau ket thuc cau dau tien sau moc.
"""
from core.config import CHUNK_MAX_WORDS
from reader.ad_player import AdResult
from reader.ad_trigger import AdTrigger
from reader.chunker import count_words, plan_batch, split_units


class ReadingSession:
    def __init__(self, tts, ad_player, trigger: AdTrigger, max_words: int = CHUNK_MAX_WORDS):
        self.tts = tts
        self.ad_player = ad_player
        self.trigger = trigger
        self.max_words = max_words

    def read(self, doc_id: str, text: str, start_idx: int = 0) -> int:
        """Tra ve chi so cau ke tiep can doc (de resume).
        = so cau neu da doc het; = i neu bi ngat o lan doc bat dau tai cau i (CHUA duoc dem)."""
        units = split_units(text)
        total_words = sum(count_words(u.text) for u in units)
        if start_idx == 0:
            self.trigger.reset()                           # van ban moi / doc lai tu dau
        i = start_idx
        while i < len(units):
            j = plan_batch(units, i, self.trigger.words_until_ad(), self.max_words)
            if not self.tts.speak_and_wait(" ".join(u.text for u in units[i:j])):
                return i                                   # bi dung chu dong
            fire = False
            for k in range(i, j):                          # dem tung cau (chong dem trung theo cau)
                fire |= self.trigger.on_chunk_finished(
                    doc_id, k, units[k].text, units[k].sentence_end)
            if fire:
                if self.ad_player.play_random_ad() == AdResult.STOPPED:
                    # Nguoi dung dung giua quang cao: KHONG tinh la da phat (bo dem giu nguyen),
                    # doc tiep tu cau ke tiep se phat lai quang cao -> khong tron duoc bang cach dung.
                    return j
                self.trigger.on_ad_played()       # PLAYED hoac SKIPPED (loi/khong co file): het no moc nay
            i = j
        if start_idx < len(units) and self.trigger.should_play_end_ad(total_words):
            self.ad_player.play_random_ad()                # van ban ngan: quang cao khi doc xong
        return len(units)
