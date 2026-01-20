import os
import hashlib
from models_db import con, now

# Put admin emails here (must match user email exactly)
ADMIN_EMAILS = {"alex@gmail.com"}

def _hash_password(password: str, salt_hex: str) -> str:
    """
    Your DB has password_hash + password_salt.
    We'll do sha256(salt + password) where salt is hex string.
    """
    password = password or ""
    s = (salt_hex or "") + password
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def register_user(full_name: str, email: str, password: str) -> int:
    full_name = (full_name or "").strip()
    email = (email or "").strip().lower()
    password = password or ""

    if not full_name or not email or not password:
        raise ValueError("Full name, email, and password are required.")

    c = con()
    cur = c.cursor()

    cur.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cur.fetchone():
        c.close()
        raise ValueError("Email already registered.")

    salt = os.urandom(16).hex()
    pw_hash = _hash_password(password, salt)

    cur.execute(
        """
        INSERT INTO users (created_ts, full_name, email, password_hash, password_salt)
        VALUES (?, ?, ?, ?, ?)
        """,
        (now(), full_name, email, pw_hash, salt),
    )
    c.commit()
    uid = cur.lastrowid
    c.close()
    return int(uid)

def login_user(email: str, password: str) -> int:
    email = (email or "").strip().lower()
    password = password or ""

    c = con()
    cur = c.cursor()
    cur.execute(
        "SELECT id, password_hash, password_salt FROM users WHERE email = ?",
        (email,),
    )
    row = cur.fetchone()
    c.close()

    if not row:
        raise ValueError("Invalid email or password.")

    user_id, stored_hash, stored_salt = row
    calc_hash = _hash_password(password, stored_salt)

    if calc_hash != stored_hash:
        raise ValueError("Invalid email or password.")

    return int(user_id)

def get_user_email(user_id: int) -> str:
    c = con()
    cur = c.cursor()
    cur.execute("SELECT email FROM users WHERE id = ?", (int(user_id),))
    row = cur.fetchone()
    c.close()
    return row[0] if row else ""

def is_admin_user(user_id: int) -> bool:
    email = (get_user_email(user_id) or "").strip().lower()
    return email in {e.lower() for e in ADMIN_EMAILS}
