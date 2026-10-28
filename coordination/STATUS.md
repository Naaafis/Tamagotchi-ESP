# Task board

Status: `todo` · `in progress` · `review` · `blocked` · `done`

| ID | Task | Phase | Depends on | Owner | Status | Branch / PR |
|---|---|---|---|---|---|---|
| T0 | Bootstrap repo: plan, materials, wiring, references, coordination | 0 | — | Claude | done | [#1](https://github.com/Naaafis/Tamagotchi-ESP/pull/1) |
| T1 | Flash CircuitPython (N8R8 build) onto the S3 | 1 | — | Nafis | done | — |
| T2 | Screen bring-up: `code.py` draws a centered 240×240 square + text on the ILI9341 | 1 | T1 | Claude | done | [#2](https://github.com/Naaafis/Tamagotchi-ESP/pull/2) |
| T3 | Buttons bring-up: show which of A/B/C was pressed (keypad, pull-ups) | 1 | T2 | Claude | done | [#5](https://github.com/Naaafis/Tamagotchi-ESP/pull/5) |
| T4 | Backlight PWM on GPIO 7 with fade up/down | 1 | T2 | Claude | done | [#5](https://github.com/Naaafis/Tamagotchi-ESP/pull/5) |
| T5 | Audio bring-up: MAX98357A beep (tones generated in code, no wav) | 1 | T1 | Claude | blocked: needs Nafis (speaker wires to solder) | `task/T5-T11-sound` |
| T6 | Desktop simulator: same game code in a pygame window, keys A/S/D | 2 | T0 | Claude | done | [#3](https://github.com/Naaafis/Tamagotchi-ESP/pull/3) |
| T7 | Game core: stats, decay, needs (eat, sleep, play, drink, treat, affection), attention logic, no permanent death | 3 | T0 | Claude | done | [#3](https://github.com/Naaafis/Tamagotchi-ESP/pull/3) |
| T8 | Menu + input: Tamagotchi icon rows, A cycles / B selects / C cancels | 3 | T7 | Claude | done | [#5](https://github.com/Naaafis/Tamagotchi-ESP/pull/5) |
| T9 | Reference photos of Christina's Tamagotchi into `docs/reference/` | 4 | — | Nafis | todo | — |
| T10 | Art: pet sprites (idle, happy, sad, sleep, eat) + icons for every need, 240×240 layout | 4 | T8, T9 | | todo | |
| T11 | Sound + backlight events wired to attention and button presses | 5 | T5, T4, T8 | Claude | in progress | `task/T5-T11-sound` |
| T12 | Long-run wiring test: 50cm jumpers, tune SPI baudrate | 6 | T2 | Nafis | todo | — |
| T13 | Battery runtime test (target 5+ hours) | 6 | T11 | Nafis | todo | — |
| T14 | Harness + strain relief, hand unit to Christina | 6 | T12, T13 | Nafis | todo | — |
| T15 | Full-evening soak test + quick-start card for Christina | 7 | T14 | | todo | |
