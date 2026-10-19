#!/usr/bin/env python3
"""
Four Adafruit NeoKey breakouts on a Raspberry Pi.

- NeoPixel data (chained through all four NeoKeys): GPIO27
- Buttons: GPIO0, GPIO5, GPIO6, GPIO13  (S+ to GPIO, S- to GND)

Each button cycles the color of its own key's pixel.
Ctrl+C turns the pixels off and exits.
"""

import time

import board
import digitalio
import neopixel

# ---- Configuration ---------------------------------------------------------

PIXEL_PIN = board.D12
NUM_PIXELS = 4
BRIGHTNESS = 0.3  # 0.0 - 1.0

# Button pins, in the same order as the pixels in the data chain.
# If pressing a button lights the wrong key, reorder this list.
BUTTON_PINS = [board.D26, board.D5, board.D6, board.D13]

COLORS = [
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

pixels = neopixel.NeoPixel(
    PIXEL_PIN,
    NUM_PIXELS,
    brightness=BRIGHTNESS,
    auto_write=False,
    pixel_order=neopixel.GRB,
)

buttons = []
for pin in BUTTON_PINS:
    btn = digitalio.DigitalInOut(pin)
    btn.direction = digitalio.Direction.INPUT
    btn.pull = digitalio.Pull.UP  # switch pulls the pin to GND when pressed
    buttons.append(btn)

# Start each key on a different color so it's obvious they all work.
color_index = [i * 2 % len(COLORS) for i in range(NUM_PIXELS)]
was_pressed = [False] * NUM_PIXELS
last_change = [0.0] * NUM_PIXELS


def show_all():
    for i in range(NUM_PIXELS):
        pixels[i] = COLORS[color_index[i]]
    pixels.show()


# ---- Main loop -------------------------------------------------------------

show_all()
print("Running. Press the keys to cycle colors, Ctrl+C to quit.")

try:
    while True:
        now = time.monotonic()
        changed = False

        for i, btn in enumerate(buttons):
            pressed = not btn.value  # active low
            if pressed != was_pressed[i] and now - last_change[i] > DEBOUNCE_S:
                last_change[i] = now
                was_pressed[i] = pressed
                if pressed:  # act on press, not release
                    color_index[i] = (color_index[i] + 1) % len(COLORS)
                    print(f"Key {i + 1} -> color {color_index[i]}")
                    changed = True

        if changed:
            show_all()

        time.sleep(0.005)

except KeyboardInterrupt:
    pass
finally:
    pixels.fill((0, 0, 0))
    pixels.show()
    pixels.deinit()
    for btn in buttons:
        btn.deinit()
    print("\nPixels off, bye.")