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
    """Enable the continuous celebration rainbow."""
    with _lock:
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
        _render_rainbow_chase()
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


def _render_rainbow_chase():
    """Render one frame of a Grateful Dead liquid light show.

    Psychedelic oil-projection effect with the Dead's palette:
    deep red, electric blue, warm amber, purple, tie-dye green.
    Colors morph and blend organically with occasional lightning bolt flashes.
    """
    if _strip is None:
        return

    t = time.time()

    # Dead palette — rich, saturated concert poster colors
    palette = [
        (200, 30, 30),   # Steal Your Face red
        (180, 50, 180),  # purple
        (30, 80, 220),   # electric blue
        (20, 160, 100),  # tie-dye green
        (220, 140, 20),  # amber/gold
        (200, 40, 100),  # hot pink
        (30, 80, 220),   # electric blue again for weight
        (200, 30, 30),   # red again to loop smoothly
    ]

    # Slow drift through the palette — each LED samples a different point
    # on a smoothly interpolated color wave that shifts over time
    wave_speed = 0.15   # how fast the colors drift
    wave_stretch = 1.8  # how spread out colors are across the strip
    breathe_speed = 0.7 # breathing/pulsing speed

    for i in range(LED_COUNT):
        # Each LED's position in the color wave
        pos = (i / LED_COUNT * wave_stretch + t * wave_speed) % 1.0
        # Map to palette with smooth interpolation
        scaled = pos * (len(palette) - 1)
        idx = int(scaled)
        frac = scaled - idx
        c1 = palette[idx]
        c2 = palette[min(idx + 1, len(palette) - 1)]
        r = c1[0] + (c2[0] - c1[0]) * frac
        g = c1[1] + (c2[1] - c1[1]) * frac
        b = c1[2] + (c2[2] - c1[2]) * frac

        # Organic breathing — overlapping sine waves at different frequencies
        # gives that liquid, wobbly light-show feel
        breathe = 0.5 + 0.25 * math.sin(t * breathe_speed + i * 0.4)
        breathe += 0.15 * math.sin(t * breathe_speed * 1.7 - i * 0.25)
        breathe += 0.1 * math.sin(t * breathe_speed * 0.6 + i * 0.8)
        breathe = max(0.15, min(1.0, breathe))

        _strip[i] = (int(r * breathe), int(g * breathe), int(b * breathe))

    # Lightning bolt flash — Steal Your Face nod
    # Brief white flash that races across the strip every ~8 seconds
    bolt_cycle = t % 8.0
    if bolt_cycle < 0.3:
        bolt_pos = (bolt_cycle / 0.3) * LED_COUNT
        for i in range(LED_COUNT):
            dist = abs(i - bolt_pos)
            if dist < 3:
                flash = 1.0 - (dist / 3)
                flash = flash * flash
                existing = _strip[i]
                _strip[i] = (
                    min(255, int(existing[0] + 220 * flash)),
                    min(255, int(existing[1] + 220 * flash)),
                    min(255, int(existing[2] + 220 * flash)),
                )

    _strip.show()


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
