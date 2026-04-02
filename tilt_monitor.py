#!/usr/bin/env python3
"""Tilt Hydrometer Monitor - reads BLE iBeacon data from Tilt devices."""

import asyncio
import json
from datetime import datetime
from aioblescan import create_bt_socket, BLEScanRequester, HCI_Event
from aioblescan.plugins import Tilt

import db
import led

# Tilt UUID -> color mapping (UUIDs without dashes, as returned by the Tilt plugin)
TILT_UUIDS = {
    "a495bb10c5b14b44b5121370f02d74de": "Red",
    "a495bb20c5b14b44b5121370f02d74de": "Green",
    "a495bb30c5b14b44b5121370f02d74de": "Black",
    "a495bb40c5b14b44b5121370f02d74de": "Purple",
    "a495bb50c5b14b44b5121370f02d74de": "Orange",
    "a495bb60c5b14b44b5121370f02d74de": "Blue",
    "a495bb70c5b14b44b5121370f02d74de": "Yellow",
    "a495bb80c5b14b44b5121370f02d74de": "Pink",
}

_tilt_decoder = Tilt()
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
    ev = HCI_Event()
    ev.decode(data)

    result = _tilt_decoder.decode(ev)
    if result:
        parsed = json.loads(result)
        uuid = parsed["uuid"].lower()
        if uuid in TILT_UUIDS:
            color = TILT_UUIDS[uuid]
            temp_f = parsed["major"]
            sg = parsed["minor"] / 1000
            timestamp = datetime.now().isoformat()

            brew_id = db.ensure_active_brew(color, timestamp)
            db.insert_reading(brew_id, timestamp, color, temp_f,
                              round((temp_f - 32) * 5 / 9, 1), sg)

            # Update LED strip
            _compute_led_state(brew_id)

            print(
                f"[{timestamp}] Tilt {color}: {temp_f}\u00b0F ({round((temp_f - 32) * 5 / 9, 1)}\u00b0C) SG: {sg:.3f}"
            )


async def main():
    print("Starting Tilt Monitor...")
    print("Scanning for Tilt Hydrometers (Ctrl+C to stop)\n")

    db.init_db()
    db.migrate_from_json()
    led.start()

    sock = create_bt_socket(0)
    loop = asyncio.get_running_loop()
    transport, conn = await loop._create_connection_transport(
        sock, BLEScanRequester, None, None
    )
    conn.process = process_packet
    await conn.send_scan_request()

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        await conn.stop_scan_request()
        transport.close()


if __name__ == "__main__":
    asyncio.run(main())
