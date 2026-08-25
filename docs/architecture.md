# Architecture

## Components

- `engine/` -- Python background engine: meeting detection, audio capture,
  VAD, Whisper transcription, summarization (local Phi-3 or Anthropic API),
  file writer, local status API. Headless -- no UI of its own.
- `desktop/` -- Tauri + Svelte native desktop app: tray icon (Start/Stop
  recording, show window, quit) and a window for browsing past
  notes/summaries and editing config. Talks to the engine over its status
  API and reads/writes `storage_dir`/`config.yaml` directly.

They're separate processes, both required to be running for the app to
work end to end -- see `usage.md`.

## macOS / Windows support (documented, not yet implemented)

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
