"""Backend Android TextToSpeech qua pyjnius.  CHI import tren Android (can jnius).

Luong hoat dong:
  TextToSpeech(ctx, OnInitListener) --onInit--> setLanguage/setSpeechRate
  setOnUtteranceProgressListener(TtsBridge(callback))     # TtsBridge = Java, xem java_src/
  speak(text, QUEUE_FLUSH, None, utteranceId) --> onStart ... onDone(utteranceId)

Luu y:
- Goi tu thread Python (SDL thread / service), KHONG goi tu UI thread cua Android vi
  constructor cho onInit.
- Phai giu tham chieu cac listener, neu khong GC se huy va callback bi mat.
- Callback den tu thread cua TTS, khong phai thread chinh.
"""
import threading

from jnius import PythonJavaClass, autoclass, java_method

from core.config import JAVA_PACKAGE, TTS_LOCALE
from reader.tts_engine import TTSError

_PKG = JAVA_PACKAGE.replace(".", "/")

TextToSpeech = autoclass("android.speech.tts.TextToSpeech")
Locale = autoclass("java.util.Locale")
TtsBridge = autoclass(f"{JAVA_PACKAGE}.TtsBridge")


class _InitListener(PythonJavaClass):
    __javainterfaces__ = ["android/speech/tts/TextToSpeech$OnInitListener"]
    __javacontext__ = "app"

    def __init__(self, on_init):
        super().__init__()
        self._on_init = on_init

    @java_method("(I)V")
    def onInit(self, status):
        self._on_init(status)


class _Callback(PythonJavaClass):
    __javainterfaces__ = [f"{_PKG}/TtsCallback"]
    __javacontext__ = "app"

    def __init__(self, dispatch):
        super().__init__()
        self._d = dispatch

    @java_method("(Ljava/lang/String;)V")
    def onStart(self, uid):
        self._d("start", uid)

    @java_method("(Ljava/lang/String;)V")
    def onDone(self, uid):
        self._d("done", uid)

    @java_method("(Ljava/lang/String;I)V")
    def onError(self, uid, code):
        self._d("error", uid, code)

    @java_method("(Ljava/lang/String;Z)V")
    def onStop(self, uid, interrupted):
        self._d("stop", uid, interrupted)


def _get_context():
    activity = autoclass("org.kivy.android.PythonActivity").mActivity
    if activity is not None:
        return activity
    return autoclass("org.kivy.android.PythonService").mService   # dang chay trong service


class AndroidTTSBackend:
    def __init__(self, locale=TTS_LOCALE, rate: float = 1.0, init_timeout: float = 10.0):
        self._listener = None
        self._init_done = threading.Event()
        self._init_status = None

        self._init_listener = _InitListener(self._on_init)        # giu tham chieu
        self._tts = TextToSpeech(_get_context(), self._init_listener)
        if not self._init_done.wait(init_timeout):
            raise TTSError("TextToSpeech khong khoi tao duoc (timeout)")
        if self._init_status != TextToSpeech.SUCCESS:
            raise TTSError(f"TextToSpeech init that bai, status={self._init_status}")

        lang = self._tts.setLanguage(Locale(*locale))
        if lang < 0:   # LANG_MISSING_DATA (-1) / LANG_NOT_SUPPORTED (-2)
            raise TTSError(f"Chua co giong doc {locale} tren may (code {lang}); "
                           "huong dan nguoi dung cai du lieu giong noi")
        self._tts.setSpeechRate(float(rate))

        self._callback = _Callback(self._dispatch)                # giu tham chieu
        self._bridge = TtsBridge(self._callback)                  # giu tham chieu
        self._tts.setOnUtteranceProgressListener(self._bridge)

    @staticmethod
    def max_input_length() -> int:
        return int(TextToSpeech.getMaxSpeechInputLength())

    # ---- TTSBackend ----
    def set_listener(self, listener) -> None:
        self._listener = listener

    def speak(self, text: str, utterance_id: str) -> None:
        if len(text) > self.max_input_length():
            raise TTSError("Van ban vuot gioi han TTS; chunker phai cat nho hon")
        rc = self._tts.speak(text, TextToSpeech.QUEUE_FLUSH, None, utterance_id)
        if rc != TextToSpeech.SUCCESS:
            raise TTSError(f"speak() tra ve loi {rc}")

    def stop(self) -> None:
        self._tts.stop()

    def shutdown(self) -> None:
        self._tts.shutdown()

    # ---- noi bo ----
    def _on_init(self, status):
        self._init_status = status
        self._init_done.set()

    def _dispatch(self, kind, uid, arg=None):
        l = self._listener
        if l is None:
            return
        if kind == "start":
            l.on_start(uid)
        elif kind == "done":
            l.on_done(uid)
        elif kind == "error":
            l.on_error(uid, arg)
        elif kind == "stop":
            l.on_stop(uid, bool(arg))
