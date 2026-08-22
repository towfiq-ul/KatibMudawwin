from __future__ import annotations

import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Callable, List, Optional

from katib_mudawwin.audio.base import AudioSource
from katib_mudawwin.audio.vad import UtteranceSegmenter, VoiceActivityDetector
from katib_mudawwin.audio.wav_writer import StreamingWavWriter
from katib_mudawwin.config import AppConfig, VadConfig
from katib_mudawwin.detection.detector import MeetingDetector
from katib_mudawwin.models import AudioSource as AudioSourceLabel
from katib_mudawwin.models import SessionState, SessionStatus, TranscriptEntry
from katib_mudawwin.session.writer import TranscriptWriter
from katib_mudawwin.storage import db
from katib_mudawwin.transcription.whisper_engine import WhisperEngine

logger = logging.getLogger(__name__)


class _StreamPipeline:
    """One audio stream (mic or Zoom loopback) -> VAD segmenter -> Whisper
    -> TranscriptWriter, tagged with a fixed AudioSourceLabel."""

    def __init__(
        self,
        source: AudioSource,
        label: AudioSourceLabel,
        vad: VoiceActivityDetector,
        vad_config: VadConfig,
        frame_ms: float,
        whisper: WhisperEngine,
        writer: TranscriptWriter,
        audio_writer: Optional[StreamingWavWriter] = None,
    ):
        self.source = source
        self.label = label
        self.whisper = whisper
        self.writer = writer
        self.audio_writer = audio_writer
        self.frame_samples = max(1, int(source.sample_rate * frame_ms / 1000))
        self.segmenter = UtteranceSegmenter(vad_config, frame_ms, vad.is_speech)

    def _handle_utterance(self, utterance) -> None:
        if utterance is None or len(utterance) == 0:
            return
        text = self.whisper.transcribe_array(utterance)
        if not text:
            return
        self.writer.write_entry(TranscriptEntry(datetime.now(), self.label, text))

    def step(self) -> None:
        """Drains every complete frame currently buffered on the source, so
        a slow outer poll loop never lets a backlog build up between calls."""
        while True:
            frame = self.source.read_chunk(self.frame_samples)
            if len(frame) < self.frame_samples:
                break
            if self.audio_writer is not None:
                self.audio_writer.write(frame)
            utterance = self.segmenter.push_frame(frame)
            self._handle_utterance(utterance)

    def finish(self) -> None:
        self._handle_utterance(self.segmenter.flush_remaining())

    def close_audio(self) -> int:
        """Closes the raw-audio writer, if any, returning bytes written."""
        if self.audio_writer is None:
            return 0
        return self.audio_writer.close()


class SessionRecorder:
    """Orchestrates one meeting's worth of detection -> capture -> VAD ->
    transcription, driven by repeated run_once() calls (a real loop in
    production via run_forever(), or back-to-back calls against fake
    detectors/audio sources in tests -- see test_session_recorder.py, which
    exercises the whole pipeline offline). Summarization is a separate,
    on-demand step (`make summary` / katib_mudawwin.summarize_notes), not
    part of this lifecycle -- see summarize_notes.py for why."""

    def __init__(
        self,
        config: AppConfig,
        detector: MeetingDetector,
        mic_source_factory: Callable[[], AudioSource],
        zoom_source_factory: Callable[[], AudioSource],
        whisper: WhisperEngine,
        frame_ms: float = 20,
    ):
        self.config = config
        self.detector = detector
        self._mic_source_factory = mic_source_factory
        self._zoom_source_factory = zoom_source_factory
        self.whisper = whisper
        self.frame_ms = frame_ms
        self.state = SessionState()
        self._writer: Optional[TranscriptWriter] = None
        self._pipelines: List[_StreamPipeline] = []
        self._meeting_id: Optional[str] = None
        self._db = db.connect(db.default_db_path(self.config.storage_dir))
        # Guards session start/end and the step() loop against concurrent
        # force_start()/force_stop() calls from the status API and tray
        # threads racing the run_forever() polling thread.
        self._lock = threading.Lock()

    def _start_session(self) -> None:
        started_at = datetime.now()
        self._writer = TranscriptWriter(self.config.storage_dir, started_at)
        self.state = SessionState(
            status=SessionStatus.RECORDING,
            started_at=started_at,
            transcript_path=str(self._writer.transcript_path),
            summary_path=str(self._writer.summary_path),
        )

        mic = self._mic_source_factory()
        zoom = self._zoom_source_factory()
        mic.start()
        zoom.start()

        self._meeting_id = uuid.uuid4().hex
        audio_dir = self.config.storage_dir / "audio" / self._meeting_id

        self._pipelines = [
            _StreamPipeline(
                mic,
                AudioSourceLabel.ME,
                VoiceActivityDetector(self.config.vad, mic.sample_rate),
                self.config.vad,
                self.frame_ms,
                self.whisper,
                self._writer,
                audio_writer=StreamingWavWriter(audio_dir / "mic.wav", mic.sample_rate),
            ),
            _StreamPipeline(
                zoom,
                AudioSourceLabel.OTHERS,
                VoiceActivityDetector(self.config.vad, zoom.sample_rate),
                self.config.vad,
                self.frame_ms,
                self.whisper,
                self._writer,
                audio_writer=StreamingWavWriter(audio_dir / "zoom.wav", zoom.sample_rate),
            ),
        ]
        logger.info("Meeting started, writing to %s", self._writer.transcript_path)

    def _end_session(self) -> None:
        assert self._writer is not None
        audio_paths: dict[AudioSourceLabel, str] = {}
        audio_bytes = 0
        for pipeline in self._pipelines:
            # Drain whatever's already buffered on the source before
            # stopping it, so audio captured since the last poll tick isn't
            # lost, then flush the VAD's trailing partial utterance.
            pipeline.step()
            pipeline.finish()
            pipeline.source.stop()
            audio_bytes += pipeline.close_audio()
            if pipeline.audio_writer is not None:
                audio_paths[pipeline.label] = str(pipeline.audio_writer.path)
        self._pipelines = []
        self._writer.close()
        self._writer.finalize()

        db.record_meeting(
            self._db,
            meeting_id=self._meeting_id,
            started_at=self.state.started_at.isoformat(),
            ended_at=datetime.now().isoformat(),
            transcript_path=str(self._writer.transcript_path),
            summary_path=str(self._writer.summary_path),
            mic_audio_path=audio_paths.get(AudioSourceLabel.ME),
            zoom_audio_path=audio_paths.get(AudioSourceLabel.OTHERS),
            audio_bytes=audio_bytes,
        )

        logger.info("Meeting ended, transcript at %s", self._writer.transcript_path)
        self._writer = None
        self._meeting_id = None
        self.state = SessionState(status=SessionStatus.IDLE)

    def run_once(self) -> None:
        with self._lock:
            event = self.detector.poll()
            if event == "meeting_started":
                self._start_session()
            elif event == "meeting_ended":
                self._end_session()

            for pipeline in self._pipelines:
                pipeline.step()

    def force_start(self) -> None:
        with self._lock:
            if self.state.status == SessionStatus.IDLE:
                self._start_session()

    def force_stop(self) -> None:
        with self._lock:
            if self.state.status == SessionStatus.RECORDING:
                self._end_session()

    def run_forever(self, poll_interval: float) -> None:  # pragma: no cover - real loop
        while True:
            self.run_once()
            time.sleep(poll_interval)
