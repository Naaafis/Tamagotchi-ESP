# References

Upstream repos we read or borrow from. Clone them into `references/` (git-ignored) with:

```
./scripts/fetch-references.sh
```

We don't fork unless we need to change and track upstream code. If we do, fork under `Naaafis/` and note it here.

| Repo | Use it for | Caveats |
|---|---|---|
| [neubauek/CircuitPython-Virtual-Pet](https://github.com/neubauek/CircuitPython-Virtual-Pet) | Closest match in spirit: CircuitPython, 3 buttons, Tamagotchi-style care loop. Borrow game-loop structure and stat logic. MIT. | Built for a 128×64 monochrome OLED using native `framebuf`, not `displayio`. Its art is 1-bit; we can scale it, but the rendering code has to be rewritten for the ILI9341. |
| [FoamyGuy/Blinka_Displayio_PyGameDisplay](https://github.com/FoamyGuy/Blinka_Displayio_PyGameDisplay) | Desktop simulator: runs CircuitPython `displayio` code in a pygame window. | Docs warn it isn't updated for Blinka_DisplayIO 1.0+. Pin an older `blinka-displayio` if imports fail. |
| [adafruit/Adafruit_CircuitPython_ILI9341](https://github.com/adafruit/Adafruit_CircuitPython_ILI9341) | Screen driver. | Use with `fourwire.FourWire` on CircuitPython 9+. |
| [jcrona/tamalib](https://github.com/jcrona/tamalib) | Reference for how the real P1 behaves (timings, states). | Real emulator needs the original ROM (not provided, copyright) and can't do custom needs. Read-only reference. |
| [RBEGamer/TamagotchiESP32](https://github.com/RBEGamer/TamagotchiESP32) / [Almarch/Nanogotchi](https://github.com/Almarch/Nanogotchi) | ESP32 ports of TamaLib; icon art and button handling ideas. | Same ROM caveat. Built for 128×64 I2C OLED. |
| [beccamakes/esp32-s3-tamagotchi](https://github.com/beccamakes/esp32-s3-tamagotchi) | ESP32-S3 + 3 buttons state machine and pixel animation ideas. | Arduino, AMOLED board, habit-tracker game. |

## Rejected

| Repo | Why not |
|---|---|
| [CyberXcyborg/ESP32-TamaPetchi](https://github.com/CyberXcyborg/ESP32-TamaPetchi) | Mostly a phone web UI. The on-screen v2.0 is unfinished, targets a 240×240 ST7789 with touch, and its documented S3 audio pins (25/26/27) don't exist on the S3. |
| Raspberry Pi pygame repos (TerenceGrover/tamagotchi, kldaly5430/Raspberry-Pi-Tamagotchi) | Moved off the Pi. Still useful as art/logic reference if needed. |

## Firmware

- CircuitPython build for this board: **ESP32-S3-DevKitC-1-N8R8** (no N16R8 build exists; the N8R8 build runs fine on it). <https://circuitpython.org/board/espressif_esp32s3_devkitc_1_n8r8/>
- Flash from Chrome with the **Open Installer** button on that page, over the board's native **USB** port.
