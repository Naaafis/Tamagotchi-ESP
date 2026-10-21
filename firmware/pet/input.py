"""Three-button menu navigation, Tamagotchi style.

A moves the highlight along the icons (and off again after the last one),
B performs the highlighted icon, C clears the highlight. Game decides what a
selection means; this only tracks the cursor.
"""

A = "A"
B = "B"
C = "C"
BUTTONS = (A, B, C)

MOVE = "move"
SELECT = "select"
CANCEL = "cancel"

NONE = -1  # cursor value when nothing is highlighted


class Menu:
    def __init__(self, items):
        self.items = tuple(items)
        self.cursor = NONE

    @property
    def selected(self):
        """Highlighted item name, or None."""
        if self.cursor == NONE:
            return None
        return self.items[self.cursor]

    def press(self, button):
        """Apply a press. Returns MOVE, SELECT, CANCEL or None (press ignored).

        SELECT is only returned when something is highlighted.
        """
        if button == A:
            self.cursor += 1
            if self.cursor >= len(self.items):
                self.cursor = NONE
            return MOVE
        if button == B:
            if self.cursor == NONE:
                return None
            return SELECT
        if button == C:
            self.cursor = NONE
            return CANCEL
        return None

    def clear(self):
        self.cursor = NONE
