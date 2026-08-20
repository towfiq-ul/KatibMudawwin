from pathlib import Path

from zoom_notes_engine.detection.linux_detector import PactlAudioSignalSource

FIXTURES = Path(__file__).parent / "fixtures"


class FakeCompletedProcess:
    def __init__(self, stdout: str):
        self.stdout = stdout


def _patch_pactl(monkeypatch, sink_inputs_json: str, source_outputs_json: str = "[]"):
    def fake_run(cmd, **kwargs):
        if "sink-inputs" in cmd:
            return FakeCompletedProcess(sink_inputs_json)
        if "source-outputs" in cmd:
            return FakeCompletedProcess(source_outputs_json)
        raise AssertionError(f"unexpected pactl command: {cmd}")

    monkeypatch.setattr(
        "zoom_notes_engine.detection.linux_detector.subprocess.run", fake_run
    )


def test_active_zoom_sink_input_is_detected(monkeypatch):
    fixture = (FIXTURES / "pactl_sink_inputs_with_zoom.json").read_text()
    _patch_pactl(monkeypatch, fixture)
    source = PactlAudioSignalSource(process_hint="zoom")
    monkeypatch.setattr(source, "_process_running", lambda: True)

    snapshot = source.snapshot()
    assert snapshot.zoom_process_running is True
    assert snapshot.zoom_sink_input_active is True
    assert snapshot.is_active is True


def test_corked_zoom_sink_input_is_not_active(monkeypatch):
    fixture = (FIXTURES / "pactl_sink_inputs_idle.json").read_text()
    _patch_pactl(monkeypatch, fixture)
    source = PactlAudioSignalSource(process_hint="zoom")
    monkeypatch.setattr(source, "_process_running", lambda: True)

    snapshot = source.snapshot()
    assert snapshot.zoom_sink_input_active is False
    assert snapshot.is_active is False


def test_zoom_not_running_short_circuits_without_calling_pactl(monkeypatch):
    def fail_run(cmd, **kwargs):
        raise AssertionError("pactl should not be called when Zoom isn't running")

    monkeypatch.setattr(
        "zoom_notes_engine.detection.linux_detector.subprocess.run", fail_run
    )
    source = PactlAudioSignalSource(process_hint="zoom")
    monkeypatch.setattr(source, "_process_running", lambda: False)

    snapshot = source.snapshot()
    assert snapshot.zoom_process_running is False
    assert snapshot.is_active is False
