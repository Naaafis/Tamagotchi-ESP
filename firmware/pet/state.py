"""Pet stats, decay, poops, death and care actions.

Pure Python so it runs unchanged on CircuitPython 10 and CPython: no hardware,
no displayio, no time module. The caller passes `now` in seconds to tick().

Five stats run 0..STAT_MAX and drain while the pet is awake. When one drops to
LOW_THRESHOLD the need shows and the attention flag goes on. At zero the pet
sulks; it recovers as soon as it gets what it was missing, but a pet left
sulking for DEATH_SULK_MINUTES (x DECAY_SCALE) dies. Holding the middle button
starts a new one (pet.game).

Every so often, and more likely soon after eating or drinking, the pet poops.
Up to MAX_POOPS stay on screen until cleaned; while they are there the
attention flag is on and fun and affection drain faster.
"""

import random

# ---- Tuning knobs -----------------------------------------------------------

# How slowly everything happens: each time in EMPTY_MINUTES, POOP_MINUTES,
# MEAL_POOP_MINUTES and DEATH_SULK_MINUTES is multiplied by this. At 3.3 a
# need comes up every ~10 min, a poop every ~6-10 min, and the first need ~8
# min after power-on. Raise it to make the pet less needy, lower it to make
# it ask more often.
DECAY_SCALE = 3.3

STAT_MAX = 100

# Stat order everywhere (dict iteration order is not guaranteed on MicroPython).
STAT_NAMES = ("hunger", "thirst", "energy", "fun", "affection")

# Minutes for each stat to drain from full to empty while awake, before
# DECAY_SCALE. A stat asks for care when it reaches LOW_THRESHOLD, so after a
# full refill hunger asks again 0.7 * 21 * DECAY_SCALE minutes later. Across
# all five stats that is one ask every ~3.1 * DECAY_SCALE minutes once they are
# out of phase (1/14.7 + 1/11.9 + ... per minute at DECAY_SCALE 1).
EMPTY_MINUTES = {
    "hunger": 21,
    "thirst": 17,
    "energy": 36,
    "fun": 20,
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
    "affection": 50,
}

# At or below this the need is "low": attention icon on, pet looks sad.
LOW_THRESHOLD = 30

# At or above this the pet is "full" and refuses food or drink (it shakes its
# head and the food stays, like the original). After a meal that is the next
# ~(100 - FULL_LEVEL) / 100 * 21 * DECAY_SCALE minutes.
FULL_LEVEL = 90

# Actions the pet can refuse when the stat they fill is already full.
REFUSABLE = ("eat", "drink")

# Poops. The next one comes a random POOP_MINUTES after the last (x
# DECAY_SCALE); eating or drinking pulls it to a random MEAL_POOP_MINUTES
# later if that is sooner. At DECAY_SCALE 3.3 that is one every ~6-10 min.
# No pooping while asleep; one that comes due then appears on waking.
MAX_POOPS = 4
POOP_MINUTES = (2.0, 3.0)
MEAL_POOP_MINUTES = (0.7, 1.4)

# While poops are on screen these stats drain faster: 1 + this much per poop
# (1.5x with one, 3x with four).
DIRTY_STATS = ("fun", "affection")
DIRTY_DRAIN_PER_POOP = 0.5

# A pet left sulking (some stat at zero) this long dies: minutes before
# DECAY_SCALE, so ~10 min at 3.3. Its needs only hit zero ~17 minutes after
# the first ask, so that is about half an hour of ignoring it.
DEATH_SULK_MINUTES = 3.0

# Other stats drain this much slower while the pet sleeps.
SLEEP_DECAY_FACTOR = 0.5

# A nap refills energy from empty to full in this many seconds, then the pet
# wakes by itself (never sooner than NAP_MIN_SECONDS). Any button also wakes it.
SLEEP_FULL_SECONDS = 20.0
NAP_MIN_SECONDS = 5.0

# How long the pet holds its eating / drinking / playing pose after an action.
REACTION_SECONDS = 2.0

# ---- Actions ----------------------------------------------------------------

# Actions that each fill one stat. "clean" (clears the poops) is the other one.
ACTIONS = ("eat", "drink", "sleep", "play", "affection")
CLEAN = "clean"

# Which stat each action restores.
ACTION_STAT = {
    "eat": "hunger",
    "drink": "thirst",
    "sleep": "energy",
    "play": "fun",
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
    "affection": STAT_MAX,
}

# Poses the UI knows how to draw.
POSE_IDLE = "idle"
POSE_HAPPY = "happy"
POSE_SAD = "sad"
POSE_SULK = "sulk"
POSE_SLEEP = "sleep"
POSE_DEAD = "dead"


def decay_per_second(name):
    """Points per second the stat loses while awake (before the poop factor)."""
    return STAT_MAX / (EMPTY_MINUTES[name] * DECAY_SCALE * 60.0)


def death_seconds():
    return DEATH_SULK_MINUTES * DECAY_SCALE * 60.0


def _clamp(value):
    if value < 0:
        return 0.0
    if value > STAT_MAX:
        return float(STAT_MAX)
    return value


class Pet:
    """One pet. Call tick(now) every loop, do(action, now) on a button."""

    def __init__(self, now=0.0, levels=None, rng=None):
        self.rng = random if rng is None else rng  # needs uniform(a, b)
        self.stats = {}
        for name in STAT_NAMES:
            start = START_LEVELS[name]
            if levels is not None and name in levels:
                start = levels[name]
            self.stats[name] = _clamp(float(start))
        self.asleep = False
        self.attention = False
        self.dead = False
        self.died = False  # True on the tick() that it died
        self.poops = 0
        self.pooped = 0  # poops that appeared during the last tick()
        self.reaction = None  # action name while the pet shows that reaction
        self._reaction_until = 0.0
        self._slept_at = 0.0
        self._sulk_since = None  # when some stat hit zero, while one is still there
        self._last_now = now
        self._next_poop = now + self._minutes(POOP_MINUTES)
        self._update_attention()

    def _minutes(self, span):
        """Seconds for a random time in span (minutes before DECAY_SCALE)."""
        return self.rng.uniform(span[0], span[1]) * DECAY_SCALE * 60.0

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
        if self.dead:
            return False
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
        """Action that would fix the most urgent need, or None when all is well.

        A low stat comes first; with only poops to complain about it's "clean".
        """
        if not self.attention:
            return None
        if self.low_needs():
            return STAT_ACTION[self.lowest()]
        return CLEAN

    @property
    def pose(self):
        """What the pet looks like right now: one of the POSE_* strings."""
        if self.dead:
            return POSE_DEAD
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
        if self.poops:
            parts.append("poop %d" % self.poops)
        if self.asleep:
            parts.append("(asleep)")
        if self.dead:
            parts.append("(dead)")
        if self.attention:
            parts.append("ATTENTION")
        return "  ".join(parts)

    # ---- time ----

    def tick(self, now):
        """Advance to `now` (seconds). Returns True when attention just came on.

        Afterwards self.pooped is how many poops appeared and self.died is
        True if the pet died during this step. A clock that goes backwards
        (ticks_ms wrap, debugger pause) is treated as no time passing rather
        than a huge or negative step. One long step and many short ones end in
        the same state: the step is split at each poop, and the moment a stat
        runs out is worked out exactly.
        """
        self.pooped = 0
        self.died = False
        if self.dead or now < self._last_now:
            self._last_now = now
            return False
        was = self.attention
        t = self._last_now
        while not self.asleep and self._next_poop <= now:
            at = self._next_poop if self._next_poop > t else t
            self._advance(t, at)
            t = at
            self.poop(t)
        self._advance(t, now)
        self._last_now = now

        if (
            self.asleep
            and self.stats["energy"] >= STAT_MAX
            and now - self._slept_at >= NAP_MIN_SECONDS
        ):
            self.asleep = False

        if self.reaction is not None and now >= self._reaction_until:
            self.reaction = None

        if self._sulk_since is not None and now - self._sulk_since >= death_seconds():
            self.dead = True
            self.died = True
            self.asleep = False
            self.reaction = None

        self._update_attention()
        return self.attention and not was

    def _advance(self, t0, t1):
        """Drain (or, asleep, refill) the stats from t0 to t1 at a steady rate."""
        dt = t1 - t0
        if dt <= 0:
            return
        factor = SLEEP_DECAY_FACTOR if self.asleep else 1.0
        dirty = 1.0 + DIRTY_DRAIN_PER_POOP * self.poops
        ran_out_at = None
        for name in STAT_NAMES:
            value = self.stats[name]
            if self.asleep and name == "energy":
                self.stats[name] = _clamp(value + STAT_MAX * dt / SLEEP_FULL_SECONDS)
                continue
            rate = decay_per_second(name) * factor
            if name in DIRTY_STATS:
                rate *= dirty
            if value > 0 and value <= rate * dt:
                at = t0 + value / rate
                if ran_out_at is None or at < ran_out_at:
                    ran_out_at = at
            self.stats[name] = _clamp(value - rate * dt)
        if not self.sulking:
            self._sulk_since = None
        elif self._sulk_since is None:
            self._sulk_since = t1 if ran_out_at is None else ran_out_at

    def _update_attention(self):
        self.attention = not self.dead and (self.poops > 0 or len(self.low_needs()) > 0)
        if not self.sulking:  # cared for: a later sulk starts the death clock over
            self._sulk_since = None

    # ---- actions ----

    def do(self, action, now):
        """Perform a care action. Returns True if it was a known action."""
        if self.dead:
            return False
        if action == CLEAN:
            if self.asleep:
                self.wake(now)
            self.clean()
            return True
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
        if action in ("eat", "drink"):  # what goes in comes out
            soon = now + self._minutes(MEAL_POOP_MINUTES)
            if soon < self._next_poop:
                self._next_poop = soon
        self._update_attention()
        return True

    def poop(self, now):
        """A poop appears (unless MAX_POOPS are already there). Returns True if one did.

        Also schedules the next one. tick() calls this when one is due; the
        game's debug hold calls it directly.
        """
        appeared = self.poops < MAX_POOPS
        if appeared:
            self.poops += 1
            self.pooped += 1
        self._next_poop = now + self._minutes(POOP_MINUTES)
        self._update_attention()
        return appeared

    def clean(self):
        """Flush every poop away. Returns how many there were."""
        count = self.poops
        self.poops = 0
        self._update_attention()
        return count

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
