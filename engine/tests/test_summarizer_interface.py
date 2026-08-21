import pytest

from katib_mudawwin.config import SummarizerConfig
from katib_mudawwin.summarization import get_summarizer
from katib_mudawwin.summarization.llm_summarizer import LlmSummarizer
from katib_mudawwin.summarization.local_summarizer import LocalSummarizer


def test_get_summarizer_returns_local_by_default():
    config = SummarizerConfig()
    summarizer = get_summarizer(config)
    assert isinstance(summarizer, LocalSummarizer)


def test_get_summarizer_returns_llm_when_configured(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    config = SummarizerConfig(provider="anthropic")
    summarizer = get_summarizer(config)
    assert isinstance(summarizer, LlmSummarizer)


def test_llm_summarizer_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    config = SummarizerConfig(provider="anthropic")
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        get_summarizer(config)


def test_unknown_provider_raises():
    config = SummarizerConfig()
    config.provider = "not-a-real-provider"  # type: ignore[assignment]
    with pytest.raises(ValueError, match="Unknown summarizer provider"):
        get_summarizer(config)
