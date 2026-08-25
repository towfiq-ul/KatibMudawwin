#!/usr/bin/env bash
set -uo pipefail

# Report whether the engine status API is up. (Local summarization runs
# in-process in the engine -- no separate service to check. The desktop app
# is a GUI process, not a backgroundable service with an HTTP health
# endpoint -- see Makefile's desktop-run for how to launch it.) Reads the
# actual host/port from the engine config when the venv is set up;
# otherwise falls back to the documented default.

VENV_PYTHON="engine/.venv/bin/python"
CONFIG_VALS=""
if [ -x "$VENV_PYTHON" ]; then
  CONFIG_VALS=$("$VENV_PYTHON" -c "
from katib_mudawwin.config import load_config
c = load_config()
print(c.server.status_api_host, c.server.status_api_port)
" 2>/dev/null)
fi

if [ -n "$CONFIG_VALS" ]; then
  read -r ENGINE_HOST ENGINE_PORT <<< "$CONFIG_VALS"
else
  ENGINE_HOST="127.0.0.1"
  ENGINE_PORT="8765"
fi

echo "zoom-app-screen-note-taker -- service status"
echo ""

down=0

check() {
  local name="$1" url="$2"
  if curl -sf -m 2 "$url" >/dev/null 2>&1; then
    printf "  %-38s UP\n" "$name"
    return 0
  fi
  printf "  %-38s DOWN\n" "$name"
  return 1
}

if check "engine status API ($ENGINE_HOST:$ENGINE_PORT)" "http://$ENGINE_HOST:$ENGINE_PORT/health"; then
  if [ -x "$VENV_PYTHON" ]; then
    session=$(curl -sf -m 2 "http://$ENGINE_HOST:$ENGINE_PORT/status" | "$VENV_PYTHON" -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('status', 'unknown'))
except Exception:
    pass
" 2>/dev/null)
    [ -n "$session" ] && printf "    session: %s\n" "$session"
  fi
else
  down=$((down + 1))
fi

echo ""
if [ "$down" -eq 0 ]; then
  echo "All services up."
else
  echo "$down service(s) down."
fi
exit 0
