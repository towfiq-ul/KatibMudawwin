from __future__ import annotations

import time
import wave
from pathlib import Path

import numpy as np

from katib_mudawwin.audio.base import AudioSource


class FilePlaybackSource(AudioSource):
    """Test double: streams a mono 16-bit PCM .wav fixture as if it were
    live audio. Stands in for both the mic and Zoom-loopback sources in
    offline tests of the VAD/Whisper/writer pipeline -- no live audio
    device, pactl, or Zoom call needed.

    `realtime=True` paces reads to real wall-clock time (useful for
    exercising timing-sensitive code); `realtime=False` (default) returns
    chunks immediately, for fast tests."""

    def __init__(self, wav_path: Path, sample_rate: int = 16000, realtime: bool = False):
        with wave.open(str(wav_path), "rb") as wf:
            if wf.getframerate() != sample_rate:
                raise ValueError(
                    f"fixture sample rate {wf.getframerate()} != expected {sample_rate}; "
                    "resample the fixture first"
                )
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
                raise ValueError("fixture must be mono 16-bit PCM")
            raw = wf.readframes(wf.getnframes())
        self.sample_rate = sample_rate
        self._samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        self._position = 0
        self._realtime = realtime

    def start(self) -> None:
        self._position = 0

    def read_chunk(self, num_frames: int) -> np.ndarray:
        if self._realtime:
            time.sleep(num_frames / self.sample_rate)
        chunk = self._samples[self._position : self._position + num_frames]
        self._position += num_frames
        return chunk

    def stop(self) -> None:
        self._position = len(self._samples)

    @property
    def exhausted(self) -> bool:
        return self._position >= len(self._samples)
