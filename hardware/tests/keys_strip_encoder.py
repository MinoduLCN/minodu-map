#!/usr/bin/env python3
"""
NeoKeys + NeoPixel strip on ONE data line, driven by Stemma QT rotary encoders.

Wiring:  GPIO10 (SPI MOSI) -> NeoKey 1 -> NeoKey 2 -> NeoKey 3 -> NeoKey 4 -> 8-LED strip
Buttons: GPIO0, 5, 6, 13 (S+ to GPIO, S- to GND)
Encoders: Adafruit Stemma QT rotary encoders (seesaw), chained on I2C.
          Default address is 0x36; bridge the A0 jumper on a second board to
          move it to 0x37.

- Pixels 0-3: the keys. Each button cycles the color of its own key.
- Pixels 4-11: the strip. Each encoder owns one pixel on the strip.
    - Turning an encoder moves its pixel along the strip.
    - Pushing an encoder cycles the color of its pixel.
    - If two encoders land on the same strip position, the later-indexed
      encoder's color wins.

Ctrl+C turns everything off and exits.

Run with:  ~/neokey/bin/python keys_strip_encoder.py
"""

import time

import board
import digitalio
import neopixel_spi
from adafruit_seesaw import digitalio as seesaw_digitalio
from adafruit_seesaw import rotaryio, seesaw

# ---- Configuration ---------------------------------------------------------

NUM_KEYS = 4
NUM_STRIP = 8
NUM_PIXELS = NUM_KEYS + NUM_STRIP
STRIP_START = NUM_KEYS  # first strip pixel in the chain

BRIGHTNESS = 0.3

# Button pins, in the same order as the key pixels in the chain.
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

# Stemma QT rotary encoders (Adafruit 4991 / seesaw).
# One entry per encoder; its index also chooses its starting strip pixel and
# starting color.
ENCODER_I2C_ADDRS = [0x36, 0x37]
ENCODER_SWITCH_PIN = 24  # seesaw pin for the push switch (same on each board)
# seesaw I2C reads sometimes return a corrupted 32-bit value; any single-loop
# delta larger than this is treated as a glitch and discarded.
ENCODER_MAX_SANE_DELTA = 100

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

i2c = board.I2C()


def read_encoder_stable(enc):
    """Return a position reading that repeats; filters seesaw I2C glitches."""
    prev = enc.position
    for _ in range(5):
        time.sleep(0.005)
        cur = enc.position
        if cur == prev:
            return cur
        prev = cur
    return prev


encoders = []       # rotaryio.IncrementalEncoder
enc_switches = []   # seesaw_digitalio.DigitalIO
enc_last_pos = []   # last stable position seen
enc_strip_pos = []  # strip pixel index owned by this encoder
enc_color = []      # color index owned by this encoder
enc_was_pressed = []
enc_last_change = []

for idx, addr in enumerate(ENCODER_I2C_ADDRS):
    ss = seesaw.Seesaw(i2c, addr=addr)
    enc = rotaryio.IncrementalEncoder(ss)
    ss.pin_mode(ENCODER_SWITCH_PIN, ss.INPUT_PULLUP)
    sw = seesaw_digitalio.DigitalIO(ss, ENCODER_SWITCH_PIN)

    encoders.append(enc)
    enc_switches.append(sw)
    enc_last_pos.append(read_encoder_stable(enc))
    enc_strip_pos.append(idx % NUM_STRIP)
    enc_color.append((idx * 3) % len(KEY_COLORS))
    enc_was_pressed.append(False)
    enc_last_change.append(0.0)

color_index = [i * 2 % len(KEY_COLORS) for i in range(NUM_KEYS)]
was_pressed = [False] * NUM_KEYS
last_change = [0.0] * NUM_KEYS


def draw_keys():
    for i in range(NUM_KEYS):
        pixels[i] = KEY_COLORS[color_index[i]]


def draw_strip():
    for i in range(NUM_STRIP):
        pixels[STRIP_START + i] = (0, 0, 0)
    # Later encoders overwrite earlier ones on a tie.
    for pos, cidx in zip(enc_strip_pos, enc_color):
        pixels[STRIP_START + pos] = KEY_COLORS[cidx]


def startup_animation():
    """Prove the strip is wired and addressable."""
    for i in range(NUM_STRIP):
        pixels[STRIP_START + i] = (255, 255, 255)
    pixels.show()
    time.sleep(0.3)

    for color in [(255, 0, 0), (0, 255, 0), (0, 0, 255)]:
        for i in range(NUM_STRIP):
            for j in range(NUM_STRIP):
                pixels[STRIP_START + j] = (0, 0, 0)
            pixels[STRIP_START + i] = color
            pixels.show()
            time.sleep(0.06)

    for i in range(NUM_STRIP):
        pixels[STRIP_START + i] = (0, 0, 0)
    pixels.show()


# ---- Main loop -------------------------------------------------------------

draw_keys()
pixels.show()
startup_animation()
draw_strip()
pixels.show()
print(f"Running with {len(encoders)} encoder(s). Ctrl+C to quit.")

try:
    while True:
        now = time.monotonic()
        dirty = False

        # NeoKey buttons: cycle each key's own color.
        for i, btn in enumerate(buttons):
            pressed = not btn.value
            if pressed != was_pressed[i] and now - last_change[i] > DEBOUNCE_S:
                last_change[i] = now
                was_pressed[i] = pressed
                if pressed:
                    color_index[i] = (color_index[i] + 1) % len(KEY_COLORS)
                    draw_keys()
                    dirty = True

        # Each encoder: rotation moves its pixel, press cycles its color.
        for i, enc in enumerate(encoders):
            pos = enc.position
            if pos != enc_last_pos[i]:
                delta = pos - enc_last_pos[i]
                if abs(delta) > ENCODER_MAX_SANE_DELTA:
                    enc_last_pos[i] = pos  # resync, drop glitch
                else:
                    enc_last_pos[i] = pos
                    enc_strip_pos[i] = (enc_strip_pos[i] + delta) % NUM_STRIP
                    draw_strip()
                    dirty = True

            enc_pressed = not enc_switches[i].value
            if enc_pressed != enc_was_pressed[i] and now - enc_last_change[i] > DEBOUNCE_S:
                enc_last_change[i] = now
                enc_was_pressed[i] = enc_pressed
                if enc_pressed:
                    enc_color[i] = (enc_color[i] + 1) % len(KEY_COLORS)
                    draw_strip()
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
