"""Run the pygame emulator with a tiny demo app wired in.

Launches a window that shows:
    - 4 button LEDs lit in each mode's color (active mode brighter)
    - 16-pixel strip rendering a scroll indicator: a dim bar in the mode color
      with one bright pixel at the current scroll position
    - Right-encoder press toggles mute; mute is shown as all-dim strip
    - A console log line for every button press / encoder click

Run from the repo root:
    python -m venv .venv
    source .venv/bin/activate
    pip install pygame
    python src/emulator_demo.py
"""

from __future__ import annotations

import sys
import time

import pygame

from config import BUTTON_MODES, MODE_COLORS, NUM_BUTTONS, NUM_STRIP, STRIP_START
from hal.emulator import EmulatorBoard


def dim(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(c * factor))) for c in color)


def main() -> int:
    board = EmulatorBoard()
    clock = pygame.time.Clock()

    mode_idx = 0
    scroll = 0
    volume = 50  # 0..100
    muted = False

    # edge-tracking state
    prev_buttons = [False] * NUM_BUTTONS
    prev_enc_pos = [board.encoder_position(0), board.encoder_position(1)]
    prev_enc_btn = [False, False]

    def log(msg: str) -> None:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

    log("emulator demo running — press buttons 1-4, spin encoders, Q to quit")

    while board.running:
        board.poll()

        # button edges
        for i in range(NUM_BUTTONS):
            if board.buttons[i] and not prev_buttons[i]:
                mode_idx = i
                scroll = 0
                log(f"button {i + 1} → mode = {BUTTON_MODES[i]}")
            prev_buttons[i] = board.buttons[i]

        # left encoder → scroll
        pos0 = board.encoder_position(0)
        if pos0 != prev_enc_pos[0]:
            delta = pos0 - prev_enc_pos[0]
            prev_enc_pos[0] = pos0
            scroll = (scroll + delta) % NUM_STRIP
            log(f"scroll → {scroll}")

        # left encoder press → "select"
        if board.encoder_buttons[0] and not prev_enc_btn[0]:
            log(f"select item {scroll} in {BUTTON_MODES[mode_idx]}")
        prev_enc_btn[0] = board.encoder_buttons[0]

        # right encoder → volume
        pos1 = board.encoder_position(1)
        if pos1 != prev_enc_pos[1]:
            delta = pos1 - prev_enc_pos[1]
            prev_enc_pos[1] = pos1
            volume = max(0, min(100, volume + delta * 5))
            log(f"volume → {volume}")

        # right encoder press → mute
        if board.encoder_buttons[1] and not prev_enc_btn[1]:
            muted = not muted
            log(f"mute → {muted}")
        prev_enc_btn[1] = board.encoder_buttons[1]

        # --- paint LEDs -----------------------------------------------------
        active_mode = BUTTON_MODES[mode_idx]
        for i, mode in enumerate(BUTTON_MODES):
            base = MODE_COLORS[mode]
            board.pixels[i] = base if i == mode_idx else dim(base, 0.15)

        base = MODE_COLORS[active_mode]
        strip_dim = dim(base, 0.08) if not muted else (10, 10, 10)
        for i in range(NUM_STRIP):
            board.pixels[STRIP_START + i] = strip_dim
        if not muted:
            vol_fill = int(NUM_STRIP * (volume / 100))
            # faint "volume floor" rendered as a brighter tail from the left
            for i in range(vol_fill):
                board.pixels[STRIP_START + i] = dim(base, 0.25)
            board.pixels[STRIP_START + scroll] = base

        board.show()
        clock.tick(60)

    board.shutdown()
    log("bye")
    return 0


if __name__ == "__main__":
    sys.exit(main())
