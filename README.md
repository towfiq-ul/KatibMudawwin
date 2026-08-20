# zoom-app-screen-note-taker

A local, personal meeting note-taker that runs alongside the Zoom desktop client.
It detects when you're in a Zoom meeting, transcribes your mic and the meeting
audio locally with Whisper, and writes a full transcript plus an AI-generated
summary to timestamped `.txt` files.

It is **not** a published Zoom Marketplace app — it works by capturing audio
locally, since Zoom's live-captions API (RTMS) requires a Business/Enterprise
plan. See `/home/towfiq/.claude/plans/compiled-riding-anchor.md` (or ask Claude)
for the full design.

## Components

- `engine/` — Python background engine: meeting detection, audio capture, VAD,
  Whisper transcription, summarization (Ollama or Claude), file writer, tray
  icon, local status API.
- `dashboard/` — Node.js local web UI for browsing past notes/summaries and
  editing config.

## Status

Milestones 1–11 (scaffolding through dashboard/polish) are implemented.
Milestone 12 -- validating the real Zoom detection/audio-capture code
against an actual live meeting, and tuning debounce thresholds -- is the
one remaining step, and needs a real or test Zoom call to do (see the
design doc).

## Running it (Linux)

```bash
make engine-setup      # create engine/.venv, install the Python engine
make engine-test        # run the offline test suite
make dashboard-setup    # npm install for the dashboard
make engine-run          # start the engine (tray icon, status API, detection loop)
make dashboard-run       # start the dashboard on http://localhost:5173
```

`make engine-run` starts the real engine: it polls for an active Zoom
audio signal via `pactl`, and once a meeting is detected, captures your
mic + Zoom's own output, transcribes them locally with Whisper, and
writes `<timestamp>_meeting-notes.txt` / `<timestamp>_summary.txt` to
`storage_dir` when the meeting ends. A tray icon and the dashboard both
offer a manual Start/Stop override.

To autostart it on login, see `scripts/zoom-note-engine.service`.

## Prerequisites (Linux)

```bash
sudo apt install pulseaudio-utils ffmpeg libportaudio2
```

- [Ollama](https://ollama.com) installed and a model pulled, e.g.:
  ```bash
  ollama pull phi3:3.8b-mini-128k
  ```
  ...if you want local summarization. For Claude API summarization instead,
  set `ANTHROPIC_API_KEY` in your environment.

## macOS / Windows differences (documented, not yet implemented/tested)

This has only been built and tested on Linux so far. Porting the audio
capture layer (`engine/src/zoom_notes_engine/audio/linux_capture.py`) and
detector (`.../detection/linux_detector.py`) would need:

- **macOS**: there's no built-in monitor/loopback source like PipeWire's,
  so capturing Zoom's own output requires a virtual audio device such as
  [BlackHole](https://github.com/ExistentialAudio/BlackHole) routed the
  same way the null-sink/loopback recipe does on Linux. Meeting detection
  would need a macOS-appropriate signal (e.g. Core Audio's active-stream
  APIs) in place of `pactl`.
- **Windows**: WASAPI loopback capture (via `pyaudiowpatch` or `soundcard`)
  can capture system output directly, no virtual device needed. Zoom
  historically runs a separate `CptHost.exe` call-engine process while
  actively in a meeting, which may be a cleaner detection signal than the
  audio-activity heuristic used on Linux.

Both would still slot into the existing `AudioSource`/`AudioSignalSource`
interfaces (`audio/base.py`, `detection/base.py`) -- only the concrete
implementations need platform-specific versions, not the rest of the
pipeline.

## Note on consent

This tool records audio from meetings you're in, including other participants.
Make sure you comply with your jurisdiction's meeting-recording consent
requirements before using it.
