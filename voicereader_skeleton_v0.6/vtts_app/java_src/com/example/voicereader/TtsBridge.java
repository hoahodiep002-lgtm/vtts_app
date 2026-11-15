package com.example.voicereader;

import android.speech.tts.UtteranceProgressListener;

/** Cau noi: nhan su kien tu Android TTS va chuyen sang TtsCallback (do Python implement). */
public class TtsBridge extends UtteranceProgressListener {
    private final TtsCallback cb;

    public TtsBridge(TtsCallback cb) { this.cb = cb; }

    @Override public void onStart(String id) { cb.onStart(id); }
    @Override public void onDone(String id)  { cb.onDone(id); }

    @Override @SuppressWarnings("deprecation")
    public void onError(String id) { cb.onError(id, -1); }

    @Override public void onError(String id, int errorCode) { cb.onError(id, errorCode); }
    @Override public void onStop(String id, boolean interrupted) { cb.onStop(id, interrupted); }
}
