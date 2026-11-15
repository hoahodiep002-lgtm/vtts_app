# VoiceReader (skeleton)

Android app: nghe nhac offline + chuyen van ban thanh giong doc (PDF/DOCX/TXT/anh), quang cao am thanh moi 1000 tu, goi Pro tat quang cao.

## Chay test tren PC (khong can Kivy/Android)
    python -m unittest discover -s tests -v

## Build Android
    pip install buildozer
    buildozer android debug      # APK de thu
    buildozer android release    # AAB cho Play Store

## Trang thai module
| Module | Trang thai |
|---|---|
| reader/chunker, ad_trigger, session | Xong + co test (v0.5: <1000 tu -> 1 quang cao khi doc xong; >=1000 tu -> moi 1000 tu 1 quang cao tai dau ket thuc cau) |
| core/db | Xong + co test |
| extractors txt | Xong; pdf/docx can lib; image = OCR backend (ML Kit) chua noi |
| reader/tts_engine (logic cho onDone, chong dem thua) | Xong + co test (fake backend) |
| reader/android_tts + java_src/ (TextToSpeech that) | Da viet, CHUA chay tren may Android that |
| reader/ad_player (chon file 7-10s, cho OnCompletion, STOPPED/SKIPPED) | Xong + co test (fake backend) |
| reader/android_ad (MediaPlayer that) | Da viet, CHUA chay tren may Android that; chua xu ly audio focus |
| music/*, billing, translator, service | STUB (can pyjnius, test tren may that) |

## Quang cao: dat file vao assets/ads/ (.mp3/.ogg, 7-10s; file ngoai khoang bi loai, xem AdLibrary.problems)

## Can chot
1. Quang cao am thanh: tu host hay mang quang cao.
2. Dich: offline (ML Kit) hay online.
3. OCR: ML Kit (de xuat) / Tesseract tu build / server.
4. Chua thu build Buildozer that: can thu som voi pypdf, lxml, python-docx.
