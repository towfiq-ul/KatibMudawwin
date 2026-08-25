# PRD: KātibMudawwin — Local Zoom Meeting Note-Taker

**Version:** 3.0 (refined against the actual codebase — supersedes the v2.0
draft, which described a different product: manual multi-session capture,
Tauri UI, and full diarization/SQLite from day one. See §5 for what changed
and why.)
**Target Platform:** Linux (primary, implemented); macOS/Windows documented
but not implemented.
**Product Type:** Local-first background service + local web dashboard.

## 1. Executive Summary

KātibMudawwin is a personal, local Zoom meeting note-taker. It runs
alongside the Zoom desktop client, automatically detects when a Zoom
meeting is active, captures the user's microphone and Zoom's own output
independently, transcribes both locally with Whisper, and writes a
timestamped transcript to disk. Summarization is a separate, on-demand
step. It is not a Zoom Marketplace app and does not join meetings as a
bot — everything is local audio capture from the user's own machine.

Two components:
- `engine/` — Python background service: meeting detection, audio capture,
  VAD, Whisper transcription, on-demand summarization, file writer, tray
  icon, local status API (Flask, port 8765).
- `dashboard/` — Node/Express local web UI (port 5173) for browsing past
  notes/summaries and editing the engine's `config.yaml`.

## 2. Current State (What Is Actually Implemented)

This section is the source of truth for "what exists today" — it
describes the real pipeline in `engine/src/katib_mudawwin/`, not an
aspirational design.

### 2.1 Detection & recording model

- `MeetingDetector` polls an `AudioSignalSource` (on Linux, `pactl`-based —
  `linux_detector.py`) on an interval (`detection.poll_interval_seconds`,
  default 5s), debounced on both start (`start_debounce_seconds`, default
  5s) and end (`end_debounce_seconds`, default 20s) to avoid flapping on
  brief silence.
- One meeting = one continuous recording from `meeting_started` to
  `meeting_ended`. There is **no manual multi-session model** — the
  detector owns the session boundary. A manual override
  (`force_start()`/`force_stop()`, exposed via the tray icon, the
  dashboard, and the status API's `/start`/`/stop`) can start or end a
  session directly, guarded by the same lock the poll loop uses so the two
  never race.

### 2.2 Audio capture & transcription

- Two independent streams are captured per meeting: the microphone
  (`AudioSourceLabel.ME`) and Zoom's loopback output via a null sink
  (`AudioSourceLabel.OTHERS`, `audio.zoom_null_sink_name`, default
  `zoom_capture`).
- Each stream runs its own pipeline: `AudioSource -> VAD segmenter ->
  Whisper -> TranscriptWriter`. VAD (`webrtcvad`, tunable
  `aggressiveness`/`min_silence_ms`/`max_utterance_seconds`) buffers frames
  into utterances; each completed utterance is transcribed independently
  by `WhisperEngine` (`faster-whisper`, default model `base.en`, CPU/int8
  by default, configurable).
- **No raw audio is currently persisted.** Frames and utterances are held
  in memory only long enough to be transcribed, then discarded. Only the
  resulting text lines are written to disk.
- "Me" vs. "Others" is a binary label from *which capture stream* the
  audio came from — there is no diarization among multiple remote
  speakers today.

### 2.3 Transcript storage

- While recording, entries are appended live to a fixed working file,
  `storage_dir/note.txt`, flushed and `fsync`'d after every write.
- On meeting end, that file is moved (not copied) to its permanent
  location: `storage_dir/notes/<yyyymmdd>/note_<yyyymmdd_hhmmss>.txt`.
  Timestamps in filenames and transcript lines are always CST/CDT
  (`America/Chicago`), regardless of the system's local timezone.
- If the engine crashes before finalization, the unfinalized transcript at
  `note.txt` is lost (the next meeting's writer truncates rather than
  appends, so it won't corrupt the next meeting — but the prior one isn't
  recovered).

### 2.4 Summarization

- Not automatic. Run `make summary [yyyymmdd]` (`summarize_notes.py`) to
  (re)generate `storage_dir/notes/<date>/summary_note_<date>.txt`, one
  block per `note_*.txt` found for that date. Re-running regenerates the
  whole file rather than appending, so it's idempotent.
- Provider is selected by `summarizer.provider` in config: `local`
  (Phi-3-mini-4k-instruct GGUF via `llama-cpp-python`, in-process, weights
  lazily downloaded/cached from Hugging Face Hub on first use) or
  `anthropic` (Anthropic SDK, needs `ANTHROPIC_API_KEY` or
  `summarizer.anthropic.api_key` in config).
- The prompt asks for key discussion points, decisions, and action items,
  with an instruction to only use information present in the transcript.
  There is **no chunking** of long transcripts today — the whole day's
  transcript text is sent in one call per meeting, which is a real risk
  for very long meetings against small local-model context windows
  (`local.n_ctx`, default 4096).

### 2.5 Config, API, UI

- `AppConfig` (Pydantic) loads from an OS-appropriate path (
  `~/.config/katib-mudawwin/config.yaml` on Linux), missing file/fields
  fall back to defaults. `ConfigWatcher` polls the file's mtime so the
  engine picks up dashboard-driven edits without a restart.
- Flask status API (`status_api.py`), default `127.0.0.1:8765`:
  `GET /health`, `GET /status`, `POST /start`, `POST /stop`.
- Tray icon (`pystray`, needs `--system-site-packages` for
  PyGObject/AppIndicator3) provides a manual Start/Stop and mirrors
  status.
- Dashboard is a plain Express app, no build step: `notes.js` (reads
  transcript/summary files from `storage_dir`), `config.js`
  (reads/writes the engine's `config.yaml`), `engine.js` (proxies to the
  status API), `branding.js` (serves `branding.json`).
- `default_storage_dir()`/`default_config_path()` in `config.py` must stay
  in sync with their JS equivalents in `dashboard/src/lib/config.js` — a
  mismatch means the dashboard reads a different directory than the
  engine writes to.

### 2.6 Testing

- `engine/tests/` is an offline pytest suite exercising the pipeline
  against `fake_signal_source.py`/`file_playback_source.py` fixtures, not
  real `pactl`/Zoom. Milestone 12 (real-meeting validation — mic-leak fix,
  VAD retuning) has already landed per recent commits; update `README.md`'s
  "Status" section if it still lists this as outstanding.

## 3. Product Goals (Current)

### Must hold
- No Zoom bot, no host privileges, no control of Zoom itself.
- Local-first: audio and transcripts never leave the machine by default;
  cloud summarization is opt-in and explicit.
- Recording state is always visible (tray icon + dashboard).
- A manual override to start/stop is always available, independent of
  automatic detection.
- The transcript is never silently lost without at least a logged error —
  summarization failures must not lose the transcript (already true today:
  see `SessionRecorder`/`summarize_notes.py` — summarization errors are
  logged, never raised over a good transcript).

### Secondary (already true or in progress)
- Configurable Whisper model size for CPU-only systems.
- Config hot-reload without restarting the engine.

## 4. Non-Goals / Explicitly Descoped

- **Manual multi-session recording within one meeting** (the v2.0 draft's
  core differentiator — user-controlled Start/Stop segments merged
  chronologically). Decided in this refinement: **not pursued**. Automatic
  detection stays the primary session boundary; the existing force-start/
  stop override is sufficient. Revisit only if automatic detection proves
  unreliable in practice.
- Zoom bot / Marketplace app / RTMS live captions.
- Automatically recording every meeting without the visible-recording
  guarantee.
- Covert recording or bypassing organizational recording policies.

## 5. Decisions Made In This Refinement

The v2.0 draft proposed a much larger rewrite (Tauri UI, SQLite,
multi-session capture, full diarization + voiceprints, all from an
initial version). Reconciling that draft against the actual codebase
surfaced four real fork points, resolved as follows:

| Area | Decision |
|---|---|
| Recording model | **Keep automatic detection** (current). Manual multi-session is descoped (§4). |
| Storage | **Add** a SQLite metadata layer and persisted raw audio, under a retention cap (§6.1, §6.2). |
| UI | **Keep** tray + Express dashboard. Tauri desktop app is a documented **future** item (§10), not committed. |
| Diarization | **Add** pyannote-based diarization + voiceprint enrollment for the Others stream (§6.3). |

## 6. Planned Next Features

These are the two concrete, approved additions to build next. Both are a
real architecture change — the current pipeline discards audio after
transcription and has no database.

### 6.1 Raw Audio Persistence

- Persist each stream per meeting: `audio/<meeting-id>/mic.wav`,
  `audio/<meeting-id>/zoom.wav`. A mixed track is not required by anything
  decided here; add it later only if a concrete need (e.g. playback)
  shows up.
- Written alongside the existing live VAD/Whisper pipeline — raw capture
  and live transcription are independent consumers of the same audio
  frames, so persistence must not add latency that causes frame drops.
- Raw audio must never be committed to git. `*.wav` and `ZoomNotes/` are
  already gitignored at the repo root; if `storage_dir` moves or changes,
  keep that invariant.

### 6.2 SQLite Metadata Layer + Retention

- A trimmed schema matching the **single-session-per-meeting** model
  (no `recording_sessions` table — see §9 for the actual schema). SQLite
  holds metadata only — transcript/summary text stays in
  `notes/<date>/*.txt` as today; no change to `TranscriptWriter`'s output
  format.
- Retention sweep over persisted raw audio only (not transcripts/summaries,
  which stay indefinitely — they're tiny by comparison):
  - Delete a meeting's raw audio once it is **older than 30 days**, or
  - Delete oldest-first once **total raw-audio storage (summed across all
    meetings' `audio/<meeting-id>/` directories) exceeds 10 GB**,
  whichever triggers first.
- **Manual command**, mirroring `make summary`: e.g. `make retention-sweep`
  / `python -m katib_mudawwin.retention_sweep`. Not run automatically —
  consistent with keeping meeting-end and engine-stop fast and
  side-effect-free, the same reasoning that already keeps summarization
  on-demand.

### 6.3 Speaker Diarization + Voiceprint Enrollment

- Runs as a **post-meeting, on-demand** stage against the persisted
  `zoom.wav` (needs §6.1) — diarization models want the full audio, not
  per-utterance streaming chunks, so this cannot run live in the current
  VAD pipeline without a redesign, and none is planned. Invoked like
  summarization, e.g. `make diarize [yyyymmdd]` /
  `python -m katib_mudawwin.diarize_notes` — never blocks meeting-end or
  `force_stop()`.
- Distinguishes multiple remote speakers within the Others stream
  ("Speaker 1", "Speaker 2", ...) instead of one flat "Others" label. "Me"
  stays identified directly from the mic stream, unchanged.
- Voiceprint enrollment lives in the **dashboard** as a new page/route
  (a "Speakers" page alongside the existing notes-browsing and config
  pages), backed by a new dashboard route + engine-side storage under
  `speakers/` (§8). Explicit, user-initiated recording of a voice sample
  per person, stored locally, deletable, never uploaded. Future meetings
  match enrolled voiceprints to auto-label recurring speakers; unmatched
  speakers stay as "Speaker N" until renamed.
- Candidate library: `pyannote.audio`. Check its license and model-weight
  license (some pyannote pipelines gate weights behind a Hugging Face
  license acceptance) before depending on it.

## 7. Revised Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    Tray icon + Dashboard                     │
│              (manual override, config, browsing)             │
└───────────────────────────┬───────────────────────────────────┘
                            │ status API (Flask)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    MeetingDetector (pactl)                    │
│              automatic start/end, debounced                   │
└───────────────────────────┬───────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     SessionRecorder                            │
│                                                                 │
│  Mic  ──→ VAD segmenter ──→ Whisper ──→ TranscriptWriter       │
│  Zoom ──→ VAD segmenter ──→ Whisper ──→ TranscriptWriter       │
│   │                                                             │
│   └──→ [NEW] raw WAV writer ──→ audio/<meeting-id>/*.wav       │
└───────────────────────────┬───────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              [NEW] Post-meeting diarization                   │
│         pyannote over zoom.wav → speaker labels                │
│         voiceprint matching → recurring speaker names          │
└───────────────────────────┬───────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│         Transcript (notes/<date>/note_*.txt) + [NEW] SQLite    │
└───────────────────────────┬───────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│        On-demand summarization (make summary) — unchanged      │
└─────────────────────────────────────────────────────────────┘
```

## 8. Storage Layout (Revised)

```text
<storage_dir>/                      (default ~/ZoomNotes on Linux)
├── note.txt                        # live working transcript (current meeting)
├── notes/
│   └── <yyyymmdd>/
│       ├── note_<yyyymmdd_hhmmss>.txt
│       └── summary_note_<yyyymmdd>.txt
├── audio/                          # [NEW] gitignored, retention-capped
│   └── <meeting-id>/
│       ├── mic.wav
│       └── zoom.wav
├── speakers/                       # [NEW] enrolled voiceprints
│   └── <speaker-id>.wav
└── db.sqlite                       # [NEW]
```

## 9. Database Schema (Trimmed To The Actual Model)

No `recording_sessions` table — a meeting *is* the session.

```sql
CREATE TABLE meetings (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    transcript_path TEXT NOT NULL,
    summary_path TEXT,
    mic_audio_path TEXT,
    zoom_audio_path TEXT,
    audio_bytes INTEGER,             -- for the retention sweep
    diarization_status TEXT          -- pending | done | failed
);

CREATE TABLE speakers (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    voiceprint_path TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE meeting_speakers (      -- which enrolled speaker was
    meeting_id TEXT NOT NULL,        -- matched to which diarized label
    diarized_label TEXT NOT NULL,    -- e.g. "Speaker 1"
    speaker_id TEXT,                 -- NULL until matched/named
    FOREIGN KEY (meeting_id) REFERENCES meetings(id),
    FOREIGN KEY (speaker_id) REFERENCES speakers(id)
);
```

## 10. Future / Not Committed

Kept as documented roadmap items, not scheduled:
- **Tauri + React desktop app**, replacing tray + web dashboard with a
  native window. Decided in this refinement to keep this as future scope,
  not build now (tray + Express is lighter for a solo local tool — no
  Rust toolchain, no bundling step, already working).
- Transcript/meeting search.
- Export formats beyond the current `.txt` (`.md`, `.json`, `.srt`, PDF
  notes).
- Global hotkey for manual start/stop.
- Automatic session/silence segmentation (superseded by §4's decision, but
  could resurface if automatic detection needs finer control).
- Cross-meeting RAG / semantic search.
- Calendar/Jira/Slack/Notion integrations.
- macOS (BlackHole-based loopback) / Windows (WASAPI loopback) ports —
  interfaces (`audio/base.py`, `detection/base.py`) already support this;
  only concrete implementations are missing.

## 11. Privacy & Security

- Audio and transcripts are local by default; cloud summarization
  (Anthropic) is opt-in via config.
- Recording state must stay visible (tray + dashboard) at all times.
- **Current gap:** `AnthropicConfig.api_key` can hold a literal key in
  `config.yaml` in plaintext (masked only in the dashboard's display, not
  in storage). Prefer `api_key_env`. OS keyring integration is not
  implemented — flagged as a future improvement, not a current guarantee.
- New with §6.1/§6.3: raw audio and voiceprints are a new category of
  sensitive local data. Both must be deletable by the user and excluded
  from git (already true for `*.wav` via `.gitignore`).
- This tool records audio from meeting participants who have not
  necessarily consented to a locally-stored, diarized, speaker-identified
  recording. This is a materially bigger privacy surface than today's
  discard-after-transcription behavior — the user remains responsible for
  applicable consent laws and org policies, and this should be called out
  more prominently once §6.1/§6.3 ship (e.g. a one-time warning on first
  enabling raw audio persistence).

## 12. Roadmap

### Done
- Milestones 1–12 per `README.md`/`CLAUDE.md`: detection, dual-stream
  capture, VAD, Whisper transcription, file-based transcript storage,
  on-demand summarization (local + Anthropic), status API, tray, dashboard,
  config hot-reload, real-meeting validation.

### Next
- Milestone 13: raw audio persistence (§6.1) + SQLite metadata layer
  (§6.2, §9) + retention sweep.
- Milestone 14: pyannote diarization + voiceprint enrollment (§6.3),
  built on top of Milestone 13's stored audio.

### Future (§10)
- Tauri desktop app, search, export formats, hotkeys, RAG, integrations,
  macOS/Windows ports.

## 13. Resolved Questions

All open questions from the previous draft are now settled:

1. **Retention sweep trigger:** manual command (`make retention-sweep`),
   not automatic — see §6.2.
2. **Diarization timing:** on-demand (`make diarize [date]`), like
   summarization — see §6.3.
3. **Voiceprint enrollment UI:** dashboard, new "Speakers" page/route —
   see §6.3.
4. **10 GB cap scope:** total across all meetings' raw audio — see §6.2.
5. **Transcript storage:** stays file-based (`notes/<date>/*.txt`); SQLite
   is metadata-only — see §6.2, §9.
