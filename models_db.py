import sqlite3
from datetime import datetime

DB_PATH = "app.db"

def con():
    return sqlite3.connect(DB_PATH)

def now():
    return datetime.utcnow().isoformat()

def init_db_all():
    c = con()
    cur = c.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_ts TEXT NOT NULL,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        password_salt TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS application_decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL,
        admin_user_id INTEGER,
        created_ts TEXT NOT NULL,
        new_status TEXT NOT NULL,
        note TEXT,
        FOREIGN KEY(application_id) REFERENCES applications(id),
        FOREIGN KEY(admin_user_id) REFERENCES users(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        created_ts TEXT NOT NULL,
        program_level TEXT NOT NULL,
        program_name TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'In Progress',
        UNIQUE(user_id, program_level, program_name),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL,
        uploaded_ts TEXT NOT NULL,
        doc_type TEXT NOT NULL,
        original_filename TEXT NOT NULL,
        saved_path TEXT NOT NULL,
        FOREIGN KEY(application_id) REFERENCES applications(id)
    )
    """)

    c.commit()
    c.close()
