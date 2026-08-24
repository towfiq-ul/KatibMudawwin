from __future__ import annotations

import json
from pathlib import Path

# Single source of truth for the product name, shared with the desktop app
# via branding.json at the repo root -- see
# desktop/src-tauri/src/branding.rs.
_BRANDING_PATH = Path(__file__).resolve().parents[3] / "branding.json"


def _load() -> dict:
    try:
        with open(_BRANDING_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


_branding = _load()

DISPLAY_NAME: str = _branding.get("displayName", "KātibMudawwin")
CONFIG_DIR_NAME: str = _branding.get("configDirName", "katib-mudawwin")
