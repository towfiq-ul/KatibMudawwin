from zoom_notes_engine.config import DetectionConfig
from zoom_notes_engine.detection.base import AudioActivitySnapshot
from zoom_notes_engine.detection.detector import MeetingDetector, MeetingDetectorState
from zoom_notes_engine.detection.fake_signal_source import ScriptedAudioSignalSource

ACTIVE = AudioActivitySnapshot(
    zoom_process_running=True, zoom_sink_input_active=True, zoom_source_output_active=False
)
IDLE = AudioActivitySnapshot(
    zoom_process_running=True, zoom_sink_input_active=False, zoom_source_output_active=False
)


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


def make_detector(snapshots, start_debounce=5, end_debounce=20):
    clock = FakeClock()
    config = DetectionConfig(start_debounce_seconds=start_debounce, end_debounce_seconds=end_debounce)
    source = ScriptedAudioSignalSource(snapshots)
    detector = MeetingDetector(source, config, clock=clock)
    return detector, clock


def test_meeting_starts_only_after_sustained_activity():
    detector, clock = make_detector([ACTIVE] * 5, start_debounce=5)

    assert detector.poll() is None  # IDLE -> STARTING at t=0
    clock.advance(2)
    assert detector.poll() is None  # still within debounce window (t=2)
    clock.advance(4)
    assert detector.poll() == "meeting_started"  # t=6 >= 5s debounce
    assert detector.state == MeetingDetectorState.IN_MEETING


def test_brief_activity_blip_does_not_start_a_meeting():
    detector, clock = make_detector([ACTIVE, IDLE, IDLE], start_debounce=5)

    assert detector.poll() is None  # IDLE -> STARTING
    clock.advance(2)
    assert detector.poll() is None  # signal drops before debounce -> back to IDLE
    assert detector.state == MeetingDetectorState.IDLE


def test_meeting_ends_only_after_sustained_silence():
    detector, clock = make_detector([ACTIVE] * 2 + [IDLE] * 5, start_debounce=1, end_debounce=15)

    detector.poll()  # IDLE -> STARTING
    clock.advance(2)
    assert detector.poll() == "meeting_started"  # -> IN_MEETING

    assert detector.poll() is None  # signal drops -> ENDING
    clock.advance(10)
    assert detector.poll() is None  # still within end-debounce window
    clock.advance(10)
    assert detector.poll() == "meeting_ended"


def test_brief_mute_does_not_end_a_meeting():
    detector, clock = make_detector(
        [ACTIVE] * 2 + [IDLE] + [ACTIVE] * 5, start_debounce=1, end_debounce=15
    )

    detector.poll()
    clock.advance(2)
    assert detector.poll() == "meeting_started"

    assert detector.poll() is None  # brief mute -> ENDING
    clock.advance(3)
    assert detector.poll() is None  # audio resumes within debounce -> back to IN_MEETING
    assert detector.state == MeetingDetectorState.IN_MEETING
