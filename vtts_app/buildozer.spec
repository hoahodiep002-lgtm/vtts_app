[app]
title = VoiceReader
package.name = voicereader
package.domain = com.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,mp3,ogg,json
source.exclude_dirs = tests, bin, .buildozer, __pycache__
version = 0.1.0

# pdfplumber/pypdfium2 co native, kho build -> dung pypdf (thuan Python).
# pytesseract khong chay duoc tren Android -> OCR qua ML Kit (pyjnius).
requirements = python3,kivy==2.3.0,kivymd,pyjnius,android,pillow,lxml,python-docx,pypdf,charset-normalizer

orientation = portrait
fullscreen = 0

# --- Android ---
# CHU Y: kiem tra lai target API toi thieu cua Google Play truoc khi phat hanh.
android.api = 34
android.minapi = 21
android.ndk = 25b
android.gradle_dependencies = ...
services = playback:...
android.archs = arm64-v8a
android.accept_sdk_license = True
android.release_artifact = aab
android.debug_artifact = apk

android.permissions = INTERNET, READ_MEDIA_AUDIO, READ_MEDIA_IMAGES, READ_EXTERNAL_STORAGE, FOREGROUND_SERVICE, FOREGROUND_SERVICE_MEDIA_PLAYBACK, POST_NOTIFICATIONS, WAKE_LOCK

# ML Kit OCR + Play Billing (can xac nhan phien ban khi build that)
android.gradle_dependencies = com.google.mlkit:text-recognition:16.0.0, com.android.billingclient:billing:7.0.0

# Cau noi Java cho TTS (package phai khop package.domain + package.name)
android.add_src = java_src

# Foreground service de phat nhac / doc khi tat man hinh
services = playback:services/playback_service.py:foreground:sticky

[buildozer]
log_level = 2
warn_on_root = 1
