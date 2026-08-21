from datetime import datetime
from zoneinfo import ZoneInfo

from katib_mudawwin.models import AudioSource, TranscriptEntry
from katib_mudawwin.session.writer import TranscriptWriter, timestamp_prefix

CST = ZoneInfo("America/Chicago")


def test_working_file_at_storage_root(tmp_path):
    started_at = datetime(2026, 8, 20, 14, 30, 0, tzinfo=CST)
    writer = TranscriptWriter(tmp_path, started_at)
    try:
        assert writer.transcript_path == tmp_path / "note.txt"
        assert writer.summary_path == (
            tmp_path / "notes" / "20260820" / "summary_note_20260820.txt"
        )
        assert timestamp_prefix(started_at) == "20260820_143000"
    finally:
        writer.close()


def test_entries_are_flushed_immediately(tmp_path):
    started_at = datetime(2026, 8, 20, 14, 30, 0, tzinfo=CST)
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


def test_finalize_moves_working_file_into_dated_folder(tmp_path):
    started_at = datetime(2026, 8, 20, 14, 30, 0, tzinfo=CST)
    writer = TranscriptWriter(tmp_path, started_at)
    entry = TranscriptEntry(
        timestamp=datetime(2026, 8, 20, 14, 31, 5),
        source=AudioSource.OTHERS,
        text="Let's get started.",
    )
    writer.write_entry(entry)
    writer.close()

    working_path = tmp_path / "note.txt"
    assert working_path.exists()

    writer.finalize()

    final_path = tmp_path / "notes" / "20260820" / "note_20260820_143000.txt"
    assert not working_path.exists()
    assert writer.transcript_path == final_path
    assert "Let's get started." in final_path.read_text(encoding="utf-8")


def test_new_session_truncates_leftover_working_file(tmp_path):
    """A crash before finalize() leaves note.txt at the storage root; the
    next session must start clean rather than appending onto it."""
    (tmp_path / "note.txt").write_text("leftover from a crashed session\n")

    started_at = datetime(2026, 8, 20, 14, 30, 0, tzinfo=CST)
    writer = TranscriptWriter(tmp_path, started_at)
    try:
        contents = writer.transcript_path.read_text(encoding="utf-8")
        assert "leftover from a crashed session" not in contents
    finally:
        writer.close()


def test_summary_path_is_shared_across_meetings_same_day(tmp_path):
    """summary_path is precomputed per the day, not per meeting -- see
    summarize_notes.py, which is what actually writes to it."""
    first = TranscriptWriter(tmp_path, datetime(2026, 8, 20, 9, 0, 0, tzinfo=CST))
    first.close()
    first.finalize()

    second = TranscriptWriter(tmp_path, datetime(2026, 8, 20, 15, 0, 0, tzinfo=CST))
    second.close()
    second.finalize()

    assert first.summary_path == second.summary_path
    assert first.summary_path == tmp_path / "notes" / "20260820" / "summary_note_20260820.txt"
