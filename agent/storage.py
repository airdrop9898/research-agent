"""Persistent session storage for multi-turn research refinement."""
import json
import sqlite3
import time
from pathlib import Path
from typing import Optional, List, Dict
from .config import OUTPUT_DIR


DB_PATH = OUTPUT_DIR / "sessions.db"


def init_db():
    """Create sessions table if not exists."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            goal TEXT NOT NULL,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            data TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            turn_idx INTEGER NOT NULL,
            user_input TEXT NOT NULL,
            findings TEXT NOT NULL,
            report_path TEXT,
            created_at REAL NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    conn.commit()
    conn.close()


def save_session(session_id: str, goal: str, data: Dict):
    """Insert or update session."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    now = time.time()
    cur = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
    if cur.fetchone():
        conn.execute(
            "UPDATE sessions SET data = ?, updated_at = ? WHERE id = ?",
            (json.dumps(data, default=str), now, session_id),
        )
    else:
        conn.execute(
            "INSERT INTO sessions (id, goal, created_at, updated_at, data) VALUES (?, ?, ?, ?, ?)",
            (session_id, goal, now, now, json.dumps(data, default=str)),
        )
    conn.commit()
    conn.close()


def get_session(session_id: str) -> Optional[Dict]:
    """Load session by id."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT goal, created_at, updated_at, data FROM sessions WHERE id = ?",
        (session_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": session_id,
        "goal": row[0],
        "created_at": row[1],
        "updated_at": row[2],
        "data": json.loads(row[3]),
    }


def add_turn(session_id: str, user_input: str, findings: List[Dict], report_path: str = None):
    """Add a refinement turn to session."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT COALESCE(MAX(turn_idx), -1) + 1 FROM turns WHERE session_id = ?",
        (session_id,),
    )
    next_idx = cur.fetchone()[0]
    conn.execute(
        "INSERT INTO turns (session_id, turn_idx, user_input, findings, report_path, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, next_idx, user_input, json.dumps(findings, default=str), report_path, time.time()),
    )
    conn.commit()
    conn.close()
    return next_idx


def get_turns(session_id: str) -> List[Dict]:
    """Get all turns for a session, oldest first."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT turn_idx, user_input, findings, report_path, created_at FROM turns WHERE session_id = ? ORDER BY turn_idx ASC",
        (session_id,),
    )
    turns = []
    for row in cur.fetchall():
        turns.append({
            "turn_idx": row[0],
            "user_input": row[1],
            "findings": json.loads(row[2]),
            "report_path": row[3],
            "created_at": row[4],
        })
    conn.close()
    return turns


def list_sessions(limit: int = 20) -> List[Dict]:
    """List recent sessions."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT id, goal, created_at, updated_at FROM sessions ORDER BY updated_at DESC LIMIT ?",
        (limit,),
    )
    sessions = [{"id": r[0], "goal": r[1], "created_at": r[2], "updated_at": r[3]} for r in cur.fetchall()]
    conn.close()
    return sessions


def new_session_id() -> str:
    """Generate short session id."""
    import secrets
    return secrets.token_hex(4)
