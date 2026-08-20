import numpy as np

from katib_mudawwin.audio.vad import UtteranceSegmenter, VoiceActivityDetector
from katib_mudawwin.config import VadConfig


def make_frame(value=0.1, length=320):  # 20ms @ 16kHz = 320 samples
    return np.full(length, value, dtype=np.float32)


def scripted(decisions):
    it = iter(decisions)

    def fn(frame):
        return next(it)

    return fn


def test_flushes_on_sustained_silence_after_speech():
    # frame_ms=20, min_silence_ms=60 -> 3 consecutive silence frames needed
    config = VadConfig(aggressiveness=2, min_silence_ms=60, max_utterance_seconds=10)
    decisions = [True, True, False, False, False, True]
    seg = UtteranceSegmenter(config, frame_ms=20, is_speech_fn=scripted(decisions))

    results = [seg.push_frame(make_frame()) for _ in decisions]

    assert results[:4] == [None, None, None, None]
    assert results[4] is not None  # flush once 3rd consecutive silence frame lands
    assert len(results[4]) == 320 * 5  # 2 speech + 3 silence frames included
    assert results[5] is None  # new speech frame starts a fresh utterance


def test_silence_before_any_speech_is_ignored():
    config = VadConfig(aggressiveness=2, min_silence_ms=40, max_utterance_seconds=10)
    decisions = [False, False, False, False]
    seg = UtteranceSegmenter(config, frame_ms=20, is_speech_fn=scripted(decisions))

    results = [seg.push_frame(make_frame()) for _ in decisions]
    assert all(r is None for r in results)


def test_max_utterance_cap_forces_flush_even_without_silence():
    # max_utterance_seconds=0.06 -> 60ms -> 3 frames of 20ms
    config = VadConfig(aggressiveness=2, min_silence_ms=1000, max_utterance_seconds=0.06)
    decisions = [True, True, True, True]
    seg = UtteranceSegmenter(config, frame_ms=20, is_speech_fn=scripted(decisions))

    results = [seg.push_frame(make_frame()) for _ in decisions]
    assert results[0] is None
    assert results[1] is None
    assert results[2] is not None  # hit the cap at 60ms
    assert len(results[2]) == 320 * 3


def test_flush_remaining_returns_partial_buffer_at_stream_end():
    config = VadConfig(aggressiveness=2, min_silence_ms=1000, max_utterance_seconds=10)
    seg = UtteranceSegmenter(config, frame_ms=20, is_speech_fn=scripted([True, True]))
    seg.push_frame(make_frame())
    seg.push_frame(make_frame())

    remaining = seg.flush_remaining()
    assert remaining is not None
    assert len(remaining) == 320 * 2
    assert seg.flush_remaining() is None  # nothing left the second time


def test_voice_activity_detector_rejects_digital_silence():
    vad = VoiceActivityDetector(VadConfig(aggressiveness=2), sample_rate=16000)
    silence = np.zeros(320, dtype=np.float32)  # 20ms @ 16kHz
    assert vad.is_speech(silence) is False
