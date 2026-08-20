from __future__ import annotations

import requests

from zoom_notes_engine.config import OllamaConfig
from zoom_notes_engine.summarization.base import Summarizer
from zoom_notes_engine.summarization.prompts import SUMMARY_PROMPT_TEMPLATE


class OllamaSummarizer(Summarizer):
    def __init__(self, config: OllamaConfig):
        self.config = config

    def summarize(self, transcript_text: str) -> str:
        prompt = SUMMARY_PROMPT_TEMPLATE.format(transcript=transcript_text)
        response = requests.post(
            f"{self.config.base_url}/api/generate",
            json={
                "model": self.config.model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_ctx": self.config.num_ctx},
            },
            timeout=300,
        )
        response.raise_for_status()
        return response.json()["response"].strip()
