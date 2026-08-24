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
  writer, local status API. Headless -- no UI of its own.
- `desktop/` — Tauri + Svelte native desktop app: tray icon (Start/Stop
  recording, show window, quit) and a window for browsing past
  notes/summaries and editing config. Talks to the engine over its status
  API and reads/writes `storage_dir`/`config.yaml` directly.

## Status

Milestones 1–11 (scaffolding through dashboard/polish) are implemented.
Milestone 12 -- validating the real Zoom detection/audio-capture code
against an actual live meeting, and tuning debounce thresholds -- is the
one remaining step, and needs a real or test Zoom call to do. The tray icon
and local web dashboard from that milestone have since been replaced by the
native `desktop/` app.

## Quick install (Linux)

```bash
curl -fsSL https://raw.githubusercontent.com/towfiq-ul/KatibMudawwin/master/install.sh | bash
```

Clones the repo to `~/KatibMudawwin` and runs `make build`. Set
`KM_INSTALL_DIR` to clone elsewhere, or `KM_BRANCH` to install a branch other
than `master`. It always runs under `bash`, regardless of your login shell,
since it's piped straight into `bash`. See `install.sh` for what it does --
it's a thin wrapper around the `make build` below, nothing it can't also be
done by hand.

## Running it (Linux)

```bash
make build              # engine-setup + desktop-setup: install all deps
make engine-test        # run the offline test suite
make engine-run          # start the engine in the foreground (status API, detection loop)
make desktop-run          # start the desktop app in dev mode (window + tray icon)
```

The engine polls for an active Zoom audio signal via `pactl`, and once a
meeting is detected, captures your mic + Zoom's own output, transcribes
them locally with Whisper, and writes the live transcript to a fixed
`note.txt` at the root of `storage_dir` while the meeting is in progress.
When the meeting ends, that file is moved into its permanent
`notes/<yyyymmdd>/note_<yyyymmdd_hhmmss>.txt` location. Timestamps are
always CST/CDT regardless of the system's local timezone. The desktop
app's tray icon and window both offer a manual Start/Stop override.

Summarization is not automatic -- run `make summary` (or `make summary
<yyyymmdd>` for a specific day) to summarize a day's notes on demand. This
(re)writes `notes/<yyyymmdd>/summary_note_<yyyymmdd>.txt` with one block
per meeting that day; re-running it regenerates the file rather than
duplicating entries.

Each meeting's raw mic + Zoom audio is also persisted (never held entirely
in RAM) to `audio/<meeting-id>/mic.wav` and `audio/<meeting-id>/zoom.wav`,
with metadata (paths, timestamps, size) recorded in `db.sqlite` at the
root of `storage_dir`. Both are local-only and gitignored -- raw audio and
the database are never committed. Raw audio is not deleted automatically;
run `make retention-sweep` to delete it once a meeting is older than
`retention.max_age_days` (default 30) or once total raw-audio storage
exceeds `retention.max_total_audio_bytes` (default 10 GB), oldest first.
Transcripts and summaries are never touched by the sweep.

`engine-run`/`desktop-run` start each in the foreground, blocking the
terminal with live log output -- use them while developing. The engine can
also run as a background process:

```bash
make start          # alias for engine-start
make stop            # alias for engine-stop
make engine-start     # start the engine in the background, logs at .run/engine.log
make engine-stop
```

PIDs are tracked in `.run/*.pid`; `engine-stop` first calls the status
API's `/stop` so any in-progress recording is finalized (transcript +
summary written) before the process is killed, rather than cut off mid-session.

The desktop app isn't backgrounded the same way -- it's a GUI app with its
own tray-resident lifecycle (closing its window hides it to tray; the tray's
Quit item is the real exit), so `make desktop-run` is a dev-mode launch, and
production use is the built `.deb`/AppImage (`cd desktop && npm run tauri
build`) launched like any other installed app.

```bash
make retention-sweep    # delete raw audio past the age/size retention caps
```

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

`desktop/` additionally needs a Rust toolchain ([rustup.rs](https://rustup.rs)),
Node/npm, and Tauri's Linux build dependencies:

```bash
sudo apt install libwebkit2gtk-4.1-dev libgtk-3-dev build-essential curl wget file \
  libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev
```

`make deps-linux` checks for all of the above.

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

This tool records audio from meetings you're in, including other
participants, and -- unlike earlier versions -- now persists that raw
audio to disk (see above) rather than discarding it after transcription.
Make sure you comply with your jurisdiction's meeting-recording consent
requirements before using it.
