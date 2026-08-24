#!/usr/bin/env bash
# Quick installer for KātibMudawwin.
#
#   curl -fsSL https://raw.githubusercontent.com/towfiq-ul/KatibMudawwin/master/install.sh | bash
#
# Clones the repo and runs `make build` (engine venv + desktop npm install).
# Runs under bash regardless of your login shell, since it's piped straight
# into `bash`. Linux only for now -- see README's macOS/Windows notes.
#
# Override defaults with env vars, e.g.:
#   KM_INSTALL_DIR=~/dev/katib-mudawwin KM_BRANCH=tauri-desktop-app \
#     curl -fsSL .../install.sh | bash
set -euo pipefail

REPO_URL="${KM_REPO_URL:-https://github.com/towfiq-ul/KatibMudawwin.git}"
BRANCH="${KM_BRANCH:-master}"
INSTALL_DIR="${KM_INSTALL_DIR:-$HOME/KatibMudawwin}"

if [ "$(uname -s)" != "Linux" ]; then
  echo "KātibMudawwin currently only runs on Linux (see README's macOS/Windows notes)." >&2
  exit 1
fi

for cmd in git make python3; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    echo "Install it (e.g. sudo apt install $cmd) and re-run this script." >&2
    exit 1
  fi
done

if [ -d "$INSTALL_DIR/.git" ]; then
  echo "Found existing checkout at $INSTALL_DIR, updating..."
  git -C "$INSTALL_DIR" fetch origin "$BRANCH"
  git -C "$INSTALL_DIR" checkout "$BRANCH"
  git -C "$INSTALL_DIR" pull --ff-only origin "$BRANCH"
elif [ -e "$INSTALL_DIR" ]; then
  echo "$INSTALL_DIR already exists and isn't a git checkout." >&2
  echo "Set KM_INSTALL_DIR to a different path and re-run." >&2
  exit 1
else
  echo "Cloning $REPO_URL (branch $BRANCH) into $INSTALL_DIR..."
  git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

echo ""
bash scripts/install_linux_deps.sh || {
  echo ""
  echo "Some system dependencies are missing (see above)." >&2
  echo "Install them, then re-run 'make build' in $INSTALL_DIR." >&2
}

echo ""
echo "Installing engine + desktop dependencies (make build)..."
make build

cat <<EOF

KātibMudawwin is installed at $INSTALL_DIR

Next steps:
  cd $INSTALL_DIR
  make engine-run    # start the engine (status API, meeting detection)
  make desktop-run   # start the desktop app (tray icon + window)

See $INSTALL_DIR/README.md for config, autostart (scripts/katib-mudawwin.service),
and consent/recording-law notes.
EOF
