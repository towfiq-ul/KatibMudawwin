# KātibMudawwin

A local, personal meeting note-taker that runs alongside the Zoom desktop client.
It detects when you're in a Zoom meeting, transcribes your mic and the meeting
audio locally with Whisper, and writes a full transcript plus an AI-generated
summary to timestamped `.txt` files.

It is **not** a published Zoom Marketplace app — it works by capturing audio
locally, since Zoom's live-captions API (RTMS) requires a Business/Enterprise
plan.

## Components

- `engine/` — Python background engine: meeting detection, audio capture, VAD,
  Whisper transcription, summarization (local Phi-3 or Anthropic API), file
  writer, tray icon, local status API.
- `dashboard/` — Node.js local web UI for browsing past notes/summaries and
  editing config.

## Status

Milestones 1–11 (scaffolding through dashboard/polish) are implemented.
Milestone 12 -- validating the real Zoom detection/audio-capture code
against an actual live meeting, and tuning debounce thresholds -- is the
one remaining step, and needs a real or test Zoom call to do.

## Running it (Linux)

```bash
make build              # engine-setup + dashboard-setup: install all deps
make engine-test        # run the offline test suite
make engine-run          # start the engine in the foreground (tray icon, status API, detection loop)
make dashboard-run       # start the dashboard in the foreground on http://localhost:5173
```

The engine polls for an active Zoom audio signal via `pactl`, and once a
meeting is detected, captures your mic + Zoom's own output, transcribes
them locally with Whisper, and writes the live transcript to a fixed
`note.txt` at the root of `storage_dir` while the meeting is in progress.
When the meeting ends, that file is moved into its permanent
`notes/<yyyymmdd>/note_<yyyymmdd_hhmmss>.txt` location. Timestamps are
always CST/CDT regardless of the system's local timezone. A tray icon and
the dashboard both offer a manual Start/Stop override.

Summarization is not automatic -- run `make summary` (or `make summary
<yyyymmdd>` for a specific day) to summarize a day's notes on demand. This
(re)writes `notes/<yyyymmdd>/summary_note_<yyyymmdd>.txt` with one block
per meeting that day; re-running it regenerates the file rather than
duplicating entries.

`-run` starts each service in the foreground, blocking the terminal
with its live log output -- use it while developing. To run them as
background processes instead:

```bash
make start          # engine-start + dashboard-start
make stop            # engine-stop + dashboard-stop
make engine-start     # just the engine, logs at .run/engine.log
make engine-stop
make dashboard-start   # just the dashboard, logs at .run/dashboard.log
make dashboard-stop
```

PIDs are tracked in `.run/*.pid`; `engine-stop` first calls the status
API's `/stop` so any in-progress recording is finalized (transcript +
summary written) before the process is killed, rather than cut off mid-session.

To autostart it on login, see `scripts/katib-mudawwin.service`.

## Prerequisites (Linux)

```bash
sudo apt install pulseaudio-utils ffmpeg libportaudio2
```

Summarization defaults to a local Phi-3 model, running in-process via
llama-cpp-python -- no separate service to install or start. The GGUF
weights (~2.3GB) download once from Hugging Face Hub and are cached the
first time a meeting is summarized. For Anthropic API summarization instead,
set `summarizer.provider: anthropic` in your config and set
`ANTHROPIC_API_KEY` in your environment.

## macOS / Windows differences (documented, not yet implemented/tested)

This has only been built and tested on Linux so far. Porting the audio
capture layer (`engine/src/katib_mudawwin/audio/linux_capture.py`) and
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
