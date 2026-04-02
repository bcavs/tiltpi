#!/usr/bin/env python3
"""Tilt Hydrometer Monitor - reads BLE iBeacon data from Tilt devices."""

import asyncio
from datetime import datetime
from aioblescan import create_bt_socket, BLEScanner
from aioblescan.plugins.ibeacon import IBeacon

import db
import led

# Tilt UUID -> color mapping
TILT_UUIDS = {
    "a495bb10-c5b1-4b44-b512-1370f02d74de": "Red",
    "a495bb20-c5b1-4b44-b512-1370f02d74de": "Green",
    "a495bb30-c5b1-4b44-b512-1370f02d74de": "Black",
    "a495bb40-c5b1-4b44-b512-1370f02d74de": "Purple",
    "a495bb50-c5b1-4b44-b512-1370f02d74de": "Orange",
    "a495bb60-c5b1-4b44-b512-1370f02d74de": "Blue",
    "a495bb70-c5b1-4b44-b512-1370f02d74de": "Yellow",
    "a495bb80-c5b1-4b44-b512-1370f02d74de": "Pink",
}

_celebration_shown = False


def _compute_led_state(brew_id):
    """Compute LED state from the current brew's readings."""
    global _celebration_shown

    brew = db.get_brew(brew_id)
    if not brew:
        led.update(0, "idle")
        return

    readings = db.get_readings(brew_id)
    if not readings:
        led.update(0, "idle")
        return

    og = brew["og"] or readings[0]["gravity"]
    sg = readings[-1]["gravity"]
    target_fg = brew["target_fg"] or 1.010
    temp_f = readings[-1]["temp_f"]

    # Attenuation progress
    if og > target_fg:
        progress = max(0, min(100, ((og - sg) / (og - target_fg)) * 100))
    else:
        progress = 0

    # Fermentation status (same logic as frontend)
    status = "active"
    if len(readings) >= 24:
        recent = readings[-12:]
        older = readings[-24:-12]
        recent_avg = sum(r["gravity"] for r in recent) / len(recent)
        older_avg = sum(r["gravity"] for r in older) / len(older)
        drop = older_avg - recent_avg
        if drop < 0.0005:
            status = "complete"
        elif drop < 0.002:
            status = "slowing"
    elif len(readings) < 2:
        status = "idle"

    # Temperature alert
    temp_alert = temp_f < brew["temp_low"] or temp_f > brew["temp_high"]

    led.update(progress, status, temp_alert)

    # Celebration on completion (once per brew)
    if status == "complete" and sg <= target_fg + 0.002 and not _celebration_shown:
        _celebration_shown = True
        led.celebrate()


def process_packet(data):
    """Process a BLE packet and extract Tilt data if present."""
    global _celebration_shown
    ev = BLEScanner.decode(data)
    beacon = IBeacon.decode(ev)

    if beacon:
        uuid = beacon.get("uuid", "").lower()
        if uuid in TILT_UUIDS:
            color = TILT_UUIDS[uuid]
            temp_f = beacon.get("major")
            sg = beacon.get("minor") / 1000
            timestamp = datetime.now().isoformat()

            brew_id = db.ensure_active_brew(color, timestamp)
            db.insert_reading(brew_id, timestamp, color, temp_f,
                              round((temp_f - 32) * 5 / 9, 1), sg)

            # Update LED strip
            _compute_led_state(brew_id)

            print(
                f"[{timestamp}] Tilt {color}: {temp_f}°F ({round((temp_f - 32) * 5 / 9, 1)}°C) SG: {sg:.3f}"
            )


async def main():
    print("Starting Tilt Monitor...")
    print("Scanning for Tilt Hydrometers (Ctrl+C to stop)\n")

    db.init_db()
    db.migrate_from_json()
    led.start()

    sock = create_bt_socket(0)
    fac = BLEScanner(process_packet)

    loop = asyncio.get_event_loop()
    transport, protocol = await loop.create_connection(fac, sock=sock)

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        transport.close()


if __name__ == "__main__":
    asyncio.run(main())
