import wave

import numpy as np

from katib_mudawwin.audio.file_playback_source import FilePlaybackSource
from katib_mudawwin.config import AppConfig, DetectionConfig, VadConfig
from katib_mudawwin.detection.base import AudioActivitySnapshot
from katib_mudawwin.detection.detector import MeetingDetector
from katib_mudawwin.detection.fake_signal_source import ScriptedAudioSignalSource
from katib_mudawwin.session.recorder import SessionRecorder
from katib_mudawwin.summarization.base import Summarizer

SAMPLE_RATE = 16000
ACTIVE = AudioActivitySnapshot(True, True, False)
IDLE = AudioActivitySnapshot(True, False, False)


class FakeWhisperEngine:
    """Stands in for the real faster-whisper model -- deterministic and
    instant, so this integration test doesn't need to load/run a real
    model (that's covered separately in test_whisper_engine.py)."""

    def __init__(self):
        self.calls = 0

    def transcribe_array(self, audio) -> str:
        self.calls += 1
        return f"utterance {self.calls}"


class FakeSummarizer(Summarizer):
    def __init__(self):
        self.received = None

    def summarize(self, transcript_text: str) -> str:
        self.received = transcript_text
        return "SUMMARY: things were discussed."


def _write_wav(path, seconds=0.5, sample_rate=SAMPLE_RATE):
    num_samples = int(seconds * sample_rate)
    tone = np.sin(2 * np.pi * 220 * np.arange(num_samples) / sample_rate)
    samples = (tone * 10000).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(samples.tobytes())


def test_full_offline_pipeline_writes_transcript_and_summary(tmp_path, monkeypatch):
    # Treat every frame as speech, so the segmenter reliably produces
    # utterances from our synthetic tone without depending on webrtcvad's
    # real judgment of a non-speech test signal.
    monkeypatch.setattr(
        "katib_mudawwin.audio.vad.VoiceActivityDetector.is_speech",
        lambda self, frame: True,
    )

    mic_wav = tmp_path / "mic.wav"
    zoom_wav = tmp_path / "zoom.wav"
    _write_wav(mic_wav)
    _write_wav(zoom_wav)

    storage_dir = tmp_path / "notes"
    config = AppConfig(
        storage_dir=storage_dir,
        vad=VadConfig(aggressiveness=0, min_silence_ms=1000, max_utterance_seconds=0.3),
        detection=DetectionConfig(
            start_debounce_seconds=0, end_debounce_seconds=0, poll_interval_seconds=0.01
        ),
    )

    # With both debounces at 0 and a real (fast) clock, one ACTIVE poll
    # after the first arms the detector, and one IDLE poll after that ends
    # it deterministically -- no real-time waiting needed in this test.
    detector = MeetingDetector(
        ScriptedAudioSignalSource([ACTIVE, ACTIVE, IDLE, IDLE]),
        config.detection,
    )

    whisper = FakeWhisperEngine()
    summarizer = FakeSummarizer()

    recorder = SessionRecorder(
        config=config,
        detector=detector,
        mic_source_factory=lambda: FilePlaybackSource(mic_wav, sample_rate=SAMPLE_RATE),
        zoom_source_factory=lambda: FilePlaybackSource(zoom_wav, sample_rate=SAMPLE_RATE),
        whisper=whisper,
        summarizer=summarizer,
        frame_ms=20,
    )

    for _ in range(6):
        recorder.run_once()

    assert whisper.calls >= 2  # at least one flush per stream
    assert summarizer.received is not None
    assert "utterance" in summarizer.received.lower()

    transcript_files = list(storage_dir.glob("*_meeting-notes.txt"))
    summary_files = list(storage_dir.glob("*_summary.txt"))
    assert len(transcript_files) == 1
    assert len(summary_files) == 1
    assert "SUMMARY: things were discussed." in summary_files[0].read_text()


def test_summarizer_failure_still_preserves_transcript(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "katib_mudawwin.audio.vad.VoiceActivityDetector.is_speech",
        lambda self, frame: True,
    )

    mic_wav = tmp_path / "mic.wav"
    zoom_wav = tmp_path / "zoom.wav"
    _write_wav(mic_wav)
    _write_wav(zoom_wav)

    storage_dir = tmp_path / "notes"
    config = AppConfig(
        storage_dir=storage_dir,
        vad=VadConfig(aggressiveness=0, min_silence_ms=1000, max_utterance_seconds=0.3),
        detection=DetectionConfig(start_debounce_seconds=0, end_debounce_seconds=0),
    )
    detector = MeetingDetector(
        ScriptedAudioSignalSource([ACTIVE, ACTIVE, IDLE, IDLE]), config.detection
    )

    class FailingSummarizer(Summarizer):
        def summarize(self, transcript_text: str) -> str:
            raise RuntimeError("summarizer unreachable")

    recorder = SessionRecorder(
        config=config,
        detector=detector,
        mic_source_factory=lambda: FilePlaybackSource(mic_wav, sample_rate=SAMPLE_RATE),
        zoom_source_factory=lambda: FilePlaybackSource(zoom_wav, sample_rate=SAMPLE_RATE),
        whisper=FakeWhisperEngine(),
        summarizer=FailingSummarizer(),
        frame_ms=20,
    )

    for _ in range(6):
        recorder.run_once()

    transcript_files = list(storage_dir.glob("*_meeting-notes.txt"))
    summary_files = list(storage_dir.glob("*_summary.txt"))
    assert len(transcript_files) == 1
    assert "utterance" in transcript_files[0].read_text().lower()
    assert len(summary_files) == 0  # summarization failed, no summary written
