from __future__ import annotations

import os

import anthropic

from zoom_notes_engine.config import ClaudeConfig
from zoom_notes_engine.summarization.base import Summarizer
from zoom_notes_engine.summarization.prompts import SUMMARY_PROMPT_TEMPLATE


class ClaudeSummarizer(Summarizer):
    def __init__(self, config: ClaudeConfig):
        self.config = config
        api_key = config.api_key or os.environ.get(config.api_key_env)
        if not api_key:
            raise RuntimeError(
                f"Neither summarizer.claude.api_key nor the "
                f"{config.api_key_env} environment variable is set; "
                "one of them is required to use Claude for summarization."
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
