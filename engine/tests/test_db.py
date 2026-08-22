from katib_mudawwin.storage import db


def _connect(tmp_path):
    return db.connect(db.default_db_path(tmp_path))


def test_default_db_path(tmp_path):
    assert db.default_db_path(tmp_path) == tmp_path / "db.sqlite"


def test_record_and_read_back_meeting(tmp_path):
    conn = _connect(tmp_path)
    db.record_meeting(
        conn,
        meeting_id="m1",
        started_at="2026-08-20T09:00:00",
        ended_at="2026-08-20T09:30:00",
        transcript_path=str(tmp_path / "notes" / "20260820" / "note_20260820_090000.txt"),
        summary_path=str(tmp_path / "notes" / "20260820" / "summary_note_20260820.txt"),
        mic_audio_path=str(tmp_path / "audio" / "m1" / "mic.wav"),
        zoom_audio_path=str(tmp_path / "audio" / "m1" / "zoom.wav"),
        audio_bytes=1234,
    )

    row = conn.execute("SELECT * FROM meetings WHERE id = ?", ("m1",)).fetchone()
    assert row["started_at"] == "2026-08-20T09:00:00"
    assert row["audio_bytes"] == 1234
    assert row["mic_audio_path"].endswith("mic.wav")


def test_list_meetings_with_audio_is_oldest_first_and_excludes_deleted(tmp_path):
    conn = _connect(tmp_path)
    for meeting_id, started_at, audio_bytes in [
        ("newer", "2026-08-20T15:00:00", 100),
        ("oldest", "2026-08-20T09:00:00", 200),
        ("no-audio-left", "2026-08-19T09:00:00", 0),
    ]:
        db.record_meeting(
            conn,
            meeting_id=meeting_id,
            started_at=started_at,
            ended_at=started_at,
            transcript_path="note.txt",
            summary_path="summary.txt",
            mic_audio_path="mic.wav" if audio_bytes else None,
            zoom_audio_path="zoom.wav" if audio_bytes else None,
            audio_bytes=audio_bytes,
        )

    rows = db.list_meetings_with_audio(conn)
    assert [row["id"] for row in rows] == ["oldest", "newer"]


def test_clear_meeting_audio(tmp_path):
    conn = _connect(tmp_path)
    db.record_meeting(
        conn,
        meeting_id="m1",
        started_at="2026-08-20T09:00:00",
        ended_at="2026-08-20T09:30:00",
        transcript_path="note.txt",
        summary_path="summary.txt",
        mic_audio_path="mic.wav",
        zoom_audio_path="zoom.wav",
        audio_bytes=1234,
    )

    db.clear_meeting_audio(conn, "m1")

    row = conn.execute("SELECT * FROM meetings WHERE id = ?", ("m1",)).fetchone()
    assert row["mic_audio_path"] is None
    assert row["zoom_audio_path"] is None
    assert row["audio_bytes"] == 0
    # transcript/summary paths are untouched by clearing audio
    assert row["transcript_path"] == "note.txt"
