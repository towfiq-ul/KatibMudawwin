from __future__ import annotations

from typing import Callable, List, Optional

import numpy as np
import webrtcvad

from zoom_notes_engine.config import VadConfig


class VoiceActivityDetector:
    """Thin wrapper around webrtcvad, working in float32 numpy frames.
    Frames must be exactly 10/20/30ms at the configured sample rate -- the
    caller (UtteranceSegmenter) is responsible for framing."""

    def __init__(self, config: VadConfig, sample_rate: int):
        self._vad = webrtcvad.Vad(config.aggressiveness)
        self.sample_rate = sample_rate

    def is_speech(self, frame: np.ndarray) -> bool:
        pcm16 = (np.clip(frame, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()
        return self._vad.is_speech(pcm16, self.sample_rate)


class UtteranceSegmenter:
    """Consumes fixed-size audio frames one at a time and emits a completed
    utterance (concatenated float32 array) when trailing silence exceeds
    `min_silence_ms` or the buffered utterance hits `max_utterance_seconds`.

    Takes a plain `is_speech(frame) -> bool` callable rather than a
    VoiceActivityDetector directly, so the segmentation/flush-timing logic
    can be unit-tested with a scripted sequence of True/False decisions --
    no real audio or webrtcvad needed to verify it's correct (see
    test_vad_segmentation.py)."""

    def __init__(
        self,
        config: VadConfig,
        frame_ms: float,
        is_speech_fn: Callable[[np.ndarray], bool],
    ):
        self.config = config
        self.frame_ms = frame_ms
        self._is_speech_fn = is_speech_fn
        self._buffer: List[np.ndarray] = []
        self._buffered_ms: float = 0.0
        self._silence_run_ms: float = 0.0

    def _flush(self) -> Optional[np.ndarray]:
        if not self._buffer:
            return None
        utterance = np.concatenate(self._buffer)
        self._buffer = []
        self._buffered_ms = 0.0
        self._silence_run_ms = 0.0
        return utterance

    def push_frame(self, frame: np.ndarray) -> Optional[np.ndarray]:
        speech = self._is_speech_fn(frame)
        max_ms = self.config.max_utterance_seconds * 1000

        if speech:
            self._buffer.append(frame)
            self._buffered_ms += self.frame_ms
            self._silence_run_ms = 0.0
            if self._buffered_ms >= max_ms:
                return self._flush()
            return None

        if not self._buffer:
            return None  # silence before any speech started -- nothing to do

        self._buffer.append(frame)  # keep brief pauses inside the utterance
        self._buffered_ms += self.frame_ms
        self._silence_run_ms += self.frame_ms
        if self._silence_run_ms >= self.config.min_silence_ms:
            return self._flush()
        if self._buffered_ms >= max_ms:
            return self._flush()
        return None

    def flush_remaining(self) -> Optional[np.ndarray]:
        """Call at stream end to flush any partially-buffered utterance."""
        return self._flush()
