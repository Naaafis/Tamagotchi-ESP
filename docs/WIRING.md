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
| LED | 3V3 (bring-up) → GPIO 7 (PWM dimming) | Start on 3V3. Move to GPIO 7 once the screen works, then dim in software. Check the board has a transistor on LED before driving from GPIO. |
| SDO (MISO) | not connected | Only for reading from the screen. |
| T_CLK, T_CS, T_DIN, T_DO, T_IRQ | not connected | Touch layer, unused. |

Over the 50cm run: start with SPI at ~24 MHz. If you see garbage, drop to 10-20 MHz. Run a GND wire alongside SCK in the bundle.

## Buttons

Each button: one leg to its GPIO, the other leg to a **shared GND** wire. Internal pull-ups are enabled in software (`keypad.Keys(..., value_when_pressed=False, pull=True)`), so no resistors.

| Button | Role | ESP32-S3 |
|---|---|---|
| A (left) | Cycle icons | GPIO 4 |
| B (middle) | Select | GPIO 5 |
| C (right) | Cancel / back | GPIO 6 |
| Shared | Ground | GND |

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
| SD | leave floating (on, L+R mono mix) |
| Speaker + / − | speaker |

## Power

Power bank → USB-C → board's USB port. Use the port labeled **USB** (native USB) during development so the board mounts as `CIRCUITPY`. Either port powers it in the costume.

## Wire budget

| Run | Wires |
|---|---|
| Bag → chest (screen) | 8 (VCC, GND, CS, RST, DC, MOSI, SCK, LED) |
| Bag → belly (buttons) | 4 |
| Bag → speaker (if mounted up front) | 2 |
