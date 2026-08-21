from __future__ import annotations

from katib_mudawwin.config import SummarizerConfig
from katib_mudawwin.summarization.base import Summarizer


def get_summarizer(config: SummarizerConfig) -> Summarizer:
    if config.provider == "local":
        from katib_mudawwin.summarization.local_summarizer import LocalSummarizer

        return LocalSummarizer(config.local)
    if config.provider == "anthropic":
        from katib_mudawwin.summarization.llm_summarizer import LlmSummarizer

        return LlmSummarizer(config.anthropic)
    raise ValueError(f"Unknown summarizer provider: {config.provider!r}")


__all__ = ["Summarizer", "get_summarizer"]
