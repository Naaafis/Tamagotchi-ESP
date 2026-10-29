#!/usr/bin/env python3
"""Desktop simulator: runs the game from firmware/pet in a pygame window.

    .venv/bin/python sim/run_desktop.py

Keys: A / S / D are buttons A / B / C (hold D to leave the left/right game).
Esc or closing the window quits.
The window is the 320x240 screen scaled up (3x by default); everything
outside the centered 240x240 square stays black, like the real panel.
There is no audio: the terminal prints which tune the board would play
(pet.sound), the button tick included.

Options:
    --scale N          window scale (default 3)
    --screenshot PATH  save the window to PATH when quitting
    --seconds S        quit after S seconds (for screenshots)
    --press A,A,B      feed these presses, one every 0.4 s after start
    --headless         no window (SDL dummy driver); pair with --screenshot
"""

import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
# Appended, not prepended: firmware/code.py must not shadow the stdlib `code` module.
sys.path.append(os.path.join(REPO, "firmware"))

import busdisplay  # noqa: E402
import pygame  # noqa: E402
import blinka_displayio_pygamedisplay as pgd  # noqa: E402

from pet import sound  # noqa: E402
from pet.game import Game  # noqa: E402

WIDTH = 320
HEIGHT = 240
FRAME_RATE = 30  # window redraws per second; the real panel refreshes at about this rate
PRESS_INTERVAL = 0.4
STATUS_INTERVAL = 1.0


class PrintPlayer:
    """Stands in for the board's speaker: prints the tune instead of playing it."""

    def __init__(self, start):
        self._start = start

    def play(self, tune):
        print("[%6.1fs] sound: %s (%d ms)" % (time.monotonic() - self._start, sound.name(tune), sound.duration_ms(tune)))


class SimDisplay(pgd.PyGameDisplay):
    """A 320x240 displayio display that is drawn on the main thread.

    The stock PyGameDisplay refreshes from displayio's background thread: it
    posts one pygame event, sets a "refresh pending" flag, and leaves the real
    drawing to whoever pumps the event on the main thread. If that one event
    is lost (pygame's set_blocked() flushes the queue, for one) the flag never
    clears, no second event is ever posted, and the window stays black for
    good. That is what happened on macOS. So auto_refresh is off here and the
    sim calls refresh() itself once per frame, which draws right there.

    The group is rendered at the panel's native 320x240 into an offscreen
    surface and scaled to the window by pygame. Drawing a 3x-scaled group
    through displayio's pure-Python rasteriser costs 220 ms a frame; this
    costs 25 ms for a full frame and almost nothing while the pet idles,
    because only the areas displayio marks dirty are redrawn.
    """

    def __init__(self, scale, caption):
        self._scale = scale
        self._window = None
        super().__init__(width=WIDTH, height=HEIGHT, caption=caption, auto_refresh=False)

    def _initialize(self, init_sequence):
        pygame.init()
        pygame.display.set_caption(self._caption)
        self._window = pygame.display.set_mode((self.width * self._scale, self.height * self._scale))
        # PyGameDisplay._refresh_area() blits each redrawn area into this.
        self._pygame_screen = pygame.Surface((self.width, self.height))

    def _get_refresh_areas(self):
        # PyGameDisplay always redraws the whole display; BusDisplay asks the
        # group what changed.
        return busdisplay.BusDisplay._get_refresh_areas(self)

    def _refresh_display(self):
        # Not PyGameDisplay._refresh_display(): that flips before we scale.
        busdisplay.BusDisplay._refresh_display(self)
        self._window.blit(pygame.transform.scale(self._pygame_screen, self._window.get_size()), (0, 0))
        pygame.display.flip()


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--scale", type=int, default=3)
    parser.add_argument("--screenshot", metavar="PATH")
    parser.add_argument("--seconds", type=float)
    parser.add_argument("--press", default="")
    parser.add_argument("--headless", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"

    keys = {pygame.K_a: "A", pygame.K_s: "B", pygame.K_d: "C"}
    scripted = [p.strip().upper() for p in args.press.split(",") if p.strip()]

    display = SimDisplay(args.scale, "Tamagotchi sim  (A/S/D = buttons A/B/C)")

    start = time.monotonic()
    game = Game(now=start, width=WIDTH, height=HEIGHT)
    sounds = sound.Sounds(PrintPlayer(start))

    def on_attention():
        print("[%6.1fs] attention: %s" % (time.monotonic() - start, game.pet.summary()))
        sounds.attention()

    def on_button(name):
        print("[%6.1fs] button %s" % (time.monotonic() - start, name))
        sounds.button()

    def on_action(action):
        print("[%6.1fs] action: %s" % (time.monotonic() - start, action))

    def on_cue(name):
        print("[%6.1fs] cue: %s" % (time.monotonic() - start, name))
        sounds.cue(name)

    def on_sulk():
        print("[%6.1fs] sulk: %s" % (time.monotonic() - start, game.pet.summary()))
        sounds.sulk()

    game.on_attention = on_attention
    game.on_button = on_button
    game.on_action = on_action
    game.on_cue = on_cue
    game.on_sulk = on_sulk
    sounds.play(sound.STARTUP)

    # Same as firmware/code.py on the board; the scaling is pygame's, not displayio's.
    display.root_group = game.root_group

    next_status = start
    next_press = start + PRESS_INTERVAL
    next_frame = start
    running = True
    while running:
        now = time.monotonic()
        events = []
        for event in pygame.event.get():
            if event.type in (pygame.QUIT, pygame.WINDOWCLOSE):
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in keys:
                    events.append(keys[event.key])
        if scripted and now >= next_press:
            events.append(scripted.pop(0))
            next_press = now + PRESS_INTERVAL

        down = pygame.key.get_pressed()
        held = [name for key, name in keys.items() if down[key]]
        game.update(now, events, held)
        sounds.update(now, game.pet.attention)

        if now >= next_frame:
            next_frame = now + 1 / FRAME_RATE
            display.refresh()
        if now >= next_status:
            next_status = now + STATUS_INTERVAL
            pygame.display.set_caption("Tamagotchi sim  A/S/D = A/B/C   |   " + game.pet.summary())
        if args.seconds is not None and now - start >= args.seconds:
            running = False
        time.sleep(1 / 60)

    if args.screenshot:
        display.refresh()
        pygame.image.save(pygame.display.get_surface(), args.screenshot)
        print("saved", args.screenshot)
    pygame.quit()


if __name__ == "__main__":
    main()
