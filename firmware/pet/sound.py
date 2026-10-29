"""What the pet sounds like: the tunes, and which one plays when.

Hardware-agnostic like the rest of pet/. A tune is a tuple of (hz, ms) notes,
0 Hz being a rest. Sounds turns the Game's hooks into tunes and hands them to
a player whose play(tune) returns at once: hw.board_esp32s3.Audio on the board
(square waves through the MAX98357A), a print-only stand-in in the simulator.

    sounds = Sounds(player)
    game.on_button = lambda name: sounds.button()
    game.on_attention = sounds.attention
    game.on_sulk = sounds.sulk
    game.on_cue = sounds.cue          # animation beats: bites, refusals, hops, the game
    while True:
        game.update(now, presses)
        sounds.update(now, game.pet.attention)   # starts this frame's tune, if any
"""

# ---- Tunes ------------------------------------------------------------------
# (hz, ms) per note, 0 Hz = rest. Classic Tamagotchi beeps: short, high, square.
# The board renders at 16 kHz, so keep notes under ~4 kHz.

# Every button press.
TICK = ((2637, 30),)

# The attention icon turned on: three quick high beeps.
CHIRP = ((3136, 60), (0, 50), (3136, 60), (0, 50), (3136, 60))

# The happy hop at the end of an accepted action, and winning the game: a
# rising major arpeggio (G6 B6 D7 G7).
HAPPY = ((1568, 70), (0, 20), (1976, 70), (0, 20), (2349, 70), (0, 20), (3136, 160))

# Each bite of food or a treat, and each sip.
BLIP = ((1760, 40),)

# The pet refuses food or drink: a falling "uh-uh".
REFUSE = ((523, 110), (0, 50), (392, 160))

# A round of the left/right game: guessed right, guessed wrong.
MATCH = ((2637, 50), (0, 30), (3136, 100))
MISS = ((330, 120), (0, 40), (262, 200))

# The pet started sulking (a stat hit zero), and losing the game: low and
# falling (G4 Eb4 C4).
SAD = ((392, 200), (0, 40), (311, 200), (0, 40), (262, 500))

# Power-on: a short two-note hello, so you can tell the sound works.
STARTUP = ((2093, 60), (0, 30), (3136, 90))

TUNES = (TICK, CHIRP, HAPPY, BLIP, REFUSE, MATCH, MISS, SAD, STARTUP)
NAMES = {
    TICK: "tick",
    CHIRP: "chirp",
    HAPPY: "happy",
    BLIP: "blip",
    REFUSE: "refuse",
    MATCH: "match",
    MISS: "miss",
    SAD: "sad",
    STARTUP: "startup",
}

# The tune for each animation cue (pet.anim, pet.minigame).
CUES = {
    "bite": BLIP,
    "sip": BLIP,
    "refuse": REFUSE,
    "happy": HAPPY,
    "match": MATCH,
    "miss": MISS,
    "win": HAPPY,
    "lose": SAD,
}

# While the pet keeps asking for attention, chirp again this often. Counted
# from the last chirp or button press, so it doesn't nag someone who is
# already in the menu.
REMINDER_SECONDS = 20.0


def name(tune):
    """Short name of a tune for logs ("chirp"), or "tune" if it isn't one of ours."""
    return NAMES.get(tune, "tune")


def duration_ms(tune):
    total = 0
    for _hz, ms in tune:
        total += ms
    return total


class Sounds:
    """Picks the tune for each game event and starts at most one per frame.

    Wire the Game's hooks to button(), attention(), sulk() and cue(), and
    call update(now, attention) once per frame after game.update(). Within one
    frame a tick never replaces a bigger sound, and any other sound replaces
    a pending tick. A new
    sound cuts off whatever is still playing. With mute set nothing reaches
    the player, but update() still reports what would have played.
    """

    def __init__(self, player, mute=False, reminder_seconds=REMINDER_SECONDS):
        self.player = player
        self.mute = mute
        self.reminder_seconds = reminder_seconds
        self._tune = None  # asked for this frame
        self._restart_reminder = False
        self._next_reminder = None  # when the next reminder chirp is due; None while attention is off

    def play(self, tune):
        """Ask for tune to start at the end of this frame."""
        if tune == TICK and self._tune is not None:
            return
        self._tune = tune

    def button(self):
        self.play(TICK)
        self._restart_reminder = True

    def attention(self):
        self.play(CHIRP)
        self._restart_reminder = True

    def cue(self, name):
        """An animation beat; cues without a tune are silent."""
        tune = CUES.get(name)
        if tune is not None:
            self.play(tune)

    def sulk(self):
        self.play(SAD)

    def update(self, now, attention):
        """Repeat the chirp while attention stays on, then start this frame's tune.

        now is in seconds; attention is whether the pet is asking right now.
        Returns the tune started this frame, or None.
        """
        if not attention:
            self._next_reminder = None
        elif self._restart_reminder or self._next_reminder is None:
            self._next_reminder = now + self.reminder_seconds
        elif now >= self._next_reminder:
            self.play(CHIRP)
            self._next_reminder = now + self.reminder_seconds
        self._restart_reminder = False

        tune = self._tune
        self._tune = None
        if tune is not None and not self.mute:
            self.player.play(tune)
        return tune
