import os
import random
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reader.ad_player import AdFile, AdLibrary, AdPlayer, AdResult
from reader.ad_trigger import AdTrigger, MemoryStore
from reader.session import ReadingSession
from tests.test_ad_rules import Rec, doc


class FakeBackend:
    """Mo phong MediaPlayer: callback den tu THREAD KHAC."""
    def __init__(self, durations, mode="complete", delay=0.03):
        self.durations, self.mode, self.delay = durations, mode, delay
        self.listener = None
        self.played, self.stops = [], 0

    def set_listener(self, l):
        self.listener = l

    def duration(self, path):
        return self.durations.get(Path(path).name)

    def play(self, path, token):
        if self.mode == "raise":
            raise IOError("khong mo duoc file")
        self.played.append(Path(path).name)
        threading.Thread(target=self._fire, args=(token,), daemon=True).start()

    def _fire(self, token):
        if self.mode == "instant":
            self.listener.on_complete(token)
            return
        time.sleep(self.delay)
        if self.mode == "complete":
            self.listener.on_complete(token)
        elif self.mode == "stale_then_complete":
            self.listener.on_complete(token - 1000)          # token cu, phai bi bo qua
            time.sleep(self.delay)
            self.listener.on_complete(token)
        elif self.mode == "error":
            self.listener.on_error(token, 1, -1004)
        # "silent": khong goi gi

    def stop(self):
        self.stops += 1


_TMPS = []


def tearDownModule():
    for t in _TMPS:
        t.cleanup()


def setup(durations, mode="complete", margin=0.2, seed=1):
    tmp = tempfile.TemporaryDirectory()
    _TMPS.append(tmp)                       # giu tham chieu, don o tearDownModule
    for name in durations:
        Path(tmp.name, name).write_bytes(b"x")
    Path(tmp.name, "ghi_chu.txt").write_text("khong phai audio")
    b = FakeBackend(durations, mode)
    lib = AdLibrary(b, dirs=[tmp.name], min_seconds=7, max_seconds=10, tolerance=0.5,
                    rng=random.Random(seed))
    return tmp, b, lib, AdPlayer(b, lib, timeout_margin=margin)


GOOD = {"a.mp3": 7.0, "b.mp3": 8.5, "c.ogg": 10.2}   # 10.2 con trong sai so 0.5


class LibraryTests(unittest.TestCase):
    def test_only_valid_duration_files_are_used(self):
        tmp, b, lib, _ = setup({**GOOD, "ngan.mp3": 3.0, "dai.mp3": 15.0, "hong.mp3": None})
        names = {Path(f.path).name for f in lib.scan()}
        self.assertEqual(names, set(GOOD))
        self.assertEqual(len(lib.problems), 3)          # ngan, dai, hong (txt bi bo qua im lang)

    def test_empty_dir_gives_none(self):
        tmp, b, lib, _ = setup({})
        self.assertIsNone(lib.pick())

    def test_never_repeats_same_ad_back_to_back(self):
        tmp, b, lib, _ = setup(GOOD)
        last = None
        for _ in range(60):
            f = lib.pick(avoid=last)
            self.assertNotEqual(f.path, last)
            last = f.path

    def test_single_ad_may_repeat(self):
        tmp, b, lib, _ = setup({"a.mp3": 8.0})
        f = lib.pick()
        self.assertEqual(lib.pick(avoid=f.path).path, f.path)


class PlayerTests(unittest.TestCase):
    def test_waits_for_completion_then_played(self):
        tmp, b, lib, p = setup(GOOD)
        t0 = time.time()
        self.assertEqual(p.play_random_ad(), AdResult.PLAYED)
        self.assertGreaterEqual(time.time() - t0, 0.03)
        self.assertGreaterEqual(b.stops, 1)               # da giai phong player

    def test_instant_completion_not_lost(self):
        tmp, b, lib, p = setup(GOOD, mode="instant")
        self.assertEqual(p.play_random_ad(), AdResult.PLAYED)

    def test_stale_token_ignored(self):
        tmp, b, lib, p = setup(GOOD, mode="stale_then_complete")
        t0 = time.time()
        self.assertEqual(p.play_random_ad(), AdResult.PLAYED)
        self.assertGreaterEqual(time.time() - t0, 0.06)

    def test_no_ads_returns_skipped_without_touching_backend(self):
        tmp, b, lib, p = setup({})
        self.assertEqual(p.play_random_ad(), AdResult.SKIPPED)
        self.assertEqual(b.played, [])

    def test_onError_skips_and_marks_file_bad(self):
        tmp, b, lib, p = setup({"a.mp3": 8.0}, mode="error")
        self.assertEqual(p.play_random_ad(), AdResult.SKIPPED)
        self.assertEqual(p.play_random_ad(), AdResult.SKIPPED)
        self.assertEqual(len(b.played), 1)                # lan 2 khong thu lai file hong

    def test_play_exception_skips_and_marks_bad(self):
        tmp, b, lib, p = setup({"a.mp3": 8.0}, mode="raise")
        self.assertEqual(p.play_random_ad(), AdResult.SKIPPED)
        self.assertIsNone(lib.pick())

    def test_timeout_skips_instead_of_hanging(self):
        tmp, b, lib, p = setup({"a.mp3": 8.0}, mode="silent", margin=0.1)
        lib.scan()
        lib.files = [AdFile(lib.files[0].path, 0.05)]      # gia lap quang cao 0.05s ma khong bao xong
        t0 = time.time()
        self.assertEqual(p.play_random_ad(), AdResult.SKIPPED)
        self.assertLess(time.time() - t0, 1.0)

    def test_stop_during_ad_returns_stopped(self):
        tmp, b, lib, p = setup(GOOD, mode="silent", margin=5)
        threading.Timer(0.05, p.stop).start()
        self.assertEqual(p.play_random_ad(), AdResult.STOPPED)

    def test_late_completion_of_stopped_ad_does_not_leak_into_next(self):
        tmp, b, lib, p = setup({"a.mp3": 8.0, "b.mp3": 8.0}, mode="silent", margin=5)
        threading.Timer(0.05, p.stop).start()
        self.assertEqual(p.play_random_ad(), AdResult.STOPPED)
        old = 1                                            # token cua lan phat dau
        threading.Timer(0.05, lambda: p.on_complete(old)).start()
        threading.Timer(0.15, p.stop).start()
        self.assertEqual(p.play_random_ad(), AdResult.STOPPED)


class SessionIntegrationTests(unittest.TestCase):
    class StopOnceAd:
        def __init__(self, rec):
            self.rec, self.results = rec, [AdResult.STOPPED]

        def play_random_ad(self):
            r = self.results.pop(0) if self.results else AdResult.PLAYED
            self.rec.log.append("AD:" + r.value)
            return r

    def test_user_stop_during_ad_returns_position_and_ad_is_owed_again(self):
        rec, store = Rec(), MemoryStore()
        trig = AdTrigger(store)
        s = ReadingSession(rec, self.StopOnceAd(rec), trig)
        text = doc(1500)
        nxt = s.read("d", text)
        self.assertEqual(rec.log[-1], "AD:stopped")
        self.assertEqual(nxt, 100)                         # dung ngay sau cau 100 (1000 tu)
        self.assertEqual(store.words, 1000)                # CHUA tinh la da phat quang cao
        s.read("d", text, start_idx=nxt)                   # doc tiep
        self.assertEqual(rec.log.count("AD:played"), 1)    # quang cao duoc phat lai, khong bi mat
        self.assertEqual(rec.log.index("AD:played") - rec.log.index("AD:stopped"), 2)  # sau 1 cau

    def test_skipped_ad_does_not_block_or_repeat(self):
        class SkipAd:
            n = 0
            def play_random_ad(self):
                SkipAd.n += 1
                return AdResult.SKIPPED
        rec = Rec()
        ReadingSession(rec, SkipAd(), AdTrigger(MemoryStore())).read("d", doc(1500))
        self.assertEqual(SkipAd.n, 1)                      # het no moc, khong thu lai moi cau


if __name__ == "__main__":
    unittest.main()
