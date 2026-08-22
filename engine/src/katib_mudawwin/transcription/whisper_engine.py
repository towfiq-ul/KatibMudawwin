from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from faster_whisper import WhisperModel

from katib_mudawwin.config import WhisperConfig


@dataclass
class TranscriptionResult:
    text: str
    # faster-whisper's detected language for this utterance (ISO-639-1,
    # e.g. "en", "bn", "hi") -- None only if `text` is empty.
    language: Optional[str]


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
    # previously hallucinated text. task="translate" makes Whisper emit
    # English text regardless of the spoken language, so notes are always
    # in English -- on an English-only (".en") model this is a no-op, since
    # faster-whisper's tokenizer ignores `task` for non-multilingual models
    # (see tokenizer.py: self.task = None unless multilingual).
    _TRANSCRIBE_KWARGS = {
        "vad_filter": True,
        "condition_on_previous_text": False,
        "task": "translate",
    }

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

    def transcribe_array(self, audio: np.ndarray) -> TranscriptionResult:
        """Transcribes a mono float32 numpy array in [-1.0, 1.0], sampled at
        the engine's expected rate (16kHz), and returns the joined text plus
        the detected language. Intended to be called once per VAD-segmented
        utterance or test chunk."""
        model = self._ensure_loaded()
        segments, info = model.transcribe(
            audio, language=self._language(), **self._TRANSCRIBE_KWARGS
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return TranscriptionResult(text, info.language if text else None)

    def transcribe_wav_file(self, path: Path) -> TranscriptionResult:
        model = self._ensure_loaded()
        segments, info = model.transcribe(
            str(path), language=self._language(), **self._TRANSCRIBE_KWARGS
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return TranscriptionResult(text, info.language if text else None)
