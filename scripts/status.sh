#!/usr/bin/env bash
set -uo pipefail

# Report which project services are up: the engine status API, the
# dashboard, and (if configured as the summarizer) Ollama. Reads actual
# host/port settings from the engine config when the venv is set up;
# otherwise falls back to the documented defaults.

VENV_PYTHON="engine/.venv/bin/python"
CONFIG_VALS=""
if [ -x "$VENV_PYTHON" ]; then
  CONFIG_VALS=$("$VENV_PYTHON" -c "
from zoom_notes_engine.config import load_config
c = load_config()
print(c.server.status_api_host, c.server.status_api_port, c.dashboard.port, c.summarizer.ollama.base_url)
" 2>/dev/null)
fi

if [ -n "$CONFIG_VALS" ]; then
  read -r ENGINE_HOST ENGINE_PORT DASHBOARD_PORT OLLAMA_URL <<< "$CONFIG_VALS"
else
  ENGINE_HOST="127.0.0.1"
  ENGINE_PORT="8765"
  DASHBOARD_PORT="5173"
  OLLAMA_URL="http://localhost:11434"
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

check "dashboard (localhost:$DASHBOARD_PORT)" "http://localhost:$DASHBOARD_PORT/health" || down=$((down + 1))

check "ollama ($OLLAMA_URL)" "$OLLAMA_URL" || down=$((down + 1))

echo ""
if [ "$down" -eq 0 ]; then
  echo "All services up."
else
  echo "$down service(s) down."
fi
exit 0
