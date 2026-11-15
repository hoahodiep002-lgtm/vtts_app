import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reader.ad_trigger import AdTrigger, MemoryStore
from reader.chunker import count_words, plan_batch, split_units
from reader.session import ReadingSession


def sentence(n):
    return " ".join(["từ"] * n) + "."


class Rec:
    """Ghi lai chuoi su kien doc/quang cao; tinh so tu da doc tai moi quang cao."""
    def __init__(self):
        self.read_words = 0
        self.ad_at, self.last_text_before_ad = [], []
        self.last = ""

    def speak_and_wait(self, text):
        self.read_words += count_words(text)
        self.last = text
        return True

    def play_random_ad(self):
        self.ad_at.append(self.read_words)
        self.last_text_before_ad.append(self.last)


def run(text, **kw):
    r = Rec()
    ReadingSession(r, r, AdTrigger(MemoryStore(), **kw)).read("d", text)
    return r


class PrecisionTests(unittest.TestCase):
    def test_ad_at_first_period_after_word_1000(self):
        # cau 7 tu: 142 cau = 994 tu (chua du), cau 143 = 1001 tu -> chen NGAY sau cau 143
        r = run(sentence(7) * 1 + (" " + sentence(7)) * 299)
        self.assertEqual(r.ad_at[0], 1001)

    def test_ad_exactly_at_1000_when_period_falls_on_1000(self):
        r = run(" ".join([sentence(10)] * 150))
        self.assertEqual(r.ad_at, [1000])

    def test_ad_always_right_after_a_period(self):
        r = run(" ".join([sentence(7)] * 300))
        for t in r.last_text_before_ad:
            self.assertTrue(t.rstrip().endswith("."))

    def test_long_text_gets_an_ad_every_1000_words(self):
        # 5000 tu, cau 25 tu: chen o 1000, 2000, 3000, 4000, 5000 (moc 5000 trung cau cuoi)
        r = run(" ".join([sentence(25)] * 200))
        self.assertEqual(r.ad_at, [1000, 2000, 3000, 4000, 5000])

    def test_remainder_carries_so_spacing_stays_1000_words_on_average(self):
        r = run(" ".join([sentence(7)] * 300))        # 2100 tu
        self.assertEqual(r.ad_at, [1001, 2002])        # moc 1000, 2000 moi lam tron len ranh gioi cau

    def test_pro_gets_no_ads(self):
        self.assertEqual(run(" ".join([sentence(25)] * 200), is_pro=True).ad_at, [])

    def test_milestone_on_last_sentence_still_plays_ad(self):
        self.assertEqual(run(" ".join([sentence(10)] * 100)).ad_at, [1000])   # dung 1000 tu, het bai


class PlanBatchTests(unittest.TestCase):
    def test_stops_at_sentence_where_need_reached(self):
        units = split_units(" ".join([sentence(7)] * 50))
        j = plan_batch(units, 0, need=20)       # 7,14,21 -> dung sau cau thu 3
        self.assertEqual(j, 3)

    def test_default_groups_up_to_max_words(self):
        units = split_units(" ".join([sentence(7)] * 50))
        self.assertEqual(plan_batch(units, 0, max_words=60), 8)   # 8*7=56

    def test_trigger_words_until_ad(self):
        st = MemoryStore(300)
        self.assertEqual(AdTrigger(st).words_until_ad(), 700)
        self.assertEqual(AdTrigger(st, is_pro=True).words_until_ad(), float("inf"))


if __name__ == "__main__":
    unittest.main()
