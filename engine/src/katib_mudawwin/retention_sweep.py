"""On-demand retention sweep for persisted raw audio.

Run `python -m katib_mudawwin.retention_sweep` (or `make retention-sweep`)
to delete raw audio (audio/<meeting-id>/mic.wav + zoom.wav) for meetings
that are either older than `retention.max_age_days`, or -- once those are
gone -- oldest-first until total raw-audio storage no longer exceeds
`retention.max_total_audio_bytes`. Transcripts and summaries are never
touched. Not run automatically, for the same reason summarization and
diarization aren't: keeping meeting-end and `make stop` fast and
side-effect-free (see summarize_notes.py).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from katib_mudawwin.config import load_config
from katib_mudawwin.storage import db


def _delete_audio_files(mic_path: str | None, zoom_path: str | None) -> None:
    parent: Path | None = None
    for raw_path in (mic_path, zoom_path):
        if not raw_path:
            continue
        path = Path(raw_path)
        parent = path.parent
        if path.exists():
            path.unlink()
    if parent is not None:
        try:
            parent.rmdir()  # only succeeds once both files are gone
        except OSError:
            pass


def run_sweep(conn: sqlite3.Connection, max_age_days: int, max_total_bytes: int) -> List[str]:
    """Returns the ids of meetings whose raw audio was deleted."""
    cutoff = datetime.now() - timedelta(days=max_age_days)
    rows = db.list_meetings_with_audio(conn)  # oldest-first
    total_bytes = sum(row["audio_bytes"] for row in rows)

    deleted = []
    for row in rows:
        over_age = datetime.fromisoformat(row["started_at"]) < cutoff
        over_cap = total_bytes > max_total_bytes
        if not (over_age or over_cap):
            # Rows are oldest-first: once one is neither too old nor
            # needed to get under the cap, no younger row is either.
            break
        _delete_audio_files(row["mic_audio_path"], row["zoom_audio_path"])
        db.clear_meeting_audio(conn, row["id"])
        total_bytes -= row["audio_bytes"]
        deleted.append(row["id"])

    return deleted


def main() -> None:
    config = load_config()
    conn = db.connect(db.default_db_path(config.storage_dir))
    deleted = run_sweep(
        conn,
        max_age_days=config.retention.max_age_days,
        max_total_bytes=config.retention.max_total_audio_bytes,
    )
    if deleted:
        print(f"Deleted raw audio for {len(deleted)} meeting(s): {', '.join(deleted)}")
    else:
        print("Nothing to delete.")


if __name__ == "__main__":
    main()
