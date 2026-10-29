# Wiring

Board: AYWHP ESP32-S3 (DevKitC-1 layout, N16R8). Pins are labeled by GPIO number (e.g. `11` or `IO11`).

**Never use:** GPIO 0, 3, 45, 46 (boot strapping), 19, 20 (native USB), 26-37 (flash and octal PSRAM on N16R8).

## Screen: HiLetgo 2.8" ILI9341

| Screen pin | ESP32-S3 | Notes |
|---|---|---|
| VCC | 3V3 | |
| GND | GND | |
| CS | GPIO 10 | |
| RESET | GPIO 8 | |
| DC | GPIO 9 | |
| SDI (MOSI) | GPIO 11 | |
| SCK | GPIO 12 | |
| LED | GPIO 7 | PWM dimming in software (`Backlight` in `firmware/hw/board_esp32s3.py`). |
| SDO (MISO) | not connected | Only for reading from the screen. |
| T_CLK, T_CS, T_DIN, T_DO, T_IRQ | not connected | Touch layer, unused. |

A right-angle female header adapter sits on the screen's pin header and the jumpers plug into it, so they leave the panel at 90° (along the back of the board) instead of sticking straight out.

Over the 50cm run: start with SPI at ~24 MHz. If you see garbage, drop to 10-20 MHz. Run a GND wire alongside SCK in the bundle.

## Buttons: 1×3 membrane keypad

JESSINIE MG001V, three keys on a 4-pin 2.54 mm plug: one common pin and one pin per key. A press connects that key's pin to the common. The common goes to GND and each key pin to a GPIO with the internal pull-up on (`keypad.Keys(..., value_when_pressed=False, pull=True)`), so no resistors.

| Plug pin | ESP32-S3 | Physical key | Button |
|---|---|---|---|
| 1 | GND | common | |
| 2 | GPIO 4 | middle | B (select) |
| 3 | GPIO 5 | right | C (cancel / back) |
| 4 | GPIO 6 | left | A (cycle icons) |

Pin 1 is the common: confirmed on the board, all three keys register with it on GND. If the plug is ever reversed, no key or only one key registers.

The plug's key pins are not in left-to-right order. The firmware maps them (`BUTTON_PINS` in `firmware/hw/board_esp32s3.py`) so physical left/middle/right are A/B/C. If the order is ever wrong again, change it there instead of rewiring.

Total wires to the belly: 4.

## Audio: MAX98357A

Lives in the bag next to the board. Only the 2 speaker wires need to run anywhere longer.

| Amp pin | ESP32-S3 |
|---|---|
| VIN | 5V (VBUS) |
| GND | GND |
| BCLK | GPIO 15 |
| LRC | GPIO 16 |
| DIN | GPIO 17 |
| GAIN | leave floating (9 dB) |
| SD | 3V3 (jumper: amp on, plays the left channel; CircuitPython sends our mono samples on both channels) |
| Speaker + / − | speaker |

## Power

Power bank → USB-C → board's USB port. Use the port labeled **USB** (native USB) during development so the board mounts as `CIRCUITPY`. Either port powers it in the costume.

## Wire budget

| Run | Wires |
|---|---|
| Bag → chest (screen) | 8 (VCC, GND, CS, RST, DC, MOSI, SCK, LED) |
| Bag → belly (buttons) | 4 |
| Bag → speaker (if mounted up front) | 2 |
