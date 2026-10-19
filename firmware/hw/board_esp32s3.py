"""Display setup for the AYWHP ESP32-S3 (DevKitC-1 layout). Pins per docs/WIRING.md.

Screen: HiLetgo 2.8" ILI9341, 320x240, SPI.
  SCK  -> IO12    MOSI -> IO11    CS -> IO10
  DC   -> IO9     RST  -> IO8     LED -> 3V3 (T4 moves it to IO7 for PWM)
"""

import board
import busio
import displayio
import fourwire
import adafruit_ili9341

# Drop to 10-20 MHz if the screen shows garbage over the 50cm jumpers (see PLAN.md risks).
SPI_BAUDRATE = 24_000_000

# 0 or 180. Flip if the image is upside down relative to the costume mount.
ROTATION = 0

WIDTH = 320
HEIGHT = 240

_display = None


def get_display():
    """Return the ILI9341 as a displayio display, creating it on first call."""
    global _display
    if _display is not None:
        return _display

    displayio.release_displays()
    spi = busio.SPI(clock=board.IO12, MOSI=board.IO11)
    bus = fourwire.FourWire(
        spi,
        command=board.IO9,
        chip_select=board.IO10,
        reset=board.IO8,
        baudrate=SPI_BAUDRATE,
    )
    _display = adafruit_ili9341.ILI9341(
        bus, width=WIDTH, height=HEIGHT, rotation=ROTATION
    )
    return _display
