"""Knowledge graph: SQLite FTS5-based searchable archive of research findings.

Indexes every finding (question + answer + sources) so future research can
retrieve relevant prior knowledge across sessions.
"""
import json
import sqlite3
import time
from typing import List, Dict, Optional
from .config import OUTPUT_DIR


KG_DB = OUTPUT_DIR / "knowledge.db"


def init_kg():
    """Create FTS5 virtual table for full-text search."""
    conn = sqlite3.connect(KG_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            source_urls TEXT,
            source_titles TEXT,
            quality_avg REAL,
            indexed_at REAL NOT NULL
        )
    """)
    # FTS5 mirror table
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS findings_fts USING fts5(
            question, answer, source_titles,
            content='findings', content_rowid='id',
            tokenize='porter unicode61'
        )
    """)
    # Triggers to keep FTS in sync
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS findings_ai AFTER INSERT ON findings BEGIN
            INSERT INTO findings_fts(rowid, question, answer, source_titles)
            VALUES (new.id, new.question, new.answer, new.source_titles);
        END
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS findings_ad AFTER DELETE ON findings BEGIN
            DELETE FROM findings_fts WHERE rowid = old.id;
        END
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON findings(session_id)")
    conn.commit()
    conn.close()


def index_findings(session_id: str, findings: List[Dict]):
    """Add findings to KG."""
    init_kg()
    if not findings:
        return
    conn = sqlite3.connect(KG_DB)
    now = time.time()
    for f in findings:
        sources = f.get("sources", [])
        urls = [s.get("url", "") for s in sources]
        titles = [s.get("title", "") for s in sources]
        scores = [s.get("quality_score", 0) for s in sources if s.get("quality_score")]
        avg = sum(scores) / len(scores) if scores else 0
        conn.execute(
            """INSERT INTO findings (session_id, question, answer, source_urls, source_titles, quality_avg, indexed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session_id, f.get("question", ""), f.get("answer", ""),
             json.dumps(urls), " | ".join(titles), avg, now),
        )
    conn.commit()
    conn.close()


def search_kg(query: str, limit: int = 10, min_quality: float = 0) -> List[Dict]:
    """Full-text search prior findings."""
    init_kg()
    conn = sqlite3.connect(KG_DB)
    # FTS5 match query — sanitize quotes
    fts_query = query.replace('"', '""')
    try:
        cur = conn.execute(
            """SELECT f.id, f.session_id, f.question, f.answer, f.source_urls, f.source_titles, f.quality_avg, f.indexed_at,
                      bm25(findings_fts) as rank
               FROM findings_fts
               JOIN findings f ON findings_fts.rowid = f.id
               WHERE findings_fts MATCH ?
               AND f.quality_avg >= ?
               ORDER BY rank ASC
               LIMIT ?""",
            (fts_query, min_quality, limit),
        )
        results = []
        for row in cur.fetchall():
            results.append({
                "id": row[0], "session_id": row[1],
                "question": row[2], "answer": row[3],
                "source_urls": json.loads(row[4]) if row[4] else [],
                "source_titles": row[5],
                "quality_avg": row[6], "indexed_at": row[7],
                "rank": row[8],
            })
        return results
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def kg_stats() -> Dict:
    """KG index stats."""
    init_kg()
    conn = sqlite3.connect(KG_DB)
    n = conn.execute("SELECT COUNT(*) FROM findings").fetchone()[0]
    sessions = conn.execute("SELECT COUNT(DISTINCT session_id) FROM findings").fetchone()[0]
    avg_q = conn.execute("SELECT AVG(quality_avg) FROM findings").fetchone()[0] or 0
    conn.close()
    return {
        "total_findings": n,
        "total_sessions": sessions,
        "avg_quality_score": round(avg_q, 1),
        "db_path": str(KG_DB),
    }
