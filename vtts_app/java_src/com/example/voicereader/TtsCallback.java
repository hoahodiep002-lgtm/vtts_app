package com.example.voicereader;

/** Interface thuan de pyjnius implement (UtteranceProgressListener la abstract class nen khong implement truc tiep duoc). */
public interface TtsCallback {
    void onStart(String utteranceId);
    void onDone(String utteranceId);
    void onError(String utteranceId, int errorCode);
    void onStop(String utteranceId, boolean interrupted);
}
