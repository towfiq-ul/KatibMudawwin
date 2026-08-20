from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field, field_validator


# Keep these two functions in sync with defaultStorageDir() /
# defaultConfigPath() in dashboard/src/lib/config.js -- if the two diverge,
# the dashboard can end up reading a different directory than the engine
# writes to, with meetings recorded but never listed.
def default_storage_dir() -> Path:
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Documents" / "ZoomNotes"
    if system == "Windows":
        return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "ZoomNotes"
    return Path.home() / "ZoomNotes"


def default_config_path() -> Path:
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("APPDATA", str(Path.home())))
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    return base / "zoom-note-taker" / "config.yaml"


class DetectionConfig(BaseModel):
    poll_interval_seconds: float = 5
    start_debounce_seconds: float = 5
    end_debounce_seconds: float = 20
    zoom_process_hint: str = "zoom"


class AudioConfig(BaseModel):
    sample_rate: int = 16000
    mic_device: Optional[str] = None
    zoom_null_sink_name: str = "zoom_capture"


class VadConfig(BaseModel):
    aggressiveness: int = 2
    min_silence_ms: int = 700
    max_utterance_seconds: float = 30


class WhisperConfig(BaseModel):
    model_size: str = "base.en"
    device: str = "cpu"
    compute_type: str = "int8"


class OllamaConfig(BaseModel):
    base_url: str = "http://localhost:11434"
    model: str = "phi3:3.8b-mini-128k"
    # Ollama caps the context window per-model (often 2k-4k) regardless of what
    # the model can theoretically handle, unless told otherwise -- this keeps
    # most full meeting transcripts from being silently truncated.
    num_ctx: int = 16384


class ClaudeConfig(BaseModel):
    model: str = "claude-sonnet-5"
    api_key_env: str = "ANTHROPIC_API_KEY"
    # Optional: paste a literal key here instead of using an env var. Takes
    # precedence over api_key_env when set. The dashboard masks this field
    # when displaying config, but it is still stored in plaintext in
    # config.yaml -- prefer api_key_env unless you specifically want this.
    api_key: Optional[str] = None


class SummarizerConfig(BaseModel):
    provider: Literal["ollama", "claude"] = "ollama"
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    claude: ClaudeConfig = Field(default_factory=ClaudeConfig)


class ServerConfig(BaseModel):
    status_api_host: str = "127.0.0.1"
    status_api_port: int = 8765


class DashboardConfig(BaseModel):
    port: int = 5173


class AppConfig(BaseModel):
    storage_dir: Path = Field(default_factory=default_storage_dir)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    vad: VadConfig = Field(default_factory=VadConfig)
    whisper: WhisperConfig = Field(default_factory=WhisperConfig)
    summarizer: SummarizerConfig = Field(default_factory=SummarizerConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)

    @field_validator("storage_dir", mode="before")
    @classmethod
    def _expand_storage_dir(cls, v: object) -> Path:
        return Path(str(v)).expanduser()


def load_config(path: Optional[Path] = None) -> AppConfig:
    """Loads config from `path` (or the OS-appropriate default location).
    Missing file -> defaults. Fields omitted in the file -> their defaults."""
    config_path = path or default_config_path()
    if not config_path.exists():
        return AppConfig()
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return AppConfig.model_validate(raw)


class ConfigWatcher:
    """Polls the config file's mtime and reloads when it changes, so the
    engine can pick up edits made through the dashboard without restarting."""

    def __init__(self, path: Optional[Path] = None):
        self.path = path or default_config_path()
        self.config = load_config(self.path)
        self._mtime: Optional[float] = (
            self.path.stat().st_mtime if self.path.exists() else None
        )

    def poll(self) -> bool:
        """Returns True if the config file changed and was reloaded."""
        if not self.path.exists():
            return False
        mtime = self.path.stat().st_mtime
        if self._mtime is not None and mtime == self._mtime:
            return False
        self._mtime = mtime
        self.config = load_config(self.path)
        return True
