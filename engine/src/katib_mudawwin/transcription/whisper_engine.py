from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from faster_whisper import WhisperModel

from katib_mudawwin.config import WhisperConfig


class WhisperEngine:
    """Thin wrapper around a single, lazily-loaded faster-whisper model
    instance. Loading the model is expensive, so callers should create one
    WhisperEngine and reuse it for the whole session."""

    # Our own webrtcvad segmenting is deliberately lenient (see VadConfig)
    # to avoid over-segmenting quiet/compressed Zoom audio mid-sentence,
    # which means it lets some marginal/non-speech frames through. Without
    # these, faster-whisper hallucinates fluent-sounding filler on that
    # marginal audio (e.g. "I hope you enjoyed this video...", repeated
    # "Okay. Okay. Okay.") rather than returning empty -- confirmed against
    # real meeting recordings. vad_filter runs Whisper's own (stricter)
    # Silero VAD to skip non-speech before decoding;
    # condition_on_previous_text=False stops it from looping on its own
    # previously hallucinated text.
    _TRANSCRIBE_KWARGS = {"vad_filter": True, "condition_on_previous_text": False}

    def __init__(self, config: WhisperConfig):
        self.config = config
        self._model: Optional[WhisperModel] = None

    def _ensure_loaded(self) -> WhisperModel:
        if self._model is None:
            self._model = WhisperModel(
                self.config.model_size,
                device=self.config.device,
                compute_type=self.config.compute_type,
            )
        return self._model

    def _language(self) -> Optional[str]:
        return "en" if self.config.model_size.endswith(".en") else None

    def transcribe_array(self, audio: np.ndarray) -> str:
        """Transcribes a mono float32 numpy array in [-1.0, 1.0], sampled at
        the engine's expected rate (16kHz), and returns the joined text.
        Intended to be called once per VAD-segmented utterance or test chunk."""
        model = self._ensure_loaded()
        segments, _info = model.transcribe(
            audio, language=self._language(), **self._TRANSCRIBE_KWARGS
        )
        return " ".join(segment.text.strip() for segment in segments).strip()

    def transcribe_wav_file(self, path: Path) -> str:
        model = self._ensure_loaded()
        segments, _info = model.transcribe(
            str(path), language=self._language(), **self._TRANSCRIBE_KWARGS
        )
        return " ".join(segment.text.strip() for segment in segments).strip()
