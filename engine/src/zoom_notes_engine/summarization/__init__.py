from __future__ import annotations

from zoom_notes_engine.config import SummarizerConfig
from zoom_notes_engine.summarization.base import Summarizer


def get_summarizer(config: SummarizerConfig) -> Summarizer:
    if config.provider == "ollama":
        from zoom_notes_engine.summarization.ollama_summarizer import OllamaSummarizer

        return OllamaSummarizer(config.ollama)
    if config.provider == "claude":
        from zoom_notes_engine.summarization.claude_summarizer import ClaudeSummarizer

        return ClaudeSummarizer(config.claude)
    raise ValueError(f"Unknown summarizer provider: {config.provider!r}")


__all__ = ["Summarizer", "get_summarizer"]
