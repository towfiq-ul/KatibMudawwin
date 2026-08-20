from __future__ import annotations

from typing import Optional

from katib_mudawwin.config import LocalLlmConfig
from katib_mudawwin.summarization.base import Summarizer
from katib_mudawwin.summarization.prompts import SUMMARY_PROMPT_TEMPLATE


class LocalSummarizer(Summarizer):
    """Runs Phi-3 in-process via llama-cpp-python -- no separate service
    (unlike Ollama) needs to be running. Loading the model is expensive, so
    it's deferred until the first summarize() call rather than done in
    __init__, the same lazy-loading pattern used by WhisperEngine."""

    def __init__(self, config: LocalLlmConfig):
        self.config = config
        self._llama: Optional["Llama"] = None  # noqa: F821

    def _ensure_loaded(self):
        if self._llama is None:
            from llama_cpp import Llama

            self._llama = Llama.from_pretrained(
                repo_id=self.config.repo_id,
                filename=self.config.filename,
                n_ctx=self.config.n_ctx,
                n_threads=self.config.n_threads,
                verbose=False,
            )
        return self._llama

    def summarize(self, transcript_text: str) -> str:
        llama = self._ensure_loaded()
        prompt = SUMMARY_PROMPT_TEMPLATE.format(transcript=transcript_text)
        result = llama.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
        )
        return result["choices"][0]["message"]["content"].strip()
