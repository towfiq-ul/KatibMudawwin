from __future__ import annotations

import json
import subprocess
from typing import List

import psutil

from katib_mudawwin.detection.base import AudioActivitySnapshot, AudioSignalSource


class PactlAudioSignalSource(AudioSignalSource):
    """Real Linux implementation: shells out to `pactl -f json list
    sink-inputs`/`source-outputs` and checks whether any entry belongs to
    Zoom and is actively streaming (not corked/idle). A cheap `psutil`
    process check gates the pactl calls so we don't shell out at all when
    Zoom isn't even running.

    NOTE: the exact `application.*` property values and JSON shape are
    assumed from PulseAudio/pipewire-pulse documentation (see the hand-built
    fixtures in engine/tests/fixtures/) and need to be confirmed against a
    real Zoom call -- that's milestone 12 in the design doc, not this one.
    """

    def __init__(self, process_hint: str = "zoom"):
        self.process_hint = process_hint.lower()

    def _process_running(self) -> bool:
        hint = self.process_hint
        for proc in psutil.process_iter(["name"]):
            name = (proc.info.get("name") or "").lower()
            if hint in name:
                return True
        return False

    def _pactl_json(self, kind: str) -> List[dict]:
        try:
            result = subprocess.run(
                ["pactl", "-f", "json", "list", kind],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return []
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return []

    def _any_active_for_zoom(self, entries: List[dict]) -> bool:
        for entry in entries:
            props = entry.get("properties", {}) or {}
            binary = (props.get("application.process.binary") or "").lower()
            name = (props.get("application.name") or "").lower()
            if self.process_hint not in binary and self.process_hint not in name:
                continue
            if not entry.get("corked", False):
                return True
        return False

    def snapshot(self) -> AudioActivitySnapshot:
        if not self._process_running():
            return AudioActivitySnapshot(
                zoom_process_running=False,
                zoom_sink_input_active=False,
                zoom_source_output_active=False,
            )
        sink_inputs = self._pactl_json("sink-inputs")
        source_outputs = self._pactl_json("source-outputs")
        return AudioActivitySnapshot(
            zoom_process_running=True,
            zoom_sink_input_active=self._any_active_for_zoom(sink_inputs),
            zoom_source_output_active=self._any_active_for_zoom(source_outputs),
        )
