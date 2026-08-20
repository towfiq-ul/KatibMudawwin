from pathlib import Path

from katib_mudawwin.config import AppConfig, load_config


def test_defaults_with_no_file(tmp_path):
    config = load_config(tmp_path / "does-not-exist.yaml")
    assert isinstance(config, AppConfig)
    assert config.summarizer.provider == "local"
    assert config.whisper.model_size == "base.en"
    assert config.storage_dir.is_absolute()


def test_partial_override_keeps_other_defaults(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "summarizer:\n  provider: claude\n  claude:\n    model: claude-sonnet-5\n"
    )
    config = load_config(config_path)
    assert config.summarizer.provider == "claude"
    assert config.summarizer.claude.model == "claude-sonnet-5"
    # Untouched sections still fall back to defaults.
    assert config.whisper.model_size == "base.en"
    assert config.audio.sample_rate == 16000


def test_storage_dir_expands_user(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("storage_dir: ~/SomeNotesFolder\n")
    config = load_config(config_path)
    assert "~" not in str(config.storage_dir)
    assert str(config.storage_dir).endswith("SomeNotesFolder")
