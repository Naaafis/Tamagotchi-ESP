"""Action animations (firmware/pet/anim.py) and how the Game plays them."""

import pytest

from pet import anim, minigame, sprites
from pet.game import MENU_ITEMS, Game
from pet.sound import CUES
from pet.state import FULL_LEVEL, STAT_MAX

ALL_SETS = dict(anim.ACTIONS)
for _name, _frames in anim.REFUSALS.items():
    ALL_SETS["refuse " + _name] = _frames
ALL_SETS["game ready"] = minigame.READY
ALL_SETS["game match"] = minigame.MATCH
ALL_SETS["game miss"] = minigame.MISS
ALL_SETS["game win"] = minigame.WIN
ALL_SETS["game lose"] = minigame.LOSE
ALL_SETS["game prompt"] = (minigame.PROMPT,)
for _score in range(minigame.ROUNDS + 1):
    ALL_SETS["game score %d" % _score] = minigame.score_frames(_score)
ALL_SETS["sleeping"] = tuple(anim.frame(0, "lie_sleep", x=anim.LIE_X, overlays=o) for o in anim.SLEEPING)
for _n in range(len(anim.POOP_PILE) + 1):
    ALL_SETS["clean %d" % _n] = anim.clean_frames(_n)
    ALL_SETS["main with %d poops" % _n] = (anim.frame(0, "sad", x=anim.POOP_PET_X, overlays=anim.POOP_PILE[:_n]),)
ALL_SETS["die"] = anim.DIE
ALL_SETS["gone"] = (anim.frame(0, None, overlays=anim.GONE),)
ALL_SETS["hatch"] = anim.HATCH


def ink_box(rows):
    """(left, top, right, bottom) of the non-'.' cells, inclusive."""
    xs = [x for row in rows for x in range(len(row)) if row[x] != "."]
    ys = [y for y in range(len(rows)) if row_has_ink(rows[y])]
    return min(xs), min(ys), max(xs), max(ys)


def row_has_ink(row):
    return row.strip(".") != ""


def fx_rows(name):
    if name == anim.POOP:
        return sprites.POOP_FRAMES[0]
    sheet = sprites.fx_sheet()
    i = sprites.fx_index(name)
    return sheet[i * sprites.FX_SIZE : (i + 1) * sprites.FX_SIZE]


def cues(frames):
    return [f[anim.CUE] for f in frames if f[anim.CUE] is not None]


def overlay_names(f):
    return [o[0] for o in f[anim.OVERLAYS]]


@pytest.mark.parametrize("name", sorted(ALL_SETS))
def test_frames_use_known_art_and_stay_on_the_stage(name):
    for f in ALL_SETS[name]:
        assert len(f) == 7
        assert isinstance(f[anim.MS], int) and f[anim.MS] >= 0
        pet = f[anim.PET]
        if pet is not None:
            assert pet in sprites.PET_FRAMES
            assert 0 <= f[anim.X] <= anim.STAGE_W - sprites.PET_SIZE
            assert 0 <= f[anim.Y] <= anim.STAGE_H - sprites.PET_SIZE
        names = overlay_names(f)
        assert len([n for n in names if n != anim.POOP]) <= anim.MAX_OVERLAYS
        assert names.count(anim.POOP) <= anim.MAX_POOP_OVERLAYS
        for fx_name, x, y, flip in f[anim.OVERLAYS]:
            assert fx_name in sprites.FX_NAMES or fx_name == anim.POOP
            left, top, right, bottom = ink_box(fx_rows(fx_name))
            if flip:
                left, right = sprites.FX_SIZE - 1 - right, sprites.FX_SIZE - 1 - left
            assert 0 <= x + left and x + right < anim.STAGE_W, (fx_name, x)
            assert 0 <= y + top and y + bottom < anim.STAGE_H, (fx_name, y)
        assert f[anim.CUE] is None or f[anim.CUE] in CUES


@pytest.mark.parametrize("action", sorted(anim.ACTIONS) + ["refuse eat", "refuse drink", "clean 1", "clean 4"])
def test_each_animation_lasts_two_to_four_seconds(action):
    frames = ALL_SETS[action]
    assert 2000 <= anim.duration_ms(frames) <= 4000


@pytest.mark.parametrize(
    "action, props, cue",
    [
        ("eat", ["food0", "food0", "food1", "food1", "food2", "food2", None], "bite"),
        ("drink", ["cup0", "cup0", "cup1", "cup1", "cup2", "cup2", "cup3"], "sip"),
    ],
)
def test_three_bites_shrink_the_prop_then_the_happy_hop(action, props, cue):
    frames = anim.ACTIONS[action]
    eating = frames[: len(props)]
    shown = [overlay_names(f)[0] if f[anim.OVERLAYS] else None for f in eating]
    assert shown == props
    for f in eating:
        assert f[anim.PET] in ("side", "side_eat")
        assert f[anim.X] == anim.BESIDE_X  # facing the prop
    mouths = [f[anim.PET] for f in eating[1:]]
    assert mouths == ["side_eat", "side"] * 3  # open, chomp
    assert cues(frames) == [cue] * 3 + ["happy"]
    assert frames[len(props) :] == anim.HOP


def test_the_hop_is_happy_with_a_sparkle_and_goes_up_and_down():
    pets = [f[anim.PET] for f in anim.HOP]
    assert pets == ["happy_up", "happy", "happy_up", "happy"]
    assert all(f[anim.X] == anim.HOME_X for f in anim.HOP)
    assert any("sparkle0" in overlay_names(f) for f in anim.HOP)


@pytest.mark.parametrize("action, prop", [("eat", "food0"), ("drink", "cup0")])
def test_refusal_shakes_its_head_and_the_food_stays(action, prop):
    frames = anim.REFUSALS[action]
    for f in frames:
        assert overlay_names(f) == [prop]
    shakes = [f[anim.FLIP] for f in frames if f[anim.PET] == "no"]
    assert shakes == [False, True, False, True]
    assert cues(frames) == ["refuse"]


def test_affection_bounces_with_hearts_then_hops():
    frames = anim.AFFECTION
    hearts = [f for f in frames if "heart" in overlay_names(f)]
    assert len(hearts) >= 4
    bouncing = [f[anim.PET] for f in frames[: len(frames) - len(anim.HOP)]]
    assert "happy" in bouncing and "happy_up" in bouncing
    assert frames[-len(anim.HOP) :] == anim.HOP
    assert cues(frames) == ["happy"]


@pytest.mark.parametrize("poops", [1, 2, 3, 4])
def test_the_flush_sweeps_left_to_right_and_takes_each_poop_as_it_passes(poops):
    frames = anim.clean_frames(poops)
    sweep = frames[: len(anim.WAVE_STEPS)]
    waves = [[o[1] for o in f[anim.OVERLAYS] if o[0] == "wave"] for f in sweep]
    assert all(len(w) == 2 and w[0] == w[1] for w in waves)  # one column, two tiles tall
    xs = [w[0] for w in waves]
    assert xs == sorted(xs) and xs[0] == 0 and xs[-1] >= 20  # left to right, all the way
    counts = [overlay_names(f).count(anim.POOP) for f in sweep]
    assert counts[0] == poops
    assert counts == sorted(counts, reverse=True)  # once gone, gone
    assert counts[-1] == 0
    for f in sweep:  # a poop still showing is always ahead of the wave
        wave_x = [o[1] for o in f[anim.OVERLAYS] if o[0] == "wave"][0]
        for o in f[anim.OVERLAYS]:
            if o[0] == anim.POOP:
                assert o[1] > wave_x
    assert sweep[0][anim.X] == anim.POOP_PET_X  # where the pet stood with poops about
    assert frames[-len(anim.HOP) :] == anim.hop("flush")
    assert cues(frames) == ["flush"]


def test_cleaning_nothing_is_just_a_quick_sweep():
    frames = anim.clean_frames(0)
    assert anim.duration_ms(frames) < 1200
    assert cues(frames) == []
    assert all(f[anim.PET] == "idle0" and f[anim.X] == anim.HOME_X for f in frames)
    assert any("wave" in overlay_names(f) for f in frames)


def test_poops_pile_up_two_by_two_beside_the_pet():
    pile = anim.POOP_PILE
    assert len(pile) == 4
    assert pile[0][2] == pile[1][2] > pile[2][2] == pile[3][2]  # bottom row first
    sheet = sprites.pet_sheet()
    poses = [sprites.pet_frame_index(p, c) for c in sprites.CHARACTERS for p in ("idle0", "idle1", "sad", "sulk")]
    pet_right = anim.POOP_PET_X + max(ink_box(sheet[i * 16 : i * 16 + 16])[2] for i in poses)
    for _, x, y, _ in pile:
        for rows in sprites.POOP_FRAMES:
            assert x + ink_box(rows)[0] > pet_right + 1  # a gap between pet and poop
            assert ink_box(rows)[2] < anim.POOP_PILE[1][1] - anim.POOP_PILE[0][1] - 1  # a gap between neighbours


def test_dying_the_ufo_beams_it_up_and_flies_off():
    pets = [f[anim.PET] for f in anim.DIE]
    assert pets.index("lie") < pets.index("rise1") < pets.index("rise2")
    assert pets[-1] is None  # gone
    saucer_x = [o[1] for f in anim.DIE for o in f[anim.OVERLAYS] if o[0] == "ufo_l"]
    assert saucer_x[0] == 0 and saucer_x[-1] > anim.HOME_X  # glides in, flies off right
    beamed = [f[anim.PET] for f in anim.DIE if "beam" in overlay_names(f)]
    assert beamed == ["lie"]  # the beam shines on it; it floats up after
    assert cues(anim.DIE) == ["die"]
    assert 4000 <= anim.duration_ms(anim.DIE) <= 6000
    assert overlay_names(anim.frame(0, None, overlays=anim.GONE)) == ["ufo_tiny"]


def test_sleep_yawns_lies_down_and_closes_its_eyes():
    pets = [f[anim.PET] for f in anim.SLEEP]
    assert pets.index("yawn") < pets.index("lie") < pets.index("lie_sleep")
    assert pets[-1] == "lie_sleep"
    assert cues(anim.SLEEP) == []  # no hop: it falls asleep
    assert any("z_small" in overlay_names(f) for f in anim.SLEEP)
    zs = [overlay_names(o) for o in [anim.frame(0, None, overlays=o) for o in anim.SLEEPING]]
    assert ["z_small"] in zs and any("z_big" in z for z in zs) and [] in zs


# ---- In the game ------------------------------------------------------------


class Hooks:
    def __init__(self, g):
        self.buttons = []
        self.actions = []
        self.cues = []
        g.on_button = self.buttons.append
        g.on_action = self.actions.append
        g.on_cue = self.cues.append


def select(item):
    return ["C"] + ["A"] * (MENU_ITEMS.index(item) + 1) + ["B"]


def run(g, start, seconds, presses=None):
    """Step every 50 ms; presses maps a time to the presses that frame."""
    presses = presses or {}
    now = start
    while now < start + seconds:
        g.update(now, presses.get(round(now, 2), ()))
        now = round(now + 0.05, 2)
    return now


def game(**levels):
    g = Game(now=0.0, build_ui=False, hatch=False)
    for name, value in levels.items():
        g.pet.stats[name] = value
    return g


def test_presses_during_an_animation_are_ignored_not_queued():
    g = game(hunger=40)
    hooks = Hooks(g)
    g.update(1.0, select("eat"))
    assert hooks.buttons == ["C", "A", "B"]
    cursor = g.menu.cursor
    end = run(g, 1.05, 3.0, {1.5: ["A"], 2.0: ["C"], 2.5: ["B"]})
    assert g.scene is not None
    assert hooks.buttons == ["C", "A", "B"]  # no tick, no effect
    assert g.menu.cursor == cursor
    run(g, end, 1.5)
    assert g.scene is None
    assert g.menu.cursor == cursor  # nothing replays afterwards
    assert hooks.actions == ["eat"]
    assert hooks.cues == ["bite", "bite", "bite", "happy"]


def test_eating_when_full_is_refused_and_changes_nothing():
    g = game(hunger=FULL_LEVEL + 5)
    hooks = Hooks(g)
    g.update(1.0, select("eat"))
    hunger = g.pet.stats["hunger"]
    run(g, 1.05, 3.0)
    assert g.scene is None
    assert hooks.actions == []
    assert hooks.cues == ["refuse"]
    assert g.pet.stats["hunger"] <= hunger


def test_drinking_when_full_is_refused():
    g = game(thirst=STAT_MAX)
    hooks = Hooks(g)
    g.update(1.0, select("drink"))
    run(g, 1.05, 3.0)
    assert hooks.cues == ["refuse"]
    assert hooks.actions == []


def test_affection_animation_runs_and_restores_affection():
    g = game(affection=10)
    hooks = Hooks(g)
    g.update(1.0, select("affection"))
    assert g.pet.level("affection") == STAT_MAX
    run(g, 1.05, 3.5)
    assert g.scene is None
    assert hooks.cues == ["happy"]


def test_lights_go_out_only_after_the_falling_asleep_animation():
    g = game(energy=10)
    g.update(1.0, select("sleep"))
    assert g.pet.asleep
    assert not g.lights_off  # yawning, lights still on
    run(g, 1.05, anim.duration_ms(anim.SLEEP) / 1000.0 + 0.1)
    assert g.scene is None
    assert g.lights_off
    assert g.pet.asleep


def test_a_long_stall_still_fires_every_cue_and_finishes():
    g = game(hunger=40)
    hooks = Hooks(g)
    g.update(1.0, select("eat"))
    g.update(30.0)  # the loop froze for half a minute
    assert g.scene is None
    assert hooks.cues == ["bite", "bite", "bite", "happy"]
