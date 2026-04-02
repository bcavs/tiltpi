# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TiltPi is a Raspberry Pi application that monitors Tilt Hydrometers (beer fermentation sensors) via Bluetooth LE and displays real-time readings on a web dashboard. Two-process architecture: a BLE scanner daemon writes to a shared SQLite database, and a Flask server reads it.

## Commands

```bash
# Setup
python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt

# Run BLE scanner (requires sudo for Bluetooth socket access)
sudo venv/bin/python tilt_monitor.py

# Run Flask dashboard (port 8080)
python dashboard.py

# Generate fake fermentation data for testing without a Tilt device
python generate_dummy_data.py

# Production install (systemd services)
./setup.sh
```

## Architecture

**Data flow:** BLE packets → `tilt_monitor.py` (async) → `data/tiltpi.db` (SQLite) → `dashboard.py` (Flask API) → `templates/index.html` (polls every 5s)

**db.py** — SQLite database layer. All data operations go through this module. Uses WAL journal mode for concurrent access from the monitor and dashboard processes. Two tables: `brews` (lifecycle, config, stats) and `readings` (timestamped gravity/temp data linked to a brew). Handles auto-creation of brews, auto-splitting after 7-day gaps, and one-time migration from legacy JSON files.

**tilt_monitor.py** — Async BLE scanner using `aioblescan`. Decodes Tilt iBeacon packets, maps UUIDs to colors, extracts gravity/temperature, writes readings to SQLite via `db.py`. Updates LED strip after each reading. Initializes database, runs JSON migration, and starts LED render loop on startup.

**led.py** — NeoPixel LED strip driver for visual fermentation feedback. Progress fill (attenuation %), color-coded by status (green=active, amber=slowing, copper=complete), red flash for temperature alerts, rainbow celebration on completion. Runs a background render loop at ~30fps. Gracefully degrades if no NeoPixel hardware is present (GPIO 18, 24 LEDs). Requires `adafruit-circuitpython-neopixel` on the Pi.

**dashboard.py** — Flask server on port 8080. API endpoints:
- `GET /api/readings` — active brew readings (accepts `?brew_id=N` for historical)
- `GET/POST /api/config` — active brew's settings
- `GET /api/export.csv` — CSV export (accepts `?brew_id=N`)
- `GET /api/brews` — list all brews
- `GET /api/brews/<id>/readings` — readings for a specific brew
- `POST /api/brews/start` — start a new brew (ends current if active)
- `POST /api/brews/<id>/end` — end a brew

**templates/index.html** — Self-contained SPA (vanilla JS, Chart.js, Canvas). Handles gauges, bubble animations, fermentation status detection, ABV calculation, temperature alerts, CSV export, brew history view, and brew lifecycle controls. All JS/CSS is inline in this single file.

**data/** — Runtime directory (gitignored). Contains `tiltpi.db` (SQLite database).

**systemd/** — Service unit files for both processes. Note: paths are hardcoded to `/home/ben/Desktop/tilt-monitor/` and need updating per installation.

## Brew Lifecycle

- **Auto-start:** First reading with no active brew creates one automatically
- **Auto-split:** 7+ day gap in readings ends the current brew and starts a new one
- **Manual:** Dashboard has "Start New Brew" / "End Brew" buttons
- **On end:** FG and ABV are calculated and stored on the brew record

## Key Details

- Only two Python dependencies: `aioblescan` and `flask` (sqlite3 is stdlib)
- Tilt hydrometers are identified by UUID; each maps to a color (Red, Green, Black, etc.)
- Gravity values come from iBeacon minor value / 1000; temperature from major value
- Fermentation status logic compares rolling averages of last 12 vs prior 12 readings
- The BLE scanner requires root/sudo for raw Bluetooth socket access
- Legacy JSON files (`tilt_log.json`, `brew_config.json`) are auto-migrated to SQLite on first run
