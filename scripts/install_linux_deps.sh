#!/usr/bin/env bash
set -uo pipefail

# Checks (and, unless KM_SKIP_APT_INSTALL=1, installs via apt) the system
# packages katib-mudawwin's engine and desktop/ (Tauri) build need. Debian/
# Ubuntu only (uses apt-get) -- on other distros, install the packages named
# below with your package manager instead.
#
# Desktop build deps are checked with `pkg-config`, not `ldconfig`: a -dev
# package's headers/.pc file can be missing even when a same-named runtime
# .so is already on the system (e.g. pulled in by an unrelated package) --
# ldconfig alone would report a false "OK" and only fail later, deep into a
# `cargo build`.

echo "Checking Linux system dependencies for katib-mudawwin..."

missing=()
command -v pactl >/dev/null 2>&1 || missing+=("pulseaudio-utils")
command -v ffmpeg >/dev/null 2>&1 || missing+=("ffmpeg")
ldconfig -p | grep -q libportaudio.so || missing+=("libportaudio2")

if ! command -v cc >/dev/null 2>&1 && ! command -v gcc >/dev/null 2>&1; then
  # llama-cpp-python (local Phi-3 summarization) ships prebuilt wheels for
  # most platforms, but needs a compiler if pip has to build it from source.
  missing+=("build-essential")
fi

echo ""
echo "Checking desktop/ (Tauri) build dependencies..."

command -v cargo >/dev/null 2>&1 || echo "Note: no Rust toolchain found -- install via https://rustup.rs"
command -v npm >/dev/null 2>&1 || echo "Note: no npm/node.js found -- install via https://nodejs.org"

command -v pkg-config >/dev/null 2>&1 || missing+=("pkg-config")
if command -v pkg-config >/dev/null 2>&1; then
  pkg-config --exists webkit2gtk-4.1 || missing+=("libwebkit2gtk-4.1-dev")
  pkg-config --exists gtk+-3.0 || missing+=("libgtk-3-dev")
  pkg-config --exists ayatana-appindicator3-0.1 || missing+=("libayatana-appindicator3-dev")
  pkg-config --exists librsvg-2.0 || missing+=("librsvg2-dev")
  pkg-config --exists openssl || missing+=("libssl-dev")
fi
[ -f /usr/include/xdo.h ] || missing+=("libxdo-dev")

if [ ${#missing[@]} -eq 0 ]; then
  echo ""
  echo "All system dependencies OK."
  exit 0
fi

echo ""
echo "Missing packages: ${missing[*]}"

if [ "${KM_SKIP_APT_INSTALL:-0}" = "1" ]; then
  echo "Install with: sudo apt install ${missing[*]}"
  exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "apt-get not found -- install the packages above with your distro's package manager." >&2
  exit 1
fi

echo "Installing via apt (sudo may prompt for your password)..."
sudo apt-get update && sudo apt-get install -y "${missing[@]}"
