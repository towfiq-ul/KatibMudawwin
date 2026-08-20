from datetime import datetime

from zoom_notes_engine.models import AudioSource, TranscriptEntry
from zoom_notes_engine.session.writer import TranscriptWriter, timestamp_prefix


def test_file_naming(tmp_path):
    started_at = datetime(2026, 8, 20, 14, 30, 0)
    writer = TranscriptWriter(tmp_path, started_at)
    try:
        assert writer.transcript_path.name == "2026-08-20_14-30-00_meeting-notes.txt"
        assert writer.summary_path.name == "2026-08-20_14-30-00_summary.txt"
        assert timestamp_prefix(started_at) == "2026-08-20_14-30-00"
    finally:
        writer.close()


def test_entries_are_flushed_immediately(tmp_path):
    started_at = datetime(2026, 8, 20, 14, 30, 0)
    writer = TranscriptWriter(tmp_path, started_at)
    try:
        entry = TranscriptEntry(
            timestamp=datetime(2026, 8, 20, 14, 31, 5),
            source=AudioSource.OTHERS,
            text="Let's get started.",
        )
        writer.write_entry(entry)
        # Read independently (not through the writer) to prove it's on disk,
        # not just buffered in the open file handle.
        contents = writer.transcript_path.read_text(encoding="utf-8")
        assert "[14:31:05] Others: Let's get started." in contents
    finally:
        writer.close()


def test_write_summary(tmp_path):
    started_at = datetime(2026, 8, 20, 14, 30, 0)
    writer = TranscriptWriter(tmp_path, started_at)
    try:
        writer.write_summary("- Discussed the roadmap.\n- Action: Alice to follow up.\n")
        assert "Alice to follow up" in writer.summary_path.read_text(encoding="utf-8")
    finally:
        writer.close()
