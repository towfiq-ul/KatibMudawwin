import wave

import numpy as np

from katib_mudawwin.audio.wav_writer import StreamingWavWriter


def test_writes_incremental_frames_as_valid_pcm16_wav(tmp_path):
    path = tmp_path / "audio" / "mic.wav"
    writer = StreamingWavWriter(path, sample_rate=16000)

    frame1 = np.array([0.0, 0.5, -0.5], dtype=np.float32)
    frame2 = np.array([1.0, -1.0], dtype=np.float32)
    writer.write(frame1)
    writer.write(frame2)
    size = writer.close()

    assert path.exists()
    assert size == path.stat().st_size

    with wave.open(str(path), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 16000
        assert wf.getnframes() == 5
        raw = wf.readframes(5)

    samples = np.frombuffer(raw, dtype=np.int16)
    # 1.0 / -1.0 clip to the int16 extremes rather than overflowing.
    assert samples[3] == 32767
    assert samples[4] == -32767


def test_write_ignores_empty_frames(tmp_path):
    path = tmp_path / "mic.wav"
    writer = StreamingWavWriter(path, sample_rate=16000)
    writer.write(np.array([], dtype=np.float32))
    writer.close()

    with wave.open(str(path), "rb") as wf:
        assert wf.getnframes() == 0


def test_creates_parent_directory(tmp_path):
    path = tmp_path / "audio" / "abc123" / "zoom.wav"
    writer = StreamingWavWriter(path, sample_rate=16000)
    writer.close()
    assert path.exists()
