"""Bang quy tac da duoc Sep duyet. Moi dong = 1 test; thu voi nhieu do dai cau."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reader.ad_trigger import AdTrigger, MemoryStore
from tests.test_ad_rules import Rec, doc, session

# (tong so tu, vi tri quang cao (so tu da doc), cuoi bai la quang cao?)
SPEC = [
    (300,  [300],         True,  "duoi 1000 tu: 1 quang cao khi doc xong"),
    (1000, [1000],        True,  "dung 1000 tu: 1 quang cao o cuoi cau cuoi"),
    (1500, [1000],        False, "1500 tu: 1 quang cao sau moc 1000, 500 tu cuoi khong co quang cao"),
    (2000, [1000, 2000],  True,  "dung 2000 tu: 2 quang cao, lan 2 o cuoi cau cuoi"),
    (2500, [1000, 2000],  False, "2500 tu: 2 quang cao, khong them quang cao cuoi bai"),
]


class SpecTableTests(unittest.TestCase):
    def test_table(self):
        for per in (5, 10, 25, 50):               # do dai cau khac nhau; moc 1000 luon roi dung cuoi cau
            for total, ads, ends_with_ad, label in SPEC:
                with self.subTest(label=label, words_per_sentence=per):
                    r = Rec()
                    session(r, AdTrigger(MemoryStore())).read("d", doc(total, per))
                    self.assertEqual(r.ads, ads)
                    self.assertEqual(r.log[-1] == "AD", ends_with_ad)

    def test_pro_never_gets_ads(self):
        for total, *_ in SPEC:
            with self.subTest(total=total):
                r = Rec()
                session(r, AdTrigger(MemoryStore(), is_pro=True)).read("d", doc(total, 25))
                self.assertEqual(r.ads, [])


if __name__ == "__main__":
    unittest.main()
