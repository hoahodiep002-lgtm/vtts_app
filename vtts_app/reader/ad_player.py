"""Phat quang cao am thanh ngan (7-10s). Logic thuan Python, khong import jnius.

- AdLibrary: quet thu muc, chi nhan file .mp3/.ogg co do dai trong [7, 10]s (+sai so),
  chon ngau nhien, khong lap lai file vua phat (neu co >= 2 file).
- AdPlayer.play_random_ad(): CHAN den khi quang cao phat xong (OnCompletion) roi tra ket qua:
    PLAYED  - phat xong
    SKIPPED - khong co quang cao hop le / loi / qua han cho. Viec doc KHONG bi chan.
    STOPPED - nguoi dung dung giua chung (stop())
- Loi quang cao khong bao gio duoc phep lam treo hay ngat viec doc cua nguoi dung.
"""
import itertools
import logging
import random
import threading
from enum import Enum
from pathlib import Path
from typing import NamedTuple, Optional, Protocol

from core.config import AD_DURATION_TOLERANCE, AD_MAX_SECONDS, AD_MIN_SECONDS

log = logging.getLogger(__name__)

DEFAULT_ADS_DIR = Path(__file__).resolve().parent.parent / "assets" / "ads"
AD_EXTS = (".mp3", ".ogg")


class AdResult(str, Enum):
    PLAYED = "played"
    SKIPPED = "skipped"
    STOPPED = "stopped"


class AdBackend(Protocol):
    def set_listener(self, listener: "AdPlayer") -> None: ...
    def duration(self, path: str) -> Optional[float]: ...       # giay, None neu khong doc duoc
    def play(self, path: str, token: int) -> None: ...          # bat dau phat, tra ve ngay
    def stop(self) -> None: ...                                 # dung + giai phong (idempotent)


class AdFile(NamedTuple):
    path: str
    seconds: float


class AdLibrary:
    def __init__(self, backend: AdBackend, dirs=None,
                 min_seconds: float = AD_MIN_SECONDS, max_seconds: float = AD_MAX_SECONDS,
                 tolerance: float = AD_DURATION_TOLERANCE, rng: Optional[random.Random] = None):
        self.backend = backend
        self.dirs = [Path(d) for d in (dirs or [DEFAULT_ADS_DIR])]
        self.min_seconds, self.max_seconds, self.tolerance = min_seconds, max_seconds, tolerance
        self.rng = rng or random.Random()
        self.files: list[AdFile] = []
        self.problems: list[str] = []       # de hien thi/log: file nao bi loai va vi sao
        self._bad: set[str] = set()
        self._scanned = False

    def scan(self) -> list[AdFile]:
        """Nen goi luc khoi dong app (tranh tre o lan quang cao dau tien)."""
        self.files, self.problems, self._bad = [], [], set()
        for d in self.dirs:
            if not d.is_dir():
                continue
            for p in sorted(d.iterdir()):
                if p.suffix.lower() not in AD_EXTS:
                    continue
                sec = self.backend.duration(str(p))
                if sec is None:
                    self.problems.append(f"{p.name}: khong doc duoc do dai")
                elif not (self.min_seconds - self.tolerance <= sec <= self.max_seconds + self.tolerance):
                    self.problems.append(
                        f"{p.name}: dai {sec:.1f}s, ngoai khoang {self.min_seconds:g}-{self.max_seconds:g}s")
                else:
                    self.files.append(AdFile(str(p), sec))
        self._scanned = True
        for msg in self.problems:
            log.warning("Quang cao bi loai: %s", msg)
        return self.files

    def mark_bad(self, path: str, reason: str = "") -> None:
        self._bad.add(path)
        log.warning("Quang cao loi, bo qua: %s %s", path, reason)

    def pick(self, avoid: Optional[str] = None) -> Optional[AdFile]:
        if not self._scanned:
            self.scan()
        usable = [f for f in self.files if f.path not in self._bad]
        if len(usable) > 1 and avoid is not None:
            usable = [f for f in usable if f.path != avoid]
        return self.rng.choice(usable) if usable else None


class _Pending:
    def __init__(self, token: int):
        self.token = token
        self.event = threading.Event()
        self.result: Optional[AdResult] = None
        self.bad = False


class AdPlayer:
    def __init__(self, backend: AdBackend, library: Optional[AdLibrary] = None,
                 timeout_margin: float = 5.0):
        self.backend = backend
        self.library = library or AdLibrary(backend)
        self.timeout_margin = timeout_margin
        self._tokens = itertools.count(1)
        self._play_lock = threading.Lock()      # moi lan chi 1 quang cao
        self._state_lock = threading.Lock()
        self._pending: Optional[_Pending] = None
        self._last: Optional[str] = None
        backend.set_listener(self)

    # ---- API cho ReadingSession ----
    def play_random_ad(self) -> AdResult:
        with self._play_lock:
            ad = self.library.pick(avoid=self._last)
            if ad is None:
                return AdResult.SKIPPED
            self._last = ad.path
            pending = _Pending(next(self._tokens))
            with self._state_lock:
                self._pending = pending                 # dang ky TRUOC khi phat (tranh race)
            try:
                try:
                    self.backend.play(ad.path, pending.token)
                except Exception as e:                  # file hong / khong mo duoc
                    self.library.mark_bad(ad.path, repr(e))
                    return AdResult.SKIPPED
                if not pending.event.wait(ad.seconds + self.timeout_margin):
                    log.warning("Quang cao khong bao hoan tat (timeout): %s", ad.path)
                    return AdResult.SKIPPED
            finally:
                with self._state_lock:
                    self._pending = None
                self.backend.stop()                     # luon giai phong MediaPlayer
            if pending.bad:
                self.library.mark_bad(ad.path, "onError")
            return pending.result or AdResult.SKIPPED

    def stop(self) -> None:
        """Nguoi dung dung: cat quang cao ngay, play_random_ad() tra STOPPED."""
        self._resolve(None, AdResult.STOPPED)
        self.backend.stop()

    # ---- Listener: backend goi tu thread cua Android ----
    def on_complete(self, token: int) -> None:
        self._resolve(token, AdResult.PLAYED)

    def on_error(self, token: int, what: int = 0, extra: int = 0) -> None:
        log.warning("MediaPlayer onError what=%s extra=%s", what, extra)
        self._resolve(token, AdResult.SKIPPED, bad=True)

    def _resolve(self, token: Optional[int], result: AdResult, bad: bool = False) -> None:
        with self._state_lock:
            p = self._pending
            if p is None or p.result is not None:
                return
            if token is not None and token != p.token:
                return                                  # su kien cua lan phat cu -> bo qua
            p.result, p.bad = result, bad
            p.event.set()
