#!/usr/bin/env python3
"""SQLite database layer for TiltPi."""

import json
import os
import sqlite3
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DATA_DIR, "tiltpi.db")
LOG_FILE = os.path.join(DATA_DIR, "tilt_log.json")
CONFIG_FILE = os.path.join(DATA_DIR, "brew_config.json")

AUTO_SPLIT_DAYS = 7


def get_connection():
    """Get a SQLite connection with WAL mode and row factory."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables and indexes if they don't exist."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS brews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL DEFAULT '',
            color TEXT NOT NULL DEFAULT '',
            target_fg REAL NOT NULL DEFAULT 1.010,
            temp_low REAL NOT NULL DEFAULT 60,
            temp_high REAL NOT NULL DEFAULT 75,
            og REAL,
            fg REAL,
            abv REAL,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            status TEXT NOT NULL DEFAULT 'active'
        );

        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brew_id INTEGER NOT NULL REFERENCES brews(id),
            timestamp TEXT NOT NULL,
            color TEXT NOT NULL,
            temp_f REAL NOT NULL,
            temp_c REAL NOT NULL,
            gravity REAL NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_readings_brew_id ON readings(brew_id);
        CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON readings(timestamp);
        CREATE INDEX IF NOT EXISTS idx_brews_status ON brews(status);
    """)
    conn.close()


def _row_to_dict(row):
    """Convert a sqlite3.Row to a plain dict."""
    if row is None:
        return None
    return dict(row)


def get_active_brew():
    """Get the currently active brew, or None."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM brews WHERE status = 'active' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def create_brew(color="", name="", target_fg=1.010, temp_low=60, temp_high=75):
    """Create a new active brew. Returns the brew id."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO brews (name, color, target_fg, temp_low, temp_high, started_at, status)
               VALUES (?, ?, ?, ?, ?, ?, 'active')""",
            (name, color, target_fg, temp_low, temp_high, datetime.now().isoformat()),
        )
        brew_id = cur.lastrowid
        conn.commit()
        return brew_id
    finally:
        conn.close()


def end_brew(brew_id):
    """End a brew — calculate FG, ABV, mark as completed."""
    conn = get_connection()
    try:
        brew = conn.execute("SELECT * FROM brews WHERE id = ?", (brew_id,)).fetchone()
        if not brew or brew["status"] != "active":
            return

        last_reading = conn.execute(
            "SELECT gravity FROM readings WHERE brew_id = ? ORDER BY timestamp DESC LIMIT 1",
            (brew_id,),
        ).fetchone()

        fg = last_reading["gravity"] if last_reading else None
        og = brew["og"]
        abv = round((og - fg) * 131.25, 1) if og is not None and fg is not None else None

        conn.execute(
            "UPDATE brews SET ended_at = ?, status = 'completed', fg = ?, abv = ? WHERE id = ?",
            (datetime.now().isoformat(), fg, abv, brew_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_brew(brew_id, **fields):
    """Update allowed fields on a brew."""
    allowed = {"name", "target_fg", "temp_low", "temp_high"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [brew_id]
    conn = get_connection()
    try:
        conn.execute(f"UPDATE brews SET {set_clause} WHERE id = ?", values)
        conn.commit()
    finally:
        conn.close()


def get_brew(brew_id):
    """Get a single brew by id."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM brews WHERE id = ?", (brew_id,)).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def list_brews():
    """List all brews, newest first."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM brews ORDER BY started_at DESC").fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def insert_reading(brew_id, timestamp, color, temp_f, temp_c, gravity):
    """Insert a single reading."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO readings (brew_id, timestamp, color, temp_f, temp_c, gravity)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (brew_id, timestamp, color, temp_f, temp_c, gravity),
        )
        # Set OG from the first reading if not yet set
        brew = conn.execute("SELECT og FROM brews WHERE id = ?", (brew_id,)).fetchone()
        if brew and brew["og"] is None:
            conn.execute("UPDATE brews SET og = ? WHERE id = ?", (gravity, brew_id))
        conn.commit()
    finally:
        conn.close()


def get_readings(brew_id):
    """Get all readings for a brew, ordered by timestamp."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT timestamp, color, temp_f, temp_c, gravity FROM readings WHERE brew_id = ? ORDER BY timestamp",
            (brew_id,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_last_reading(brew_id):
    """Get the most recent reading for a brew."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM readings WHERE brew_id = ? ORDER BY timestamp DESC LIMIT 1",
            (brew_id,),
        ).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def get_readings_for_active_brew():
    """Get readings for the active brew."""
    brew = get_active_brew()
    if not brew:
        return []
    return get_readings(brew["id"])


def ensure_active_brew(color, timestamp):
    """Ensure an active brew exists for this reading. Handles auto-start and auto-split.

    Returns the brew_id to use for the reading.
    """
    active = get_active_brew()

    if active is None:
        # Auto-start: no active brew, create one
        return create_brew(color=color)

    # Check for auto-split: gap of 7+ days since last reading
    last = get_last_reading(active["id"])
    if last:
        last_time = datetime.fromisoformat(last["timestamp"])
        current_time = datetime.fromisoformat(timestamp)
        if current_time - last_time > timedelta(days=AUTO_SPLIT_DAYS):
            end_brew(active["id"])
            return create_brew(color=color)

    return active["id"]


def migrate_from_json():
    """One-time migration from tilt_log.json to SQLite.

    Only runs if the JSON file exists and the database has no brews.
    Leaves JSON files in place as backup.
    """
    conn = get_connection()
    try:
        count = conn.execute("SELECT COUNT(*) FROM brews").fetchone()[0]
    finally:
        conn.close()

    if count > 0 or not os.path.exists(LOG_FILE):
        return

    with open(LOG_FILE) as f:
        readings_data = json.load(f)

    if not readings_data:
        return

    # Load config if available
    config = {"brew_name": "", "target_fg": 1.010, "temp_low": 60, "temp_high": 75}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            config.update(json.load(f))

    print(f"Migrating {len(readings_data)} readings from tilt_log.json...")

    # Create a brew using the config
    conn = get_connection()
    try:
        first_ts = readings_data[0]["timestamp"]
        cur = conn.execute(
            """INSERT INTO brews (name, color, target_fg, temp_low, temp_high, started_at, og, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'active')""",
            (
                config.get("brew_name", ""),
                readings_data[0].get("color", ""),
                config.get("target_fg", 1.010),
                config.get("temp_low", 60),
                config.get("temp_high", 75),
                first_ts,
                readings_data[0]["gravity"],
            ),
        )
        brew_id = cur.lastrowid

        # Bulk insert readings
        conn.executemany(
            """INSERT INTO readings (brew_id, timestamp, color, temp_f, temp_c, gravity)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [
                (brew_id, r["timestamp"], r["color"], r["temp_f"], r["temp_c"], r["gravity"])
                for r in readings_data
            ],
        )
        conn.commit()
        print(f"Migration complete. {len(readings_data)} readings imported as brew #{brew_id}.")
    finally:
        conn.close()
