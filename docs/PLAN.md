# Plan

## Goal

Christina goes as a Tamagotchi for Halloween. A screen on her chest shows a pixel-art pet in the original Tamagotchi layout, three yellow buttons on her belly drive it, and a small speaker beeps. Nafis delivers a self-contained, wired, secured electronics unit. Christina handles all mounting and crafting onto the costume.

- **Primary target:** Oct 31, 2026
- **Stretch:** Oct 24 (500-person party in NYC). Not expected to be ready.

## Decisions (locked)

| Decision | Choice | Why |
|---|---|---|
| Board | ESP32-S3 (AYWHP, N16R8 module) | Already owned, no soldering, instant boot, safe to pull power, low draw. Pi Zero is the backup. |
| Language | CircuitPython | Python, no compile/flash loop (save `code.py` and it reloads), good display/button/audio libraries. |
| Screen | HiLetgo 2.8" ILI9341 SPI, 320×240, LED backlit | No 2-3" square SPI panel exists. We render into a **centered 240×240 square** and black out the sides; the costume bezel hides them. |
| Buttons | 1×3 membrane keypad (JESSINIE MG001V) | A = cycle icons, B = select, C = cancel (same as the real toy). Replaced the 12mm tactile buttons. |
| Sound | MAX98357A I2S amp + 4Ω 3W 40mm speaker | Board can't drive a speaker directly. Fallback: piezo buzzer on one GPIO. |
| Placement | Screen on chest, buttons on belly, **board + amp + battery in a small bag on her back** | 50cm jumpers run over the shoulder. Lower SPI clock if the screen glitches over the long run. |
| Base code | Write our own game in CircuitPython, borrowing structure and art ideas from reference repos | No existing repo targets this screen + 3 buttons + custom needs. See [REFERENCES.md](REFERENCES.md). |

## Game requirements

- **Layout:** original Tamagotchi look. Icon row on top, pet in the middle, icon row on the bottom, inside the 240×240 square. Chunky pixel art that reads from a few feet away in the dark. Pixel-perfect accuracy is not required.
- **Needs (custom, replacing standard prompts):**
  - Eat, sleep, play (standard)
  - **Drink**
  - **Treat** (trick-or-treat, Halloween tie-in)
  - **Affection**
  - Maybe: "change the song", "outfit change"
- **Attention:** when a need is low, the attention icon lights, the speaker beeps, and the backlight brightens.
- **Backlight:** on by default at low brightness (~10-15%), brightens on events and button presses, then fades back.
- **Speed:** stats should decay fast enough that people at a party see the pet ask for things every few minutes. Must not die during a party (floor the stats, or make "death" a recoverable sulk).
- **Reference:** Christina's physical Tamagotchi. Photograph its screens for layout and icon reference.

## Architecture

```
firmware/                 -> copied onto the CIRCUITPY drive
  code.py                 entry point: picks hardware or sim backend, runs the loop
  pet/
    state.py              stats, decay, needs, state machine (pure Python, no hardware)
    ui.py                 builds displayio groups: icon rows, pet sprite, square mask
    input.py              maps A/B/C events to menu actions
    sound.py              beeps / wav playback (no-op in sim if needed)
    backlight.py          PWM brightness with fade (no-op in sim)
  hw/
    board_esp32s3.py      display, buttons, backlight, audio for the real board
  assets/                 BMP sprite sheets, wav files
sim/
  run_desktop.py          same game in a pygame window, keyboard as buttons
```

Rule: everything in `pet/` stays hardware-agnostic so the same code runs on the board and in the desktop simulator. Only `hw/` and `sim/` touch hardware or pygame.

## Phases

| # | Phase | Done when |
|---|---|---|
| 0 | Repo bootstrap | This plan, materials, wiring, coordination merged to `main`. |
| 1 | Hardware bring-up | CircuitPython flashed. Test `code.py` draws a 240×240 square, shows which button was pressed, fades the backlight, plays a beep. |
| 2 | Desktop simulator | `sim/run_desktop.py` opens a 320×240 window and runs the game with keyboard A/S/D as the buttons. |
| 3 | Game core | Stats, decay, needs, menu navigation, attention logic. Unit-testable on the laptop. |
| 4 | Look and feel | Tamagotchi layout, pet sprites (idle, happy, sad, sleeping, eating), icons for every need. Matches the reference photos. |
| 5 | Sound + backlight events | Beeps on attention and button presses, brighten-on-event. |
| 6 | Wearable integration | Harness wired with 50cm jumpers, connectors secured, battery runtime tested (target: 5+ hours). Unit handed to Christina. |
| 7 | Party-proofing | Full-evening soak test, recovery behavior if power blips, quick-start card for Christina. |

## Risks

| Risk | Mitigation |
|---|---|
| Screen glitches over 50cm wires | Lower SPI baudrate (try 10-20 MHz). Route ground next to SCK in the bundle. |
| Connectors pop loose while wearing | Strain-relief the bundle to the bag and costume an inch from each connector. Hot glue only on connector housings, never on chips. |
| No CircuitPython build for N16R8 | Use the **ESP32-S3-DevKitC-1-N8R8** build. Same octal PSRAM; flash just reports 8MB. |
| Running out of dev time | Phase 1 + a minimal Phase 3/4 (one pet, three needs) is a shippable costume. Everything else is polish. |
