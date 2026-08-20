from katib_mudawwin.models import SessionState, SessionStatus
from katib_mudawwin.status_api import create_app


class FakeRecorder:
    """Duck-types the bits of SessionRecorder that status_api.py needs, so
    this test doesn't have to spin up real audio/detection/whisper."""

    def __init__(self):
        self.state = SessionState(status=SessionStatus.IDLE)
        self.start_calls = 0
        self.stop_calls = 0

    def force_start(self):
        self.start_calls += 1
        self.state = SessionState(
            status=SessionStatus.RECORDING,
            transcript_path="/tmp/x_meeting-notes.txt",
            summary_path="/tmp/x_summary.txt",
        )

    def force_stop(self):
        self.stop_calls += 1
        self.state = SessionState(status=SessionStatus.IDLE)


def test_health():
    client = create_app(FakeRecorder()).test_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_status_reflects_recorder_state():
    client = create_app(FakeRecorder()).test_client()
    resp = client.get("/status")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "idle"


def test_start_and_stop_endpoints_call_recorder():
    recorder = FakeRecorder()
    client = create_app(recorder).test_client()

    resp = client.post("/start")
    assert resp.get_json()["status"] == "recording"
    assert recorder.start_calls == 1

    resp = client.post("/stop")
    assert resp.get_json()["status"] == "idle"
    assert recorder.stop_calls == 1
