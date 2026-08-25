#!/usr/bin/env bash
# Quick source installer for KātibMudawwin -- for development, or to run
# the latest in-progress code. Most users should instead grab a prebuilt
# .deb/.rpm/AppImage from the latest GitHub Release (built automatically by
# .github/workflows/release.yml -- see CONTRIBUTING.md for the release
# process); this script builds from source instead.
#
#   curl -fsSL https://raw.githubusercontent.com/towfiq-ul/KatibMudawwin/develop/install.sh | bash
#
# Clones the repo and runs `make build` (engine venv + desktop npm install).
# Runs under bash regardless of your login shell, since it's piped straight
# into `bash`. Linux only for now -- see README's macOS/Windows notes.
#
# Defaults to `develop` (CONTRIBUTING.md's branch model: develop -> master
# -> release -> tag) since that's the actual purpose of building from
# source rather than installing a release package -- override with
# KM_BRANCH for anything else, e.g.:
#   KM_INSTALL_DIR=~/dev/katib-mudawwin KM_BRANCH=master \
#     curl -fsSL .../install.sh | bash
set -euo pipefail

REPO_URL="${KM_REPO_URL:-https://github.com/towfiq-ul/KatibMudawwin.git}"
BRANCH="${KM_BRANCH:-develop}"
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
  echo "Some system dependencies couldn't be installed automatically (see above)." >&2
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
