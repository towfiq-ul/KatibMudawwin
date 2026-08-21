from datetime import datetime
from zoneinfo import ZoneInfo

from katib_mudawwin.session.writer import TranscriptWriter
from katib_mudawwin.summarization.base import Summarizer
from katib_mudawwin.summarize_notes import summarize_date

CST = ZoneInfo("America/Chicago")


class FakeSummarizer(Summarizer):
    def __init__(self):
        self.received = []

    def summarize(self, transcript_text: str) -> str:
        self.received.append(transcript_text)
        return f"SUMMARY[{len(self.received)}]: {transcript_text.strip().splitlines()[-1]}"


def _finalized_note(storage_dir, started_at, last_line):
    writer = TranscriptWriter(storage_dir, started_at)
    writer._fh.write(last_line + "\n")
    writer.close()
    writer.finalize()
    return writer.transcript_path


def test_summarize_date_writes_one_block_per_meeting(tmp_path):
    started_1 = datetime(2026, 8, 20, 9, 0, 0, tzinfo=CST)
    started_2 = datetime(2026, 8, 20, 15, 0, 0, tzinfo=CST)
    _finalized_note(tmp_path, started_1, "First meeting content.")
    _finalized_note(tmp_path, started_2, "Second meeting content.")

    summarizer = FakeSummarizer()
    summary_path = summarize_date(tmp_path, "20260820", summarizer)

    assert summary_path == tmp_path / "notes" / "20260820" / "summary_note_20260820.txt"
    text = summary_path.read_text(encoding="utf-8")
    assert "Meeting at 2026-08-20 09:00:00" in text
    assert "Meeting at 2026-08-20 15:00:00" in text
    assert "SUMMARY[1]" in text
    assert "SUMMARY[2]" in text
    assert len(summarizer.received) == 2


def test_summarize_date_is_idempotent(tmp_path):
    """Re-running for the same date regenerates the file rather than
    duplicating blocks."""
    started_at = datetime(2026, 8, 20, 9, 0, 0, tzinfo=CST)
    _finalized_note(tmp_path, started_at, "Meeting content.")

    summarize_date(tmp_path, "20260820", FakeSummarizer())
    summary_path = summarize_date(tmp_path, "20260820", FakeSummarizer())

    text = summary_path.read_text(encoding="utf-8")
    assert text.count("Meeting at 2026-08-20 09:00:00") == 1
