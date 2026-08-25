# KātibMudawwin -- see docs/installation.md for the full command reference,
# docs/usage.md for what each of these actually does day to day.
#
# Recipes run under bash with -eu -o pipefail: a failing command anywhere
# in a multi-line recipe (engine-start/engine-stop) aborts the recipe
# instead of silently continuing, same as the standalone scripts/*.sh.
SHELL := /usr/bin/env bash
.SHELLFLAGS := -euo pipefail -c

# Override any of these on the command line, e.g. `make PYTHON=python3.11 engine-run`.
VENV ?= engine/.venv
PYTHON ?= $(VENV)/bin/python
PIP ?= $(VENV)/bin/pip

RUN_DIR ?= .run
ENGINE_PIDFILE := $(RUN_DIR)/engine.pid
ENGINE_LOG := $(RUN_DIR)/engine.log

.DEFAULT_GOAL := help

# --- General -------------------------------------------------------------

.PHONY: help
help: ## Show this help, grouped by section
	@if [ -t 1 ]; then bold=$$'\033[1m'; cyan=$$'\033[36m'; reset=$$'\033[0m'; \
	else bold=''; cyan=''; reset=''; fi; \
	printf "%sKatibMudawwin%s -- useful commands\n" "$$bold" "$$reset"; \
	awk -v bold="$$bold" -v cyan="$$cyan" -v reset="$$reset" '\
		/^# --- / { \
			line = $$0; sub(/^# --- /, "", line); sub(/[ -]*$$/, "", line); \
			printf "\n%s%s%s\n", bold, line, reset; next; \
		} \
		/^[a-zA-Z0-9_-]+:.*## / { \
			split($$0, parts, /:.*## /); \
			printf "  %smake %-16s%s %s\n", cyan, parts[1], reset, parts[2]; \
		} \
	' $(MAKEFILE_LIST)

# --- Setup ------------------------------------------------------------

.PHONY: deps-linux
deps-linux: ## Check/install missing Linux system deps (pactl, ffmpeg, Tauri build deps)
	bash scripts/install_linux_deps.sh

.PHONY: build
build: engine-setup desktop-setup ## engine-setup + desktop-setup (install all deps)

.PHONY: engine-setup
engine-setup: ## Create engine/.venv and install the Python engine (with dev deps)
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e "./engine[dev]"

.PHONY: desktop-setup
desktop-setup: ## npm install for the Tauri desktop app
	cd desktop && npm install

# --- Run (foreground) ---------------------------------------------------

.PHONY: engine-test
engine-test: ## Run the Python test suite (pytest)
	$(PYTHON) -m pytest engine/tests -v

.PHONY: engine-run
engine-run: ## Start the engine in the foreground (status API, detection)
	$(PYTHON) -m katib_mudawwin.main

.PHONY: desktop-run
desktop-run: ## Start the desktop app in dev mode (window + tray icon)
	cd desktop && npm run tauri dev

# --- Run (background) ---------------------------------------------------

.PHONY: engine-start
engine-start: ## Start the engine in the background (logs: .run/engine.log)
	@mkdir -p $(RUN_DIR)
	@if [ -f $(ENGINE_PIDFILE) ] && kill -0 "$$(cat $(ENGINE_PIDFILE))" 2>/dev/null; then \
		echo "engine already running (pid $$(cat $(ENGINE_PIDFILE)))"; \
	else \
		nohup $(PYTHON) -m katib_mudawwin.main > $(ENGINE_LOG) 2>&1 & \
		echo $$! > $(ENGINE_PIDFILE); \
		echo "engine started (pid $$(cat $(ENGINE_PIDFILE))), logs: $(ENGINE_LOG)"; \
	fi

.PHONY: engine-stop
engine-stop: ## Stop the background engine (ends any active recording first)
	@if [ ! -f $(ENGINE_PIDFILE) ] || ! kill -0 "$$(cat $(ENGINE_PIDFILE))" 2>/dev/null; then \
		echo "engine not running"; \
		rm -f $(ENGINE_PIDFILE); \
	else \
		HOST_PORT=$$($(PYTHON) -c "from katib_mudawwin.config import load_config; c = load_config(); print(c.server.status_api_host, c.server.status_api_port)" 2>/dev/null); \
		if [ -n "$$HOST_PORT" ]; then \
			set -- $$HOST_PORT; \
			curl -sf -m 30 -X POST "http://$$1:$$2/stop" >/dev/null 2>&1 || true; \
		fi; \
		kill "$$(cat $(ENGINE_PIDFILE))" 2>/dev/null || true; \
		rm -f $(ENGINE_PIDFILE); \
		echo "engine stopped"; \
	fi

.PHONY: start
start: engine-start ## Alias for engine-start

.PHONY: stop
stop: engine-stop ## Alias for engine-stop

.PHONY: status
status: ## Check whether the engine's status API is running
	@bash scripts/status.sh

# --- Notes & packaging ---------------------------------------------------

.PHONY: summary
summary: ## Summarize a day's notes (yyyymmdd, default: today in CST)
	@$(PYTHON) -m katib_mudawwin.summarize_notes $(filter-out summary,$(MAKECMDGOALS))

.PHONY: retention-sweep
retention-sweep: ## Delete raw audio past the age/size retention caps
	$(PYTHON) -m katib_mudawwin.retention_sweep

.PHONY: bundle
bundle: ## Build installable .deb/.rpm/AppImage packages (desktop/src-tauri/target/release/bundle/)
	cd desktop && npm run tauri build

# Swallows the optional trailing date arg in `make summary 20260821` as a
# harmless no-op target, instead of Make trying (and failing) to build a
# real target named "20260821".
%:
	@:

# --- Cleanup ---------------------------------------------------------

.PHONY: clean
clean: ## Remove venv, node_modules, Rust build output, and caches
	rm -rf $(VENV)
	rm -rf desktop/node_modules
	rm -rf desktop/dist
	rm -rf desktop/src-tauri/target
	rm -rf $(RUN_DIR)
	find . -type d -name __pycache__ -not -path "./.git/*" -exec rm -rf {} +
	rm -rf engine/.pytest_cache engine/src/*.egg-info
