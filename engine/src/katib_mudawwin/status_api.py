from __future__ import annotations

from flask import Flask, jsonify, request

from katib_mudawwin.config import AppConfig
from katib_mudawwin.session.recorder import SessionRecorder
from katib_mudawwin.summarization import get_summarizer
from katib_mudawwin.summarize_notes import DATE_PATTERN, summarize_date


def create_app(recorder: SessionRecorder, config: AppConfig) -> Flask:
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

    @app.post("/summarize")
    def summarize():
        date = (request.get_json(silent=True) or {}).get("date", "")
        if not DATE_PATTERN.match(date):
            return jsonify({"error": f"invalid date {date!r} -- expected yyyymmdd"}), 400

        date_dir = config.storage_dir / "notes" / date
        if not date_dir.exists():
            return jsonify({"error": f"no notes found for {date}"}), 404

        try:
            summarizer = get_summarizer(config.summarizer)
            summary_path = summarize_date(config.storage_dir, date, summarizer)
        except Exception as e:  # summarizer/API failures shouldn't crash the status API
            return jsonify({"error": str(e)}), 500

        return jsonify({"date": date, "summary_path": str(summary_path)})

    return app


def run_status_api(recorder: SessionRecorder, config: AppConfig, host: str, port: int) -> None:  # pragma: no cover - real server
    # threaded=True: /summarize can run a local LLM inference (or, on first
    # use, download a ~2.3GB model) that takes far longer than a status
    # poll -- without this, that request would block /health and /status
    # for every other client (e.g. the desktop app's tray, which polls
    # every 2s) until it finishes.
    create_app(recorder, config).run(host=host, port=port, threaded=True)
