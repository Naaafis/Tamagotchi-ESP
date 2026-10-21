"""Smoke test: the displayio UI builds and renders every state without a display."""

import pytest

displayio = pytest.importorskip("displayio")

from pet import sprites
from pet.game import MENU_ITEMS, Game
from pet.state import STAT_MAX, STAT_NAMES
from pet.ui import PetUI, bitmap_from_rows


def test_art_rows_have_the_declared_width():
    assert len(sprites.pet_sheet()) == sprites.PET_SIZE * len(sprites.PET_FRAMES)
    assert len(sprites.icon_sheet()) == sprites.ICON_SIZE * len(sprites.ICON_NAMES)
    bitmap_from_rows(sprites.pet_sheet(), sprites.PET_SIZE)
    bitmap_from_rows(sprites.icon_sheet(), sprites.ICON_SIZE)
    with pytest.raises(ValueError):
        bitmap_from_rows(("##", "#"), 2)


def test_every_menu_item_has_an_icon():
    for item in MENU_ITEMS:
        assert item in sprites.ICON_NAMES
    assert "attention" in sprites.ICON_NAMES


def test_ui_renders_through_every_state():
    g = Game(now=0.0)
    assert g.root_group is not None
    ui = g.ui
    assert isinstance(ui, PetUI)

    g.update(0.7)  # idle frame 1
    g.update(1.0, ["A", "A"])  # cursor on drink
    assert ui._cursor == 1
    g.update(1.5, ["B"])  # drink: happy pose + bubble
    assert not ui._bubble_group.hidden
    g.update(4.0)  # reaction over
    assert ui._bubble_group.hidden

    g.pet.stats["fun"] = 0  # sulk + attention
    g.update(5.0)
    assert g.pet.sulking
    assert not ui._bubble_group.hidden  # shows what it wants
    g.update(5.0)
    assert not ui._attention_group.hidden
    g.update(5.5)
    assert ui._attention_group.hidden  # blink off

    g.pet.stats["fun"] = STAT_MAX
    presses = ["C"] + ["A"] * (MENU_ITEMS.index("sleep") + 1) + ["B"]
    g.update(6.0, presses)  # lights off
    assert g.pet.asleep
    assert ui._night
    g.update(7.0)  # sleep frame 1
    g.update(8.0, ["A"])  # wake
    assert not ui._night

    presses = ["C"] + ["A"] * (MENU_ITEMS.index("stats") + 1) + ["B"]
    g.update(9.0, presses)
    assert not ui.page_group.hidden
    assert ui.pet_group.hidden
    for i in range(len(STAT_NAMES)):
        assert ui._bars[i][1] > 0
    g.update(10.0, ["C"])
    assert ui.page_group.hidden
    assert not ui.pet_group.hidden
