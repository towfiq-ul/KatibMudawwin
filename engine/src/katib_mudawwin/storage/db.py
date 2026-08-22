from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

# One row per completed meeting -- there is no separate "sessions" table
# (see PRD.md #9): a meeting *is* the session, since the recorder has no
# manual multi-session model. Rows are written once, at meeting-end
# (session/recorder.py's _end_session), not incrementally as a meeting
# progresses -- SessionState already tracks in-progress status in memory.
SCHEMA = """
CREATE TABLE IF NOT EXISTS meetings (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    transcript_path TEXT NOT NULL,
    summary_path TEXT NOT NULL,
    mic_audio_path TEXT,
    zoom_audio_path TEXT,
    audio_bytes INTEGER NOT NULL DEFAULT 0
);
"""


def default_db_path(storage_dir: Path) -> Path:
    return storage_dir / "db.sqlite"


def connect(db_path: Path) -> sqlite3.Connection:
    """Opens (creating if needed) the metadata database and ensures the
    schema exists. check_same_thread=False because SessionRecorder is
    driven from multiple threads (the poll loop, the status API, the tray
    icon) -- callers already serialize access through SessionRecorder's
    own lock, so a single shared connection is safe here."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def record_meeting(
    conn: sqlite3.Connection,
    meeting_id: str,
    started_at: str,
    ended_at: str,
    transcript_path: str,
    summary_path: str,
    mic_audio_path: Optional[str],
    zoom_audio_path: Optional[str],
    audio_bytes: int,
) -> None:
    conn.execute(
        """INSERT INTO meetings
           (id, started_at, ended_at, transcript_path, summary_path,
            mic_audio_path, zoom_audio_path, audio_bytes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            meeting_id,
            started_at,
            ended_at,
            transcript_path,
            summary_path,
            mic_audio_path,
            zoom_audio_path,
            audio_bytes,
        ),
    )
    conn.commit()


def list_meetings_with_audio(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Meetings that still have raw audio on disk, oldest-first -- the
    order retention_sweep.py relies on to decide what to delete first."""
    cur = conn.execute(
        "SELECT id, started_at, mic_audio_path, zoom_audio_path, audio_bytes "
        "FROM meetings WHERE audio_bytes > 0 ORDER BY started_at ASC"
    )
    return cur.fetchall()


def clear_meeting_audio(conn: sqlite3.Connection, meeting_id: str) -> None:
    conn.execute(
        """UPDATE meetings SET mic_audio_path = NULL, zoom_audio_path = NULL,
           audio_bytes = 0 WHERE id = ?""",
        (meeting_id,),
    )
    conn.commit()
