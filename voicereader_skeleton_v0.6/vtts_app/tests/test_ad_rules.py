import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reader.ad_trigger import AdTrigger, MemoryStore
from reader.chunker import count_words
from reader.session import ReadingSession


def sentence(n):
    return " ".join(["từ"] * n) + "."


def doc(total, per=10):
    return " ".join([sentence(per)] * (total // per))


class Rec:
    """TTS + AdPlayer gia. stop_on_call: bi dung o lan speak thu N (0-based), chi 1 lan."""
    def __init__(self, stop_on_call=None):
        self.words_read, self.calls = 0, 0
        self.ads, self.log = [], []
        self.stop_on_call = stop_on_call

    def speak_and_wait(self, text):
        i, self.calls = self.calls, self.calls + 1
        if self.stop_on_call == i:
            self.stop_on_call = None
            return False
        self.words_read += count_words(text)
        self.log.append("READ")
        return True

    def play_random_ad(self):
        self.ads.append(self.words_read)
        self.log.append("AD")


def session(rec, trig):
    return ReadingSession(rec, rec, trig)


class ShortTextTests(unittest.TestCase):
    def test_under_1000_words_ad_at_end(self):
        r = Rec()
        session(r, AdTrigger(MemoryStore())).read("d", doc(300))
        self.assertEqual(r.ads, [300])
        self.assertEqual(r.log[-1], "AD")

    def test_999_words_ad_at_end(self):
        r = Rec()
        session(r, AdTrigger(MemoryStore())).read("d", doc(990) + " " + sentence(9))
        self.assertEqual(r.ads, [999])

    def test_empty_text_no_ad(self):
        r = Rec()
        session(r, AdTrigger(MemoryStore())).read("d", "   ")
        self.assertEqual(r.ads, [])

    def test_stopped_before_end_no_ad(self):
        r = Rec(stop_on_call=2)
        nxt = session(r, AdTrigger(MemoryStore())).read("d", doc(300))
        self.assertEqual(r.ads, [])
        self.assertLess(nxt, 30)

    def test_pro_no_ad(self):
        r = Rec()
        session(r, AdTrigger(MemoryStore(), is_pro=True)).read("d", doc(300))
        self.assertEqual(r.ads, [])

    def test_each_new_document_gets_its_own_end_ad(self):
        r, trig = Rec(), AdTrigger(MemoryStore())
        s = session(r, trig)
        s.read("a", doc(600))
        s.read("b", doc(600))               # khong cong don 600+600
        self.assertEqual(len(r.ads), 2)


class LongTextTests(unittest.TestCase):
    def test_1000_to_1999_words_one_ad_none_at_end(self):
        r = Rec()
        session(r, AdTrigger(MemoryStore())).read("d", doc(1500))
        self.assertEqual(r.ads, [1000])
        self.assertEqual(r.log[-1], "READ")        # phan du 500 tu: khong chen o cuoi

    def test_2500_words_two_ads(self):
        r = Rec()
        session(r, AdTrigger(MemoryStore())).read("d", doc(2500, per=25))
        self.assertEqual(r.ads, [1000, 2000])

    def test_number_of_ads_scales_with_length(self):
        for total, expected in [(900, 1), (1000, 1), (1500, 1), (2000, 2), (3500, 3), (6000, 6)]:
            r = Rec()
            session(r, AdTrigger(MemoryStore())).read("d", doc(total, per=25) if total % 25 == 0 else doc(total))
            self.assertEqual(len(r.ads), expected, total)

    def test_resume_keeps_counter_no_loss_no_double(self):
        r, trig = Rec(stop_on_call=4), AdTrigger(MemoryStore())
        s = session(r, trig)
        text = doc(1500)
        nxt = s.read("d", text)                       # bi ngat o lan doc thu 5
        self.assertGreater(nxt, 0)
        self.assertEqual(r.ads, [])
        s.read("d", text, start_idx=nxt)              # doc tiep, khong reset
        self.assertEqual(len(r.ads), 1)
        self.assertEqual(r.words_read, 1500 - 0)      # moi tu doc dung 1 lan (lan ngat khong tinh)
        self.assertEqual(r.log[-1], "READ")           # khong quang cao o cuoi (phan du < 1000)

    def test_restart_from_beginning_resets_counter(self):
        r, trig = Rec(), AdTrigger(MemoryStore())
        s = session(r, trig)
        s.read("d", doc(1500))
        s.read("d", doc(1500))                        # doc lai tu dau: chu ky quang cao bat dau lai
        self.assertEqual(len(r.ads), 2)


if __name__ == "__main__":
    unittest.main()
