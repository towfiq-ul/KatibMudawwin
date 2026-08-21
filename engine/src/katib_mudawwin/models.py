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

    def format_line(self) -> str:
        label = "Me" if self.source == AudioSource.ME else "Others"
        return f"[{self.timestamp.strftime('%H:%M:%S')}] {label}: {self.text}"


class SessionStatus(str, Enum):
    IDLE = "idle"
    RECORDING = "recording"


@dataclass
class SessionState:
    status: SessionStatus = SessionStatus.IDLE
    started_at: Optional[datetime] = None
    transcript_path: Optional[str] = None
    summary_path: Optional[str] = None
