"""Device configuration shared by the firmware and the emulator."""

NUM_BUTTONS = 4
NUM_STRIP = 16
NUM_PIXELS = NUM_BUTTONS + NUM_STRIP  # 20
STRIP_START = NUM_BUTTONS

NUM_ENCODERS = 2

BRIGHTNESS = 0.3

MODE_COLORS = {
    "agri_fr": (40, 80, 255),
    "agri_kab": (0, 220, 220),
    "forum": (255, 140, 0),
    "weather": (0, 220, 80),
}

BUTTON_MODES = ["agri_fr", "agri_kab", "forum", "weather"]
