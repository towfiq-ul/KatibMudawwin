from __future__ import annotations

from flask import Flask, jsonify

from katib_mudawwin.session.recorder import SessionRecorder


def create_app(recorder: SessionRecorder) -> Flask:
    app = Flask(__name__)

    def _status_payload():
        state = recorder.state
        return {
            "status": state.status.value,
            "started_at": state.started_at.isoformat() if state.started_at else None,
            "transcript_path": state.transcript_path,
            "summary_path": state.summary_path,
        }

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/status")
    def status():
        return jsonify(_status_payload())

    @app.post("/start")
    def start():
        recorder.force_start()
        return jsonify(_status_payload())

    @app.post("/stop")
    def stop():
        recorder.force_stop()
        return jsonify(_status_payload())

    return app


def run_status_api(recorder: SessionRecorder, host: str, port: int) -> None:  # pragma: no cover - real server
    create_app(recorder).run(host=host, port=port)
