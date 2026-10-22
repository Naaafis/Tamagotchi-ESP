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

## 2026-10-21 — Claude — T6+T7
- Simulator: `sim/run_desktop.py` runs `firmware/pet/` in a pygame window through `blinka-displayio-pygamedisplay 4.0.1` + `adafruit-blinka-displayio 2.7.1` (pinned in `sim/requirements.txt`). That pair works out of the box; the "not updated for Blinka_DisplayIO 1.0+" warning in the upstream README is stale, 4.x is written against 2.x. Window is 320×240 at 3×, keys A/S/D = buttons A/B/C, everything outside the 240×240 square is black.
- Found: `firmware/` at the *front* of `sys.path` makes `firmware/code.py` shadow the stdlib `code` module (pdb, and so pytest, import it). `sim/` appends it instead.
- Found: the repo's `.venv` is a miniconda 3.11 venv holding circup + pyserial for the board scripts. The sim deps went into that same venv (`.venv/bin/pip install -r sim/requirements.txt`) so there is one environment; nothing circup needs was changed.
- Game core: `pet/state.py` (six stats, drain rates written as minutes-to-empty, `LOW_THRESHOLD = 30` triggers an ask, zero = sulk with no death, sleep refills energy over 20 s then auto-wakes), `pet/input.py` (A cycles, B selects, C cancels), `pet/ui.py` (Tamagotchi layout: top row eat/drink/sleep/play, bottom row treat/affection/stats + blinking attention icon, ghost pet, bubble showing what it is getting or wants, stats page with six bars, dark theme while asleep), `pet/game.py` (`Game.update(now, events)` with `on_attention` / `on_button` no-op hooks).
- Tuning: steady-state ask rate is 1/14.7 + 1/11.9 + 1/25.2 + 1/14 + 1/20.3 + 1/18.2 per minute ≈ one ask every 2.7 min. `test_pet_asks_for_something_every_two_to_four_minutes` simulates 3 h with a carer who answers at once and checks the mean gap lands in 2-4 min. A fresh pet starts staggered (`START_LEVELS`) so the first ask comes ~3 min after power-on, not 15.
- 31 pytest tests in `sim/tests/` (decay, floor, sulk/recover, attention edge, each action, sleep, menu, page, hooks, UI smoke). Screenshots in `docs/screenshots/`.
- Decisions made on "Game requirements", please confirm or overrule (also in the PR): (1) an action refills its stat fully, not in Tamagotchi quarter-steps; (2) any button wakes a sleeping pet; (3) a 7th "stats" icon opens a bars page (the original has a meter icon too); (4) while a need is low the bubble next to the pet shows the icon it wants, so party guests don't have to open the meter.
- Not done here: wiring `Game` into `firmware/code.py` (T8), real art (T10), sound/backlight behind the hooks (T11). `Game` needs no changes for those; `code.py` sets `display.root_group = game.root_group` and calls `game.update(now, presses)`.

## 2026-10-21 — Claude — T6+T7 (sim window fix)
- Bug: on macOS the sim window stayed black while the title bar kept updating. Cause: `PyGameDisplay` refreshes from displayio's background thread by posting one pygame event and setting a "refresh pending" flag that only the main thread's event handler clears. `run_desktop.py` called `pygame.event.set_blocked(None)` after creating the display, and SDL flushes queued events of a type it blocks, so that first event was lost and no second one was ever posted. Headless screenshots looked fine only because the screenshot path forces `display.refresh()` at exit, so the live refresh path was never exercised.
- Fix (`sim/run_desktop.py` only): `SimDisplay(PyGameDisplay)` with `auto_refresh=False`; the loop calls `display.refresh()` at 30 fps on the main thread, which draws right there. The group is rendered at the native 320×240 into an offscreen surface and scaled to the window by pygame (a 3× displayio group cost 220 ms a frame, native costs 25 ms), and only the areas displayio marks dirty are redrawn, so an idle pet costs about nothing. The game's group is the display's root group, as on the board; no change to `firmware/pet/`.
- Verified: windowed screenshot after A,A shows the pet and both icon rows; the window surface is already drawn 2 s into a run without a forced refresh; dirty-area rendering is pixel-identical to full redraws over a 35-step scripted run (menu, stats page, 20 min time jumps, sleep); 31 tests pass. Pushed to PR #3.
