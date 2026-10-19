# Progress log

Append entries at the bottom. Format: `## YYYY-MM-DD — <agent> — <task ID>` then a few bullets.

## 2026-10-18 — Claude — T0
- Created plan, materials, wiring, references, and coordination docs.
- Decided: ESP32-S3 + CircuitPython, game written fresh, references used for structure and art.
- Found: no CircuitPython build for N16R8; use the DevKitC-1-N8R8 build.
- Found: neubauek/CircuitPython-Virtual-Pet targets a 128×64 OLED via native `framebuf`, so it's a logic reference, not a drop-in.
- Next: Nafis flashes CircuitPython (T1); an agent picks up T2 and T6 in parallel.

## 2026-10-18 — Claude — T2
- Board reports: `Adafruit CircuitPython 10.3.1 on 2026-09-14; ESP32-S3-DevKitC-1-N8R8 with ESP32S3`, board ID `espressif_esp32s3_devkitc_1_n8r8`. Serial console at `/dev/cu.usbmodem48CF6E8558861`.
- Marked T1 done: the flash is confirmed by `boot_out.txt`.
- Installed with circup (bundle 20261008, 10.x-mpy): `adafruit_ili9341`, `adafruit_display_text`, plus deps `adafruit_bitmap_font`, `adafruit_ticks`.
- Wrote `firmware/hw/board_esp32s3.py` (`get_display()`, `SPI_BAUDRATE = 24_000_000`, `ROTATION = 0`), `firmware/code.py` bring-up test, `scripts/deploy.sh` (rsync, no `--delete`, leaves `lib/` alone), `scripts/serial_log.py` (forces a soft reload, reads the console, exits 1 on a traceback).
- First deploy ran clean: no traceback. `code.py` prints `T2 OK: 320x240 display, square at x=40..279 y=0..239, SPI 24000000 Hz, CircuitPython 10.3.1`.
- Chose orange for the square on purpose: a blue square means the panel's colour order is swapped.
- Nafis confirmed on the real panel: centered orange square, white 1px border, black side bars, "T2 OK" and the version readable. Works first try at SPI 24 MHz, rotation 0, over the short bench jumpers. No pin, rotation, or colour-order changes needed.
- Next: T3 (buttons) and T4 (backlight on IO7) can both build on `hw.board_esp32s3.get_display()`. T12 should re-test the 24 MHz clock over the 50cm run.
