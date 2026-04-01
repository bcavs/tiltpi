#!/usr/bin/env python3
"""Tilt Hydrometer Monitor - reads BLE iBeacon data from Tilt devices."""

import asyncio
from datetime import datetime
from aioblescan import create_bt_socket, BLEScanner
from aioblescan.plugins.ibeacon import IBeacon

import db

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


def process_packet(data):
    """Process a BLE packet and extract Tilt data if present."""
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

            print(
                f"[{timestamp}] Tilt {color}: {temp_f}°F ({round((temp_f - 32) * 5 / 9, 1)}°C) SG: {sg:.3f}"
            )


async def main():
    print("Starting Tilt Monitor...")
    print("Scanning for Tilt Hydrometers (Ctrl+C to stop)\n")

    db.init_db()
    db.migrate_from_json()

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
