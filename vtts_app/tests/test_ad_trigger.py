import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import Database, WordCounterStore
from reader.ad_trigger import AdTrigger, MemoryStore
from reader.chunker import chunk_text, count_words
from reader.session import ReadingSession


def words(n: int) -> str:
    return " ".join(["từ"] * n)


class FakeTTS:
    def __init__(self):
        self.spoken = []

    def speak_and_wait(self, text):
        self.spoken.append(text)
        return True


class FakeAdPlayer:
    def __init__(self, log):
        self.log = log

    def play_random_ad(self):
        self.log.append("AD")


class CountTests(unittest.TestCase):
    def test_vietnamese_words(self):
        self.assertEqual(count_words("Xin chào, tôi là Việt Nam!"), 6)

    def test_chunks_end_on_sentence_boundary(self):
        text = (words(30) + ". ") * 5
        for c in chunk_text(text, max_words=60):
            self.assertTrue(c.endswith("."))
            self.assertLessEqual(count_words(c), 60)


class TriggerTests(unittest.TestCase):
    def test_fires_at_threshold(self):
        t = AdTrigger(MemoryStore())
        self.assertFalse(t.on_chunk_finished("d", 0, words(999)))
        self.assertTrue(t.on_chunk_finished("d", 1, words(1)))

    def test_remainder_is_kept(self):
        store = MemoryStore()
        t = AdTrigger(store)
        self.assertTrue(t.on_chunk_finished("d", 0, words(1040)))
        t.on_ad_played()
        self.assertEqual(store.words, 40)

    def test_pro_never_triggers(self):
        t = AdTrigger(MemoryStore(), is_pro=True)
        self.assertFalse(t.on_chunk_finished("d", 0, words(5000)))

    def test_replay_same_chunk_not_double_counted(self):
        store = MemoryStore()
        t = AdTrigger(store)
        t.on_chunk_finished("d", 0, words(100))
        t.on_chunk_finished("d", 0, words(100))
        self.assertEqual(store.words, 100)

    def test_counter_survives_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "t.db")
            db = Database(path)
            AdTrigger(WordCounterStore(db)).on_chunk_finished("d", 0, words(600))
            db.close()
            db2 = Database(path)
            self.assertEqual(WordCounterStore(db2).words, 600)
            db2.close()


class SessionTests(unittest.TestCase):
    def test_ad_inserted_once_per_1000_words_between_chunks(self):
        # 40 cau x 50 tu = 2000 tu -> moc 1000 va 2000 (moc 2000 trung cau cuoi)
        text = (words(50) + ". ") * 40
        events = []
        tts = FakeTTS()
        orig = tts.speak_and_wait

        def logged(c):
            events.append("READ")
            return orig(c)

        tts.speak_and_wait = logged
        session = ReadingSession(tts, FakeAdPlayer(events), AdTrigger(MemoryStore()))
        session.read("doc", text)
        self.assertEqual(events.count("AD"), 2)
        ad_pos = events.index("AD")
        read_before = sum(count_words(c) for c in tts.spoken[:ad_pos])
        self.assertGreaterEqual(read_before, 1000)
        self.assertLess(read_before, 1000 + 60)   # chen ngay sau doan vuot moc

    def test_short_text_gets_one_ad_at_the_end(self):
        events = []
        session = ReadingSession(FakeTTS(), FakeAdPlayer(events), AdTrigger(MemoryStore()))
        session.read("doc", words(300) + ".")
        self.assertEqual(events, ["AD"])

    def test_pro_reads_without_ads(self):
        events = []
        session = ReadingSession(FakeTTS(), FakeAdPlayer(events),
                                 AdTrigger(MemoryStore(), is_pro=True))
        session.read("doc", (words(50) + ". ") * 60)
        self.assertEqual(events, [])


class InterruptedTTS(FakeTTS):
    """Doan thu `stop_at` bi ngat -> khong xong."""
    def __init__(self, stop_at):
        super().__init__()
        self.stop_at = stop_at

    def speak_and_wait(self, text):
        self.spoken.append(text)
        return len(self.spoken) - 1 != self.stop_at


class InterruptTests(unittest.TestCase):
    def test_interrupted_chunk_not_counted_and_resume_index_returned(self):
        store = MemoryStore()
        text = (words(50) + ". ") * 10
        s = ReadingSession(InterruptedTTS(stop_at=3), FakeAdPlayer([]), AdTrigger(store))
        nxt = s.read("doc", text)
        self.assertEqual(nxt, 3)                 # resume tai doan 3
        self.assertEqual(store.words, 3 * 50)    # chi 3 doan xong duoc dem

    def test_resume_does_not_lose_or_double_count(self):
        store = MemoryStore()
        text = (words(50) + ". ") * 10
        trig = AdTrigger(store)
        nxt = ReadingSession(InterruptedTTS(3), FakeAdPlayer([]), trig).read("doc", text)
        ReadingSession(FakeTTS(), FakeAdPlayer([]), trig).read("doc", text, start_idx=nxt)
        self.assertEqual(store.words, 500)


class LongSentenceTests(unittest.TestCase):
    def test_huge_sentence_without_punctuation_is_split_under_tts_limit(self):
        from reader.chunker import MAX_CHARS
        for c in chunk_text(words(5000)):
            self.assertLessEqual(len(c), MAX_CHARS)


if __name__ == "__main__":
    unittest.main()
