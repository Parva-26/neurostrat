"""
history_store.py
────────────────
Persistent history storage using SQLite (zero infrastructure required).

Schema
──────
  decisions (
    id           INTEGER  PRIMARY KEY AUTOINCREMENT,
    contact_name TEXT     NOT NULL,
    role         TEXT     NOT NULL,
    context      TEXT,
    channel      TEXT     NOT NULL,
    confidence   INTEGER  NOT NULL,
    raw_channel  TEXT,
    raw_tone     TEXT,
    factors      TEXT,    ← JSON-serialised list
    metadata     TEXT,    ← JSON-serialised _meta dict
    created_at   TEXT     NOT NULL   ← ISO-8601 timestamp
  )

All queries are parameterised — no SQL injection surface.
Thread-safe: each call opens and closes its own connection
(safe for FastAPI's default async thread pool model).
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

# Default DB path — sits next to this file
_DEFAULT_DB = Path(__file__).parent / "neurostrat_history.db"


def _connect(db_path: Path = _DEFAULT_DB) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row      # dict-like rows
    return conn


def init_db(db_path: Path = _DEFAULT_DB) -> None:
    """Create the decisions table if it doesn't exist. Call once at startup."""
    with _connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id           INTEGER  PRIMARY KEY AUTOINCREMENT,
                contact_name TEXT     NOT NULL,
                role         TEXT     NOT NULL,
                context      TEXT     DEFAULT '',
                channel      TEXT     NOT NULL,
                confidence   INTEGER  NOT NULL,
                raw_channel  TEXT,
                raw_tone     TEXT,
                factors      TEXT     DEFAULT '[]',
                metadata     TEXT     DEFAULT '{}',
                created_at   TEXT     NOT NULL
            )
        """)
        conn.commit()


def save_decision(
    contact_name: str,
    role: str,
    context: str,
    response: dict,
    db_path: Path = _DEFAULT_DB,
) -> int:
    """
    Persist one strategy decision. Returns the new row id.

    Parameters
    ----------
    contact_name : str
    role         : str
    context      : str
    response     : dict   The full response dict from build_strategy_response().
    """
    meta = response.get("_meta", {})
    now  = datetime.now().isoformat()

    with _connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO decisions
              (contact_name, role, context, channel, confidence,
               raw_channel, raw_tone, factors, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                contact_name,
                role,
                context,
                response["channel"],
                response["confidence"],
                meta.get("raw_channel", ""),
                meta.get("raw_tone", ""),
                json.dumps(response.get("factors", [])),
                json.dumps(meta),
                now,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_history(
    limit: int = 50,
    offset: int = 0,
    db_path: Path = _DEFAULT_DB,
) -> list[dict]:
    """
    Return recent decisions ordered newest-first.
    Returned dicts match the frontend's HistoryItem interface.
    """
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, contact_name, role, channel, confidence, created_at
            FROM   decisions
            ORDER  BY id DESC
            LIMIT  ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

    items = []
    today = datetime.now().date()

    for row in rows:
        created = datetime.fromisoformat(row["created_at"])
        diff    = (today - created.date()).days

        if diff == 0:
            date_str = f"Today, {created.strftime('%I:%M %p')}"
        elif diff == 1:
            date_str = f"Yesterday, {created.strftime('%I:%M %p')}"
        else:
            date_str = created.strftime("%b %d, %I:%M %p")

        items.append({
            "id":         row["id"],
            "contact":    row["contact_name"],
            "role":       row["role"],
            "channel":    row["channel"],
            "confidence": row["confidence"],
            "date":       date_str,
            "status":     "Sent",
        })

    return items


def get_decision_by_id(
    decision_id: int,
    db_path: Path = _DEFAULT_DB,
) -> Optional[dict]:
    """Return a single full decision record, or None if not found."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM decisions WHERE id = ?", (decision_id,)
        ).fetchone()

    if not row:
        return None

    return {
        "id":           row["id"],
        "contact_name": row["contact_name"],
        "role":         row["role"],
        "context":      row["context"],
        "channel":      row["channel"],
        "confidence":   row["confidence"],
        "raw_channel":  row["raw_channel"],
        "raw_tone":     row["raw_tone"],
        "factors":      json.loads(row["factors"] or "[]"),
        "metadata":     json.loads(row["metadata"] or "{}"),
        "created_at":   row["created_at"],
    }


def get_stats(db_path: Path = _DEFAULT_DB) -> dict:
    """Return aggregate stats for the Profile/Settings pages."""
    with _connect(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        avg_conf = conn.execute(
            "SELECT AVG(confidence) FROM decisions"
        ).fetchone()[0]
        channel_dist = conn.execute(
            "SELECT channel, COUNT(*) as cnt FROM decisions GROUP BY channel ORDER BY cnt DESC"
        ).fetchall()

    return {
        "total_decisions": total,
        "avg_confidence":  round(avg_conf or 0, 1),
        "channel_distribution": {row["channel"]: row["cnt"] for row in channel_dist},
    }
