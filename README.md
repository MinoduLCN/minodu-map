# Minodu Map

Resources and Firmware for the Media Access Point of the Minodu LCN.

The firmware runs on a Raspberry Pi with 2 Stemma QT encoders, 4 illuminated NeoKey buttons and a 16-pixel RGB LED strip. A Pygame-based emulator lets you develop locally on macOS without the hardware — see below.

See [`CLAUDE.md`](./CLAUDE.md) for the full feature spec, control mapping, and implementation plan.

## Local development on macOS

Requires Python 3.11+ (tested on 3.12).

```shell
# clone, then from the repo root:
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Run the emulator demo:

```shell
python src/emulator_demo.py
```

A window opens with the 16 strip LEDs, 4 button LEDs and 2 encoder dials.

**Controls**

| Input                         | Keyboard                    | Mouse                                          |
| ----------------------------- | --------------------------- | ---------------------------------------------- |
| Button 1-4                    | `1` `2` `3` `4`             | click the button LED                           |
| Left encoder rotate           | `A` / `D`                   | scroll wheel over the dial, or right-drag      |
| Left encoder click            | `S`                         | left-click the dial                            |
| Right encoder rotate          | `←` / `→`                   | scroll wheel over the dial, or right-drag      |
| Right encoder click           | `↓`                         | left-click the dial                            |
| Quit                          | `Q` or `Esc`                | close window                                   |

The demo app wired to the emulator: buttons 1-4 switch modes (agri-FR, agri-KAB, forum, weather), the left encoder scrolls a selection along the strip, the right encoder adjusts a volume floor, and the right-encoder click toggles mute. Every event is logged to the console.

## On the Raspberry Pi

See [`hardware/README.md`](./hardware/README.md) for sound-card setup, I2C/SPI configuration and the systemd service template. The hardware test scripts live in [`hardware/tests/`](./hardware/tests/).
