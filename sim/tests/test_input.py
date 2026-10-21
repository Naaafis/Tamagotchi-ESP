"""Menu cursor (firmware/pet/input.py) and the Game's button handling."""

from pet import input
from pet.game import MENU_ITEMS, PAGE_STATS, Game
from pet.state import LOW_THRESHOLD, STAT_MAX, STAT_NAMES


def test_a_cycles_through_every_icon_then_back_to_none():
    menu = input.Menu(("eat", "drink", "sleep"))
    assert menu.selected is None
    seen = []
    for _ in range(3):
        assert menu.press(input.A) == input.MOVE
        seen.append(menu.selected)
    assert seen == ["eat", "drink", "sleep"]
    assert menu.press(input.A) == input.MOVE
    assert menu.selected is None
    assert menu.press(input.A) == input.MOVE
    assert menu.selected == "eat"


def test_b_selects_only_when_something_is_highlighted():
    menu = input.Menu(("eat", "drink"))
    assert menu.press(input.B) is None
    menu.press(input.A)
    assert menu.press(input.B) == input.SELECT
    assert menu.selected == "eat"  # cursor stays put after selecting


def test_c_cancels_and_unknown_buttons_are_ignored():
    menu = input.Menu(("eat", "drink"))
    menu.press(input.A)
    assert menu.press(input.C) == input.CANCEL
    assert menu.selected is None
    assert menu.press("X") is None


def game():
    return Game(now=0.0, build_ui=False)


def test_menu_lists_every_action_plus_stats():
    g = game()
    assert g.menu.items == MENU_ITEMS
    assert "stats" in MENU_ITEMS
    for item in MENU_ITEMS:
        if item != "stats":
            assert item in ("eat", "drink", "sleep", "play", "treat", "affection")


def test_selecting_an_icon_performs_the_action():
    g = game()
    low = {}
    for name in STAT_NAMES:
        low[name] = 10
    g.pet = type(g.pet)(0.0, low)
    g.update(1.0, ["A", "B"])  # first icon is eat
    assert g.pet.level("hunger") == STAT_MAX
    assert g.pet.reaction == "eat"
    assert g.pet.level("thirst") == 10


def test_stats_page_opens_on_select_and_closes_on_b_or_c():
    g = game()
    presses = ["A"] * (MENU_ITEMS.index("stats") + 1)
    g.update(1.0, presses)
    assert g.menu.selected == "stats"
    g.update(2.0, ["B"])
    assert g.page == PAGE_STATS
    g.update(3.0, ["A"])  # A does nothing while the page is open
    assert g.page == PAGE_STATS
    g.update(4.0, ["C"])
    assert g.page is None
    g.update(5.0, ["B"])
    assert g.page == PAGE_STATS
    g.update(6.0, ["B"])
    assert g.page is None


def test_any_button_wakes_a_sleeping_pet_without_doing_anything_else():
    g = game()
    presses = ["A"] * (MENU_ITEMS.index("sleep") + 1) + ["B"]
    g.update(1.0, presses)
    assert g.pet.asleep
    cursor = g.menu.cursor
    g.update(2.0, ["A"])
    assert not g.pet.asleep
    assert g.menu.cursor == cursor  # the press was consumed by waking up


def test_hooks_fire_on_button_and_on_attention_edge():
    g = game()
    buttons = []
    attention = []
    g.on_button = buttons.append
    g.on_attention = lambda: attention.append(True)
    g.update(1.0, ["A", "C", "X"])
    assert buttons == ["A", "C"]  # unknown buttons are dropped before the hook
    assert attention == []
    g.pet.stats["fun"] = LOW_THRESHOLD + 0.001
    g.update(2.0)
    assert attention == [True]
    g.update(3.0)
    assert attention == [True]  # once per edge, not once per frame
