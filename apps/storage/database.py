"""SQLite persistence for the email organizer."""
from __future__ import annotations
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = ROOT_DIR / "emails.db"

def get_db_path() -> Path:
    return Path(os.getenv("EMAIL_ORGANIZER_DB", str(DEFAULT_DB_PATH))).expanduser().resolve()

@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db() -> None:
    with connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT, gmail_id TEXT UNIQUE NOT NULL,
                sender TEXT, recipient TEXT, subject TEXT, date TEXT, body TEXT,
                processed INTEGER NOT NULL DEFAULT 0, category TEXT,
                category_confidence REAL, priority TEXT, priority_confidence REAL,
                summary TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)
        """)
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(emails)")}
        migrations = {"processed": "INTEGER NOT NULL DEFAULT 0", "category": "TEXT",
            "category_confidence": "REAL", "priority": "TEXT", "priority_confidence": "REAL",
            "summary": "TEXT", "created_at": "TEXT", "updated_at": "TEXT"}
        for column, definition in migrations.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE emails ADD COLUMN {column} {definition}")
        conn.execute("UPDATE emails SET created_at=COALESCE(created_at,CURRENT_TIMESTAMP)")
        conn.execute("UPDATE emails SET updated_at=COALESCE(updated_at,CURRENT_TIMESTAMP)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_emails_processed ON emails(processed)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_emails_category ON emails(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_emails_priority ON emails(priority)")

def upsert_email(email: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    gmail_id = str(email.get("id") or email.get("gmail_id") or "").strip()
    if not gmail_id:
        raise ValueError("Email is missing an id")
    with connection() as conn:
        exists = conn.execute("SELECT 1 FROM emails WHERE gmail_id=?", (gmail_id,)).fetchone()
        conn.execute("""
            INSERT INTO emails (gmail_id,sender,recipient,subject,date,body) VALUES (?,?,?,?,?,?)
            ON CONFLICT(gmail_id) DO UPDATE SET sender=excluded.sender,
            recipient=excluded.recipient,subject=excluded.subject,date=excluded.date,
            body=excluded.body,updated_at=CURRENT_TIMESTAMP
        """, (gmail_id,email.get("sender"),email.get("recipient"),email.get("subject"),
                email.get("date"),email.get("body")))
        row = conn.execute("SELECT * FROM emails WHERE gmail_id=?", (gmail_id,)).fetchone()
        return dict(row), exists is None

def save_email(email: dict[str, Any]) -> dict[str, Any]:
    return upsert_email(email)[0]

def get_email(email_id: int) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM emails WHERE id=?", (email_id,)).fetchone()
        return dict(row) if row else None

def list_emails(*, offset: int=0, limit: int=50, processed: bool|None=None,
                category: str|None=None, priority: str|None=None,
                search: str|None=None) -> tuple[list[dict[str, Any]], int]:
    clauses: list[str] = []
    params: list[Any] = []
    if processed is not None: clauses.append("processed=?"); params.append(int(processed))
    if category: clauses.append("category=?"); params.append(category)
    if priority: clauses.append("priority=?"); params.append(priority)
    if search:
        clauses.append("(subject LIKE ? OR sender LIKE ? OR body LIKE ?)")
        params.extend([f"%{search}%"]*3)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with connection() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM emails{where}", params).fetchone()[0]
        rows = conn.execute(f"SELECT * FROM emails{where} ORDER BY date DESC,id DESC LIMIT ? OFFSET ?",
                            [*params,limit,offset]).fetchall()
        return [dict(row) for row in rows], total

def get_emails_for_processing(limit: int|None=None, *, reprocess: bool=False) -> list[dict[str, Any]]:
    sql = "SELECT * FROM emails"
    if not reprocess:
        sql += " WHERE processed=0"
    sql += " ORDER BY id"
    params = []
    if limit is not None: sql += " LIMIT ?"; params.append(limit)
    with connection() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]

def get_unprocessed_emails(limit: int|None=None) -> list[dict[str, Any]]:
    return get_emails_for_processing(limit)

def mark_email_processed(gmail_id: str, *, category: str, category_confidence: float,
                         priority: str, priority_confidence: float, summary: str) -> None:
    with connection() as conn:
        cursor = conn.execute("""UPDATE emails SET processed=1,category=?,category_confidence=?,
            priority=?,priority_confidence=?,summary=?,updated_at=CURRENT_TIMESTAMP WHERE gmail_id=?""",
            (category,category_confidence,priority,priority_confidence,summary,gmail_id))
        if cursor.rowcount == 0: raise KeyError(f"Unknown Gmail id: {gmail_id}")

def get_stats() -> dict[str, Any]:
    with connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
        processed = conn.execute("SELECT COUNT(*) FROM emails WHERE processed=1").fetchone()[0]
        categories = {r[0]:r[1] for r in conn.execute("SELECT category,COUNT(*) FROM emails WHERE category IS NOT NULL GROUP BY category")}
        priorities = {r[0]:r[1] for r in conn.execute("SELECT priority,COUNT(*) FROM emails WHERE priority IS NOT NULL GROUP BY priority")}
    return {"total":total,"processed":processed,"unprocessed":total-processed,"categories":categories,"priorities":priorities}

def show_emails_count() -> tuple[int]: return (get_stats()["total"],)
def show_emails() -> list[dict[str, Any]]: return list_emails(limit=10_000)[0]
