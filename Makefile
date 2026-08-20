VENV := engine/.venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: help
help:
	@echo "zoom-app-screen-note-taker -- useful commands"
	@echo ""
	@echo "  make deps-linux       Check/report missing Linux system deps (pactl, ffmpeg, ollama)"
	@echo "  make engine-setup     Create engine/.venv and install the Python engine (with dev deps)"
	@echo "  make engine-test      Run the Python test suite (pytest)"
	@echo "  make engine-run       Start the engine: tray icon, status API, and Zoom meeting auto-detection"
	@echo "  make dashboard-setup  npm install for the Node dashboard"
	@echo "  make dashboard-run    Start the Node dashboard (http://localhost:5173)"
	@echo "  make status           Check which project services are running (engine, dashboard, ollama)"
	@echo "  make clean            Remove venv, node_modules, and caches"

.PHONY: deps-linux
deps-linux:
	bash scripts/install_linux_deps.sh

.PHONY: engine-setup
engine-setup:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e "./engine[dev]"

.PHONY: engine-test
engine-test:
	$(PYTHON) -m pytest engine/tests -v

.PHONY: engine-run
engine-run:
	$(PYTHON) -m zoom_notes_engine.main

.PHONY: dashboard-setup
dashboard-setup:
	cd dashboard && npm install

.PHONY: dashboard-run
dashboard-run:
	cd dashboard && npm start

.PHONY: status
status:
	@bash scripts/status.sh

.PHONY: clean
clean:
	rm -rf $(VENV)
	rm -rf dashboard/node_modules
	find . -type d -name __pycache__ -not -path "./.git/*" -exec rm -rf {} +
	rm -rf engine/.pytest_cache engine/src/*.egg-info
