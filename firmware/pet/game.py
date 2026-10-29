"""The game: pet + menu + screen, driven by Game.update(now, events, held).

    game = Game(now=time.monotonic())
    display.root_group = game.root_group
    while True:
        game.update(time.monotonic(), ["A"], held)   # presses this frame, buttons held down

Selecting an action plays its animation (pet.anim), or a refusal when the pet
is full; Play opens the left/right game (pet.minigame). While either runs it
is game.scene, and presses it doesn't use are dropped, not queued.

Hooks for sound and backlight (no-ops unless the caller sets them; the
board's code.py wires them to the speaker and backlight):
    game.on_attention()        called once each time the attention icon turns on
    game.on_button(name)       called on every press that does something, with "A", "B" or "C"
    game.on_action(action)     called when a care action is done ("eat", "sleep", ...;
                               "play" when a game ends with its fun boost)
    game.on_sulk()             called once each time the pet starts sulking (a stat hit zero)
    game.on_cue(name)          called as an animation frame with a cue starts
                               ("bite", "sip", "refuse", "happy", "match", "miss", "win", "lose")
"""

import random

from pet import anim, input
from pet.minigame import LeftRight
from pet.state import Pet

# Icon order on screen: first four on the top row, the rest on the bottom row,
# with the attention icon in the bottom-right slot.
MENU_ITEMS = ("eat", "drink", "sleep", "play", "treat", "affection", "stats")

PAGE_STATS = "stats"


def _noop(*args):
    pass


class Game:
    def __init__(self, now=0.0, width=320, height=240, build_ui=True, rng=random):
        self.pet = Pet(now)
        self.menu = input.Menu(MENU_ITEMS)
        self.page = None  # None or PAGE_STATS
        self.scene = None  # an anim.Animation or minigame.LeftRight while one runs
        self.rng = rng
        self.on_attention = _noop
        self.on_button = _noop
        self.on_action = _noop
        self.on_sulk = _noop
        self.on_cue = _noop
        self._sulking = self.pet.sulking
        self._down_since = {}  # button -> when it was pressed, while it is held
        self.ui = None
        self.root_group = None
        if build_ui:
            from pet.ui import PetUI  # displayio only needed when drawing

            self.ui = PetUI(MENU_ITEMS, width, height)
            self.root_group = self.ui.root
            self.ui.render(self, now)

    @property
    def playing(self):
        """True while the left/right game is on."""
        return isinstance(self.scene, LeftRight)

    @property
    def lights_off(self):
        """True once the pet is asleep and the falling-asleep animation is over."""
        return self.pet.asleep and self.scene is None

    def held_for(self, button, now):
        """Seconds the button has been held down, 0 if it isn't."""
        if button in self._down_since:
            return now - self._down_since[button]
        return 0.0

    def cue(self, name):
        self.on_cue(name)

    def update(self, now, events=(), held=()):
        """Advance the clock, apply button presses, redraw. Call every loop.

        events are this frame's presses; held is the buttons down right now
        (only used for holding C to leave the game).
        """
        if self.pet.tick(now):
            self.on_attention()
        # The scene first, so one that ends this frame doesn't swallow a
        # press; then again after the presses, so a scene a press just
        # started shows its first frame (and fires its cue) right away.
        self._update_scene(now)
        for button in events:
            if button in input.BUTTONS:
                self._down_since[button] = now
            self.press(button, now)
        for button in input.BUTTONS:
            if button in self._down_since and button not in held and button not in events:
                del self._down_since[button]
        self._update_scene(now)
        # After the presses, so care given in the same frame a stat ran out
        # doesn't count as a sulk.
        sulking = self.pet.sulking
        if sulking and not self._sulking:
            self.on_sulk()
        self._sulking = sulking
        if self.ui is not None:
            self.ui.render(self, now)

    def _update_scene(self, now):
        if self.scene is not None and not self.scene.update(now, self):
            self.scene = None

    def press(self, button, now):
        """One button press: "A", "B" or "C"."""
        if button not in input.BUTTONS:
            return
        if self.scene is not None:
            if self.scene.press(button, now, self):
                self.on_button(button)
            return
        self.on_button(button)
        pet = self.pet

        if pet.asleep:  # any button turns the lights back on
            pet.wake(now)
            return

        if self.page is not None:  # B or C closes the page; A does nothing
            if button != input.A:
                self.page = None
            return

        result = self.menu.press(button)
        if result == input.SELECT:
            item = self.menu.selected
            if item == PAGE_STATS:
                self.page = PAGE_STATS
            elif item == "play":
                self.scene = LeftRight(now, self.rng)
            elif not pet.accepts(item):
                self.scene = anim.Animation(anim.REFUSALS[item], now)
            elif pet.do(item, now):
                self.on_action(item)
                self.scene = anim.Animation(anim.ACTIONS[item], now)
