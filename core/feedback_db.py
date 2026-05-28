"""
core/feedback_db.py
피드백 DB 관리 - db/feedback.db
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta

FEEDBACK_DB_PATH = Path("db/feedback.db")
KST = timezone(timedelta(hours=9))


def get_feedback_conn():
    conn = sqlite3.connect(FEEDBACK_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_feedback_db():
    conn = get_feedback_conn()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        type       TEXT,
        rating     TEXT,
        content    TEXT,
        context    TEXT
    )""")
    conn.commit()
    conn.close()
    print("feedback.db initialized")


def save_feedback(feedback_type: str, rating: str, content: str, context: str = ""):
    conn = get_feedback_conn()
    conn.execute("""
        INSERT INTO feedback (created_at, type, rating, content, context)
        VALUES (?, ?, ?, ?, ?)
    """, (datetime.now(tz=KST).isoformat(), feedback_type, rating, content, context))
    conn.commit()
    conn.close()


def get_recent_bad_feedback(feedback_type: str, limit: int = 5) -> list[dict]:
    if not FEEDBACK_DB_PATH.exists():
        return []
    conn = get_feedback_conn()
    rows = conn.execute("""
        SELECT content, context, created_at FROM feedback
        WHERE type = ? AND rating = 'bad' AND content != ''
        ORDER BY created_at DESC LIMIT ?
    """, (feedback_type, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
