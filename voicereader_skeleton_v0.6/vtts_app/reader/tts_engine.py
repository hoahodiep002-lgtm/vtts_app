"""Engine TTS thuan Python (khong import jnius) -> test duoc tren PC.

Nhiem vu cot loi: speak_and_wait(text) chi tra True khi Android bao onDone
cho DUNG utterance vua gui. Moi truong hop khac KHONG duoc tinh la da doc xong,
de bo dem tu quang cao khong bi cong thua.

Ket qua:
  True   -> onDone dung utterance_id  (duoc dem tu)
  False  -> bi dung chu dong (stop())  (khong dem; resume doc lai doan nay)
  raise TTSError -> loi TTS hoac qua han cho (khong dem)
"""
import itertools
import threading
from typing import Optional, Protocol


class TTSError(Exception):
    pass


class TTSBackend(Protocol):
    def set_listener(self, listener: "TTSEngine") -> None: ...
    def speak(self, text: str, utterance_id: str) -> None: ...
    def stop(self) -> None: ...
    def shutdown(self) -> None: ...


_DONE, _ERROR, _STOPPED = "done", "error", "stopped"


class _Pending:
    def __init__(self, uid: str):
        self.uid = uid
        self.event = threading.Event()
        self.result: Optional[str] = None
        self.error_code: Optional[int] = None


class TTSEngine:
    def __init__(self, backend: TTSBackend, seconds_per_word: float = 1.0,
                 min_timeout: float = 15.0):
        self.backend = backend
        self.seconds_per_word = seconds_per_word
        self.min_timeout = min_timeout
        self._ids = itertools.count(1)
        self._speak_lock = threading.Lock()   # moi lan chi 1 utterance
        self._state_lock = threading.Lock()
        self._pending: Optional[_Pending] = None
        backend.set_listener(self)

    # ---- API cho ReadingSession ----
    def speak_and_wait(self, text: str) -> bool:
        with self._speak_lock:
            pending = _Pending(f"u{next(self._ids)}")
            with self._state_lock:
                self._pending = pending        # dang ky TRUOC khi speak (tranh race onDone den som)
            try:
                self.backend.speak(text, pending.uid)
                timeout = max(self.min_timeout, len(text.split()) * self.seconds_per_word)
                if not pending.event.wait(timeout):
                    self.backend.stop()
                    raise TTSError(f"Qua han cho onDone ({timeout:.0f}s) cho {pending.uid}")
            finally:
                with self._state_lock:
                    self._pending = None
            if pending.result == _DONE:
                return True
            if pending.result == _STOPPED:
                return False
            raise TTSError(f"TTS loi, errorCode={pending.error_code}")

    def stop(self) -> None:
        """Dung ngay. Doan dang doc coi nhu CHUA xong (co the nghe lai khi resume;
        chap nhan lech nhe de khong bao gio dem thua)."""
        self._resolve(None, _STOPPED)
        self.backend.stop()

    def shutdown(self) -> None:
        self.stop()
        self.backend.shutdown()

    # ---- Listener: backend goi tu thread cua Android TTS ----
    def on_start(self, uid: str) -> None:
        pass

    def on_done(self, uid: str) -> None:
        self._resolve(uid, _DONE)

    def on_error(self, uid: str, code: int) -> None:
        self._resolve(uid, _ERROR, code)

    def on_stop(self, uid: str, interrupted: bool) -> None:
        self._resolve(uid, _STOPPED)

    def _resolve(self, uid: Optional[str], result: str, code: Optional[int] = None) -> None:
        with self._state_lock:
            p = self._pending
            if p is None or p.result is not None:
                return                      # khong co ai cho / da chot ket qua
            if uid is not None and uid != p.uid:
                return                      # su kien cua utterance cu -> bo qua
            p.result, p.error_code = result, code
            p.event.set()
