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

## 2026-10-22 — Claude — T3+T4+T8
- Repo untangled first: the local checkout had the T3+T4 commits under the T6+T7 branch name. Fixed the branch pointers, removed the stale `~/Tamagotchi-ESP-sim` worktree, opened PR #4 for the one-commit sim window fix (74c98d7) that was sitting unmerged on `origin/task/T6-T7-sim-and-core`.
- Rebased `task/T3-T4-buttons-backlight` onto `main` (clean, no conflicts) and, per Nafis, skipped the standalone button/backlight test and went straight to the game on the board on this branch. The T3+T4 bring-up program (big letter per button, backlight % readout) is at commit 1b1746a if T12 wants it for the long-wire test.
- `firmware/hw/board_esp32s3.py`: buttons A/B/C on IO4/IO5/IO6 via `keypad.Keys` (internal pull-ups, 20 ms scan, `debounce_threshold=2`); backlight on IO7 via `pwmio` at 5 kHz behind a `Backlight` class with non-blocking linear fades (`fade_to(level, seconds)` + `update()` each loop). `button_events()` returns `(name, pressed, ticks)` with the scanner's own timestamp so the log shows real hold times.
- `firmware/code.py` runs `pet.game.Game`: presses feed `Game.update()`, `on_button` and `on_attention` fade the backlight to 100 %, and 15 s after the last press it fades to a 15 % resting level. Knobs at the top: `RESTING_LEVEL`, `BRIGHT_LEVEL`, `IDLE_SECONDS`, `FADE_UP_SECONDS`, `FADE_DOWN_SECONDS`.
- Board facts worth knowing (CircuitPython 10.3.1, N8R8 build):
  - Floats are single precision (`1.0 + 1e-7 == 1.0`), so `time.monotonic()` loses resolution over an evening. The game clock is built from `supervisor.ticks_ms()` with wrap-safe subtraction instead.
  - `gc.mem_alloc()` / `gc.mem_free()` each take ~210 ms: they walk the whole 8 MB PSRAM heap. Never call them in the loop. (I did, briefly, and chased the resulting stall for a while.)
  - `gc.collect()` is 1-3 ms with little garbage and ~220 ms the first time after boot when it frees the import-time compiler garbage. The game allocates ~2 KB/s. `code.py` collects once after setup and then only after 60 s without a press, at most every 5 min, so a collection never lands mid-play.
  - displayio refresh cost, measured with `auto_refresh` off: full 320×240 214 ms; pet frame flip (128×128) 58 ms; one icon highlight 9 ms; attention icon or bubble 10 ms; sleep/wake theme change ~200 ms; stats page open 215 ms. That is ~3 µs per pixel of compositing in displayio's scaled-TileGrid path; SPI speed is not the limit (24 MHz requested), and an opaque pet palette only shaves 58 → 50 ms. So the idle animation costs the board 58 ms every 0.6 s in the background. If it ever matters, pre-scaled sprite bitmaps (scale-1 TileGrids) are the lever; T10 could draw the art at native size.
  - Refreshes run between Python statements, so most of their cost lands inside the loop's `time.sleep()` and never shows in a frame's own time. The status line now reports the longest wall-clock gap between two frames, which does include them: 78 ms while the pet idles (one frame flip), 226 ms once at boot for the first full-screen draw.
- Serial results across ~25 min of captures while Nafis played: no tracebacks. 120+ presses, every press has exactly one release, holds 39-196 ms, fastest repeat 59 ms between a release and the next press of the same button: no double or phantom presses with `debounce_threshold=2`. Loop runs at 28-30 fps; a frame's own work is 4 ms idle and ≤ 22 ms while playing. Backlight: 100 % → 15 % fade fired 15 s after the last press every time, and came back up on each press and each attention event. First attention 189 s after power-on (hunger hits 30), then thirst at 255 s and energy at 312 s, matching the sim's timing.
- Nafis played two rounds on the real screen and buttons: 15 % resting level looks good, the fade up on a press feels snappy, no hitches, no missed or doubled presses. No tuning needed; the knobs stay at 15 % / 100 % / 15 s.
- Not done: sound (T5/T11, separate branch once the amp is soldered), real art (T10). The `on_attention`/`on_button` hooks are in place for T11; `code.py` already uses them for the backlight.
