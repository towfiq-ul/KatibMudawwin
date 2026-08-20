from __future__ import annotations

import time
from enum import Enum
from typing import Callable, Optional

from katib_mudawwin.config import DetectionConfig
from katib_mudawwin.detection.base import AudioSignalSource


class MeetingDetectorState(str, Enum):
    IDLE = "idle"
    STARTING = "starting"  # active signal seen, waiting out start_debounce
    IN_MEETING = "in_meeting"
    ENDING = "ending"  # signal went quiet, waiting out end_debounce


class MeetingDetector:
    """Debounced state machine over an AudioSignalSource. Call poll() on a
    timer (config.detection.poll_interval_seconds); it returns
    "meeting_started" / "meeting_ended" / None depending on whether a
    debounced transition just happened.

    Fully testable against a fake AudioSignalSource -- no pactl or live
    Zoom call required to verify this logic is correct (see test_detector.py
    and milestone 5 in the design doc). The real signal source
    (PactlAudioSignalSource) only needs to be swapped in for the live
    validation pass in milestone 12.
    """

    def __init__(
        self,
        signal_source: AudioSignalSource,
        config: DetectionConfig,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.signal_source = signal_source
        self.config = config
        self._clock = clock
        self.state = MeetingDetectorState.IDLE
        self._state_entered_at: float = self._clock()

    def _transition(self, new_state: MeetingDetectorState) -> None:
        self.state = new_state
        self._state_entered_at = self._clock()

    def _elapsed_in_state(self) -> float:
        return self._clock() - self._state_entered_at

    def poll(self) -> Optional[str]:
        snapshot = self.signal_source.snapshot()
        active = snapshot.is_active

        if self.state == MeetingDetectorState.IDLE:
            if active:
                self._transition(MeetingDetectorState.STARTING)
            return None

        if self.state == MeetingDetectorState.STARTING:
            if not active:
                self._transition(MeetingDetectorState.IDLE)
            elif self._elapsed_in_state() >= self.config.start_debounce_seconds:
                self._transition(MeetingDetectorState.IN_MEETING)
                return "meeting_started"
            return None

        if self.state == MeetingDetectorState.IN_MEETING:
            if not active:
                self._transition(MeetingDetectorState.ENDING)
            return None

        if self.state == MeetingDetectorState.ENDING:
            if active:
                self._transition(MeetingDetectorState.IN_MEETING)
            elif self._elapsed_in_state() >= self.config.end_debounce_seconds:
                self._transition(MeetingDetectorState.IDLE)
                return "meeting_ended"
            return None

        return None
