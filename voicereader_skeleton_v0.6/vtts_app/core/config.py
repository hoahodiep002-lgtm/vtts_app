APP_DB_NAME = "voicereader.db"

# --- Quang cao am thanh ---
AD_WORD_THRESHOLD = 1000     # moi 1000 tu da doc xong -> 1 quang cao
AD_MIN_SECONDS = 7
AD_MAX_SECONDS = 10

# --- Chunker ---
CHUNK_MAX_WORDS = 60         # moi doan ~60 tu, ket thuc o ranh gioi cau

PRO_PRODUCT_ID = "pro_remove_ads"
JAVA_PACKAGE = "com.example.voicereader"   # phai khop package.domain + package.name trong buildozer.spec
TTS_LOCALE = ("vi", "VN")
AD_DURATION_TOLERANCE = 0.5   # giay; do dai mp3 doc tu metadata co sai so nho
