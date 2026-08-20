from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from zoom_notes_engine.models import TranscriptEntry


def timestamp_prefix(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d_%H-%M-%S")


class TranscriptWriter:
    """Appends transcript entries to a per-meeting txt file, flushing and
    fsyncing after every write so a crash mid-meeting doesn't lose progress
    made so far. The summary file is written once, at the end, separately."""

    def __init__(self, storage_dir: Path, started_at: datetime):
        storage_dir.mkdir(parents=True, exist_ok=True)
        self.started_at = started_at
        prefix = timestamp_prefix(started_at)
        self.transcript_path = storage_dir / f"{prefix}_meeting-notes.txt"
        self.summary_path = storage_dir / f"{prefix}_summary.txt"

        self._fh = open(self.transcript_path, "a", encoding="utf-8")
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

    def read_transcript_text(self) -> str:
        return self.transcript_path.read_text(encoding="utf-8")

    def write_summary(self, summary_text: str) -> None:
        self.summary_path.write_text(summary_text, encoding="utf-8")
