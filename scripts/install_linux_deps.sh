#!/usr/bin/env bash
set -euo pipefail

echo "Checking Linux system dependencies for zoom-notes-engine..."

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

if ! command -v ollama >/dev/null 2>&1; then
  echo "Note: ollama not found. Install from https://ollama.com if you want local summarization."
else
  echo "ollama found. Make sure 'ollama serve' is running and a model is pulled, e.g.:"
  echo "  ollama pull phi3:3.8b-mini-128k"
fi
