from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from katib_mudawwin.models import TranscriptEntry

# Note file/folder names are always in CST/CDT regardless of the system's
# local timezone, per product decision -- datetime.astimezone() treats a
# naive `dt` as already being in the system's local time and converts it
# correctly from there, so this works whether `started_at` is naive
# (datetime.now()) or already timezone-aware.
NOTES_TZ = ZoneInfo("America/Chicago")


def timestamp_prefix(dt: datetime) -> str:
    return dt.astimezone(NOTES_TZ).strftime("%Y%m%d_%H%M%S")


class TranscriptWriter:
    """Writes the live transcript to a fixed working file (storage_dir/note.txt)
    while a meeting is in progress -- flushing and fsyncing after every
    write so a crash mid-meeting doesn't lose progress made so far -- then
    finalize() moves it into its permanent storage_dir/notes/<yyyymmdd>/
    note_<timestamp>.txt location once the meeting ends.

    Summarization is not done here -- it's a separate, on-demand step (see
    summarize_notes.py) run via `make summary` rather than automatically on
    stop. summary_path is precomputed so callers (e.g. the status API) can
    show where a summary will land once one is generated, but this class
    never writes to it.

    Note: since the working file has a fixed name, a crash before
    finalize() leaves that meeting's transcript un-relocated at
    storage_dir/note.txt -- the next session's __init__ truncates it rather
    than appending, so it won't corrupt the next meeting's notes, but the
    unfinalized transcript itself is lost."""

    def __init__(self, storage_dir: Path, started_at: datetime):
        storage_dir.mkdir(parents=True, exist_ok=True)
        self.storage_dir = storage_dir
        self.started_at = started_at

        self.transcript_path = storage_dir / "note.txt"

        ts = timestamp_prefix(started_at)
        date_part = ts.split("_")[0]
        self._final_transcript_path = storage_dir / "notes" / date_part / f"note_{ts}.txt"
        self.summary_path = storage_dir / "notes" / date_part / f"summary_note_{date_part}.txt"

        self._fh = open(self.transcript_path, "w", encoding="utf-8")
        header = f"Meeting notes -- started {started_at.isoformat(timespec='seconds')}"
        self._fh.write(header + "\n" + ("=" * len(header)) + "\n\n")
        self._flush()

    def _flush(self) -> None:
        self._fh.flush()
        os.fsync(self._fh.fileno())

    def write_entry(self, entry: TranscriptEntry) -> None:
        self._fh.write(entry.format_line() + "\n")
        self._flush()

    def close(self) -> None:
        if not self._fh.closed:
            self._flush()
            self._fh.close()

    def finalize(self) -> None:
        """Moves the working note.txt into its permanent dated location.
        Call after close(), once the meeting has ended."""
        self._final_transcript_path.parent.mkdir(parents=True, exist_ok=True)
        self.transcript_path.replace(self._final_transcript_path)
        self.transcript_path = self._final_transcript_path
