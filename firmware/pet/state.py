"""Pet stats, decay and care actions.

Pure Python so it runs unchanged on CircuitPython 10 and CPython: no hardware,
no displayio, no time module. The caller passes `now` in seconds to tick().

Six stats run 0..STAT_MAX and drain while the pet is awake. When one drops to
LOW_THRESHOLD the need shows and the attention flag goes on. At zero the pet
sulks; there is no death, it recovers as soon as it gets what it was missing.
"""

# ---- Tuning knobs -----------------------------------------------------------

# How slowly every stat drains: each time in EMPTY_MINUTES is multiplied by
# this. 1.0 is the original party pace (an ask every ~2.7 min); 3.3 gives an
# ask every ~9 min and the first one ~8 min after power-on. Raise it to make
# the pet less needy, lower it to make it ask more often.
DECAY_SCALE = 3.3

STAT_MAX = 100

# Stat order everywhere (dict iteration order is not guaranteed on MicroPython).
STAT_NAMES = ("hunger", "thirst", "energy", "fun", "treats", "affection")

# Minutes for each stat to drain from full to empty while awake, before
# DECAY_SCALE. A stat asks for care when it reaches LOW_THRESHOLD, so after a
# full refill hunger asks again 0.7 * 21 * DECAY_SCALE minutes later. Across
# all six stats that is one ask every ~2.7 * DECAY_SCALE minutes once they are
# out of phase (1/14.7 + 1/11.9 + ... per minute at DECAY_SCALE 1).
EMPTY_MINUTES = {
    "hunger": 21,
    "thirst": 17,
    "energy": 36,
    "fun": 20,
    "treats": 29,
    "affection": 26,
}

# Fresh-pet levels, staggered so the asks don't all land together. At
# DECAY_SCALE 3.3 hunger asks first, ~8 minutes after power-on, and the rest
# follow over the next 4-11 minutes.
START_LEVELS = {
    "hunger": 42,
    "thirst": 55,
    "energy": 40,
    "fun": 50,
    "treats": 50,
    "affection": 50,
}

# At or below this the need is "low": attention icon on, pet looks sad.
LOW_THRESHOLD = 30

# At or above this the pet is "full" and refuses food or drink (it shakes its
# head and the food stays, like the original). After a meal that is the next
# ~(100 - FULL_LEVEL) / 100 * 21 * DECAY_SCALE minutes.
FULL_LEVEL = 90

# Actions the pet can refuse when the stat they fill is already full. Treats
# are like the original's snacks: always welcome.
REFUSABLE = ("eat", "drink")

# Other stats drain this much slower while the pet sleeps.
SLEEP_DECAY_FACTOR = 0.5

# A nap refills energy from empty to full in this many seconds, then the pet
# wakes by itself (never sooner than NAP_MIN_SECONDS). Any button also wakes it.
SLEEP_FULL_SECONDS = 20.0
NAP_MIN_SECONDS = 5.0

# How long the pet holds its eating / drinking / playing pose after an action.
REACTION_SECONDS = 2.0

# ---- Actions ----------------------------------------------------------------

ACTIONS = ("eat", "drink", "sleep", "play", "treat", "affection")

# Which stat each action restores.
ACTION_STAT = {
    "eat": "hunger",
    "drink": "thirst",
    "sleep": "energy",
    "play": "fun",
    "treat": "treats",
    "affection": "affection",
}

# Reverse map: which action fixes each stat.
STAT_ACTION = {}
for _action in ACTIONS:
    STAT_ACTION[ACTION_STAT[_action]] = _action

# Points an action adds to its stat (STAT_MAX = always a full refill). Sleep is
# gradual instead, see SLEEP_FULL_SECONDS.
RESTORE_AMOUNT = {
    "eat": STAT_MAX,
    "drink": STAT_MAX,
    "play": STAT_MAX,
    "treat": STAT_MAX,
    "affection": STAT_MAX,
}

# Poses the UI knows how to draw.
POSE_IDLE = "idle"
POSE_HAPPY = "happy"
POSE_SAD = "sad"
POSE_SULK = "sulk"
POSE_SLEEP = "sleep"


def decay_per_second(name):
    """Points per second the stat loses while awake."""
    return STAT_MAX / (EMPTY_MINUTES[name] * DECAY_SCALE * 60.0)


def _clamp(value):
    if value < 0:
        return 0.0
    if value > STAT_MAX:
        return float(STAT_MAX)
    return value


class Pet:
    """One pet. Call tick(now) every loop, do(action, now) on a button."""

    def __init__(self, now=0.0, levels=None):
        self.stats = {}
        for name in STAT_NAMES:
            start = START_LEVELS[name]
            if levels is not None and name in levels:
                start = levels[name]
            self.stats[name] = _clamp(float(start))
        self.asleep = False
        self.attention = False
        self.reaction = None  # action name while the pet shows that reaction
        self._reaction_until = 0.0
        self._slept_at = 0.0
        self._last_now = now
        self._update_attention()

    # ---- queries ----

    def level(self, name):
        """Stat as an int 0..STAT_MAX."""
        return int(self.stats[name] + 0.5)

    def is_low(self, name):
        return self.stats[name] <= LOW_THRESHOLD

    def is_full(self, name):
        return self.stats[name] >= FULL_LEVEL

    def accepts(self, action):
        """False when the pet would refuse this action (full and it's eat or drink)."""
        if action in REFUSABLE:
            return not self.is_full(ACTION_STAT[action])
        return True

    def low_needs(self):
        """Stat names at or below LOW_THRESHOLD, in STAT_NAMES order."""
        low = []
        for name in STAT_NAMES:
            if self.is_low(name):
                low.append(name)
        return low

    def lowest(self):
        """Name of the lowest stat."""
        best = STAT_NAMES[0]
        for name in STAT_NAMES:
            if self.stats[name] < self.stats[best]:
                best = name
        return best

    @property
    def sulking(self):
        """True while any stat sits at zero."""
        for name in STAT_NAMES:
            if self.stats[name] <= 0:
                return True
        return False

    @property
    def wants(self):
        """Action that would fix the most urgent need, or None when all is well."""
        if not self.attention:
            return None
        return STAT_ACTION[self.lowest()]

    @property
    def pose(self):
        """What the pet looks like right now: one of the POSE_* strings."""
        if self.asleep:
            return POSE_SLEEP
        if self.reaction is not None:
            return POSE_HAPPY
        if self.sulking:
            return POSE_SULK
        if self.attention:
            return POSE_SAD
        return POSE_IDLE

    def summary(self):
        """One-line stat dump for logs and the simulator window title."""
        parts = []
        for name in STAT_NAMES:
            parts.append("%s %d" % (name, self.level(name)))
        if self.asleep:
            parts.append("(asleep)")
        if self.attention:
            parts.append("ATTENTION")
        return "  ".join(parts)

    # ---- time ----

    def tick(self, now):
        """Advance to `now` (seconds). Returns True when attention just came on.

        A clock that goes backwards (ticks_ms wrap, debugger pause) is treated
        as no time passing rather than a huge or negative step.
        """
        dt = now - self._last_now
        self._last_now = now
        if dt < 0:
            dt = 0.0

        factor = SLEEP_DECAY_FACTOR if self.asleep else 1.0
        for name in STAT_NAMES:
            if self.asleep and name == "energy":
                value = self.stats[name] + STAT_MAX * dt / SLEEP_FULL_SECONDS
            else:
                value = self.stats[name] - decay_per_second(name) * factor * dt
            self.stats[name] = _clamp(value)

        if (
            self.asleep
            and self.stats["energy"] >= STAT_MAX
            and now - self._slept_at >= NAP_MIN_SECONDS
        ):
            self.asleep = False

        if self.reaction is not None and now >= self._reaction_until:
            self.reaction = None

        was = self.attention
        self._update_attention()
        return self.attention and not was

    def _update_attention(self):
        self.attention = len(self.low_needs()) > 0

    # ---- actions ----

    def do(self, action, now):
        """Perform a care action. Returns True if it was a known action."""
        if action == "sleep":
            if self.asleep:
                self.wake(now)
            else:
                self.sleep(now)
            return True
        if action not in RESTORE_AMOUNT:
            return False
        if self.asleep:
            self.wake(now)
        stat = ACTION_STAT[action]
        self.stats[stat] = _clamp(self.stats[stat] + RESTORE_AMOUNT[action])
        self.reaction = action
        self._reaction_until = now + REACTION_SECONDS
        self._update_attention()
        return True

    def add(self, stat, amount):
        """Raise (or lower) one stat by amount points, clamped to 0..STAT_MAX."""
        self.stats[stat] = _clamp(self.stats[stat] + amount)
        self._update_attention()

    def sleep(self, now):
        """Lights off. Energy refills over SLEEP_FULL_SECONDS."""
        self.asleep = True
        self.reaction = None
        self._slept_at = now

    def wake(self, now):
        self.asleep = False
