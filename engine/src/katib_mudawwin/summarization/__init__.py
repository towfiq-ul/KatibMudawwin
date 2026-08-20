from __future__ import annotations

from katib_mudawwin.config import SummarizerConfig
from katib_mudawwin.summarization.base import Summarizer


def get_summarizer(config: SummarizerConfig) -> Summarizer:
    if config.provider == "local":
        from katib_mudawwin.summarization.local_summarizer import LocalSummarizer

        return LocalSummarizer(config.local)
    if config.provider == "claude":
        from katib_mudawwin.summarization.claude_summarizer import ClaudeSummarizer

        return ClaudeSummarizer(config.claude)
    raise ValueError(f"Unknown summarizer provider: {config.provider!r}")


__all__ = ["Summarizer", "get_summarizer"]
