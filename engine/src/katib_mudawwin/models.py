from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class AudioSource(str, Enum):
    ME = "me"
    OTHERS = "others"


@dataclass
class TranscriptEntry:
    timestamp: datetime
    source: AudioSource
    text: str
    # Whisper-detected language this utterance was originally spoken in
    # (ISO-639-1, e.g. "en", "bn"), None if unknown (e.g. entries predating
    # this field). `text` itself is always English -- WhisperEngine runs
    # Whisper's translate task, so non-English speech is already translated
    # by the time it reaches here. This field just records what the
    # original language was.
    language: Optional[str] = None

    def format_line(self) -> str:
        label = "Me" if self.source == AudioSource.ME else "Others"
        # Only flag non-English originals -- English is the common case and
        # tagging every line would just be noise.
        lang = f" (translated from {self.language})" if self.language and self.language != "en" else ""
        return f"[{self.timestamp.strftime('%H:%M:%S')}] {label}{lang}: {self.text}"


class SessionStatus(str, Enum):
    IDLE = "idle"
    RECORDING = "recording"


@dataclass
class SessionState:
    status: SessionStatus = SessionStatus.IDLE
    started_at: Optional[datetime] = None
    transcript_path: Optional[str] = None
    summary_path: Optional[str] = None
