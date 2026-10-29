"""Stat, decay, attention, sulk and sleep logic in firmware/pet/state.py."""

import pytest

from pet import state
from pet.state import (
    ACTIONS,
    ACTION_STAT,
    DECAY_SCALE,
    EMPTY_MINUTES,
    FULL_LEVEL,
    LOW_THRESHOLD,
    NAP_MIN_SECONDS,
    REACTION_SECONDS,
    SLEEP_DECAY_FACTOR,
    SLEEP_FULL_SECONDS,
    START_LEVELS,
    STAT_MAX,
    STAT_NAMES,
    Pet,
    decay_per_second,
)


def full_pet(now=0.0):
    levels = {}
    for name in STAT_NAMES:
        levels[name] = STAT_MAX
    return Pet(now, levels)


def test_fresh_pet_starts_at_start_levels_awake_and_content():
    pet = Pet(0.0)
    for name in STAT_NAMES:
        assert pet.level(name) == START_LEVELS[name]
        assert START_LEVELS[name] > LOW_THRESHOLD
    assert not pet.asleep
    assert not pet.attention
    assert pet.pose == state.POSE_IDLE
    assert pet.wants is None


def test_every_action_maps_to_a_distinct_stat():
    assert set(ACTIONS) == set(ACTION_STAT)
    assert sorted(ACTION_STAT.values()) == sorted(STAT_NAMES)


def test_stats_decay_linearly_at_their_rate():
    pet = full_pet()
    pet.tick(60.0)
    for name in STAT_NAMES:
        expected = STAT_MAX - STAT_MAX / (EMPTY_MINUTES[name] * DECAY_SCALE)  # one minute's worth
        assert pet.stats[name] == pytest.approx(expected)


def test_decay_is_the_same_in_one_step_or_many():
    one = full_pet()
    one.tick(300.0)
    many = full_pet()
    for i in range(1, 301):
        many.tick(float(i))
    for name in STAT_NAMES:
        assert one.stats[name] == pytest.approx(many.stats[name])


def test_stats_floor_at_zero_and_pet_sulks_instead_of_dying():
    pet = full_pet()
    pet.tick(3 * 3600.0)  # three hours alone
    for name in STAT_NAMES:
        assert pet.stats[name] == 0
    assert pet.sulking
    assert pet.attention
    assert pet.pose == state.POSE_SULK
    pet.tick(3 * 3600.0 + 1)
    assert pet.pose == state.POSE_SULK  # still here, just sulking


def test_sulk_recovers_once_cared_for():
    pet = full_pet()
    pet.tick(3 * 3600.0)
    now = 3 * 3600.0
    for action in ("eat", "drink", "play", "treat", "affection"):
        pet.do(action, now)
    assert pet.sulking  # energy is still 0
    pet.do("sleep", now)
    pet.tick(now + SLEEP_FULL_SECONDS + 1)
    assert not pet.sulking
    assert not pet.asleep
    assert pet.level("energy") == STAT_MAX


def test_backwards_clock_is_ignored():
    pet = full_pet(100.0)
    pet.tick(50.0)
    for name in STAT_NAMES:
        assert pet.stats[name] == STAT_MAX
    pet.tick(110.0)  # 60 s after the backwards step, not 10 s
    assert pet.stats["hunger"] == pytest.approx(STAT_MAX - 60 * decay_per_second("hunger"))


def test_attention_turns_on_when_a_need_drops_low_and_tick_reports_the_edge():
    pet = full_pet()
    seconds_to_low = (STAT_MAX - LOW_THRESHOLD) / decay_per_second("thirst")  # thirst drains fastest
    assert pet.tick(seconds_to_low - 1) is False
    assert not pet.attention
    assert pet.tick(seconds_to_low + 1) is True
    assert pet.attention
    assert pet.low_needs() == ["thirst"]
    assert pet.wants == "drink"
    assert pet.pose == state.POSE_SAD
    assert pet.tick(seconds_to_low + 2) is False  # only the rising edge is reported


def test_caring_clears_attention_immediately():
    pet = Pet(0.0, {"hunger": LOW_THRESHOLD})
    assert pet.attention
    pet.do("eat", 0.0)
    assert not pet.attention
    assert pet.level("hunger") == STAT_MAX


@pytest.mark.parametrize("action", ["eat", "drink", "play", "treat", "affection"])
def test_each_action_restores_its_stat_and_shows_a_reaction(action):
    levels = {}
    for name in STAT_NAMES:
        levels[name] = 10
    pet = Pet(0.0, levels)
    assert pet.do(action, 5.0)
    stat = ACTION_STAT[action]
    assert pet.level(stat) == STAT_MAX
    for name in STAT_NAMES:
        if name != stat:
            assert pet.level(name) == 10
    assert pet.reaction == action
    assert pet.pose == state.POSE_HAPPY
    pet.tick(5.0 + REACTION_SECONDS - 0.1)
    assert pet.reaction == action
    pet.tick(5.0 + REACTION_SECONDS)
    assert pet.reaction is None


def test_unknown_action_is_rejected():
    pet = full_pet()
    assert pet.do("dance", 0.0) is False


def test_sleep_refills_energy_slows_other_decay_and_wakes_by_itself():
    levels = {}
    for name in STAT_NAMES:
        levels[name] = 50
    pet = Pet(0.0, levels)
    pet.do("sleep", 0.0)
    assert pet.asleep
    assert pet.pose == state.POSE_SLEEP
    assert pet.wants is None or pet.wants == "sleep"  # nothing else is low

    pet.tick(4.0)  # mid-nap: 50 -> 70 energy, other stats drain at half speed
    assert pet.asleep
    assert pet.stats["energy"] == pytest.approx(50 + STAT_MAX * 4.0 / SLEEP_FULL_SECONDS)
    assert pet.stats["hunger"] == pytest.approx(50 - decay_per_second("hunger") * SLEEP_DECAY_FACTOR * 4.0)

    pet.tick(SLEEP_FULL_SECONDS)  # energy full, nap longer than the minimum
    assert pet.level("energy") == STAT_MAX
    assert not pet.asleep


def test_short_nap_lasts_at_least_the_minimum_even_when_rested():
    pet = full_pet()
    pet.do("sleep", 0.0)
    pet.tick(NAP_MIN_SECONDS - 1)
    assert pet.asleep
    pet.tick(NAP_MIN_SECONDS)
    assert not pet.asleep


def test_wake_and_sleep_toggle():
    pet = full_pet()
    pet.do("sleep", 0.0)
    assert pet.asleep
    pet.do("sleep", 1.0)
    assert not pet.asleep
    pet.do("sleep", 2.0)
    pet.do("eat", 3.0)  # feeding wakes it up
    assert not pet.asleep


def run_perfect_carer(hours):
    """Simulate someone who answers every ask at once. Returns ask times (s)."""
    pet = Pet(0.0)
    asks = []
    for second in range(1, int(hours * 3600) + 1):
        now = float(second)
        if pet.tick(now):
            asks.append(now)
        if pet.attention:
            pet.do(pet.wants, now)
    return asks


def test_first_ask_comes_about_eight_minutes_after_power_on():
    asks = run_perfect_carer(0.25)
    assert asks, "no ask in the first 15 minutes"
    assert 7 * 60 <= asks[0] <= 9 * 60, "first ask at %.0f s" % asks[0]


def test_pet_asks_for_something_every_eight_to_ten_minutes():
    asks = run_perfect_carer(8)
    gaps = [b - a for a, b in zip(asks, asks[1:])]
    assert len(gaps) > 40
    mean = sum(gaps) / len(gaps)
    assert 8 * 60 <= mean <= 10 * 60, "mean gap %.0f s" % mean
    assert max(gaps) <= 15 * 60 * DECAY_SCALE, "longest quiet stretch %.0f s" % max(gaps)


def test_decay_scale_stretches_every_drain_time():
    for name in STAT_NAMES:
        minutes = STAT_MAX / decay_per_second(name) / 60
        assert minutes == pytest.approx(EMPTY_MINUTES[name] * DECAY_SCALE)


def test_eat_and_drink_are_refused_when_full_and_treats_never_are():
    pet = full_pet()
    for name in STAT_NAMES:
        pet.stats[name] = FULL_LEVEL
    assert not pet.accepts("eat")
    assert not pet.accepts("drink")
    for action in ("treat", "affection", "sleep", "play"):
        assert pet.accepts(action)
    pet.stats["hunger"] = FULL_LEVEL - 0.5
    assert pet.accepts("eat")
    assert not pet.accepts("drink")


def test_add_clamps_and_updates_attention():
    pet = full_pet()
    pet.stats["fun"] = LOW_THRESHOLD - 5
    pet.tick(0.0)
    assert pet.attention
    pet.add("fun", 25)
    assert pet.level("fun") == LOW_THRESHOLD + 20
    assert not pet.attention
    pet.add("fun", 500)
    assert pet.level("fun") == STAT_MAX
    pet.add("fun", -500)
    assert pet.level("fun") == 0
