#!/usr/bin/env python3
"""Generate dummy Tilt data for testing the dashboard."""

import json
import os
from datetime import datetime, timedelta
import random

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
LOG_FILE = os.path.join(DATA_DIR, "tilt_log.json")

readings = []
now = datetime.now()
sg = 1.055  # Starting gravity (typical ale OG)
temp = 68.0  # Starting temp in °F

for i in range(200):
    timestamp = now - timedelta(hours=200 - i)
    # Gravity drops over time (fermentation)
    sg -= random.uniform(0.0001, 0.0004)
    sg = max(sg, 1.010)
    # Temperature fluctuates slightly
    temp += random.uniform(-0.3, 0.3)
    temp = max(64.0, min(72.0, temp))

    readings.append({
        "timestamp": timestamp.isoformat(),
        "color": "Red",
        "temp_f": round(temp, 1),
        "temp_c": round((temp - 32) * 5 / 9, 1),
        "gravity": round(sg, 4),
    })

with open(LOG_FILE, "w") as f:
    json.dump(readings, f, indent=2)

print(f"Wrote {len(readings)} dummy readings to {LOG_FILE}")
