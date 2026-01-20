import os
from typing import Optional, List, Dict, Any

import applications
from programmes import REQUIRED_DOCS_BACHELOR, REQUIRED_DOCS_MASTER
from models_db import con


# =====================================================
# Internal helpers (schema-robust)
# =====================================================
def _table_columns(table_name: str) -> List[str]:
    conn = con()
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    cols = [row[1] for row in cur.fetchall()]
    conn.close()
    return cols


def _pick_col(existing_cols: List[str], candidates: List[str]) -> Optional[str]:
    existing = set(existing_cols)
    for c in candidates:
        if c in existing:
            return c
    return None


def _documents_schema():
    cols = _table_columns("documents")
    id_col = _pick_col(cols, ["id", "doc_id", "document_id"])
    app_col = _pick_col(cols, ["application_id", "app_id"])
    path_col = _pick_col(cols, ["saved_path", "path", "file_path", "filepath"])
    if not id_col or not app_col:
        raise RuntimeError("Cannot detect documents schema columns.")
    return id_col, app_col, path_col


# =====================================================
# Listing
# =====================================================
def list_my_applications(user_id: int) -> List[Dict[str, Any]]:
    rows = applications.list_applications(int(user_id))
    out = []
    for app_id, level, programme, status, _ts in rows:
        out.append({"app_id": app_id, "level": level, "programme": programme, "status": status})
    return out


# =====================================================
# Summary (includes status)
# =====================================================
def application_summary(app_id: int) -> Optional[Dict[str, Any]]:
    row = applications.read_application(int(app_id))
    if not row:
        return None

    level, programme, status = row
    required = REQUIRED_DOCS_BACHELOR if level == "Bachelor" else REQUIRED_DOCS_MASTER

    docs = applications.list_documents(int(app_id))
    uploaded_types = sorted({d[1] for d in docs}) if docs else []
    missing_types = [x for x in required if x not in set(uploaded_types)]

    return {
        "app_id": int(app_id),
        "level": level,
        "programme": programme,
        "status": status,
        "required_types": required,
        "uploaded_types": uploaded_types,
        "missing_types": missing_types,
    }


# =====================================================
# Delete docs (direct SQLite, works even without app helpers)
# =====================================================
def delete_doc_by_id(doc_id: int) -> bool:
    id_col, _app_col, path_col = _documents_schema()

    conn = con()
    cur = conn.cursor()

    file_path = None
    if path_col:
        cur.execute(f"SELECT {path_col} FROM documents WHERE {id_col} = ?", (int(doc_id),))
        row = cur.fetchone()
        if not row:
            conn.close()
            return False
        file_path = row[0]

    cur.execute(f"DELETE FROM documents WHERE {id_col} = ?", (int(doc_id),))
    deleted = cur.rowcount
    conn.commit()
    conn.close()

    if deleted <= 0:
        return False

    if isinstance(file_path, str) and file_path.strip() and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    return True


def delete_all_docs_for_application(app_id: int) -> int:
    id_col, app_col, _path_col = _documents_schema()

    conn = con()
    cur = conn.cursor()
    cur.execute(f"SELECT {id_col} FROM documents WHERE {app_col} = ?", (int(app_id),))
    doc_ids = [r[0] for r in cur.fetchall()]
    conn.close()

    deleted = 0
    for did in doc_ids:
        if delete_doc_by_id(int(did)):
            deleted += 1
    return deleted
