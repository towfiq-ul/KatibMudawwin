from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AudioActivitySnapshot:
    """A point-in-time read of whether Zoom appears to be actively
    streaming audio (a sink-input playing and/or a source-output capturing)."""

    zoom_process_running: bool
    zoom_sink_input_active: bool
    zoom_source_output_active: bool

    @property
    def is_active(self) -> bool:
        return self.zoom_sink_input_active or self.zoom_source_output_active


class AudioSignalSource(ABC):
    """Abstracts "how do we know if Zoom is actively streaming audio right
    now" so the detector state machine (detector.py) can be unit-tested
    against a fake, without needing pactl or a live Zoom meeting."""

    @abstractmethod
    def snapshot(self) -> AudioActivitySnapshot:
        raise NotImplementedError
