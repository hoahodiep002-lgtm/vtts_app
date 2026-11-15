import os
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reader.tts_engine import TTSEngine, TTSError


class FakeBackend:
    """Mo phong Android: callback den tu THREAD KHAC, co the tre / loi / im lang."""
    def __init__(self, mode="done", delay=0.02):
        self.mode, self.delay = mode, delay
        self.listener = None
        self.spoken, self.stopped = [], 0

    def set_listener(self, l):
        self.listener = l

    def speak(self, text, uid):
        self.spoken.append((text, uid))
        threading.Thread(target=self._fire, args=(uid,), daemon=True).start()

    def _fire(self, uid):
        if self.mode == "instant":
            self.listener.on_done(uid)           # onDone den truoc ca khi wait() kip chay
            return
        time.sleep(self.delay)
        if self.mode == "done":
            self.listener.on_start(uid)
            self.listener.on_done(uid)
        elif self.mode == "stale_then_done":
            self.listener.on_done("u-cu-khong-lien-quan")   # phai bi bo qua
            time.sleep(self.delay)
            self.listener.on_done(uid)
        elif self.mode == "error":
            self.listener.on_error(uid, -4)
        # mode == "silent": khong goi gi

    def stop(self):
        self.stopped += 1

    def shutdown(self):
        pass


def engine(mode="done", **kw):
    b = FakeBackend(mode)
    return b, TTSEngine(b, **kw)


class EngineTests(unittest.TestCase):
    def test_returns_true_only_after_onDone(self):
        b, e = engine("done")
        t0 = time.time()
        self.assertTrue(e.speak_and_wait("xin chào các bạn"))
        self.assertGreaterEqual(time.time() - t0, 0.02)   # that su da cho

    def test_onDone_arriving_instantly_is_not_lost(self):
        b, e = engine("instant")
        self.assertTrue(e.speak_and_wait("a b c"))

    def test_stale_utterance_id_is_ignored(self):
        b, e = engine("stale_then_done")
        t0 = time.time()
        self.assertTrue(e.speak_and_wait("a b c"))
        self.assertGreaterEqual(time.time() - t0, 0.04)   # khong bi onDone cu danh lua

    def test_error_raises_and_is_not_done(self):
        b, e = engine("error")
        with self.assertRaises(TTSError):
            e.speak_and_wait("a b c")

    def test_timeout_raises_and_stops_backend(self):
        b, e = engine("silent", min_timeout=0.1, seconds_per_word=0)
        with self.assertRaises(TTSError):
            e.speak_and_wait("a b c")
        self.assertEqual(b.stopped, 1)

    def test_stop_returns_false_not_counted(self):
        b, e = engine("silent", min_timeout=5)
        threading.Timer(0.05, e.stop).start()
        self.assertFalse(e.speak_and_wait("a b c"))

    def test_each_call_uses_new_utterance_id(self):
        b, e = engine("done")
        e.speak_and_wait("a"); e.speak_and_wait("b")
        self.assertNotEqual(b.spoken[0][1], b.spoken[1][1])

    def test_late_onDone_after_stop_does_not_leak_into_next_utterance(self):
        b, e = engine("silent", min_timeout=5)
        threading.Timer(0.05, e.stop).start()
        self.assertFalse(e.speak_and_wait("cu"))
        uid_old = b.spoken[0][1]
        b.mode = "silent"
        threading.Timer(0.05, lambda: e.on_done(uid_old)).start()   # onDone muon cua utterance cu
        threading.Timer(0.15, e.stop).start()
        self.assertFalse(e.speak_and_wait("moi"))                   # van phai bi stop, khong thanh True


if __name__ == "__main__":
    unittest.main()
