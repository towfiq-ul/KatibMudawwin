from __future__ import annotations

import os

import anthropic

from katib_mudawwin.config import AnthropicConfig
from katib_mudawwin.summarization.base import Summarizer
from katib_mudawwin.summarization.prompts import SUMMARY_PROMPT_TEMPLATE


class LlmSummarizer(Summarizer):
    def __init__(self, config: AnthropicConfig):
        self.config = config
        api_key = config.api_key or os.environ.get(config.api_key_env)
        if not api_key:
            raise RuntimeError(
                f"Neither summarizer.anthropic.api_key nor the "
                f"{config.api_key_env} environment variable is set; "
                "one of them is required to use the Anthropic API for summarization."
            )
        self.client = anthropic.Anthropic(api_key=api_key)

    def summarize(self, transcript_text: str) -> str:
        prompt = SUMMARY_PROMPT_TEMPLATE.format(transcript=transcript_text)
        message = self.client.messages.create(
            model=self.config.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(
            block.text for block in message.content if block.type == "text"
        ).strip()
