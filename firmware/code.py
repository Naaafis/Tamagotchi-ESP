"""T2 screen bring-up test.

Black screen, a centered 240x240 orange square with a 1px white border,
and "T2 OK" + the CircuitPython version inside it. Everything outside the
square stays black. Orange is deliberate: if the square looks blue, the
panel's colour order is swapped.
"""

import os
import time

import bitmaptools
import displayio
import terminalio
from adafruit_display_text import label

from hw.board_esp32s3 import HEIGHT, SPI_BAUDRATE, WIDTH, get_display

SQUARE = 240
X0 = (WIDTH - SQUARE) // 2  # 40
Y0 = (HEIGHT - SQUARE) // 2  # 0

BLACK = 0x000000
WHITE = 0xFFFFFF
ORANGE = 0xFF7A00

display = get_display()

# One full-screen bitmap: 0 = black, 1 = white border, 2 = orange fill.
bitmap = displayio.Bitmap(WIDTH, HEIGHT, 3)
palette = displayio.Palette(3)
palette[0] = BLACK
palette[1] = WHITE
palette[2] = ORANGE
bitmaptools.fill_region(bitmap, X0, Y0, X0 + SQUARE, Y0 + SQUARE, 1)
bitmaptools.fill_region(bitmap, X0 + 1, Y0 + 1, X0 + SQUARE - 1, Y0 + SQUARE - 1, 2)

version = os.uname().release
cx = X0 + SQUARE // 2
cy = Y0 + SQUARE // 2

root = displayio.Group()
root.append(displayio.TileGrid(bitmap, pixel_shader=palette))
root.append(
    label.Label(
        terminalio.FONT,
        text="T2 OK",
        color=BLACK,
        scale=4,
        anchor_point=(0.5, 0.5),
        anchored_position=(cx, cy - 24),
    )
)
root.append(
    label.Label(
        terminalio.FONT,
        text="CircuitPython " + version,
        color=BLACK,
        scale=2,
        anchor_point=(0.5, 0.5),
        anchored_position=(cx, cy + 28),
    )
)
display.root_group = root

print(
    "T2 OK: %dx%d display, square at x=%d..%d y=%d..%d, SPI %d Hz, CircuitPython %s"
    % (WIDTH, HEIGHT, X0, X0 + SQUARE - 1, Y0, Y0 + SQUARE - 1, SPI_BAUDRATE, version)
)

while True:
    time.sleep(1)
