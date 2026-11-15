"""SQLite don gian. Khong phu thuoc Kivy/jnius -> test duoc tren PC."""
import sqlite3


class Database:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT)"
        )
        self.conn.commit()

    def get(self, key: str, default: str = "") -> str:
        row = self.conn.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def set(self, key: str, value) -> None:
        self.conn.execute(
            "INSERT INTO kv(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )
        self.conn.commit()

    def close(self):
        self.conn.close()


class WordCounterStore:
    """Bo dem tu ben vung: tat/mo app khong bi reset."""
    KEY = "ad_word_counter"

    def __init__(self, db: Database):
        self.db = db

    @property
    def words(self) -> int:
        return int(self.db.get(self.KEY, "0"))

    @words.setter
    def words(self, value: int) -> None:
        self.db.set(self.KEY, int(value))
