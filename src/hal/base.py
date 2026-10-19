"""Hardware abstraction layer.

The firmware talks to a `Board` that exposes:
    pixels[i] = (r, g, b)         # 0..NUM_PIXELS-1 (buttons then strip)
    board.show()                  # flush pixel buffer
    board.buttons[i]              # bool, True while pressed
    board.encoders[i].position    # cumulative int, like adafruit rotaryio
    board.encoder_buttons[i]      # bool, True while pressed
    board.poll()                  # drain input events; call every tick
    board.running                 # False once user asked to quit
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Board(ABC):
    pixels: list[tuple[int, int, int]]
    buttons: list[bool]
    encoder_buttons: list[bool]

    @property
    @abstractmethod
    def running(self) -> bool: ...

    @abstractmethod
    def show(self) -> None: ...

    @abstractmethod
    def poll(self) -> None: ...

    @abstractmethod
    def encoder_position(self, idx: int) -> int: ...
