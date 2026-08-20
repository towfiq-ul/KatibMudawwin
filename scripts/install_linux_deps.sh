#!/usr/bin/env bash
set -euo pipefail

echo "Checking Linux system dependencies for katib-mudawwin..."

missing=()
command -v pactl >/dev/null 2>&1 || missing+=("pulseaudio-utils")
command -v ffmpeg >/dev/null 2>&1 || missing+=("ffmpeg")
ldconfig -p | grep -q libportaudio.so || missing+=("libportaudio2")

if [ ${#missing[@]} -gt 0 ]; then
  echo "Missing packages: ${missing[*]}"
  echo "Install with: sudo apt install ${missing[*]}"
  exit 1
fi

echo "System dependencies OK (pactl, ffmpeg found)."

if ! python3 -c "import gi" >/dev/null 2>&1; then
  echo "Note: python3-gi not found. The tray icon's click-to-open menu needs"
  echo "  it (plus AppIndicator3), and engine-setup must create the venv with"
  echo "  --system-site-packages to see it. Without it, the tray icon falls"
  echo "  back to a backend with no popup menu -- use the dashboard instead."
  echo "  Install with: sudo apt install python3-gi gir1.2-ayatanaappindicator3-0.1"
fi

if ! command -v cc >/dev/null 2>&1 && ! command -v gcc >/dev/null 2>&1; then
  echo "Note: no C compiler found. llama-cpp-python (local Phi-3 summarization)"
  echo "  ships prebuilt wheels for most platforms, but if pip has to build it"
  echo "  from source you'll need one: sudo apt install build-essential"
fi
