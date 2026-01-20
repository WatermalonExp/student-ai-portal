from typing import List, Tuple, Optional
from models_db import con, now

# =========================
# Applications (CRUD)
# Schema: applications(id, user_id, created_ts, program_level, program_name, status)
# =========================

def create_application(user_id: int, level: str, programme: str) -> int:
    c = con()
    cur = c.cursor()
    cur.execute(
        """
        INSERT INTO applications (user_id, created_ts, program_level, program_name, status)
        VALUES (?, ?, ?, ?, 'In Progress')
        """,
        (int(user_id), now(), level, programme),
    )
    c.commit()
    app_id = cur.lastrowid
    c.close()
    return int(app_id)

def list_applications(user_id: int) -> List[Tuple]:
    """
    Returns: (id, program_level, program_name, status, created_ts)
    """
    c = con()
    cur = c.cursor()
    cur.execute(
        """
        SELECT id, program_level, program_name, status, created_ts
        FROM applications
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (int(user_id),),
    )
    rows = cur.fetchall()
    c.close()
    return rows

def read_application(app_id: int) -> Optional[Tuple[str, str, str]]:
    """
    Returns: (program_level, program_name, status)
    """
    c = con()
    cur = c.cursor()
    cur.execute(
        """
        SELECT program_level, program_name, status
        FROM applications
        WHERE id = ?
        """,
        (int(app_id),),
    )
    row = cur.fetchone()
    c.close()
    return row

def update_application_status(app_id: int, new_status: str) -> None:
    c = con()
    cur = c.cursor()
    cur.execute(
        "UPDATE applications SET status = ? WHERE id = ?",
        (new_status, int(app_id)),
    )
    c.commit()
    c.close()

def submit_application(app_id: int) -> None:
    update_application_status(int(app_id), "Submitted")

# =========================
# Admin
# =========================
def list_all_applications() -> List[Tuple]:
    """
    Returns: (id, user_id, program_level, program_name, status, created_ts)
    """
    c = con()
    cur = c.cursor()
    cur.execute(
        """
        SELECT id, user_id, program_level, program_name, status, created_ts
        FROM applications
        ORDER BY id DESC
        """
    )
    rows = cur.fetchall()
    c.close()
    return rows

# =========================
# Documents
# Schema: documents(id, application_id, uploaded_ts, doc_type, original_filename, saved_path)
# =========================

def add_document(app_id: int, doc_type: str, original_filename: str, saved_path: str) -> int:
    c = con()
    cur = c.cursor()
    cur.execute(
        """
        INSERT INTO documents (application_id, uploaded_ts, doc_type, original_filename, saved_path)
        VALUES (?, ?, ?, ?, ?)
        """,
        (int(app_id), now(), doc_type, original_filename, saved_path),
    )
    c.commit()
    doc_id = cur.lastrowid
    c.close()
    return int(doc_id)

def list_documents(app_id: int) -> List[Tuple]:
    """
    Returns: (id, doc_type, original_filename, saved_path, uploaded_ts)
    """
    c = con()
    cur = c.cursor()
    cur.execute(
        """
        SELECT id, doc_type, original_filename, saved_path, uploaded_ts
        FROM documents
        WHERE application_id = ?
        ORDER BY id DESC
        """,
        (int(app_id),),
    )
    rows = cur.fetchall()
    c.close()
    return rows

from typing import Optional
from models_db import con, now

def add_decision_note(application_id: int, admin_user_id: int, new_status: str, note: str):
    c = con()
    cur = c.cursor()
    cur.execute(
        """
        INSERT INTO application_decisions(application_id, admin_user_id, created_ts, new_status, note)
        VALUES (?, ?, ?, ?, ?)
        """,
        (int(application_id), int(admin_user_id), now(), new_status, (note or "").strip() or None),
    )
    c.commit()
    c.close()

def get_latest_decision_note(application_id: int) -> Optional[str]:
    c = con()
    cur = c.cursor()
    cur.execute(
        """
        SELECT note
        FROM application_decisions
        WHERE application_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (int(application_id),),
    )
    row = cur.fetchone()
    c.close()
    if not row:
        return None
    return row[0]

def get_latest_decision_row(application_id: int):
    """
    Returns tuple: (created_ts, new_status, note, admin_user_id) or None
    """
    c = con()
    cur = c.cursor()
    cur.execute(
        """
        SELECT created_ts, new_status, note, admin_user_id
        FROM application_decisions
        WHERE application_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (int(application_id),),
    )
    row = cur.fetchone()
    c.close()
    return row

