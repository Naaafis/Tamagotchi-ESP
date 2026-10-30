"""Poops, Clean, death by the UFO and the holds, inside the Game (firmware/pet/game.py)."""

from pet import anim
from pet.game import DEBUG_POOP_HOLD_SECONDS, MENU_ITEMS, MUTE_HOLD_SECONDS, RESET_HOLD_SECONDS, Game
from pet.state import CLEAN, MAX_POOPS, STAT_MAX, STAT_NAMES, death_seconds


class Hooks:
    def __init__(self, g):
        self.calls = []
        g.on_attention = lambda: self.calls.append("attention")
        g.on_action = lambda action: self.calls.append("action " + action)
        g.on_cue = lambda name: self.calls.append("cue " + name)
        g.on_death = lambda: self.calls.append("death")
        g.on_reset = lambda: self.calls.append("reset")
        g.on_mute_toggle = lambda: self.calls.append("mute")

    def cues(self):
        return [c[4:] for c in self.calls if c.startswith("cue ")]


def new_game():
    g = Game(now=0.0, build_ui=False, hatch=False)
    for name in STAT_NAMES:  # nothing needed, so only poops ask for attention
        g.pet.stats[name] = STAT_MAX
    g.update(0.0)
    return g, Hooks(g)


def select(item):
    return ["C"] + ["A"] * (MENU_ITEMS.index(item) + 1) + ["B"]


def run(g, start, seconds, held=()):
    """Frames every 50 ms from start for seconds; returns the end time."""
    now = start
    while now < start + seconds:
        now = round(now + 0.05, 2)
        g.update(now, (), held)
    return now


def test_a_poop_due_plops_and_asks_for_attention():
    g, hooks = new_game()
    g.pet._next_poop = 5.0
    g.update(4.9)
    assert g.pet.poops == 0
    g.update(5.1)
    assert g.pet.poops == 1
    assert hooks.cues() == ["plop"]
    assert "attention" in hooks.calls
    assert g.pet.wants == CLEAN


def test_holding_left_forces_one_poop_per_hold():
    g, hooks = new_game()
    g.update(1.0, ["A"], ["A"])
    end = run(g, 1.0, DEBUG_POOP_HOLD_SECONDS - 0.2, ["A"])
    assert g.pet.poops == 0
    end = run(g, end, 2.0, ["A"])  # past 3 s, and kept holding
    assert g.pet.poops == 1
    assert hooks.cues() == ["plop"]
    g.update(end + 0.05)  # released
    g.update(end + 0.1, ["A"], ["A"])
    run(g, end + 0.1, DEBUG_POOP_HOLD_SECONDS + 0.1, ["A"])
    assert g.pet.poops == 2


def test_clean_sweeps_the_poops_away_and_hops():
    g, hooks = new_game()
    for _ in range(3):
        g.pet.poop(0.0)
    g.update(1.0, select(CLEAN))
    assert g.pet.poops == 0  # flushed now; the sweep shows them going
    assert isinstance(g.scene, anim.Animation)
    assert g.scene.frames == anim.clean_frames(3)
    assert "action clean" in hooks.calls
    run(g, 1.0, anim.duration_ms(anim.clean_frames(3)) / 1000.0 + 0.1)
    assert g.scene is None
    assert hooks.cues() == ["flush"]


def test_clean_with_nothing_to_flush_still_sweeps():
    g, hooks = new_game()
    g.update(1.0, select(CLEAN))
    assert g.scene.frames == anim.clean_frames(0)
    assert "action clean" not in hooks.calls
    run(g, 1.0, anim.duration_ms(anim.clean_frames(0)) / 1000.0 + 0.1)
    assert g.scene is None
    assert hooks.cues() == []


def test_poops_stop_at_the_max():
    g, _ = new_game()
    for _ in range(MAX_POOPS + 2):
        g.pet.poop(0.0)
    assert g.pet.poops == MAX_POOPS


def die(g, hooks):
    """Starve it: one stat at zero, then wait out the death clock."""
    g.pet.stats["hunger"] = 0
    g.update(1.0)
    assert g.pet.sulking
    g.update(1.0 + death_seconds() + 0.1)
    assert g.pet.dead
    return 1.0 + death_seconds() + 0.1


def test_neglected_too_long_it_dies_and_the_ufo_takes_it():
    g, hooks = new_game()
    g.update(0.5, ["A"])  # menu open
    now = die(g, hooks)
    assert hooks.calls.count("death") == 1
    assert g.scene.frames == anim.DIE
    assert g.menu.selected is None
    assert "cue die" in hooks.calls
    end = run(g, now, anim.duration_ms(anim.DIE) / 1000.0 + 0.1)
    assert g.scene is None
    for button in "ABC":  # only the reset hold does anything now
        g.update(end + 0.1, [button])
        assert g.menu.selected is None and g.scene is None and g.page is None
    assert hooks.calls.count("death") == 1
    assert not g.pet.attention


def test_holding_middle_ten_seconds_starts_a_new_pet():
    g, hooks = new_game()
    now = die(g, hooks)
    g.update(now + 0.05, ["B"], ["B"])
    end = run(g, now + 0.05, RESET_HOLD_SECONDS - 0.2, ["B"])
    assert g.pet.dead
    end = run(g, end, 0.5, ["B"])
    assert not g.pet.dead
    assert hooks.calls.count("reset") == 1
    assert g.hatching  # the new pet hatches
    run(g, end, RESET_HOLD_SECONDS + 1, ["B"])  # still the same hold: no second reset
    assert hooks.calls.count("reset") == 1


def test_reset_works_while_alive_too():
    g, hooks = new_game()
    g.pet.poop(0.0)
    g.update(1.0, ["B"], ["B"])  # also opens the menu: harmless
    run(g, 1.0, RESET_HOLD_SECONDS + 0.1, ["B"])
    assert hooks.calls.count("reset") == 1
    assert g.pet.poops == 0


def test_holding_right_ten_seconds_toggles_the_sound_once_per_hold():
    g, hooks = new_game()
    g.update(1.0, ["C"], ["C"])
    end = run(g, 1.0, MUTE_HOLD_SECONDS - 0.2, ["C"])
    assert "mute" not in hooks.calls
    end = run(g, end, 0.5, ["C"])
    assert hooks.calls.count("mute") == 1
    end = run(g, end, MUTE_HOLD_SECONDS + 1, ["C"])  # still the same hold
    assert hooks.calls.count("mute") == 1
    g.update(end + 0.05)  # released
    g.update(end + 0.1, ["C"], ["C"])
    run(g, end + 0.1, MUTE_HOLD_SECONDS + 0.1, ["C"])  # a new hold toggles it back
    assert hooks.calls.count("mute") == 2


def test_in_the_game_holding_right_quits_first_then_toggles_the_sound():
    g, hooks = new_game()
    now = 1.0
    for button in select("play"):
        now = round(now + 0.05, 2)
        g.update(now, [button])
    assert g.playing
    now = round(now + 0.05, 2)
    g.update(now, ["C"], ["C"])
    end = run(g, now, 1.2, ["C"])
    assert not g.playing
    assert "mute" not in hooks.calls
    run(g, end, MUTE_HOLD_SECONDS - 1.2 + 0.1, ["C"])
    assert hooks.calls.count("mute") == 1


def test_the_sound_toggles_after_death_too():
    g, hooks = new_game()
    now = die(g, hooks)
    g.update(now + 0.05, ["C"], ["C"])
    run(g, now + 0.05, MUTE_HOLD_SECONDS + 0.1, ["C"])
    assert hooks.calls.count("mute") == 1
    assert g.pet.dead
