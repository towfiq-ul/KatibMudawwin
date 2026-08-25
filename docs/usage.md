# Usage

## How it works

The engine polls for an active Zoom audio signal via `pactl`. Once a
meeting is detected, it captures your mic and Zoom's own output separately,
transcribes both locally with Whisper, and writes the live transcript to a
fixed `note.txt` at the root of `storage_dir` while the meeting is in
progress. When the meeting ends, that file is moved into its permanent
`notes/<yyyymmdd>/note_<yyyymmdd_hhmmss>.txt` location. Timestamps are
always CST/CDT regardless of the system's local timezone.

The desktop app's tray icon and window both offer a manual Start/Stop
override, independent of automatic detection.

Each meeting's raw mic + Zoom audio is also persisted (never held entirely
in RAM) to `audio/<meeting-id>/mic.wav` and `audio/<meeting-id>/zoom.wav`,
with metadata (paths, timestamps, size) recorded in `db.sqlite` at the root
of `storage_dir`. Both are local-only and gitignored -- raw audio and the
database are never committed.

## Summarizing notes

Summarization is not automatic -- run it on demand, either:

```bash
make summary            # summarize today's notes
make summary 20260821   # summarize a specific day (yyyymmdd)
```

or click **Summarize** in the desktop app's notes browser after opening a
date's folder (calls the engine status API's `POST /summarize`, which does
the same thing).

This (re)writes `notes/<yyyymmdd>/summary_note_<yyyymmdd>.txt` with one
block per meeting that day; re-running it (either way) regenerates the
file rather than duplicating entries.

## Deleting old raw audio

Raw audio is not deleted automatically:

```bash
make retention-sweep
```

Deletes a meeting's raw audio once it's older than `retention.max_age_days`
(default 30 days), or oldest-first once total raw-audio storage exceeds
`retention.max_total_audio_bytes` (default 10 GB). Transcripts and
summaries are never touched by the sweep.

## Running in the background

`make engine-run` / `make desktop-run` start each in the foreground,
blocking the terminal with live log output -- useful while developing. The
engine can also run as a background process:

```bash
make start          # alias for engine-start
make stop            # alias for engine-stop
make engine-start     # start the engine in the background, logs at .run/engine.log
make engine-stop
```

PIDs are tracked in `.run/*.pid`; `engine-stop` first calls the status
API's `/stop` so any in-progress recording is finalized (transcript +
summary written) before the process is killed, rather than cut off
mid-session.

The desktop app isn't backgrounded the same way -- it's a GUI app with its
own tray-resident lifecycle (closing its window hides it to tray; the
tray's Quit item is the real exit). For day-to-day use, install a built
package (see `installation.md`'s "Building packages yourself") rather than
running `make desktop-run`, which is a dev-mode launch.

## Autostart on login

See `../scripts/katib-mudawwin.service` (a systemd --user unit) for
autostarting the engine when you log in.

## Privacy

This tool records audio from meeting participants who have not necessarily
consented to a locally-stored recording. Make sure you comply with your
jurisdiction's meeting-recording consent requirements before using it.
