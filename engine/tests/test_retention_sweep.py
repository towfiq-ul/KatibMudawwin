from datetime import datetime, timedelta

from katib_mudawwin.retention_sweep import run_sweep
from katib_mudawwin.storage import db


def _record(conn, tmp_path, meeting_id, started_at, audio_bytes):
    audio_dir = tmp_path / "audio" / meeting_id
    audio_dir.mkdir(parents=True)
    mic_path = audio_dir / "mic.wav"
    zoom_path = audio_dir / "zoom.wav"
    mic_path.write_bytes(b"0" * (audio_bytes // 2))
    zoom_path.write_bytes(b"0" * (audio_bytes - audio_bytes // 2))

    db.record_meeting(
        conn,
        meeting_id=meeting_id,
        started_at=started_at.isoformat(),
        ended_at=started_at.isoformat(),
        transcript_path=str(tmp_path / "notes" / "note.txt"),
        summary_path=str(tmp_path / "notes" / "summary.txt"),
        mic_audio_path=str(mic_path),
        zoom_audio_path=str(zoom_path),
        audio_bytes=audio_bytes,
    )
    return mic_path, zoom_path


def test_deletes_meetings_older_than_max_age(tmp_path):
    conn = db.connect(db.default_db_path(tmp_path))
    now = datetime.now()

    old_mic, old_zoom = _record(conn, tmp_path, "old", now - timedelta(days=40), 100)
    new_mic, new_zoom = _record(conn, tmp_path, "new", now - timedelta(days=1), 100)

    deleted = run_sweep(conn, max_age_days=30, max_total_bytes=10**12)

    assert deleted == ["old"]
    assert not old_mic.exists()
    assert not old_zoom.exists()
    assert not old_mic.parent.exists()  # empty per-meeting dir removed
    assert new_mic.exists()
    assert new_zoom.exists()

    row = conn.execute("SELECT * FROM meetings WHERE id = 'old'").fetchone()
    assert row["mic_audio_path"] is None
    assert row["audio_bytes"] == 0


def test_deletes_oldest_first_until_under_total_cap(tmp_path):
    conn = db.connect(db.default_db_path(tmp_path))
    now = datetime.now()

    # All well within the age cap -- only the size cap should trigger.
    _record(conn, tmp_path, "oldest", now - timedelta(days=2), 500)
    mid_mic, mid_zoom = _record(conn, tmp_path, "mid", now - timedelta(days=1, hours=12), 500)
    newest_mic, newest_zoom = _record(conn, tmp_path, "newest", now - timedelta(hours=1), 500)

    # Total is 1500; cap is 900 -- deleting "oldest" alone leaves 1000,
    # still over the cap, so "mid" must go too, leaving 500 (under 900).
    deleted = run_sweep(conn, max_age_days=30, max_total_bytes=900)

    assert deleted == ["oldest", "mid"]
    assert not mid_mic.exists()
    assert not mid_zoom.exists()
    assert newest_mic.exists()
    assert newest_zoom.exists()


def test_leaves_everything_when_within_caps(tmp_path):
    conn = db.connect(db.default_db_path(tmp_path))
    now = datetime.now()
    mic, zoom = _record(conn, tmp_path, "recent", now - timedelta(days=1), 100)

    deleted = run_sweep(conn, max_age_days=30, max_total_bytes=10**12)

    assert deleted == []
    assert mic.exists()
    assert zoom.exists()


def test_never_touches_transcript_or_summary_files(tmp_path):
    conn = db.connect(db.default_db_path(tmp_path))
    now = datetime.now()
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    transcript = notes_dir / "note.txt"
    summary = notes_dir / "summary.txt"
    transcript.write_text("transcript")
    summary.write_text("summary")

    _record(conn, tmp_path, "old", now - timedelta(days=40), 100)
    run_sweep(conn, max_age_days=30, max_total_bytes=10**12)

    assert transcript.exists()
    assert summary.exists()
