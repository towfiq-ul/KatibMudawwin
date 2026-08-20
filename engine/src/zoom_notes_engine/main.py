from __future__ import annotations

import logging
import threading

from zoom_notes_engine.audio.linux_capture import MicSource, ZoomLoopbackSource
from zoom_notes_engine.config import load_config
from zoom_notes_engine.detection.detector import MeetingDetector
from zoom_notes_engine.detection.linux_detector import PactlAudioSignalSource
from zoom_notes_engine.session.recorder import SessionRecorder
from zoom_notes_engine.status_api import run_status_api
from zoom_notes_engine.transcription.whisper_engine import WhisperEngine
from zoom_notes_engine.tray import build_tray_icon

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    config = load_config()
    logger.info(
        "storage_dir=%s summarizer=%s whisper=%s",
        config.storage_dir,
        config.summarizer.provider,
        config.whisper.model_size,
    )

    whisper = WhisperEngine(config.whisper)
    detector = MeetingDetector(
        PactlAudioSignalSource(config.detection.zoom_process_hint), config.detection
    )
    recorder = SessionRecorder(
        config=config,
        detector=detector,
        mic_source_factory=lambda: MicSource(
            config.audio.mic_device, config.audio.sample_rate
        ),
        zoom_source_factory=lambda: ZoomLoopbackSource(
            config.audio.zoom_null_sink_name,
            config.audio.sample_rate,
            config.detection.zoom_process_hint,
        ),
        whisper=whisper,
    )

    threading.Thread(
        target=run_status_api,
        args=(recorder, config.server.status_api_host, config.server.status_api_port),
        daemon=True,
    ).start()

    threading.Thread(
        target=recorder.run_forever,
        args=(config.detection.poll_interval_seconds,),
        daemon=True,
    ).start()

    logger.info(
        "Status API on http://%s:%s -- auto-detecting Zoom meetings now",
        config.server.status_api_host,
        config.server.status_api_port,
    )

    build_tray_icon(recorder, config).run()  # blocks until Quit


if __name__ == "__main__":
    main()
