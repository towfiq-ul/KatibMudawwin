from __future__ import annotations

import wave
from pathlib import Path

import numpy as np


class StreamingWavWriter:
    """Incrementally writes mono 16-bit PCM frames to a WAV file as they
    arrive, so a multi-hour raw recording is never held entirely in RAM --
    each frame is written and the file handle left open until close().
    Input frames are float32 samples in [-1.0, 1.0], the same format
    AudioSource.read_chunk() returns."""

    def __init__(self, path: Path, sample_rate: int):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._wf = wave.open(str(path), "wb")
        self._wf.setnchannels(1)
        self._wf.setsampwidth(2)
        self._wf.setframerate(sample_rate)

    def write(self, frame: np.ndarray) -> None:
        if len(frame) == 0:
            return
        clipped = np.clip(frame, -1.0, 1.0)
        pcm16 = (clipped * 32767).astype(np.int16)
        self._wf.writeframes(pcm16.tobytes())

    def close(self) -> int:
        """Closes the file and returns its final size in bytes."""
        self._wf.close()
        return self.path.stat().st_size
