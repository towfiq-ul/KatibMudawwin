from __future__ import annotations

import threading
import time
import webbrowser

import pystray
from PIL import Image, ImageDraw

from katib_mudawwin.branding import ASCII_NAME, CLI_COMMAND
from katib_mudawwin.config import AppConfig
from katib_mudawwin.models import SessionStatus
from katib_mudawwin.session.recorder import SessionRecorder

_MENU_POLL_SECONDS = 2.0


def _make_icon_image(color: str) -> Image.Image:
    image = Image.new("RGB", (64, 64), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, 56, 56), fill=color)
    return image


def build_tray_icon(recorder: SessionRecorder, config: AppConfig) -> pystray.Icon:
    """Minimal tray icon with a manual override -- the dashboard (served on
    config.dashboard.port) remains a fully usable control surface if the
    tray icon doesn't render (pystray can be flaky on some Wayland/GNOME
    setups without the AppIndicator extension).

    Clicking the icon pops this menu -- that requires pystray's AppIndicator
    backend (PyGObject + AppIndicator3/AyatanaAppIndicator3). Its bare X11
    fallback backend (used when those aren't importable, e.g. an isolated
    venv without --system-site-packages) has no popup-menu support at all."""

    def _is_recording(item) -> bool:
        return recorder.state.status == SessionStatus.RECORDING

    def _is_not_recording(item) -> bool:
        return recorder.state.status != SessionStatus.RECORDING

    def on_start(icon, item):
        recorder.force_start()
        icon.update_menu()

    def on_stop(icon, item):
        recorder.force_stop()
        icon.update_menu()

    def on_open_dashboard(icon, item):
        webbrowser.open(f"http://localhost:{config.dashboard.port}")

    def on_exit(icon, item):
        # Finalize any in-progress recording (transcript + summary written)
        # rather than cutting it off, then tear down the whole process --
        # icon.stop() unblocks run() in main(), and since the status API and
        # detection loop threads are daemons, the process exits with them.
        recorder.force_stop()
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Start recording", on_start, visible=_is_not_recording),
        pystray.MenuItem("Stop recording", on_stop, visible=_is_recording),
        pystray.MenuItem("Open dashboard", on_open_dashboard),
        pystray.MenuItem("Exit", on_exit),
    )

    icon = pystray.Icon(
        CLI_COMMAND,
        icon=_make_icon_image("green"),
        title=ASCII_NAME,
        menu=menu,
    )

    def _watch_state() -> None:
        """Most platforms (including AppIndicator) build the native menu
        once and don't re-evaluate visible= on every click, so recorder
        state changes made outside the tray menu -- the dashboard's
        Start/Stop buttons, or Zoom auto-detection -- would otherwise leave
        the tray menu showing stale Start/Stop visibility. Polling and
        calling update_menu() on change keeps it in sync regardless of
        what triggered the state change."""
        last_status = None
        while True:
            time.sleep(_MENU_POLL_SECONDS)
            status = recorder.state.status
            if status != last_status:
                last_status = status
                icon.update_menu()

    threading.Thread(target=_watch_state, daemon=True).start()

    return icon
