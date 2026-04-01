#!/usr/bin/env python3
"""Generate dummy Tilt data for testing the dashboard."""

import os
import random
import sqlite3
from datetime import datetime, timedelta

import db


def generate_readings(start_time, count, og, fg, temp_start=68.0):
    """Generate a list of realistic fermentation readings."""
    readings = []
    sg = og
    temp = temp_start
    gravity_drop_per_step = (og - fg) / count

    for i in range(count):
        timestamp = start_time + timedelta(hours=i)
        sg -= random.uniform(0, gravity_drop_per_step * 2)
        sg = max(sg, fg)
        temp += random.uniform(-0.3, 0.3)
        temp = max(64.0, min(74.0, temp))

        readings.append({
            "timestamp": timestamp.isoformat(),
            "color": "Red",
            "temp_f": round(temp, 1),
            "temp_c": round((temp - 32) * 5 / 9, 1),
            "gravity": round(sg, 4),
        })
    return readings


def main():
    # Remove existing DB for a clean start
    if os.path.exists(db.DB_PATH):
        os.remove(db.DB_PATH)

    db.init_db()
    now = datetime.now()
    conn = db.get_connection()

    # Brew 1: Completed pale ale, started 44 days ago, 14-day fermentation
    brew1_start = now - timedelta(days=44)
    cur = conn.execute(
        """INSERT INTO brews (name, color, target_fg, temp_low, temp_high, started_at, og, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'active')""",
        ("Summer Pale Ale", "Red", 1.012, 62, 72, brew1_start.isoformat(), 1.052),
    )
    brew1_id = cur.lastrowid
    for r in generate_readings(brew1_start, 220, 1.052, 1.012):
        conn.execute(
            "INSERT INTO readings (brew_id, timestamp, color, temp_f, temp_c, gravity) VALUES (?, ?, ?, ?, ?, ?)",
            (brew1_id, r["timestamp"], r["color"], r["temp_f"], r["temp_c"], r["gravity"]),
        )
    brew1_end = brew1_start + timedelta(days=14)
    conn.execute(
        "UPDATE brews SET ended_at = ?, status = 'completed', fg = 1.012, abv = 5.2 WHERE id = ?",
        (brew1_end.isoformat(), brew1_id),
    )

    # Brew 2: Completed stout, started 25 days ago, 12-day fermentation
    brew2_start = now - timedelta(days=25)
    cur = conn.execute(
        """INSERT INTO brews (name, color, target_fg, temp_low, temp_high, started_at, og, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'active')""",
        ("Chocolate Stout", "Red", 1.015, 60, 70, brew2_start.isoformat(), 1.065),
    )
    brew2_id = cur.lastrowid
    for r in generate_readings(brew2_start, 190, 1.065, 1.015, temp_start=66.0):
        conn.execute(
            "INSERT INTO readings (brew_id, timestamp, color, temp_f, temp_c, gravity) VALUES (?, ?, ?, ?, ?, ?)",
            (brew2_id, r["timestamp"], r["color"], r["temp_f"], r["temp_c"], r["gravity"]),
        )
    brew2_end = brew2_start + timedelta(days=12)
    conn.execute(
        "UPDATE brews SET ended_at = ?, status = 'completed', fg = 1.015, abv = 6.6 WHERE id = ?",
        (brew2_end.isoformat(), brew2_id),
    )

    # Brew 3: Active IPA, started 3 days ago (still fermenting)
    brew3_start = now - timedelta(days=3)
    cur = conn.execute(
        """INSERT INTO brews (name, color, target_fg, temp_low, temp_high, started_at, og, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'active')""",
        ("Dad's IPA", "Red", 1.012, 62, 74, brew3_start.isoformat(), 1.060),
    )
    brew3_id = cur.lastrowid
    for r in generate_readings(brew3_start, 60, 1.060, 1.035, temp_start=68.0):
        conn.execute(
            "INSERT INTO readings (brew_id, timestamp, color, temp_f, temp_c, gravity) VALUES (?, ?, ?, ?, ?, ?)",
            (brew3_id, r["timestamp"], r["color"], r["temp_f"], r["temp_c"], r["gravity"]),
        )

    conn.commit()
    conn.close()

    print("Generated dummy data:")
    for brew in db.list_brews():
        reading_count = len(db.get_readings(brew["id"]))
        status = brew["status"]
        abv = f", ABV: {brew['abv']}%" if brew["abv"] else ""
        print(f"  #{brew['id']} {brew['name']} ({status}, {reading_count} readings{abv})")


if __name__ == "__main__":
    main()
