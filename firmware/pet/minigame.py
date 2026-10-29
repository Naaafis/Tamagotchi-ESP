"""Play: the original's left/right guessing game, as a scene.

Hardware-agnostic like the rest of pet/. Five rounds. Each round the pet
stands in the middle, arrows show on both sides, and the player guesses
which way it will turn: A for left, C for right (B does nothing). The pet
turns at random; a match gets a happy hop, a miss a sad face. After five
rounds the score shows (e.g. 3/5): WIN_SCORE or more is a win, a big fun
boost and a hop; fewer is a small boost and a sad face.

No guess for GUESS_TIMEOUT seconds, or holding C for HOLD_EXIT_SECONDS,
leaves the game with no boost. Presses outside the guess are ignored.

Frames use the same tuples as pet.anim, so ui.py draws a game frame exactly
like an animation frame.
"""

from pet import input
from pet.anim import Animation, frame, fx, hop
from pet.state import STAT_MAX

ROUNDS = 5
WIN_SCORE = 3
GUESS_TIMEOUT = 8.0
HOLD_EXIT_SECONDS = 1.0
WIN_BOOST = STAT_MAX  # fun points for a win: a full refill
LOSE_BOOST = 25  # and for trying

LEFT = "left"
RIGHT = "right"

ARROW_Y = 5
LEFT_ARROW = fx("arrow", 0, ARROW_Y)
RIGHT_ARROW = fx("arrow", 22, ARROW_Y, True)

READY = (frame(300, "idle0"), frame(300, "idle1"))
PROMPT = frame(0, "idle0", overlays=(LEFT_ARROW, RIGHT_ARROW))
REVEAL_MS = 700
MATCH = (
    frame(200, "happy_up", overlays=(fx("sparkle0", 22, 0),), cue="match"),
    frame(200, "happy", overlays=(fx("sparkle1", 22, 1),)),
    frame(200, "happy_up", overlays=(fx("sparkle0", 22, 0),)),
    frame(200, "happy"),
    frame(300, "idle0"),
)
MISS = (frame(900, "sad", cue="miss"), frame(300, "idle0"))
SCORE_MS = 1500
WIN = hop("win") + hop(None)
LOSE = (frame(1500, "sad", cue="lose"),)

# Phases.
STARTING = "ready"
GUESSING = "guess"
TURNING = "turn"
RESULT = "result"
SCORING = "score"
ENDING = "end"


def reveal_frames(guess, turn):
    """The pet turns to `turn`; only the arrow the player picked stays up."""
    arrow = LEFT_ARROW if guess == LEFT else RIGHT_ARROW
    return (frame(REVEAL_MS, "side", flip=turn == RIGHT, overlays=(arrow,)),)


def score_frames(score):
    """The score, e.g. "3/5", in the middle of the stage; the pet steps away."""
    digits = (fx("d%d" % score, 9, 4), fx("slash", 13, 4), fx("d%d" % ROUNDS, 18, 4))
    return (frame(SCORE_MS, None, overlays=digits),)


class LeftRight:
    """One game. Call update(now, game) every frame; it returns False when over."""

    def __init__(self, now, rng):
        self.rng = rng  # anything with randint(a, b), e.g. the random module
        self.round = 0  # rounds finished
        self.score = 0
        self.guess = None
        self.turn = None
        self.won = None  # True / False once the score is in
        self.phase = None
        self._anim = None
        self._guess_since = 0.0
        self._start(STARTING, READY, now)

    @property
    def frame(self):
        if self.phase == GUESSING:
            return PROMPT
        return self._anim.frame

    def _start(self, phase, frames, now):
        self.phase = phase
        self._anim = None if frames is None else Animation(frames, now)
        if phase == GUESSING:
            self._guess_since = now

    def press(self, button, now, game):
        """A guesses left, C right, while the arrows are up. Returns True if used."""
        if self.phase != GUESSING or button not in (input.A, input.C):
            return False
        self.guess = LEFT if button == input.A else RIGHT
        self.turn = LEFT if self.rng.randint(0, 1) == 0 else RIGHT
        self._start(TURNING, reveal_frames(self.guess, self.turn), now)
        return True

    def update(self, now, game):
        if game.held_for(input.C, now) >= HOLD_EXIT_SECONDS:
            return False
        if self.phase == GUESSING:
            return now - self._guess_since < GUESS_TIMEOUT
        # A phase that ends this frame hands over to the next one, which gets
        # its first update (and cue) in the same frame.
        while not self._anim.update(now, game):
            if not self._next(now, game):
                return False
            if self._anim is None:  # waiting for a guess
                return True
        return True

    def _next(self, now, game):
        """Move on from the phase that just ended. False when the game is over."""
        if self.phase == STARTING:
            self._start(GUESSING, None, now)
        elif self.phase == TURNING:
            matched = self.guess == self.turn
            if matched:
                self.score += 1
            self._start(RESULT, MATCH if matched else MISS, now)
        elif self.phase == RESULT:
            self.round += 1
            if self.round < ROUNDS:
                self._start(STARTING, READY, now)
            else:
                self._start(SCORING, score_frames(self.score), now)
        elif self.phase == SCORING:
            self.won = self.score >= WIN_SCORE
            game.pet.add("fun", WIN_BOOST if self.won else LOSE_BOOST)
            game.on_action("play")
            self._start(ENDING, WIN if self.won else LOSE, now)
        else:  # ENDING
            return False
        return True
