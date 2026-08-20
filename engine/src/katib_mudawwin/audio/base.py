from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class AudioSource(ABC):
    """One mono audio stream at a fixed sample rate. Concrete
    implementations either capture real audio (mic, Zoom loopback) or
    replay a fixture file for offline testing -- callers (VAD, Whisper)
    don't need to know which."""

    sample_rate: int

    @abstractmethod
    def start(self) -> None:
        """Begin producing audio. Call once before read_chunk()."""
        raise NotImplementedError

    @abstractmethod
    def read_chunk(self, num_frames: int) -> np.ndarray:
        """Returns up to `num_frames` mono float32 samples in [-1.0, 1.0].
        May return fewer frames than requested (e.g. buffer not yet full,
        or the source is exhausted)."""
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """Stop producing audio and release any underlying resources."""
        raise NotImplementedError
