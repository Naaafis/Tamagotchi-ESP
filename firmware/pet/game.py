"""The game: pet + menu + screen, driven by Game.update(now, events).

    game = Game(now=time.monotonic())
    display.root_group = game.root_group
    while True:
        game.update(time.monotonic(), ["A"])   # events: "A" / "B" / "C" presses

Hooks for sound and backlight (no-ops unless the caller sets them; the
board's code.py wires them to the speaker and backlight):
    game.on_attention()        called once each time the attention icon turns on
    game.on_button(name)       called on every press, with "A", "B" or "C"
    game.on_action(action)     called when a care action is done ("eat", "sleep", ...)
    game.on_sulk()             called once each time the pet starts sulking (a stat hit zero)
"""

from pet import input
from pet.state import Pet

# Icon order on screen: first four on the top row, the rest on the bottom row,
# with the attention icon in the bottom-right slot.
MENU_ITEMS = ("eat", "drink", "sleep", "play", "treat", "affection", "stats")

PAGE_STATS = "stats"


def _noop(*args):
    pass


class Game:
    def __init__(self, now=0.0, width=320, height=240, build_ui=True):
        self.pet = Pet(now)
        self.menu = input.Menu(MENU_ITEMS)
        self.page = None  # None or PAGE_STATS
        self.on_attention = _noop
        self.on_button = _noop
        self.on_action = _noop
        self.on_sulk = _noop
        self._sulking = self.pet.sulking
        self.ui = None
        self.root_group = None
        if build_ui:
            from pet.ui import PetUI  # displayio only needed when drawing

            self.ui = PetUI(MENU_ITEMS, width, height)
            self.root_group = self.ui.root
            self.ui.render(self, now)

    def update(self, now, events=()):
        """Advance the clock, apply button presses, redraw. Call every loop."""
        if self.pet.tick(now):
            self.on_attention()
        for button in events:
            self.press(button, now)
        # After the presses, so care given in the same frame a stat ran out
        # doesn't count as a sulk.
        sulking = self.pet.sulking
        if sulking and not self._sulking:
            self.on_sulk()
        self._sulking = sulking
        if self.ui is not None:
            self.ui.render(self, now)

    def press(self, button, now):
        """One button press: "A", "B" or "C"."""
        if button not in input.BUTTONS:
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
            elif pet.do(item, now):
                self.on_action(item)
