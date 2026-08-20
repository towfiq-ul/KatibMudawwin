from __future__ import annotations

from typing import List

from katib_mudawwin.detection.base import AudioActivitySnapshot, AudioSignalSource


class ScriptedAudioSignalSource(AudioSignalSource):
    """Test double: returns a pre-scripted sequence of snapshots, one per
    call to snapshot(), then repeats the last one for any extra calls. Lets
    detector tests control exactly what the "audio signal" looks like at
    each poll, without pactl or a live Zoom meeting."""

    def __init__(self, snapshots: List[AudioActivitySnapshot]):
        if not snapshots:
            raise ValueError("snapshots must be non-empty")
        self._snapshots = snapshots
        self._index = 0

    def snapshot(self) -> AudioActivitySnapshot:
        snap = self._snapshots[min(self._index, len(self._snapshots) - 1)]
        self._index += 1
        return snap
