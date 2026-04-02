#!/usr/bin/env python3
"""LED strip feedback for TiltPi fermentation status.

Drives a WS2812B NeoPixel strip to show:
- Fermentation progress (fill level = attenuation %)
- Status color (green=active, amber=slowing, copper=complete)
- Red flash override when temperature is out of range
- Rainbow celebration when fermentation completes
"""

import math
import time
import threading

LED_PIN = 18
LED_COUNT = 24
BRIGHTNESS = 0.15

_strip = None
_lock = threading.Lock()
_state = {
    "progress": 0.0,       # 0-100 attenuation %
    "status": "idle",       # idle, active, slowing, complete
    "temp_alert": False,
    "celebrating": False,
}

# Try to import neopixel — gracefully degrade if not on Pi
try:
    import board
    import neopixel

    _BOARD_PINS = {18: board.D18, 21: board.D21, 10: board.D10, 12: board.D12}
    _HAS_HARDWARE = True
except (ImportError, NotImplementedError):
    _HAS_HARDWARE = False


def init():
    """Initialize the LED strip. Call once on startup."""
    global _strip
    if not _HAS_HARDWARE:
        print("[LED] No NeoPixel hardware — LED feedback disabled")
        return
    _strip = neopixel.NeoPixel(
        _BOARD_PINS[LED_PIN],
        LED_COUNT,
        brightness=BRIGHTNESS,
        auto_write=False,
        pixel_order=neopixel.GRB,
    )
    _strip.fill((0, 0, 0))
    _strip.show()
    print(f"[LED] Strip initialized: {LED_COUNT} pixels on GPIO{LED_PIN}")


def _status_color(progress, status):
    """Return (r, g, b) based on fermentation status.

    Active: green -> yellow as progress increases
    Slowing: warm amber
    Complete: rich copper
    """
    if status == "complete":
        return (140, 70, 15)  # copper
    if status == "slowing":
        return (160, 100, 10)  # amber
    # Active: green at 0%, transitioning to yellow-green at 100%
    p = max(0, min(100, progress))
    r = int(140 * (p / 100))
    g = 140
    return (r, g, 0)


def _spark_overlay(base, index, leds_on):
    """Dim spark effect sweeping across lit LEDs."""
    if leds_on <= 0:
        return base
    period = 4.0
    pos = (time.time() % period) / period * leds_on
    dist = abs(index - pos)
    if dist > 1.2:
        return base
    dim = 1.0 - (1.0 - min(dist, 1.0)) * 0.8
    return (int(base[0] * dim), int(base[1] * dim), int(base[2] * dim))


def _wheel(pos):
    """Color wheel: 0-255 -> RGB."""
    pos = pos % 256
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)


def update(progress, status, temp_alert=False):
    """Update the LED state. Called by tilt_monitor after each reading."""
    with _lock:
        _state["progress"] = progress
        _state["status"] = status
        _state["temp_alert"] = temp_alert


def celebrate():
    """Trigger the completion celebration animation."""
    with _lock:
        if _state["celebrating"]:
            return
        _state["celebrating"] = True


def _render_frame():
    """Render one frame of LED output based on current state."""
    if _strip is None:
        return

    with _lock:
        progress = _state["progress"]
        status = _state["status"]
        temp_alert = _state["temp_alert"]
        celebrating = _state["celebrating"]

    if celebrating:
        _play_celebration()
        with _lock:
            _state["celebrating"] = False
        return

    # Temperature alert: red flash
    if temp_alert:
        phase = (time.time() * 3) % 1.0
        brightness = 0.3 + 0.7 * abs(math.sin(phase * math.pi))
        r = int(200 * brightness)
        for i in range(LED_COUNT):
            _strip[i] = (r, 0, 0)
        _strip.show()
        return

    # Idle: dim breathing amber
    if status == "idle":
        phase = (time.time() * 0.5) % 1.0
        brightness = 0.05 + 0.1 * abs(math.sin(phase * math.pi))
        val = int(180 * brightness)
        for i in range(LED_COUNT):
            _strip[i] = (val, int(val * 0.55), 0)
        _strip.show()
        return

    # Progress fill with status color + spark
    leds_on = max(0, int((progress / 100.0) * LED_COUNT))
    color = _status_color(progress, status)

    for i in range(LED_COUNT):
        if i < leds_on:
            _strip[i] = _spark_overlay(color, i, leds_on)
        else:
            _strip[i] = (0, 0, 0)
    _strip.show()


def _play_celebration():
    """Rainbow comet sweep, then settle to full copper."""
    if _strip is None:
        return

    # Rainbow comet — two laps
    tail = 6
    steps = LED_COUNT * 2
    for step in range(steps):
        head = step % LED_COUNT
        speed = 1.0 - (step / steps) * 0.6
        for i in range(LED_COUNT):
            dist = (head - i) % LED_COUNT
            if dist < tail:
                fade = 1.0 - (dist / tail)
                hue = (step * 12 + i * 256 // LED_COUNT) % 256
                r, g, b = _wheel(hue)
                _strip[i] = (int(r * fade), int(g * fade), int(b * fade))
            else:
                _strip[i] = (0, 0, 0)
        _strip.show()
        time.sleep(0.025 * speed)

    # Flash white then fade to copper
    _strip.fill((180, 180, 180))
    _strip.show()
    time.sleep(0.25)

    copper = (140, 70, 15)
    for step in range(20):
        t = step / 19
        r = int(180 + (copper[0] - 180) * t)
        g = int(180 + (copper[1] - 180) * t)
        b = int(180 + (copper[2] - 180) * t)
        _strip.fill((max(0, r), max(0, g), max(0, b)))
        _strip.show()
        time.sleep(0.03)


def _run_loop():
    """Background render loop — updates LEDs ~30fps."""
    while True:
        try:
            _render_frame()
        except Exception as e:
            print(f"[LED] Error: {e}")
        time.sleep(0.033)


def start():
    """Start the LED render loop in a background thread."""
    if not _HAS_HARDWARE:
        return
    init()
    t = threading.Thread(target=_run_loop, daemon=True)
    t.start()
    print("[LED] Render loop started")
