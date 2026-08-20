from __future__ import annotations

from abc import ABC, abstractmethod


class Summarizer(ABC):
    @abstractmethod
    def summarize(self, transcript_text: str) -> str:
        """Returns a summary of the given transcript text."""
        raise NotImplementedError
