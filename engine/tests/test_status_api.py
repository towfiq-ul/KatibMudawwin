import katib_mudawwin.status_api as status_api
from katib_mudawwin.config import AppConfig
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


class FakeSummarizer:
    def summarize(self, transcript_text: str) -> str:
        return f"summary of: {transcript_text.strip()}"


def make_app(tmp_path, monkeypatch=None):
    config = AppConfig(storage_dir=tmp_path)
    if monkeypatch is not None:
        monkeypatch.setattr(status_api, "get_summarizer", lambda _config: FakeSummarizer())
    return create_app(FakeRecorder(), config), config


def test_health(tmp_path):
    app, _ = make_app(tmp_path)
    resp = app.test_client().get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_status_reflects_recorder_state(tmp_path):
    app, _ = make_app(tmp_path)
    resp = app.test_client().get("/status")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "idle"


def test_start_and_stop_endpoints_call_recorder(tmp_path):
    recorder = FakeRecorder()
    config = AppConfig(storage_dir=tmp_path)
    client = create_app(recorder, config).test_client()

    resp = client.post("/start")
    assert resp.get_json()["status"] == "recording"
    assert recorder.start_calls == 1

    resp = client.post("/stop")
    assert resp.get_json()["status"] == "idle"
    assert recorder.stop_calls == 1


def test_summarize_rejects_invalid_date(tmp_path):
    app, _ = make_app(tmp_path)
    resp = app.test_client().post("/summarize", json={"date": "not-a-date"})
    assert resp.status_code == 400


def test_summarize_404s_when_no_notes_for_date(tmp_path):
    app, _ = make_app(tmp_path)
    resp = app.test_client().post("/summarize", json={"date": "20260101"})
    assert resp.status_code == 404


def test_summarize_writes_summary_file(tmp_path, monkeypatch):
    app, config = make_app(tmp_path, monkeypatch)
    date_dir = config.storage_dir / "notes" / "20260101"
    date_dir.mkdir(parents=True)
    (date_dir / "note_20260101_090000.txt").write_text("hello", encoding="utf-8")

    resp = app.test_client().post("/summarize", json={"date": "20260101"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["date"] == "20260101"

    summary_path = date_dir / "summary_note_20260101.txt"
    assert str(summary_path) == body["summary_path"]
    assert "summary of: hello" in summary_path.read_text(encoding="utf-8")
