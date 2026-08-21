"""Ad hoc live-test driver: transcribes ONLY the Zoom speaker/output audio
(no mic, no summarizer) and appends plain lines to a fixed test_notes.txt.
Not part of the shipped app -- for milestone-12 live validation only.

Usage: engine/.venv/bin/python engine/scripts/test_transcribe_zoom.py
Stop with Ctrl+C -- it flushes the trailing partial utterance on exit.
"""

from __future__ import annotations

import signal
import sys
import time
from datetime import datetime
from pathlib import Path

from katib_mudawwin.audio.linux_capture import ZoomLoopbackSource
from katib_mudawwin.audio.vad import UtteranceSegmenter, VoiceActivityDetector
from katib_mudawwin.config import load_config
from katib_mudawwin.transcription.whisper_engine import WhisperEngine

OUTPUT_PATH = Path("/home/towfiq/workspace/KatibMudawwin/test_notes.txt")
FRAME_MS = 30.0


def main() -> None:
    config = load_config()
    zoom = ZoomLoopbackSource(
        sink_name=config.audio.zoom_null_sink_name,
        sample_rate=config.audio.sample_rate,
        process_hint=config.detection.zoom_process_hint,
    )
    vad = VoiceActivityDetector(config.vad, zoom.sample_rate)
    segmenter = UtteranceSegmenter(config.vad, FRAME_MS, vad.is_speech)
    whisper = WhisperEngine(config.whisper)
    frame_samples = max(1, int(zoom.sample_rate * FRAME_MS / 1000))

    stop = False

    def _handle_sigint(signum, frame):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _handle_sigint)
    signal.signal(signal.SIGTERM, _handle_sigint)

    zoom.start()
    print(f"Capturing Zoom speaker audio -- writing to {OUTPUT_PATH}. Ctrl+C to stop.")

    def write_line(text: str) -> None:
        if not text:
            return
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {text}\n"
        with open(OUTPUT_PATH, "a") as f:
            f.write(line)
            f.flush()
        print(line, end="")

    try:
        while not stop:
            frame = zoom.read_chunk(frame_samples)
            if len(frame) < frame_samples:
                time.sleep(0.05)
                continue
            utterance = segmenter.push_frame(frame)
            if utterance is not None and len(utterance) > 0:
                write_line(whisper.transcribe_array(utterance))
    finally:
        utterance = segmenter.flush_remaining()
        if utterance is not None and len(utterance) > 0:
            write_line(whisper.transcribe_array(utterance))
        zoom.stop()
        print("Stopped, PipeWire modules unloaded.")


if __name__ == "__main__":
    sys.exit(main())
