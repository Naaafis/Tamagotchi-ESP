# sim

Desktop simulator: runs the same game code from `firmware/pet/` in a pygame
window, with keyboard A/S/D as buttons A/B/C. Nothing in `firmware/pet/` knows
it is being simulated; `run_desktop.py` just swaps the ILI9341 for a
[PyGameDisplay](https://github.com/FoamyGuy/Blinka_Displayio_PyGameDisplay).

## Setup

```
python3 -m venv .venv
.venv/bin/pip install -r sim/requirements.txt
```

Versions are pinned in `requirements.txt`; `blinka-displayio-pygamedisplay 4.0.1`
with `adafruit-blinka-displayio 2.7.1` is the combination that works.

## Run

```
.venv/bin/python sim/run_desktop.py
```

- **A** cycles the icon highlight, **S** performs it (button B), **D** clears it (button C).
- The window is the 320×240 screen at 3× (`--scale 2` for a smaller window).
- The title bar shows the six stats once a second; presses and attention
  events are printed to the terminal.
- Two "Adafruit Blinka chip_id == None" warnings at startup are harmless.
- Screenshot: `.venv/bin/python sim/run_desktop.py --seconds 2 --press A,A --screenshot docs/screenshots/sim.png`
  (add `--headless` to render without opening a window).

If your shell exports `PYTHONPATH` pointing at another Python's site-packages,
run with `env -u PYTHONPATH .venv/bin/python ...` so the pinned packages win.

## Tests

```
.venv/bin/python -m pytest sim/tests
```

`sim/tests/` covers the stat/decay logic in `firmware/pet/state.py`, the
button/menu logic, and a smoke test that builds the displayio UI.
