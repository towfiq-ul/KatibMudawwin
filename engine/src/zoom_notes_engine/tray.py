from __future__ import annotations

import webbrowser

import pystray
from PIL import Image, ImageDraw

from zoom_notes_engine.config import AppConfig
from zoom_notes_engine.session.recorder import SessionRecorder


def _make_icon_image(color: str) -> Image.Image:
    image = Image.new("RGB", (64, 64), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, 56, 56), fill=color)
    return image


def build_tray_icon(recorder: SessionRecorder, config: AppConfig) -> pystray.Icon:
    """Minimal tray icon with a manual override -- the dashboard (served on
    config.dashboard.port) remains a fully usable control surface if the
    tray icon doesn't render (pystray can be flaky on some Wayland/GNOME
    setups without the AppIndicator extension)."""

    def on_start(icon, item):
        recorder.force_start()

    def on_stop(icon, item):
        recorder.force_stop()

    def on_open_dashboard(icon, item):
        webbrowser.open(f"http://localhost:{config.dashboard.port}")

    def on_quit(icon, item):
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Start recording", on_start),
        pystray.MenuItem("Stop recording", on_stop),
        pystray.MenuItem("Open dashboard", on_open_dashboard),
        pystray.MenuItem("Quit", on_quit),
    )

    return pystray.Icon(
        "zoom-notes-engine",
        icon=_make_icon_image("green"),
        title="Zoom Notes Engine",
        menu=menu,
    )
