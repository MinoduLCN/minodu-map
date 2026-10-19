"""Pygame-based emulator for the minodu-map hardware.

Layout (one window, ~900x420):
    top row:    16 strip LEDs in a horizontal line
    middle row: 4 big button LEDs
    bottom row: 2 encoder dials with a rotation indicator

Interaction:
    Mouse: click a button LED to press it; click an encoder's dial to click
           it; scroll wheel over an encoder rotates it; drag an encoder rotates.
    Keyboard:
        1..4           press buttons 1..4
        a / d          left encoder: rotate CCW / CW
        s              left encoder: click
        left / right   right encoder: rotate CCW / CW
        down           right encoder: click
        q or ESC       quit
"""

from __future__ import annotations

import math
import sys

import pygame

from config import NUM_BUTTONS, NUM_ENCODERS, NUM_PIXELS, NUM_STRIP, STRIP_START
from hal.base import Board

WIN_W, WIN_H = 940, 440
BG = (24, 24, 28)
PANEL = (36, 36, 42)
OUTLINE = (90, 90, 100)
TEXT = (210, 210, 215)

STRIP_LED_RADIUS = 14
STRIP_LED_SPACING = 50
STRIP_Y = 70

BTN_RADIUS = 36
BTN_SPACING = 150
BTN_Y = 200

ENC_RADIUS = 54
ENC_SPACING = 320
ENC_Y = 340

STEPS_PER_TURN = 24


class EmulatorBoard(Board):
    def __init__(self, title: str = "minodu-map emulator") -> None:
        pygame.init()
        pygame.display.set_caption(title)
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        self.font = pygame.font.SysFont("Menlo,Monaco,monospace", 14)
        self.big_font = pygame.font.SysFont("Menlo,Monaco,monospace", 16, bold=True)

        self.pixels: list[tuple[int, int, int]] = [(0, 0, 0)] * NUM_PIXELS
        self.buttons: list[bool] = [False] * NUM_BUTTONS
        self.encoder_buttons: list[bool] = [False] * NUM_ENCODERS

        self._enc_positions: list[int] = [0] * NUM_ENCODERS
        self._enc_angles: list[float] = [0.0] * NUM_ENCODERS  # for display
        self._enc_drag_last: list[float | None] = [None] * NUM_ENCODERS

        self._running = True

        strip_total_w = (NUM_STRIP - 1) * STRIP_LED_SPACING
        self._strip_x0 = (WIN_W - strip_total_w) // 2
        btn_total_w = (NUM_BUTTONS - 1) * BTN_SPACING
        self._btn_x0 = (WIN_W - btn_total_w) // 2
        enc_total_w = (NUM_ENCODERS - 1) * ENC_SPACING
        self._enc_x0 = (WIN_W - enc_total_w) // 2

    @property
    def running(self) -> bool:
        return self._running

    # --- public API ---------------------------------------------------------

    def encoder_position(self, idx: int) -> int:
        return self._enc_positions[idx]

    def show(self) -> None:
        self._draw()
        pygame.display.flip()

    def poll(self) -> None:
        for event in pygame.event.get():
            self._handle_event(event)

    def shutdown(self) -> None:
        pygame.quit()

    # --- geometry helpers ---------------------------------------------------

    def _strip_pos(self, i: int) -> tuple[int, int]:
        return self._strip_x0 + i * STRIP_LED_SPACING, STRIP_Y

    def _button_pos(self, i: int) -> tuple[int, int]:
        return self._btn_x0 + i * BTN_SPACING, BTN_Y

    def _encoder_pos(self, i: int) -> tuple[int, int]:
        return self._enc_x0 + i * ENC_SPACING, ENC_Y

    def _hit_button(self, pos: tuple[int, int]) -> int | None:
        for i in range(NUM_BUTTONS):
            cx, cy = self._button_pos(i)
            if (pos[0] - cx) ** 2 + (pos[1] - cy) ** 2 <= BTN_RADIUS**2:
                return i
        return None

    def _hit_encoder(self, pos: tuple[int, int]) -> int | None:
        for i in range(NUM_ENCODERS):
            cx, cy = self._encoder_pos(i)
            if (pos[0] - cx) ** 2 + (pos[1] - cy) ** 2 <= ENC_RADIUS**2:
                return i
        return None

    # --- input handling -----------------------------------------------------

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return

        if event.type == pygame.KEYDOWN:
            self._handle_key(event.key, pressed=True)
        elif event.type == pygame.KEYUP:
            self._handle_key(event.key, pressed=False)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._handle_mouse_down(event)
        elif event.type == pygame.MOUSEBUTTONUP:
            self._handle_mouse_up(event)
        elif event.type == pygame.MOUSEMOTION:
            self._handle_mouse_motion(event)
        elif event.type == pygame.MOUSEWHEEL:
            self._handle_wheel(event)

    _KEY_TO_BUTTON = {
        pygame.K_1: 0,
        pygame.K_2: 1,
        pygame.K_3: 2,
        pygame.K_4: 3,
    }

    def _handle_key(self, key: int, pressed: bool) -> None:
        if key in (pygame.K_ESCAPE, pygame.K_q):
            if pressed:
                self._running = False
            return

        if key in self._KEY_TO_BUTTON:
            self.buttons[self._KEY_TO_BUTTON[key]] = pressed
            return

        if not pressed:
            # encoder click release
            if key == pygame.K_s:
                self.encoder_buttons[0] = False
            elif key == pygame.K_DOWN:
                self.encoder_buttons[1] = False
            return

        # key-down for encoders
        if key == pygame.K_a:
            self._rotate_encoder(0, -1)
        elif key == pygame.K_d:
            self._rotate_encoder(0, +1)
        elif key == pygame.K_s:
            self.encoder_buttons[0] = True
        elif key == pygame.K_LEFT:
            self._rotate_encoder(1, -1)
        elif key == pygame.K_RIGHT:
            self._rotate_encoder(1, +1)
        elif key == pygame.K_DOWN:
            self.encoder_buttons[1] = True

    def _handle_mouse_down(self, event: pygame.event.Event) -> None:
        if event.button == 1:
            bi = self._hit_button(event.pos)
            if bi is not None:
                self.buttons[bi] = True
                return
            ei = self._hit_encoder(event.pos)
            if ei is not None:
                # left-click on encoder = click it; drag with shift-ish? keep
                # it simple: a right-click or drag rotates, plain click clicks.
                self.encoder_buttons[ei] = True
                self._enc_drag_last[ei] = self._mouse_angle(ei, event.pos)
        elif event.button == 3:
            ei = self._hit_encoder(event.pos)
            if ei is not None:
                self._enc_drag_last[ei] = self._mouse_angle(ei, event.pos)

    def _handle_mouse_up(self, event: pygame.event.Event) -> None:
        if event.button == 1:
            for i in range(NUM_BUTTONS):
                self.buttons[i] = False
            for i in range(NUM_ENCODERS):
                self.encoder_buttons[i] = False
                self._enc_drag_last[i] = None
        elif event.button == 3:
            for i in range(NUM_ENCODERS):
                self._enc_drag_last[i] = None

    def _handle_mouse_motion(self, event: pygame.event.Event) -> None:
        for i in range(NUM_ENCODERS):
            if self._enc_drag_last[i] is None:
                continue
            now = self._mouse_angle(i, event.pos)
            delta = now - self._enc_drag_last[i]
            # unwrap
            while delta > math.pi:
                delta -= 2 * math.pi
            while delta < -math.pi:
                delta += 2 * math.pi
            steps = int(delta / (2 * math.pi) * STEPS_PER_TURN)
            if steps != 0:
                self._rotate_encoder(i, steps)
                self._enc_drag_last[i] = now

    def _handle_wheel(self, event: pygame.event.Event) -> None:
        pos = pygame.mouse.get_pos()
        ei = self._hit_encoder(pos)
        if ei is not None:
            self._rotate_encoder(ei, event.y)

    def _mouse_angle(self, enc_idx: int, pos: tuple[int, int]) -> float:
        cx, cy = self._encoder_pos(enc_idx)
        return math.atan2(pos[1] - cy, pos[0] - cx)

    def _rotate_encoder(self, idx: int, steps: int) -> None:
        self._enc_positions[idx] += steps
        self._enc_angles[idx] += steps * (2 * math.pi / STEPS_PER_TURN)

    # --- rendering ----------------------------------------------------------

    def _draw(self) -> None:
        self.screen.fill(BG)

        self._label("LED strip (16)", 20, STRIP_Y - 30)
        for i in range(NUM_STRIP):
            x, y = self._strip_pos(i)
            color = self.pixels[STRIP_START + i]
            self._draw_led(x, y, STRIP_LED_RADIUS, color)
            idx_label = self.font.render(str(i), True, (120, 120, 130))
            self.screen.blit(idx_label, idx_label.get_rect(center=(x, y + 24)))

        self._label("Button LEDs (4)   ← keys 1-4", 20, BTN_Y - 60)
        for i in range(NUM_BUTTONS):
            x, y = self._button_pos(i)
            color = self.pixels[i]
            pressed = self.buttons[i]
            self._draw_button(x, y, color, pressed, label=str(i + 1))

        self._label("Encoders   ← left: A/D rotate, S click   right: ←/→ rotate, ↓ click", 20, ENC_Y - 80)
        for i in range(NUM_ENCODERS):
            x, y = self._encoder_pos(i)
            angle = self._enc_angles[i]
            pos = self._enc_positions[i]
            pressed = self.encoder_buttons[i]
            label = ("left (scroll/select)", "right (volume/mute)")[i]
            self._draw_encoder(x, y, angle, pos, pressed, label)

        hint = self.font.render("Click LEDs/encoders with mouse  ·  wheel over encoder = rotate  ·  Q to quit", True, (140, 140, 150))
        self.screen.blit(hint, hint.get_rect(center=(WIN_W // 2, WIN_H - 16)))

    def _label(self, text: str, x: int, y: int) -> None:
        surf = self.big_font.render(text, True, TEXT)
        self.screen.blit(surf, (x, y))

    def _draw_led(self, x: int, y: int, r: int, color: tuple[int, int, int]) -> None:
        pygame.draw.circle(self.screen, PANEL, (x, y), r + 2)
        pygame.draw.circle(self.screen, color, (x, y), r)
        pygame.draw.circle(self.screen, OUTLINE, (x, y), r + 2, width=1)

    def _draw_button(self, x: int, y: int, color: tuple[int, int, int], pressed: bool, label: str) -> None:
        outer = BTN_RADIUS + (6 if pressed else 2)
        pygame.draw.circle(self.screen, (60, 60, 70) if pressed else PANEL, (x, y), outer)
        pygame.draw.circle(self.screen, color, (x, y), BTN_RADIUS)
        pygame.draw.circle(self.screen, OUTLINE, (x, y), BTN_RADIUS, width=2)
        txt = self.big_font.render(label, True, _contrast(color))
        self.screen.blit(txt, txt.get_rect(center=(x, y)))

    def _draw_encoder(self, x: int, y: int, angle: float, pos: int, pressed: bool, label: str) -> None:
        pygame.draw.circle(self.screen, (60, 60, 70) if pressed else PANEL, (x, y), ENC_RADIUS + 4)
        pygame.draw.circle(self.screen, (90, 90, 100), (x, y), ENC_RADIUS)
        pygame.draw.circle(self.screen, OUTLINE, (x, y), ENC_RADIUS, width=2)
        # pointer
        px = int(x + math.cos(angle - math.pi / 2) * (ENC_RADIUS - 10))
        py = int(y + math.sin(angle - math.pi / 2) * (ENC_RADIUS - 10))
        pygame.draw.line(self.screen, (240, 240, 240), (x, y), (px, py), width=4)
        pygame.draw.circle(self.screen, (240, 240, 240), (px, py), 5)
        # label + pos readout
        lbl = self.font.render(label, True, TEXT)
        self.screen.blit(lbl, lbl.get_rect(center=(x, y + ENC_RADIUS + 18)))
        pos_lbl = self.font.render(f"pos={pos}", True, (160, 160, 170))
        self.screen.blit(pos_lbl, pos_lbl.get_rect(center=(x, y + ENC_RADIUS + 36)))


def _contrast(color: tuple[int, int, int]) -> tuple[int, int, int]:
    r, g, b = color
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    return (0, 0, 0) if luma > 140 else (240, 240, 240)


if __name__ == "__main__":  # pragma: no cover
    # Minimal self-test: show the window and echo input, with the strip lit
    # white and buttons mirrored into their LEDs.
    board = EmulatorBoard()
    clock = pygame.time.Clock()
    for i in range(NUM_STRIP):
        board.pixels[STRIP_START + i] = (32, 32, 32)
    while board.running:
        board.poll()
        for i in range(NUM_BUTTONS):
            board.pixels[i] = (255, 255, 255) if board.buttons[i] else (40, 40, 40)
        board.show()
        clock.tick(60)
    board.shutdown()
    sys.exit(0)
