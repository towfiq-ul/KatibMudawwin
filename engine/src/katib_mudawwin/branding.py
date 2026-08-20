from __future__ import annotations

import json
from pathlib import Path

# Single source of truth for the product name, shared with the dashboard via
# branding.json at the repo root -- see dashboard/src/lib/branding.js.
_BRANDING_PATH = Path(__file__).resolve().parents[3] / "branding.json"


def _load() -> dict:
    try:
        with open(_BRANDING_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


_branding = _load()

DISPLAY_NAME: str = _branding.get("displayName", "KātibMudawwin")
# X11's WM_NAME property is Latin-1 (STRING type), which can't hold the
# macron in DISPLAY_NAME -- pystray's Xorg backend crashes on that encode.
# Use this ASCII form anywhere a window/tray title needs to survive X11.
ASCII_NAME: str = _branding.get("asciiName", "Katib Mudawwin")
CONFIG_DIR_NAME: str = _branding.get("configDirName", "katib-mudawwin")
CLI_COMMAND: str = _branding.get("cliCommand", "katib-mudawwin")
