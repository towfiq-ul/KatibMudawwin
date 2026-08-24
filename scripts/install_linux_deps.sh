#!/usr/bin/env bash
set -uo pipefail

echo "Checking Linux system dependencies for katib-mudawwin..."

any_missing=0

missing=()
command -v pactl >/dev/null 2>&1 || missing+=("pulseaudio-utils")
command -v ffmpeg >/dev/null 2>&1 || missing+=("ffmpeg")
ldconfig -p | grep -q libportaudio.so || missing+=("libportaudio2")

if [ ${#missing[@]} -gt 0 ]; then
  any_missing=1
  echo "Missing packages: ${missing[*]}"
  echo "Install with: sudo apt install ${missing[*]}"
else
  echo "System dependencies OK (pactl, ffmpeg, libportaudio2 found)."
fi

if ! command -v cc >/dev/null 2>&1 && ! command -v gcc >/dev/null 2>&1; then
  echo "Note: no C compiler found. llama-cpp-python (local Phi-3 summarization)"
  echo "  ships prebuilt wheels for most platforms, but if pip has to build it"
  echo "  from source you'll need one: sudo apt install build-essential"
fi

echo ""
echo "Checking desktop/ (Tauri) build dependencies..."

desktop_missing_apt=()
command -v cargo >/dev/null 2>&1 || echo "Note: no Rust toolchain found -- install via https://rustup.rs"
command -v npm >/dev/null 2>&1 || echo "Note: no npm/node.js found -- install via https://nodejs.org"
ldconfig -p | grep -q libwebkit2gtk-4.1 || desktop_missing_apt+=("libwebkit2gtk-4.1-dev")
ldconfig -p | grep -q libgtk-3 || desktop_missing_apt+=("libgtk-3-dev")
ldconfig -p | grep -q libayatana-appindicator3 || desktop_missing_apt+=("libayatana-appindicator3-dev")
ldconfig -p | grep -q librsvg-2 || desktop_missing_apt+=("librsvg2-dev")
command -v pkg-config >/dev/null 2>&1 || desktop_missing_apt+=("pkg-config")
[ -f /usr/include/xdo.h ] || desktop_missing_apt+=("libxdo-dev")
ldconfig -p | grep -q libssl.so || desktop_missing_apt+=("libssl-dev")

if [ ${#desktop_missing_apt[@]} -gt 0 ]; then
  any_missing=1
  echo "Missing desktop build packages: ${desktop_missing_apt[*]}"
  echo "Install with:"
  echo "  sudo apt install libwebkit2gtk-4.1-dev libgtk-3-dev build-essential curl wget file \\"
  echo "    libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev"
else
  echo "Desktop build dependencies OK."
fi

exit "$any_missing"
