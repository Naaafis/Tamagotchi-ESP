"""T3+T4 buttons and backlight bring-up test.

Same centered 240x240 orange square as T2. The last button pressed shows as a
big letter in the middle, the backlight level along the bottom.

  A tap      -> just shows "A"
  A held     -> fades the backlight down to 10% over 1 s (hold ~0.4 s to trigger)
  B          -> fades the backlight up to 100% over 1 s
  C          -> flashes the square cyan for a quarter second

Every press, release and hold is printed to serial with a millisecond
timestamp, so double-fires and phantom presses show up as extra lines.
"""

import time

import bitmaptools
import displayio
import terminalio
from adafruit_display_text import label

from hw.board_esp32s3 import (
    BACKLIGHT_FREQUENCY,
    DEBOUNCE_THRESHOLD,
    HEIGHT,
    WIDTH,
    button_events,
    get_backlight,
    get_display,
    get_keys,
    ticks_diff,
    ticks_ms,
)

SQUARE = 240
X0 = (WIDTH - SQUARE) // 2  # 40
Y0 = (HEIGHT - SQUARE) // 2  # 0

BLACK = 0x000000
WHITE = 0xFFFFFF
ORANGE = 0xFF7A00
CYAN = 0x00C8FF

HOLD_MS = 400  # how long A must stay down to count as "held"
FLASH_MS = 250  # how long the square stays cyan after C
FADE_SECONDS = 1.0
DIM_LEVEL = 0.10
BRIGHT_LEVEL = 1.00

# Backlight first so the screen is lit while the display initialises.
backlight = get_backlight()
display = get_display()
get_keys()  # start scanning now so a press during setup isn't lost

# One full-screen bitmap: 0 = black, 1 = white border, 2 = fill.
bitmap = displayio.Bitmap(WIDTH, HEIGHT, 3)
palette = displayio.Palette(3)
palette[0] = BLACK
palette[1] = WHITE
palette[2] = ORANGE
bitmaptools.fill_region(bitmap, X0, Y0, X0 + SQUARE, Y0 + SQUARE, 1)
bitmaptools.fill_region(bitmap, X0 + 1, Y0 + 1, X0 + SQUARE - 1, Y0 + SQUARE - 1, 2)

cx = X0 + SQUARE // 2
cy = Y0 + SQUARE // 2

title = label.Label(
    terminalio.FONT,
    text="T3+T4 buttons+backlight",
    color=BLACK,
    scale=2,
    anchor_point=(0.5, 0.5),
    anchored_position=(cx, Y0 + 22),
)
last_button = label.Label(
    terminalio.FONT,
    text="-",
    color=BLACK,
    scale=10,
    anchor_point=(0.5, 0.5),
    anchored_position=(cx, cy - 6),
)
status = label.Label(
    terminalio.FONT,
    text="",
    color=BLACK,
    scale=2,
    anchor_point=(0.5, 0.5),
    anchored_position=(cx, Y0 + SQUARE - 36),
)
hint = label.Label(
    terminalio.FONT,
    text="hold A: dim  B: bright  C: flash",
    color=BLACK,
    scale=1,
    anchor_point=(0.5, 0.5),
    anchored_position=(cx, Y0 + SQUARE - 14),
)

root = displayio.Group()
root.append(displayio.TileGrid(bitmap, pixel_shader=palette))
root.append(title)
root.append(last_button)
root.append(status)
root.append(hint)
display.root_group = root


def pct(level):
    return int(level * 100 + 0.5)


def show_status():
    text = "backlight %d%%" % pct(backlight.brightness)
    if backlight.fading:
        text += " > %d%%" % pct(backlight.target)
    if status.text != text:
        status.text = text


def log(name, what):
    print("[%7d ms] %s %s" % (ticks_ms(), name, what))


show_status()
print(
    "T3+T4 OK: buttons A/B/C on IO4/IO5/IO6, debounce_threshold=%d; "
    "backlight IO7 PWM %d Hz at %d%%; display %dx%d"
    % (DEBOUNCE_THRESHOLD, BACKLIGHT_FREQUENCY, pct(backlight.brightness), WIDTH, HEIGHT)
)

a_down_since = None  # ticks when A went down, None when up
a_hold_fired = False
flash_until = None  # ticks when the cyan flash ends, None when not flashing

while True:
    now = ticks_ms()

    for name, pressed in button_events():
        log(name, "press" if pressed else "release")
        if pressed:
            if last_button.text != name:
                last_button.text = name
            if name == "A":
                a_down_since = now
                a_hold_fired = False
            elif name == "B":
                backlight.fade_to(BRIGHT_LEVEL, FADE_SECONDS)
            elif name == "C":
                palette[2] = CYAN
                flash_until = now + FLASH_MS
        elif name == "A":
            a_down_since = None

    if a_down_since is not None and not a_hold_fired and ticks_diff(now, a_down_since) >= HOLD_MS:
        a_hold_fired = True
        log("A", "hold")
        backlight.fade_to(DIM_LEVEL, FADE_SECONDS)

    if flash_until is not None and ticks_diff(now, flash_until) >= 0:
        palette[2] = ORANGE
        flash_until = None

    backlight.update()
    show_status()  # only touches the label when the text actually changes

    time.sleep(0.005)
