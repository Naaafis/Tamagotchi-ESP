#!/usr/bin/env python3
"""Desktop simulator: runs the game from firmware/pet in a pygame window.

    .venv/bin/python sim/run_desktop.py

Keys: A / S / D are buttons A / B / C. Esc or closing the window quits.
The window is the 320x240 screen scaled up (3x by default); everything
outside the centered 240x240 square stays black, like the real panel.

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

WIDTH = 320
HEIGHT = 240
PRESS_INTERVAL = 0.4
STATUS_INTERVAL = 1.0


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

    import pygame
    import displayio
    import blinka_displayio_pygamedisplay as pgd

    from pet.game import Game

    keys = {pygame.K_a: "A", pygame.K_s: "B", pygame.K_d: "C"}
    scripted = [p.strip().upper() for p in args.press.split(",") if p.strip()]

    display = pgd.PyGameDisplay(
        width=WIDTH * args.scale,
        height=HEIGHT * args.scale,
        caption="Tamagotchi sim  (A/S/D = buttons A/B/C)",
        native_frames_per_second=30,
    )

    # Only the events we and the display driver read may enter the queue;
    # otherwise mouse motion piles up behind the driver's refresh events.
    wanted = [pygame.QUIT, pygame.WINDOWCLOSE, pygame.KEYDOWN] + pgd._PYGAME_REDRAW_EVENTS
    wanted.append(pgd._DISPLAYIO_EVENT)
    pygame.event.set_blocked(None)
    pygame.event.set_allowed(wanted)

    start = time.monotonic()
    game = Game(now=start, width=WIDTH, height=HEIGHT)
    game.on_attention = lambda: print("[%6.1fs] attention: %s" % (time.monotonic() - start, game.pet.summary()))
    game.on_button = lambda name: print("[%6.1fs] button %s" % (time.monotonic() - start, name))

    # The game draws at 320x240; scale the whole thing up for the window.
    root = displayio.Group(scale=args.scale)
    root.append(game.root_group)
    display.root_group = root

    next_status = start
    next_press = start + PRESS_INTERVAL
    running = True
    while running:
        if display.check_quit(0):  # handles refresh + window close
            running = False
            break
        now = time.monotonic()
        events = []
        for event in pygame.event.get(eventtype=pygame.KEYDOWN):
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key in keys:
                events.append(keys[event.key])
        if scripted and now >= next_press:
            events.append(scripted.pop(0))
            next_press = now + PRESS_INTERVAL

        game.update(now, events)

        if now >= next_status:
            next_status = now + STATUS_INTERVAL
            pygame.display.set_caption("Tamagotchi sim  A/S/D = A/B/C   |   " + game.pet.summary())
        if args.seconds is not None and now - start >= args.seconds:
            running = False
        time.sleep(1 / 60)

    if args.screenshot and pygame.display.get_init():
        display.refresh()
        pygame.image.save(pygame.display.get_surface(), args.screenshot)
        print("saved", args.screenshot)
    pygame.quit()


if __name__ == "__main__":
    main()
