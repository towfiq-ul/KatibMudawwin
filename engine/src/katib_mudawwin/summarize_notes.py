"""On-demand summarization CLI.

Run `python -m katib_mudawwin.summarize_notes [yyyymmdd]` (or `make summary
[yyyymmdd]`) to summarize a day's meeting notes. Summarization is no longer
triggered automatically when a meeting stops -- the local summarizer's
first run downloads a ~2.3GB model from Hugging Face, which made `make
stop` block for several minutes. Running it on demand, separately, avoids
that.

Reads every notes/<date>/note_*.txt transcript for the given date (default:
today, in CST -- the same timezone used for note filenames, see
session/writer.py) and (re)writes notes/<date>/summary_note_<date>.txt with
one block per meeting. Re-running for the same date regenerates the whole
file from scratch rather than appending, so repeat runs don't duplicate
blocks.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

from katib_mudawwin.config import load_config
from katib_mudawwin.session.writer import NOTES_TZ
from katib_mudawwin.summarization import Summarizer, get_summarizer

DATE_PATTERN = re.compile(r"^\d{8}$")
NOTE_FILE_PATTERN = re.compile(r"^note_(\d{8})_(\d{6})\.txt$")


def today_cst() -> str:
    return datetime.now().astimezone(NOTES_TZ).strftime("%Y%m%d")


def _meeting_label(note_path: Path) -> str:
    match = NOTE_FILE_PATTERN.match(note_path.name)
    if not match:
        return note_path.name
    date_part, time_part = match.groups()
    return (
        f"{date_part[0:4]}-{date_part[4:6]}-{date_part[6:8]} "
        f"{time_part[0:2]}:{time_part[2:4]}:{time_part[4:6]}"
    )


def summarize_date(storage_dir: Path, date: str, summarizer: Summarizer) -> Path:
    """(Re)writes notes/<date>/summary_note_<date>.txt with one block per
    note_*.txt transcript found for that date, overwriting rather than
    appending so re-running is idempotent."""
    date_dir = storage_dir / "notes" / date
    note_files = sorted(p for p in date_dir.glob("note_*.txt") if NOTE_FILE_PATTERN.match(p.name))
    summary_path = date_dir / f"summary_note_{date}.txt"

    blocks = []
    for note_path in note_files:
        transcript_text = note_path.read_text(encoding="utf-8")
        summary_text = summarizer.summarize(transcript_text)
        header = f"Meeting at {_meeting_label(note_path)}"
        blocks.append(f"{header}\n{'-' * len(header)}\n{summary_text.rstrip()}\n")

    summary_path.write_text("\n".join(blocks), encoding="utf-8")
    return summary_path


def main() -> None:
    date = sys.argv[1] if len(sys.argv) > 1 else today_cst()
    if not DATE_PATTERN.match(date):
        print(f"Invalid date {date!r} -- expected yyyymmdd")
        sys.exit(1)

    config = load_config()
    date_dir = config.storage_dir / "notes" / date
    if not date_dir.exists():
        print(f"No notes found for {date} at {date_dir}")
        sys.exit(1)

    summarizer = get_summarizer(config.summarizer)
    summary_path = summarize_date(config.storage_dir, date, summarizer)
    print(f"Summary written to {summary_path}")


if __name__ == "__main__":
    main()
