from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from faster_whisper import WhisperModel

from zoom_notes_engine.config import WhisperConfig


class WhisperEngine:
    """Thin wrapper around a single, lazily-loaded faster-whisper model
    instance. Loading the model is expensive, so callers should create one
    WhisperEngine and reuse it for the whole session."""

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
        segments, _info = model.transcribe(audio, language=self._language())
        return " ".join(segment.text.strip() for segment in segments).strip()

    def transcribe_wav_file(self, path: Path) -> str:
        model = self._ensure_loaded()
        segments, _info = model.transcribe(str(path), language=self._language())
        return " ".join(segment.text.strip() for segment in segments).strip()
