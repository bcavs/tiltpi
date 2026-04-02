#!/usr/bin/env python3
"""Test LED states by cycling through fermentation scenarios."""

import time
import led

HOLD = 5  # seconds per state


def main():
    led.start()  # init + start background render loop

    states = [
        ("Idle (amber breathing)", "idle", 0, False),
        ("Active — early (10%)", "active", 10, False),
        ("Active — mid (40%)", "active", 40, False),
        ("Active — high (70%)", "active", 70, False),
        ("Slowing (85%)", "slowing", 85, False),
        ("Temperature alert!", "active", 50, True),
        ("Complete (100%)", "complete", 100, False),
    ]

    print("LED test — cycling through states\n")

    for label, status, progress, temp_alert in states:
        print(f"  {label}")
        led.update(progress, status, temp_alert)
        time.sleep(HOLD)

    print("\n  Celebration animation!")
    led.celebrate()
    time.sleep(6)  # give the render loop time to play it

    print("\n  Back to idle")
    led.update(0, "idle")
    time.sleep(HOLD)

    print("\nDone.")


if __name__ == "__main__":
    main()
