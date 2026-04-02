#!/usr/bin/env python3
"""Test individual LED states.

Usage:
  sudo venv/bin/python test_leds.py              # cycle through all states
  sudo venv/bin/python test_leds.py idle          # test idle
  sudo venv/bin/python test_leds.py active        # test active (50%)
  sudo venv/bin/python test_leds.py slowing       # test slowing (85%)
  sudo venv/bin/python test_leds.py complete       # test complete (Dead light show)
  sudo venv/bin/python test_leds.py temp           # test temperature alert
  sudo venv/bin/python test_leds.py progress 70    # test active at specific %
"""

import sys
import time
import led


def run_state(label, status, progress, temp_alert, duration=None):
    print(f"  {label}")
    led.update(progress, status, temp_alert)
    if status == "complete":
        led.celebrate()
    if duration:
        time.sleep(duration)
    else:
        # Run until Ctrl+C
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass


def cycle_all():
    states = [
        ("Idle (amber breathing)", "idle", 0, False),
        ("Active — early (10%)", "active", 10, False),
        ("Active — mid (40%)", "active", 40, False),
        ("Active — high (70%)", "active", 70, False),
        ("Slowing (85%)", "slowing", 85, False),
        ("Temperature alert!", "active", 50, True),
        ("Complete (Grateful Dead)", "complete", 100, False),
    ]

    print("Cycling through all states (5s each)\n")
    for label, status, progress, temp_alert in states:
        run_state(label, status, progress, temp_alert, duration=5)
        # Reset celebrating flag between states
        with led._lock:
            led._state["celebrating"] = False

    print("\n  Back to idle")
    led.update(0, "idle")
    time.sleep(3)
    print("Done.")


def main():
    led.start()

    arg = sys.argv[1] if len(sys.argv) > 1 else None

    if arg is None:
        cycle_all()
        return

    print(f"\nRunning '{arg}' — Ctrl+C to stop\n")

    if arg == "idle":
        run_state("Idle", "idle", 0, False)
    elif arg == "active":
        run_state("Active (50%)", "active", 50, False)
    elif arg == "slowing":
        run_state("Slowing (85%)", "slowing", 85, False)
    elif arg == "complete":
        run_state("Complete (Grateful Dead)", "complete", 100, False)
    elif arg == "temp":
        run_state("Temperature alert", "active", 50, True)
    elif arg == "progress":
        pct = float(sys.argv[2]) if len(sys.argv) > 2 else 50
        run_state(f"Active ({pct}%)", "active", pct, False)
    else:
        print(f"Unknown state: {arg}")
        print("Options: idle, active, slowing, complete, temp, progress <pct>")


if __name__ == "__main__":
    main()
