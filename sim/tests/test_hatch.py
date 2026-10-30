"""The egg hatch, the critters it hatches into, and dying when left alone (pet.game, pet.anim, pet.sprites)."""

import random

import pytest

from pet import anim, sprites
from pet.game import Game, pick_character
from pet.state import IDLE_DEATH_MINUTES, STAT_MAX, STAT_NAMES

STANDING = ("idle0", "idle1", "happy", "sad", "sulk", "side", "side_eat", "no", "yawn")
HATCH_SECONDS = anim.duration_ms(anim.HATCH) / 1000.0


def art(character, name):
    i = sprites.pet_frame_index(name, character)
    return tuple(sprites.pet_sheet()[i * sprites.PET_SIZE : (i + 1) * sprites.PET_SIZE])


def ink(rows, x0=0, y0=0, flip=False):
    """Stage pixels the rows cover when drawn at (x0, y0)."""
    width = len(rows[0])
    return {
        (x0 + (width - 1 - x if flip else x), y0 + y)
        for y, row in enumerate(rows)
        for x, ch in enumerate(row)
        if ch != "."
    }


def fx_rows(name):
    if name == anim.POOP:
        return sprites.POOP_FRAMES[0]
    i = sprites.fx_index(name)
    return sprites.fx_sheet()[i * sprites.FX_SIZE : (i + 1) * sprites.FX_SIZE]


# ---- The art ----------------------------------------------------------------


@pytest.mark.parametrize("character", sprites.CHARACTERS)
def test_every_critter_stands_on_the_same_floor_and_keeps_its_happy_poses_clear(character):
    for name in STANDING:
        rows = art(character, name)
        assert max(y for y in range(16) if "#" in rows[y]) == 13, name  # feet on row 13
    for name in ("happy", "happy_up"):
        xs = [x for x, _ in ink(art(character, name))]
        assert min(xs) >= 1 and max(xs) <= 14, name  # the hearts and sparkle sit just outside
    assert "#" not in art(character, "happy")[0]  # so happy_up is happy one row higher
    assert art(character, "happy_up") == art(character, "happy")[1:] + (sprites._BLANK16,)


def scenes_with_the_pet():
    sets = [anim.HOP, anim.AFFECTION, anim.HATCH, anim.SLEEP]
    sets += list(anim.ACTIONS.values()) + list(anim.REFUSALS.values())
    sets += [tuple(anim.frame(0, "lie_sleep", x=anim.LIE_X, overlays=o) for o in anim.SLEEPING)]
    for n in range(len(anim.POOP_PILE) + 1):  # (Clean's wave washes over the pet on purpose)
        for pose in ("idle0", "idle1", "sad", "sulk"):
            sets.append((anim.frame(0, pose, x=anim.POOP_PET_X, overlays=anim.POOP_PILE[:n]),))
    return [f for frames in sets for f in frames]


@pytest.mark.parametrize("character", sprites.CHARACTERS)
def test_no_overlay_ever_covers_any_critter(character):
    for f in scenes_with_the_pet():
        if f[anim.PET] is None:
            continue
        pet = ink(art(character, f[anim.PET]), f[anim.X], f[anim.Y], f[anim.FLIP])
        for name, x, y, flip in f[anim.OVERLAYS]:
            assert not pet & ink(fx_rows(name), x, y, flip), (f[anim.PET], name, x, y)


# ---- The hatch --------------------------------------------------------------


def test_the_egg_rests_wobbles_cracks_and_pops_into_a_hop():
    pets = [f[anim.PET] for f in anim.HATCH]
    assert pets[0] == "egg"
    tilts = [f[anim.FLIP] for f in anim.HATCH if f[anim.PET] == "egg_tilt"]
    assert True in tilts and False in tilts  # both ways
    assert pets.index("egg_tilt") < pets.index("egg_crack1") < pets.index("egg_crack2") < pets.index("happy")
    assert pets[-1] == "happy"
    cues = [f[anim.CUE] for f in anim.HATCH if f[anim.CUE] is not None]
    assert cues == ["wobble"] * cues.count("wobble") + ["crack", "crack", "hatch"]
    popped = [f for f in anim.HATCH if f[anim.CUE] == "hatch"][0]
    assert popped[anim.PET] == "happy" and "shell" in [o[0] for o in popped[anim.OVERLAYS]]
    assert 5.0 <= HATCH_SECONDS <= 8.0


def test_a_new_game_starts_with_the_egg_and_ignores_presses_until_it_hatches():
    g = Game(now=0.0, build_ui=False)
    cues = []
    g.on_cue = cues.append
    assert g.hatching and g.character in sprites.CHARACTERS
    t = 0.0
    while t < HATCH_SECONDS - 0.1:
        t = round(t + 0.05, 2)
        g.update(t, ["A"])
    assert g.menu.cursor < 0  # no press got through
    assert g.hatching
    g.update(HATCH_SECONDS + 0.1)
    assert not g.hatching and g.scene is None
    assert cues[-3:] == ["crack", "crack", "hatch"]
    g.update(HATCH_SECONDS + 0.2, ["A"])
    assert g.menu.cursor >= 0


def test_every_critter_hatches_sometimes():
    random.seed(1)
    assert {Game(now=0.0, build_ui=False).character for _ in range(200)} == set(sprites.CHARACTERS)


def test_a_new_pet_after_the_reset_is_always_a_different_critter():
    random.seed(2)
    g = Game(now=0.0, build_ui=False, hatch=False)
    seen = set()
    for i in range(60):
        before = g.character
        g.reset(float(i))
        assert g.character != before
        assert g.hatching
        seen.add(g.character)
    assert seen == set(sprites.CHARACTERS)
    for c in sprites.CHARACTERS:
        assert pick_character(c) != c


def test_holding_left_does_not_make_the_egg_poop():
    g = Game(now=0.0, build_ui=False)
    g.update(0.05, ["A"], ["A"])
    t = 0.05
    while t < HATCH_SECONDS - 0.1:
        t = round(t + 0.05, 2)
        g.update(t, (), ["A"])
    assert g.pet.poops == 0


# ---- Left alone -------------------------------------------------------------

IDLE_SECONDS = IDLE_DEATH_MINUTES * 60


def content_game():
    """No egg, and every stat kept full so only the idle clock can kill it."""
    g = Game(now=0.0, build_ui=False, hatch=False)
    deaths = []
    g.on_death = lambda: deaths.append(True)
    return g, deaths


def step(g, t, presses=(), asleep=False):
    for name in STAT_NAMES:
        g.pet.stats[name] = STAT_MAX
    if asleep:
        g.pet.asleep = True
        g.pet.stats["energy"] = 0  # so it doesn't wake by itself
    g.update(t, presses)


def test_left_alone_fifteen_minutes_it_dies_however_it_is_doing():
    g, deaths = content_game()
    for t in range(1, int(IDLE_SECONDS)):
        step(g, float(t))
    assert not g.pet.dead
    step(g, IDLE_SECONDS + 0.5)
    assert g.pet.dead and deaths == [True]
    assert [f[anim.PET] for f in g.scene.frames] == [f[anim.PET] for f in anim.DIE]


def test_any_press_starts_the_idle_clock_over():
    g, deaths = content_game()
    for t in range(1, 600):
        step(g, float(t))
    step(g, 600.0, ["C"])  # back: does nothing, still counts
    for t in range(601, 600 + int(IDLE_SECONDS)):
        step(g, float(t))
    assert not g.pet.dead
    step(g, 600 + IDLE_SECONDS + 0.5)
    assert g.pet.dead


def test_the_idle_clock_waits_while_it_sleeps():
    g, deaths = content_game()
    for t in range(1, 1800):  # half an hour asleep, untouched
        step(g, float(t), asleep=True)
    assert not g.pet.dead
    g.pet.asleep = False  # it woke up by itself
    for t in range(1800, 1800 + int(IDLE_SECONDS) - 1):
        step(g, float(t))
    assert not g.pet.dead
    step(g, 1800 + IDLE_SECONDS + 0.5)
    assert g.pet.dead


# ---- On screen --------------------------------------------------------------


def test_the_screen_switches_to_the_new_critter_after_a_reset():
    random.seed(3)
    g = Game(now=0.0, hatch=False)
    g.update(0.1)
    first = g.character
    ui = g.ui
    assert ui._pet_grid[0] == sprites.pet_frame_index(ui._pet_name, first)
    g.reset(1.0)
    second = g.character
    t = 1.0
    while g.hatching:
        t = round(t + 0.05, 2)
        g.update(t)
        if ui._pet_name is not None:
            assert ui._pet_grid[0] == sprites.pet_frame_index(ui._pet_name, second)
    assert ui._pet_name in ("idle0", "idle1")
    assert ui._pet_grid[0] == sprites.pet_frame_index(ui._pet_name, second)
    assert second != first
