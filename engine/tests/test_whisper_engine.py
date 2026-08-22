import wave
from pathlib import Path

import numpy as np
import pytest

from katib_mudawwin.config import WhisperConfig
from katib_mudawwin.transcription.whisper_engine import WhisperEngine

FIXTURE = Path(__file__).parent / "fixtures" / "sample_meeting.wav"


@pytest.mark.skipif(
    not FIXTURE.exists(),
    reason=(
        "engine/tests/fixtures/sample_meeting.wav not present -- run "
        "scripts/record_test_fixture.sh to record it (uses your mic, no Zoom needed)"
    ),
)
def test_transcribes_fixture_in_chunks():
    with wave.open(str(FIXTURE), "rb") as wf:
        sample_rate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

    engine = WhisperEngine(
        WhisperConfig(model_size="base.en", device="cpu", compute_type="int8")
    )

    chunk_size = sample_rate * 5  # ~5s chunks, per milestone 4's "artificial chunks"
    texts = []
    for start in range(0, len(samples), chunk_size):
        chunk = samples[start : start + chunk_size]
        if len(chunk) == 0:
            continue
        texts.append(engine.transcribe_array(chunk).text)

    full_text = " ".join(texts).lower()
    assert "test" in full_text
    assert "transcription" in full_text
