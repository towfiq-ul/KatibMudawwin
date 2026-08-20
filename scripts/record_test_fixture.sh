#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="$(cd "$(dirname "$0")/.." && pwd)/engine/tests/fixtures"
OUT="$OUT_DIR/sample_meeting.wav"
mkdir -p "$OUT_DIR"

echo "This records a ~15s mono 16kHz clip used as a Whisper test fixture."
echo "It does NOT involve Zoom -- just your microphone."
echo ""
echo "When recording starts, please say clearly:"
echo '  "This is a test of the meeting transcription pipeline. Testing one two three."'
echo ""
read -r -p "Press Enter to start recording (15 seconds)... " _

arecord -f S16_LE -r 16000 -c 1 -d 15 "$OUT"

echo "Saved to $OUT"
