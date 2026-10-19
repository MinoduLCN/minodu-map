#!/usr/bin/env python3
"""
NeoKeys + NeoPixel strip on ONE data line.

Wiring:  GPIO10 (SPI MOSI) -> NeoKey 1 -> NeoKey 2 -> NeoKey 3 -> NeoKey 4 -> 8-LED strip
Buttons: GPIO0, 5, 6, 13 (S+ to GPIO, S- to GND)

- Pixels 0-3: the keys. Each button cycles the color of its own key.
- Pixels 4-11: the strip. Loops rainbow -> comet -> breathing -> sparkle.

Ctrl+C turns everything off and exits.

Run with:  ~/neokey/bin/python keys.py
"""

import math
import random
import time

import board
import digitalio
import neopixel_spi

# ---- Configuration ---------------------------------------------------------

NUM_KEYS = 4
NUM_STRIP = 8
NUM_PIXELS = NUM_KEYS + NUM_STRIP
STRIP_START = NUM_KEYS  # first strip pixel in the chain

BRIGHTNESS = 0.3
SECONDS_PER_EFFECT = 8

# Button pins, in the same order as the key pixels in the chain.
# If pressing a button lights the wrong key, reorder this list.
BUTTON_PINS = [board.D26, board.D5, board.D6, board.D13]

KEY_COLORS = [
    (255, 0, 0),      # red
    (255, 80, 0),     # orange
    (255, 200, 0),    # yellow
    (0, 255, 0),      # green
    (0, 255, 200),    # cyan
    (0, 0, 255),      # blue
    (150, 0, 255),    # purple
    (255, 0, 120),    # pink
    (255, 255, 255),  # white
]

DEBOUNCE_S = 0.03

# ---- Setup -----------------------------------------------------------------

pixels = neopixel_spi.NeoPixel_SPI(
    board.SPI(),  # data out on MOSI = GPIO10
    NUM_PIXELS,
    brightness=BRIGHTNESS,
    auto_write=False,
    pixel_order=neopixel_spi.GRB,
)

buttons = []
for pin in BUTTON_PINS:
    btn = digitalio.DigitalInOut(pin)
    btn.direction = digitalio.Direction.INPUT
    btn.pull = digitalio.Pull.UP
    buttons.append(btn)

color_index = [i * 2 % len(KEY_COLORS) for i in range(NUM_KEYS)]
was_pressed = [False] * NUM_KEYS
last_change = [0.0] * NUM_KEYS


def draw_keys():
    for i in range(NUM_KEYS):
        pixels[i] = KEY_COLORS[color_index[i]]


def set_strip(i, color):
    pixels[STRIP_START + i] = color


def fill_strip(color):
    for i in range(NUM_STRIP):
        set_strip(i, color)


# ---- Strip animations ------------------------------------------------------
# Each effect is a generator: it draws one frame into the strip part of the
# chain, then yields how long to wait before the next frame. The main loop
# sends the whole chain out, so keys and strip update together.


def wheel(pos):
    pos %= 256
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)


def rainbow():
    offset = 0
    while True:
        for i in range(NUM_STRIP):
            set_strip(i, wheel(i * 256 // NUM_STRIP + offset))
        offset = (offset + 2) % 256
        yield 0.02


def comet(tail=4):
    hue, pos, direction = 0, 0, 1
    while True:
        r, g, b = wheel(hue)
        fill_strip((0, 0, 0))
        for t in range(tail):
            i = pos - t * direction
            if 0 <= i < NUM_STRIP:
                fade = (tail - t) / tail
                set_strip(i, (int(r * fade), int(g * fade), int(b * fade)))
        pos += direction
        if pos in (0, NUM_STRIP - 1):
            direction = -direction
            hue = (hue + 40) % 256
        yield 0.06


def breathe():
    start = time.monotonic()
    while True:
        t = time.monotonic() - start
        level = (math.sin(t * 2) + 1) / 2
        r, g, b = wheel(int(t * 20))
        fill_strip((int(r * level), int(g * level), int(b * level)))
        yield 0.02


def sparkle():
    buf = [(0, 0, 0)] * NUM_STRIP
    while True:
        buf = [(int(r * 0.8), int(g * 0.8), int(b * 0.8)) for r, g, b in buf]
        if random.random() < 0.5:
            buf[random.randrange(NUM_STRIP)] = wheel(random.randrange(256))
        for i, c in enumerate(buf):
            set_strip(i, c)
        yield 0.04


EFFECTS = [rainbow, comet, breathe, sparkle]

# ---- Main loop -------------------------------------------------------------

draw_keys()
print("Running. Press the keys to cycle colors, Ctrl+C to quit.")

effect_num = 0
effect = EFFECTS[effect_num]()
effect_end = time.monotonic() + SECONDS_PER_EFFECT
next_frame = 0.0

try:
    while True:
        now = time.monotonic()
        dirty = False

        # Buttons
        for i, btn in enumerate(buttons):
            pressed = not btn.value
            if pressed != was_pressed[i] and now - last_change[i] > DEBOUNCE_S:
                last_change[i] = now
                was_pressed[i] = pressed
                if pressed:
                    color_index[i] = (color_index[i] + 1) % len(KEY_COLORS)
                    draw_keys()
                    dirty = True

        # Strip animation
        if now >= effect_end:
            effect_num = (effect_num + 1) % len(EFFECTS)
            effect = EFFECTS[effect_num]()
            effect_end = now + SECONDS_PER_EFFECT
            next_frame = now
        if now >= next_frame:
            next_frame = now + next(effect)
            dirty = True

        if dirty:
            pixels.show()

        time.sleep(0.005)

except KeyboardInterrupt:
    pass
finally:
    pixels.fill((0, 0, 0))
    pixels.show()
    pixels.deinit()
    for btn in buttons:
        btn.deinit()
    print("\nAll off, bye.")