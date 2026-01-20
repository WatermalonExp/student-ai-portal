import sqlite3
from datetime import datetime

DB_PATH = "app.db"

def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            user_text TEXT NOT NULL,
            assistant_text TEXT NOT NULL
        )
    """)
    con.commit()
    con.close()

def log_chat(user_text: str, assistant_text: str):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO chat_logs (ts, user_text, assistant_text) VALUES (?, ?, ?)",
        (datetime.utcnow().isoformat(), user_text, assistant_text)
    )
    con.commit()
    con.close()
