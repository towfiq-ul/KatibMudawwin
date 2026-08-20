# Test fixtures

`sample_meeting.wav` is **not checked in** (recorded audio, and `.wav` is
gitignored) -- generate it locally with:

```bash
./scripts/record_test_fixture.sh
```

It records ~15s from your microphone (no Zoom involved) and asks you to say
a specific phrase, which `test_whisper_engine.py` checks for in the
transcription output. If the file isn't present, that test is skipped
automatically rather than failing.

The `pactl_sink_inputs_*.json` fixtures *are* checked in -- they're
hand-crafted, based on documented PulseAudio/pipewire-pulse JSON output
shape, standing in for a real `pactl -f json list sink-inputs` capture.
They haven't yet been confirmed against a real Zoom call (see milestone 12
in the design doc); if the real property names/values differ, only
`detection/linux_detector.py`'s parsing needs adjusting, not the tests'
intent.
