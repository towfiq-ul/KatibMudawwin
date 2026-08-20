import wave

import numpy as np
import pytest

from zoom_notes_engine.audio.file_playback_source import FilePlaybackSource

SAMPLE_RATE = 16000


def _write_wav(path, samples: np.ndarray, sample_rate=SAMPLE_RATE, channels=1, sampwidth=2):
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        wf.writeframes(samples.tobytes())


def _synthetic_int16(num_samples: int) -> np.ndarray:
    # A simple ramp, not real speech -- this test only checks playback
    # mechanics (chunking, exhaustion, validation), not transcription
    # accuracy (that's test_whisper_engine.py, against a real recording).
    return (np.arange(num_samples, dtype=np.int16) % 1000) - 500


def test_reads_chunks_in_order_and_reports_exhaustion(tmp_path):
    wav_path = tmp_path / "fixture.wav"
    samples = _synthetic_int16(SAMPLE_RATE)  # 1 second
    _write_wav(wav_path, samples)

    source = FilePlaybackSource(wav_path, sample_rate=SAMPLE_RATE)
    source.start()

    chunk_size = SAMPLE_RATE // 4  # 250ms chunks
    read_frames = 0
    while not source.exhausted:
        chunk = source.read_chunk(chunk_size)
        if len(chunk) == 0:
            break
        read_frames += len(chunk)

    assert read_frames == len(samples)
    assert source.exhausted


def test_rejects_wrong_sample_rate(tmp_path):
    wav_path = tmp_path / "fixture.wav"
    _write_wav(wav_path, _synthetic_int16(8000), sample_rate=8000)

    with pytest.raises(ValueError, match="sample rate"):
        FilePlaybackSource(wav_path, sample_rate=SAMPLE_RATE)


def test_rejects_non_mono(tmp_path):
    wav_path = tmp_path / "fixture.wav"
    stereo = np.repeat(_synthetic_int16(SAMPLE_RATE), 2)
    _write_wav(wav_path, stereo, channels=2)

    with pytest.raises(ValueError, match="mono"):
        FilePlaybackSource(wav_path, sample_rate=SAMPLE_RATE)
