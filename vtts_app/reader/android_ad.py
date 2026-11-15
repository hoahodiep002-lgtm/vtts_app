"""Backend MediaPlayer qua pyjnius. CHI import tren Android.

Luong: MediaPlayer() -> setAudioAttributes -> setDataSource(path) -> set listeners
       -> prepare() (dong bo, file ngan) -> start() ... OnCompletionListener.onCompletion

Luu y (chua kiem chung tren may that):
- Callback cua MediaPlayer duoc giao tren Looper cua thread tao no; thread Python
  khong co Looper nen se la main looper cua Android. Python chi cho bang Event nen khong deadlock.
- Giu tham chieu listener, neu khong GC se huy va mat callback.
- Chua xu ly audio focus (nhac nen khong tu tam dung/ha am khi quang cao phat).
"""
import threading

from jnius import PythonJavaClass, autoclass, java_method

MediaPlayer = autoclass("android.media.MediaPlayer")
MediaMetadataRetriever = autoclass("android.media.MediaMetadataRetriever")
AudioAttributes = autoclass("android.media.AudioAttributes")
AudioAttributesBuilder = autoclass("android.media.AudioAttributes$Builder")


class _Completion(PythonJavaClass):
    __javainterfaces__ = ["android/media/MediaPlayer$OnCompletionListener"]
    __javacontext__ = "app"

    def __init__(self, cb):
        super().__init__()
        self._cb = cb

    @java_method("(Landroid/media/MediaPlayer;)V")
    def onCompletion(self, mp):
        self._cb()


class _Error(PythonJavaClass):
    __javainterfaces__ = ["android/media/MediaPlayer$OnErrorListener"]
    __javacontext__ = "app"

    def __init__(self, cb):
        super().__init__()
        self._cb = cb

    @java_method("(Landroid/media/MediaPlayer;II)Z")
    def onError(self, mp, what, extra):
        self._cb(what, extra)
        return True          # da xu ly -> Android khong goi them onCompletion


class AndroidAdBackend:
    def __init__(self):
        self._listener = None
        self._mp = None
        self._refs = None
        self._lock = threading.Lock()

    def set_listener(self, listener) -> None:
        self._listener = listener

    def duration(self, path: str):
        r = MediaMetadataRetriever()
        try:
            r.setDataSource(path)
            ms = r.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)
            return int(ms) / 1000.0 if ms else None
        except Exception:
            return None
        finally:
            try:
                r.release()
            except Exception:
                pass

    def play(self, path: str, token: int) -> None:
        self.stop()                                   # giai phong lan truoc (neu con)
        mp = MediaPlayer()
        completion = _Completion(lambda: self._listener.on_complete(token))
        error = _Error(lambda what, extra: self._listener.on_error(token, what, extra))
        try:
            attrs = (AudioAttributesBuilder()
                     .setUsage(AudioAttributes.USAGE_MEDIA)
                     .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                     .build())
            mp.setAudioAttributes(attrs)
            mp.setDataSource(path)
            mp.setOnCompletionListener(completion)
            mp.setOnErrorListener(error)
            mp.prepare()
            mp.start()
        except Exception:
            try:
                mp.release()
            except Exception:
                pass
            raise
        with self._lock:
            self._mp, self._refs = mp, (completion, error)

    def stop(self) -> None:
        with self._lock:
            mp, self._mp, self._refs = self._mp, None, None
        if mp is not None:
            for fn in (mp.stop, mp.release):          # stop() co the nem IllegalStateException
                try:
                    fn()
                except Exception:
                    pass
