# Installation

## Prebuilt packages (recommended)

Download the latest `.deb`, `.rpm`, or AppImage from the
[Releases page](https://github.com/towfiq-ul/KatibMudawwin/releases) and
install/run it like any other package:

```bash
sudo apt install ./KatibMudawwin_*.deb      # Debian/Ubuntu
sudo rpm -i KatibMudawwin-*.rpm             # Fedora/RHEL
```

or just make the AppImage executable and double-click it.

These are built and published automatically for every release -- see
`../CONTRIBUTING.md` for how releases are cut. No build toolchain needed.

## From source

For development, or to run the latest in-progress code from `develop`:

```bash
curl -fsSL https://raw.githubusercontent.com/towfiq-ul/KatibMudawwin/develop/install.sh | bash
```

This clones the repo to `~/KatibMudawwin` and runs `make build` (sets up
the engine's Python venv, installs the desktop app's npm dependencies).
Runs under `bash` regardless of your login shell, since it's piped
straight into `bash`.

Environment variable overrides:

| Variable | Default | Purpose |
|---|---|---|
| `KM_INSTALL_DIR` | `~/KatibMudawwin` | Where to clone the repo |
| `KM_BRANCH` | `develop` | Which branch to build |
| `KM_REPO_URL` | `https://github.com/towfiq-ul/KatibMudawwin.git` | Repo to clone |

See `install.sh` itself for the full logic -- it's a thin wrapper around
`make build`, nothing it can't also be done by hand.

### System prerequisites (Linux)

`install.sh` installs these automatically via `scripts/install_linux_deps.sh`
(also runnable directly as `make deps-linux`). For reference, the packages
involved:

```bash
# Engine (audio capture, local summarization)
sudo apt install pulseaudio-utils ffmpeg libportaudio2 build-essential

# Desktop app (Tauri) build + packaging
sudo apt install libwebkit2gtk-4.1-dev libgtk-3-dev libayatana-appindicator3-dev \
  librsvg2-dev libssl-dev libxdo-dev pkg-config rpm patchelf
```

`desktop/` also needs a Rust toolchain ([rustup.rs](https://rustup.rs)) and
Node/npm -- `install_linux_deps.sh` only checks for these and points you at
the installer; it doesn't install them itself.

Summarization defaults to a local Phi-3 model, running in-process via
`llama-cpp-python` -- no separate service to install or start. The GGUF
weights (~2.3GB) download once from Hugging Face Hub and are cached the
first time a meeting is summarized. For Anthropic API summarization
instead, set `summarizer.provider: anthropic` in your config and set
`ANTHROPIC_API_KEY` in your environment.

## Building packages yourself

```bash
make bundle
```

Builds `.deb`, `.rpm`, and an AppImage into
`desktop/src-tauri/target/release/bundle/{deb,rpm,appimage}/`. This is
exactly what CI runs for each release.

## All `make` commands

Run `make help`, or see the reference below:

```bash
make build              # engine-setup + desktop-setup: install all deps
make engine-setup       # create engine/.venv, install the Python engine
make engine-test        # run the offline test suite
make engine-run         # start the engine in the foreground
make engine-start       # start the engine in the background
make engine-stop        # stop the background engine
make desktop-setup      # npm install for the desktop app
make desktop-run        # start the desktop app in dev mode
make bundle             # build installable .deb/.rpm/AppImage packages
make start / make stop  # aliases for engine-start / engine-stop
make summary [DATE]     # summarize a day's notes (yyyymmdd, default: today)
make retention-sweep    # delete raw audio past the age/size retention caps
make status             # check whether the engine's status API is running
make deps-linux         # check/install missing system deps
make clean              # remove venv, node_modules, build output, caches
```
