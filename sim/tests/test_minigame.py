"""The left/right guessing game (firmware/pet/minigame.py) inside the Game."""

from pet import minigame
from pet.game import MENU_ITEMS, Game
from pet.minigame import GUESS_TIMEOUT, HOLD_EXIT_SECONDS, LOSE_BOOST, ROUNDS, LeftRight
from pet.state import STAT_MAX


class Turns:
    """Stands in for the random module: the pet turns left (0) or right (1) in this order."""

    def __init__(self, turns):
        self.turns = list(turns)

    def randint(self, a, b):
        return self.turns.pop(0)


class Hooks:
    def __init__(self, g):
        self.buttons = []
        self.actions = []
        self.cues = []
        g.on_button = self.buttons.append
        g.on_action = self.actions.append
        g.on_cue = self.cues.append


def start(turns, fun=20):
    g = Game(now=0.0, build_ui=False, rng=Turns(turns))
    g.pet.stats["fun"] = fun
    hooks = Hooks(g)
    g.update(1.0, ["A"] * (MENU_ITEMS.index("play") + 1) + ["B"])
    assert g.playing
    return g, hooks


def play(g, guesses, now=1.0, held=()):
    """Answer each prompt with the next guess until the game ends. Returns the end time."""
    guesses = list(guesses)
    while g.scene is not None and now < 120:
        now = round(now + 0.05, 2)
        presses = ()
        if g.scene.phase == minigame.GUESSING and guesses:
            presses = [guesses.pop(0)]
        g.update(now, presses, held)
    return now


def test_five_right_guesses_win_with_a_full_fun_refill():
    g, hooks = start([0, 1, 0, 1, 0])
    scene = g.scene
    end = play(g, ["A", "C", "A", "C", "A"])
    assert scene.round == ROUNDS
    assert scene.score == 5
    assert scene.won
    assert g.scene is None
    assert g.pet.level("fun") == STAT_MAX
    assert hooks.actions == ["play"]
    assert hooks.cues == ["match"] * 5 + ["win"]
    assert end - 1.0 < 25  # a whole game is short


def test_five_wrong_guesses_lose_with_a_small_boost():
    g, hooks = start([1, 1, 1, 1, 1])
    scene = g.scene
    play(g, ["A"] * 5)
    assert scene.score == 0
    assert scene.won is False
    assert abs(g.pet.stats["fun"] - (20 + LOSE_BOOST)) < 1
    assert hooks.cues == ["miss"] * 5 + ["lose"]


def test_three_out_of_five_wins_and_two_loses():
    g, _ = start([0, 0, 0, 1, 1])
    scene = g.scene
    play(g, ["A"] * 5)
    assert (scene.score, scene.won) == (3, True)
    g, _ = start([0, 0, 1, 1, 1])
    scene = g.scene
    play(g, ["A"] * 5)
    assert (scene.score, scene.won) == (2, False)


def test_score_screen_shows_the_score_out_of_five():
    frames = minigame.score_frames(3)
    names = [o[0] for o in frames[0][5]]
    assert names == ["d3", "slash", "d5"]
    assert frames[0][1] is None  # the pet steps away for the score


def test_b_does_nothing_and_presses_outside_the_prompt_are_ignored():
    g, hooks = start([0])
    scene = g.scene
    assert scene.phase == minigame.STARTING
    g.update(1.1, ["A"])  # still getting ready: ignored
    assert scene.phase == minigame.STARTING
    now = 1.1
    while scene.phase != minigame.GUESSING:
        now = round(now + 0.05, 2)
        g.update(now)
    buttons = len(hooks.buttons)
    g.update(now + 0.05, ["B"])
    assert scene.phase == minigame.GUESSING
    assert len(hooks.buttons) == buttons  # no tick for B
    g.update(now + 0.1, ["C"])  # guess right
    assert scene.phase == minigame.TURNING
    assert scene.guess == minigame.RIGHT
    assert hooks.buttons[-1] == "C"
    g.update(now + 0.15, ["A"])  # mid-turn: ignored
    assert scene.guess == minigame.RIGHT


def test_no_guess_for_eight_seconds_leaves_the_game_with_no_boost():
    g, hooks = start([0])
    now = 1.0
    while g.scene.phase != minigame.GUESSING:
        now = round(now + 0.05, 2)
        g.update(now)
    g.update(now + GUESS_TIMEOUT - 0.1)
    assert g.playing
    g.update(now + GUESS_TIMEOUT + 0.05)
    assert not g.playing
    assert g.scene is None
    assert hooks.actions == []
    assert g.pet.stats["fun"] < 20


def test_holding_c_leaves_the_game_but_a_tap_does_not():
    g, hooks = start([1, 1, 1, 1, 1])
    now = 1.0
    while g.scene.phase != minigame.GUESSING:
        now = round(now + 0.05, 2)
        g.update(now)
    g.update(now + 0.05, ["C"], held=["C"])  # a tap: guesses right, released next frame
    g.update(now + 0.1)
    g.update(now + 0.1 + HOLD_EXIT_SECONDS + 0.1)
    assert g.playing
    t = now + 2.0
    g.update(t, held=["C"])  # held without a fresh press doesn't count
    g.update(t + HOLD_EXIT_SECONDS + 0.1, held=["C"])
    assert g.playing
    while g.scene.phase != minigame.GUESSING:
        t = round(t + 0.05, 2)
        g.update(t)
    g.update(t + 0.05, ["C"], held=["C"])
    g.update(t + 0.05 + HOLD_EXIT_SECONDS / 2, held=["C"])
    assert g.playing
    g.update(t + 0.05 + HOLD_EXIT_SECONDS + 0.01, held=["C"])
    assert not g.playing
    assert hooks.actions == []


def test_playing_flag_only_while_the_game_runs():
    g = Game(now=0.0, build_ui=False, rng=Turns([0] * 5))
    assert not g.playing
    g.update(1.0, ["A"] * (MENU_ITEMS.index("play") + 1) + ["B"])
    assert g.playing
    assert isinstance(g.scene, LeftRight)
    play(g, ["A"] * 5)
    assert not g.playing
