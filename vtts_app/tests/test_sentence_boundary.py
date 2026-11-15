import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reader.ad_trigger import AdTrigger, MemoryStore
from reader.chunker import MAX_CHARS, chunk_text_ex, count_words
from reader.session import ReadingSession


def words(n):
    return " ".join(["từ"] * n)


class RecTTS:
    def __init__(self, events):
        self.events, self.chunks = events, []

    def speak_and_wait(self, text):
        self.chunks.append(text)
        self.events.append(("READ", text))
        return True


class RecAd:
    def __init__(self, events):
        self.events = events

    def play_random_ad(self):
        self.events.append(("AD", None))


class ChunkerFlagTests(unittest.TestCase):
    def test_only_last_piece_of_long_sentence_ends_sentence(self):
        cs = chunk_text_ex(words(2500) + ".")
        self.assertGreater(len(cs), 1)
        self.assertTrue(all(not c.sentence_end for c in cs[:-1]))
        self.assertTrue(cs[-1].sentence_end)
        self.assertTrue(all(len(c.text) <= MAX_CHARS for c in cs))

    def test_normal_text_always_sentence_end(self):
        cs = chunk_text_ex((words(30) + ". ") * 6)
        self.assertTrue(all(c.sentence_end for c in cs))

    def test_no_words_lost_or_added(self):
        text = (words(30) + ". ") + words(2500) + ". " + (words(20) + ".")
        self.assertEqual(sum(count_words(c.text) for c in chunk_text_ex(text)), 2550)


class LongSentenceAdTests(unittest.TestCase):
    def test_ad_waits_for_end_of_long_sentence(self):
        # Cau dai 2500 tu: manh dau (1000 tu) cham nguong NGAY GIUA cau.
        text = words(2500) + ". " + words(50) + "."
        events = []
        ReadingSession(RecTTS(events), RecAd(events), AdTrigger(MemoryStore())).read("d", text)
        self.assertEqual([e[0] for e in events].count("AD"), 1)
        ad_pos = [e[0] for e in events].index("AD")
        read_before = sum(count_words(t) for k, t in events[:ad_pos])
        self.assertEqual(read_before, 2500)       # dung het cau dai roi moi chen

    def test_overshoot_gives_single_ad_not_back_to_back(self):
        text = words(5000) + ". " + (words(50) + ". ") * 5
        events = []
        store = MemoryStore()
        ReadingSession(RecTTS(events), RecAd(events), AdTrigger(store)).read("d", text)
        self.assertEqual([e[0] for e in events].count("AD"), 1)
        self.assertEqual(store.words, (5000 + 250) % 1000)

    def test_overshoot_remainder_kept_in_trigger(self):
        store = MemoryStore()
        t = AdTrigger(store)
        self.assertTrue(t.on_chunk_finished("d", 0, words(2500)))
        t.on_ad_played()
        self.assertEqual(store.words, 500)

    def test_mid_sentence_chunk_counts_words_but_never_fires(self):
        store = MemoryStore()
        t = AdTrigger(store)
        self.assertFalse(t.on_chunk_finished("d", 0, words(1200), sentence_end=False))
        self.assertEqual(store.words, 1200)
        self.assertTrue(t.on_chunk_finished("d", 1, words(10), sentence_end=True))


if __name__ == "__main__":
    unittest.main()
