VENV := engine/.venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

RUN_DIR := .run
ENGINE_PIDFILE := $(RUN_DIR)/engine.pid
ENGINE_LOG := $(RUN_DIR)/engine.log
DASHBOARD_PIDFILE := $(RUN_DIR)/dashboard.pid
DASHBOARD_LOG := $(RUN_DIR)/dashboard.log

.PHONY: help
help:
	@echo "zoom-app-screen-note-taker -- useful commands"
	@echo ""
	@echo "  make deps-linux       Check/report missing Linux system deps (pactl, ffmpeg)"
	@echo "  make build            engine-setup + dashboard-setup (install all deps)"
	@echo "  make engine-setup     Create engine/.venv and install the Python engine (with dev deps)"
	@echo "  make engine-test      Run the Python test suite (pytest)"
	@echo "  make engine-run       Start the engine in the foreground (tray icon, status API, detection)"
	@echo "  make engine-start     Start the engine in the background (logs: $(ENGINE_LOG))"
	@echo "  make engine-stop      Stop the background engine (ends any active recording first)"
	@echo "  make dashboard-setup  npm install for the Node dashboard"
	@echo "  make dashboard-run    Start the dashboard in the foreground (http://localhost:5173)"
	@echo "  make dashboard-start  Start the dashboard in the background (logs: $(DASHBOARD_LOG))"
	@echo "  make dashboard-stop   Stop the background dashboard"
	@echo "  make start            engine-start + dashboard-start"
	@echo "  make stop             engine-stop + dashboard-stop"
	@echo "  make summary [DATE]   Summarize a day's notes (yyyymmdd, default: today in CST)"
	@echo "  make status           Check which project services are running (engine, dashboard)"
	@echo "  make clean            Remove venv, node_modules, and caches"

.PHONY: deps-linux
deps-linux:
	bash scripts/install_linux_deps.sh

.PHONY: build
build: engine-setup dashboard-setup

.PHONY: engine-setup
engine-setup:
	# --system-site-packages: pystray's tray-icon popup menu needs PyGObject +
	# AppIndicator3 (python3-gi / libayatana-appindicator3-1), which are OS
	# packages, not pip-installable in an isolated venv. Without this flag
	# pystray silently falls back to its bare X11 backend, which has no menu
	# support at all (HAS_MENU = False) -- only a single default click action.
	python3 -m venv --system-site-packages $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e "./engine[dev]"

.PHONY: engine-test
engine-test:
	$(PYTHON) -m pytest engine/tests -v

.PHONY: engine-run
engine-run:
	$(PYTHON) -m katib_mudawwin.main

.PHONY: dashboard-setup
dashboard-setup:
	cd dashboard && npm install

.PHONY: dashboard-run
dashboard-run:
	cd dashboard && npm start

.PHONY: engine-start
engine-start:
	@mkdir -p $(RUN_DIR)
	@if [ -f $(ENGINE_PIDFILE) ] && kill -0 "$$(cat $(ENGINE_PIDFILE))" 2>/dev/null; then \
		echo "engine already running (pid $$(cat $(ENGINE_PIDFILE)))"; \
	else \
		nohup $(PYTHON) -m katib_mudawwin.main > $(ENGINE_LOG) 2>&1 & \
		echo $$! > $(ENGINE_PIDFILE); \
		echo "engine started (pid $$(cat $(ENGINE_PIDFILE))), logs: $(ENGINE_LOG)"; \
	fi

.PHONY: engine-stop
engine-stop:
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

.PHONY: dashboard-start
dashboard-start:
	@mkdir -p $(RUN_DIR)
	@if [ -f $(DASHBOARD_PIDFILE) ] && kill -0 "$$(cat $(DASHBOARD_PIDFILE))" 2>/dev/null; then \
		echo "dashboard already running (pid $$(cat $(DASHBOARD_PIDFILE)))"; \
	else \
		nohup node dashboard/server.js > $(DASHBOARD_LOG) 2>&1 & \
		echo $$! > $(DASHBOARD_PIDFILE); \
		echo "dashboard started (pid $$(cat $(DASHBOARD_PIDFILE))), logs: $(DASHBOARD_LOG)"; \
	fi

.PHONY: dashboard-stop
dashboard-stop:
	@if [ ! -f $(DASHBOARD_PIDFILE) ] || ! kill -0 "$$(cat $(DASHBOARD_PIDFILE))" 2>/dev/null; then \
		echo "dashboard not running"; \
		rm -f $(DASHBOARD_PIDFILE); \
	else \
		kill "$$(cat $(DASHBOARD_PIDFILE))" 2>/dev/null || true; \
		rm -f $(DASHBOARD_PIDFILE); \
		echo "dashboard stopped"; \
	fi

.PHONY: start
start: engine-start dashboard-start

.PHONY: stop
stop: engine-stop dashboard-stop

.PHONY: summary
summary:
	@$(PYTHON) -m katib_mudawwin.summarize_notes $(filter-out summary,$(MAKECMDGOALS))

# Swallows the optional trailing date arg in `make summary 20260821` as a
# harmless no-op target, instead of Make trying (and failing) to build a
# real target named "20260821".
%:
	@:

.PHONY: status
status:
	@bash scripts/status.sh

.PHONY: clean
clean:
	rm -rf $(VENV)
	rm -rf dashboard/node_modules
	rm -rf $(RUN_DIR)
	find . -type d -name __pycache__ -not -path "./.git/*" -exec rm -rf {} +
	rm -rf engine/.pytest_cache engine/src/*.egg-info
