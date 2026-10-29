"""Smoke test: the displayio UI builds and renders every state without a display."""

import pytest

displayio = pytest.importorskip("displayio")

from pet import anim, minigame, sprites
from pet.game import MENU_ITEMS, Game
from pet.state import STAT_MAX, STAT_NAMES
from pet.ui import PetUI, bitmap_from_rows


def test_art_rows_have_the_declared_width():
    assert len(sprites.pet_sheet()) == sprites.PET_SIZE * len(sprites.PET_FRAMES)
    assert len(sprites.icon_sheet()) == sprites.ICON_SIZE * len(sprites.ICON_NAMES)
    assert len(sprites.fx_sheet()) == sprites.FX_SIZE * len(sprites.FX_NAMES)
    bitmap_from_rows(sprites.pet_sheet(), sprites.PET_SIZE)
    bitmap_from_rows(sprites.icon_sheet(), sprites.ICON_SIZE)
    bitmap_from_rows(sprites.fx_sheet(), sprites.FX_SIZE)
    with pytest.raises(ValueError):
        bitmap_from_rows(("##", "#"), 2)


def test_every_menu_item_has_an_icon():
    for item in MENU_ITEMS:
        assert item in sprites.ICON_NAMES
    assert "attention" in sprites.ICON_NAMES


class Fixed:
    """A scene that shows one frame forever."""

    def __init__(self, frame):
        self.frame = frame

    def update(self, now, game):
        return True

    def press(self, button, now, game):
        return False


def test_ui_renders_through_every_state():
    g = Game(now=0.0)
    assert g.root_group is not None
    ui = g.ui
    assert isinstance(ui, PetUI)

    g.update(0.7)  # idle frame 1
    assert ui._pet_name == "idle1"
    g.update(1.0, ["A", "A"])  # cursor on drink
    assert ui._cursor == 1
    g.update(1.5, ["B"])  # drink: the cup appears beside the pet
    assert ui._pet_name == "side"
    assert ui._pet_x == anim.BESIDE_X
    assert ui._slot_shown[0][0] == "cup0"
    assert ui._bubble_group.hidden
    g.update(1.5 + anim.duration_ms(anim.DRINK) / 1000.0 + 0.1)  # over: back home
    assert g.scene is None
    assert ui._pet_x == anim.HOME_X
    assert ui._slot_shown == [None] * len(ui._slots)

    g.pet.stats["fun"] = 0  # sulk + attention
    g.update(6.0)
    assert g.pet.sulking
    assert ui._pet_name == "sulk"
    assert not ui._bubble_group.hidden  # shows what it wants
    g.update(6.0)
    assert not ui._attention_group.hidden
    g.update(6.5)
    assert ui._attention_group.hidden  # blink off

    g.pet.stats["fun"] = STAT_MAX
    presses = ["C"] + ["A"] * (MENU_ITEMS.index("sleep") + 1) + ["B"]
    g.update(7.0, presses)  # yawns first, lights still on
    assert g.pet.asleep
    assert not ui._night
    g.update(7.0 + anim.duration_ms(anim.SLEEP) / 1000.0 + 0.1)  # lights off
    assert ui._night
    assert ui._pet_name == "lie_sleep"
    g.update(11.0)
    g.update(12.0, ["A"])  # wake
    assert not ui._night
    assert ui._pet_name in ("idle0", "idle1")

    presses = ["C"] + ["A"] * (MENU_ITEMS.index("stats") + 1) + ["B"]
    g.update(13.0, presses)
    assert not ui.page_group.hidden
    assert ui.stage.hidden
    for i in range(len(STAT_NAMES)):
        assert ui._bars[i][1] > 0
    g.update(14.0, ["C"])
    assert ui.page_group.hidden
    assert not ui.stage.hidden


def all_frames():
    frames = []
    for group in list(anim.ACTIONS.values()) + list(anim.REFUSALS.values()):
        frames.extend(group)
    frames.extend(minigame.READY + minigame.MATCH + minigame.MISS + minigame.WIN + minigame.LOSE)
    frames.append(minigame.PROMPT)
    for guess in (minigame.LEFT, minigame.RIGHT):
        for turn in (minigame.LEFT, minigame.RIGHT):
            frames.extend(minigame.reveal_frames(guess, turn))
    for score in range(minigame.ROUNDS + 1):
        frames.extend(minigame.score_frames(score))
    return frames


def test_every_animation_and_game_frame_renders():
    g = Game(now=0.0)
    ui = g.ui
    now = 1.0
    for f in all_frames():
        g.scene = Fixed(f)
        g.update(now)
        assert ui._pet_name == f[anim.PET]
        if f[anim.PET] is not None:
            assert ui._pet_grid[0] == sprites.pet_frame_index(f[anim.PET])
            assert (ui._pet_grid.x, ui._pet_grid.y) == (f[anim.X], f[anim.Y])
            assert ui._pet_grid.flip_x == f[anim.FLIP]
        assert ui._pet_grid.hidden == (f[anim.PET] is None)
        overlays = f[anim.OVERLAYS]
        for i in range(len(ui._slots)):
            slot = ui._slots[i]
            if i < len(overlays):
                name, x, y, flip = overlays[i]
                assert not slot.hidden
                assert slot[0] == sprites.fx_index(name)
                assert (slot.x, slot.y, slot.flip_x) == (x, y, flip)
            else:
                assert slot.hidden
        now += 0.1
