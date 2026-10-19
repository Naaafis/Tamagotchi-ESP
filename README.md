# Tamagotchi-ESP

Wearable Tamagotchi Halloween costume: ESP32-S3 + 2.8" ILI9341 screen running a Tamagotchi-style virtual pet with 3 buttons and sound. Built on forked open-source pet projects, with a coordination directory for agent progress.

**Target:** finished, wearable unit for **Oct 31, 2026**.

| Doc | What's in it |
|---|---|
| [docs/PLAN.md](docs/PLAN.md) | Goals, decisions, architecture, phases, timeline |
| [docs/MATERIALS.md](docs/MATERIALS.md) | Parts list, links, order status |
| [docs/WIRING.md](docs/WIRING.md) | Pin map for screen, buttons, backlight, amp |
| [docs/REFERENCES.md](docs/REFERENCES.md) | Upstream repos we borrow from, and what for |
| [coordination/](coordination/) | Task board, agent rules, progress log |

## Layout

```
docs/           plan, materials, wiring, references
coordination/   STATUS.md (task board), AGENTS.md (rules), LOG.md (progress)
firmware/       everything that gets copied onto the CIRCUITPY drive
sim/            desktop simulator (runs the same game in a pygame window)
scripts/        helper scripts (fetch reference repos, deploy to board)
references/     cloned upstream repos (git-ignored, fetched by script)
```
