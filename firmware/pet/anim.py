"""Action animations, timed like the original Tamagotchi, as plain data.

Hardware-agnostic: no displayio. ui.py draws whatever frame is current.

The middle of the screen is a stage STAGE_W x STAGE_H art pixels (each drawn
8x8). The pet is a 16x16 frame from sprites.PET_FRAMES at (x, y); overlays
are 8x8 tiles from sprites.FX_NAMES (food, cup, hearts, sparkles, Z's,
arrows, digits). A frame is a tuple:

    (ms, pet, x, y, flip, overlays, cue)

ms is how long it shows. pet is a frame name or None (hidden). flip mirrors
the pet (side frames face left; flipped they face right). overlays is a
tuple of (name, x, y, flip). cue, when set, is passed to the game's on_cue
hook as the frame starts: "bite", "sip", "refuse", "happy", ... (pet.sound
maps cues to tunes).

The original's beat is about half a second: food appears, three bites with
the food shrinking each time, then the pet hops with a sparkle.
"""

STAGE_W = 30  # art pixels: 240 px square / 8
STAGE_H = 16  # between the icon rows: 128 px / 8
MAX_OVERLAYS = 4  # the UI has this many overlay slots

# Index of each field in a frame tuple.
MS = 0
PET = 1
X = 2
Y = 3
FLIP = 4
OVERLAYS = 5
CUE = 6

HOME_X = 7  # pet centered: 7 + 16 + 7 = 30
HOME_Y = 0
BESIDE_X = 12  # pet standing beside a prop
LIE_X = 5  # lying down, left of center so the Z's rise up and to the right
PROP_X = 2
PROP_Y = 7  # props' ink ends on their row 6, level with the pet's feet


def frame(ms, pet, x=HOME_X, y=HOME_Y, flip=False, overlays=(), cue=None):
    return (ms, pet, x, y, flip, overlays, cue)


def fx(name, x, y, flip=False):
    """One overlay for a frame's overlays tuple."""
    return (name, x, y, flip)


def duration_ms(frames):
    total = 0
    for f in frames:
        total += f[MS]
    return total


# ---- The happy hop ----------------------------------------------------------
# After every accepted action: back to the middle, two little hops with a
# twinkling sparkle, and the jingle. Hops and bounces use the "happy_up" frame
# rather than moving the pet (see sprites._HAPPY_UP: a move costs twice a swap).



def hop(cue="happy"):
    """Two hops with a sparkle; cue fires as the first hop starts."""
    return (
        frame(250, "happy_up", overlays=(fx("sparkle0", 22, 0),), cue=cue),
        frame(250, "happy", overlays=(fx("sparkle1", 22, 1),)),
        frame(250, "happy_up", overlays=(fx("sparkle0", 22, 0),)),
        frame(250, "happy"),
    )


HOP = hop()


# ---- Eat, drink, treat ------------------------------------------------------

APPEAR_MS = 500
MOUTH_MS = 350  # mouth open, then the same again chewing


def _consume(props, cue):
    """Prop appears beside the pet; three bites, the prop shrinking each time.

    props is the prop at each stage: full, after one bite, after two, after
    three (None = gone). The cue fires on each chomp.
    """
    frames = [frame(APPEAR_MS, "side", x=BESIDE_X, overlays=(fx(props[0], PROP_X, PROP_Y),))]
    for bite in range(3):
        before = (fx(props[bite], PROP_X, PROP_Y),)
        after = () if props[bite + 1] is None else (fx(props[bite + 1], PROP_X, PROP_Y),)
        frames.append(frame(MOUTH_MS, "side_eat", x=BESIDE_X, overlays=before))
        frames.append(frame(MOUTH_MS, "side", x=BESIDE_X, overlays=after, cue=cue))
    return tuple(frames) + HOP


def _refuse(prop):
    """Prop appears, the pet shakes its head side to side, the prop stays."""
    there = (fx(prop, PROP_X, PROP_Y),)
    return (
        frame(APPEAR_MS, "side", x=BESIDE_X, overlays=there),
        frame(300, "no", x=BESIDE_X, overlays=there, cue="refuse"),
        frame(300, "no", x=BESIDE_X, flip=True, overlays=there),
        frame(300, "no", x=BESIDE_X, overlays=there),
        frame(300, "no", x=BESIDE_X, flip=True, overlays=there),
        frame(500, "side", x=BESIDE_X, overlays=there),
    )


EAT = _consume(("food0", "food1", "food2", None), "bite")
DRINK = _consume(("cup0", "cup1", "cup2", "cup3"), "sip")  # the empty cup stays until the hop
TREAT = _consume(("pumpkin0", "pumpkin1", "pumpkin2", None), "bite")

REFUSE_EAT = _refuse("food0")
REFUSE_DRINK = _refuse("cup0")


# ---- Affection --------------------------------------------------------------
# Bouncing on the spot while hearts float up on both sides and pop.

# Hearts sit one column clear of the pet (its ink spans stage columns 8-21).
L_HEART = 0
R_HEART = 23

AFFECTION = (
    frame(330, "happy", overlays=(fx("heart", L_HEART, 6),)),
    frame(330, "happy_up", overlays=(fx("heart", L_HEART, 3), fx("heart", R_HEART, 6))),
    frame(330, "happy", overlays=(fx("heart", L_HEART, 0), fx("heart", R_HEART, 3))),
    frame(330, "happy_up", overlays=(fx("sparkle1", L_HEART, 0), fx("heart", R_HEART, 0), fx("heart", L_HEART, 6))),
    frame(330, "happy", overlays=(fx("sparkle1", R_HEART, 0), fx("heart", L_HEART, 3))),
    frame(330, "happy_up", overlays=(fx("heart", L_HEART, 0),)),
) + HOP


# ---- Sleep ------------------------------------------------------------------
# Yawn, lie down, eyes close, the first z. Then the lights go out: the game
# leaves the animation and the screen shows SLEEPING until the pet wakes.

SMALL_Z = fx("z_small", 17, 1)  # just clear of the lying pet's head
BIG_Z = fx("z_big", 23, 0)  # higher up and further right

SLEEP = (
    frame(400, "idle0"),
    frame(900, "yawn"),
    frame(300, "idle0"),
    frame(500, "lie", x=LIE_X),
    frame(600, "lie_sleep", x=LIE_X, overlays=(SMALL_Z,)),
)

# Lights off: the pet lies asleep and "Z z z" rises, one step every Z_SECONDS:
# a small z by its head, a big Z above it, the small one fades, then the big.
Z_SECONDS = 0.6
SLEEPING = (
    (SMALL_Z,),
    (SMALL_Z, BIG_Z),
    (BIG_Z,),
    (),
)


# What each menu action plays. Play has its own scene (pet.minigame).
ACTIONS = {
    "eat": EAT,
    "drink": DRINK,
    "treat": TREAT,
    "affection": AFFECTION,
    "sleep": SLEEP,
}
REFUSALS = {
    "eat": REFUSE_EAT,
    "drink": REFUSE_DRINK,
}


class Animation:
    """Plays a tuple of frames once, then reports that it is done.

    update() advances to `now`, firing each frame's cue as the frame starts
    (frames skipped by a slow loop still fire theirs), and returns False once
    the last frame has had its time. .frame is what to draw. Presses are
    ignored while it runs, like the original.
    """

    def __init__(self, frames, now):
        self.frames = frames
        self.index = -1
        self._next = now  # when the next frame starts

    @property
    def frame(self):
        return self.frames[self.index if self.index >= 0 else 0]

    def update(self, now, game):
        while now >= self._next:
            self.index += 1
            if self.index >= len(self.frames):
                self.index = len(self.frames) - 1
                return False
            f = self.frames[self.index]
            self._next += f[MS] / 1000.0
            if f[CUE] is not None:
                game.cue(f[CUE])
        return True

    def press(self, button, now, game):
        return False
