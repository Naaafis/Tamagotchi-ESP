"""Stat, decay, attention, sulk, poop, death and sleep logic in firmware/pet/state.py."""

import random

import pytest

from pet import state
from pet.state import (
    ACTIONS,
    ACTION_STAT,
    CLEAN,
    DEATH_SULK_MINUTES,
    DECAY_SCALE,
    DIRTY_DRAIN_PER_POOP,
    EMPTY_MINUTES,
    FULL_LEVEL,
    LOW_THRESHOLD,
    MAX_POOPS,
    MEAL_POOP_MINUTES,
    POOP_MINUTES,
    NAP_MIN_SECONDS,
    REACTION_SECONDS,
    SLEEP_DECAY_FACTOR,
    SLEEP_FULL_SECONDS,
    START_LEVELS,
    STAT_MAX,
    STAT_NAMES,
    Pet,
    death_seconds,
    decay_per_second,
)


class Rng:
    """Stands in for random: uniform() returns the same point of every range."""

    def __init__(self, fraction=0.5, value=None):
        self.fraction = fraction
        self.value = value

    def uniform(self, a, b):
        if self.value is not None:
            return self.value
        return a + (b - a) * self.fraction


NEVER = Rng(value=1e9)  # poops never come due


def poop_seconds(span, fraction=0.5):
    return (span[0] + (span[1] - span[0]) * fraction) * DECAY_SCALE * 60.0


def full_pet(now=0.0, rng=NEVER):
    levels = {}
    for name in STAT_NAMES:
        levels[name] = STAT_MAX
    return Pet(now, levels, rng)


def first_empty():
    """Seconds until the fastest-draining stat of a full pet hits zero."""
    return min(STAT_MAX / decay_per_second(name) for name in STAT_NAMES)


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


def test_stats_floor_at_zero_and_a_pet_left_sulking_dies():
    pet = full_pet()
    out = first_empty()
    pet.tick(out + 1)
    assert pet.sulking
    assert not pet.dead
    assert pet.attention
    assert pet.pose == state.POSE_SULK
    pet.tick(out + death_seconds() - 1)
    assert not pet.dead
    pet.tick(out + death_seconds() + 1)
    assert pet.dead
    assert pet.died
    assert pet.pose == state.POSE_DEAD
    assert not pet.attention
    assert pet.wants is None
    pet.tick(out + death_seconds() + 2)
    assert not pet.died  # only on the tick it happened
    assert pet.do("eat", out + death_seconds() + 3) is False
    assert not pet.accepts("eat")


def test_death_takes_about_ten_minutes_of_sulking_at_the_current_scale():
    assert death_seconds() == pytest.approx(DEATH_SULK_MINUTES * DECAY_SCALE * 60)
    assert 8 * 60 <= death_seconds() <= 12 * 60


def test_one_long_step_dies_at_the_same_moment_as_many_short_ones():
    out = first_empty()
    one = full_pet()
    one.tick(out + death_seconds() + 0.5)
    assert one.dead
    many = full_pet()
    t = 0.0
    while t < out + death_seconds() - 0.5:
        t += 7.0
        many.tick(min(t, out + death_seconds() - 0.5))
    assert not many.dead
    many.tick(out + death_seconds() + 0.5)
    assert many.dead


def test_sulk_recovers_once_cared_for_and_the_death_clock_starts_over():
    pet = full_pet()
    out = first_empty()
    pet.tick(out + 60)
    assert pet.sulking
    for action in ("eat", "drink", "play", "affection"):
        pet.do(action, out + 60)
    assert not pet.sulking
    pet.stats["fun"] = 0.0  # runs out again later
    pet.tick(out + death_seconds() - 30)
    assert pet.sulking
    pet.tick(out + death_seconds() + 30)  # past the first sulk's deadline
    assert not pet.dead


def test_sleeping_refills_energy_out_of_a_sulk():
    pet = full_pet()
    pet.stats["energy"] = 0.0
    pet.tick(1.0)
    assert pet.sulking
    pet.do("sleep", 1.0)
    pet.tick(1.0 + SLEEP_FULL_SECONDS + 1)
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


@pytest.mark.parametrize("action", ["eat", "drink", "play", "affection"])
def test_each_action_restores_its_stat_and_shows_a_reaction(action):
    levels = {}
    for name in STAT_NAMES:
        levels[name] = 10
    pet = Pet(0.0, levels, NEVER)
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


def run_perfect_carer(hours, seed=1):
    """Someone who answers every ask at once.

    Returns (need_asks, poops): when a stat newly went low, and when a poop
    appeared, in seconds.
    """
    pet = Pet(0.0, rng=random.Random(seed))
    asks = []
    poops = []
    for second in range(1, int(hours * 3600) + 1):
        now = float(second)
        before = pet.low_needs()
        pet.tick(now)
        if pet.pooped:
            poops.append(now)
        for name in pet.low_needs():
            if name not in before:
                asks.append(now)
                break
        if pet.attention:
            pet.do(pet.wants, now)
        assert not pet.dead
    return asks, poops


def test_first_need_comes_about_eight_minutes_after_power_on():
    asks, _ = run_perfect_carer(0.25)
    assert asks, "no ask in the first 15 minutes"
    assert 7 * 60 <= asks[0] <= 9 * 60, "first ask at %.0f s" % asks[0]


def gaps(times):
    return [b - a for a, b in zip(times, times[1:])]


def test_needs_come_up_about_every_ten_minutes():
    asks, _ = run_perfect_carer(8)
    g = gaps(asks)
    assert len(g) > 30
    mean = sum(g) / len(g)
    assert 9 * 60 <= mean <= 12 * 60, "mean gap %.0f s" % mean
    assert max(g) <= 15 * 60 * DECAY_SCALE, "longest quiet stretch %.0f s" % max(g)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_poops_come_every_six_to_ten_minutes(seed):
    _, poops = run_perfect_carer(8, seed)
    g = gaps(poops)
    mean = sum(g) / len(g)
    assert 6 * 60 <= mean <= 10 * 60, "mean gap %.0f s" % mean
    assert 5 * 60 <= poops[0] <= 11 * 60, "first poop at %.0f s" % poops[0]


def test_a_perfect_carer_never_loses_the_pet():
    run_perfect_carer(8, seed=4)  # asserts it never dies


def test_first_poop_comes_when_scheduled():
    pet = full_pet(rng=Rng(0.5))
    due = poop_seconds(POOP_MINUTES)
    pet.tick(due - 1)
    assert pet.poops == 0
    assert not pet.attention
    assert pet.tick(due + 1) is True  # attention edge
    assert pet.poops == 1
    assert pet.pooped == 1
    assert pet.wants == CLEAN
    assert pet.pose == state.POSE_SAD
    pet.tick(due + 2)
    assert pet.pooped == 0


def test_eating_or_drinking_brings_the_next_poop_forward():
    for action in ("eat", "drink"):
        pet = full_pet(rng=Rng(0.5))
        pet.stats[ACTION_STAT[action]] = 20
        pet.do(action, 10.0)
        soon = 10.0 + poop_seconds(MEAL_POOP_MINUTES)
        assert soon < poop_seconds(POOP_MINUTES)
        pet.tick(soon - 1)
        assert pet.poops == 0
        pet.tick(soon + 1)
        assert pet.poops == 1


def test_poops_pile_up_to_four_and_then_stop_appearing():
    pet = full_pet(rng=Rng(0.0))
    every = poop_seconds(POOP_MINUTES, 0.0)
    pet.tick(every * 3.5)
    assert pet.poops == 3
    pet.tick(every * 10.5)  # one long step: the extra poops are capped, not stored up
    assert pet.poops == MAX_POOPS
    assert pet.pooped == 1  # only the fourth actually appeared in this step
    assert pet.poop(every * 11) is False
    assert pet.poops == MAX_POOPS


def test_no_pooping_while_asleep_it_waits_until_it_wakes():
    pet = full_pet(rng=Rng(0.5))
    due = poop_seconds(POOP_MINUTES)
    pet.stats["energy"] = 0.0
    pet.tick(due - 5)
    pet.do("sleep", due - 5)
    pet.tick(due + 1)
    assert pet.asleep
    assert pet.poops == 0
    pet.wake(due + 2)
    pet.tick(due + 3)
    assert pet.poops == 1


def test_poops_make_fun_and_affection_drain_faster_and_cleaning_stops_it():
    clean = full_pet()
    dirty = full_pet()
    dirty.poop(0.0)
    dirty.poop(0.0)
    clean.tick(600.0)
    dirty.tick(600.0)
    factor = 1 + DIRTY_DRAIN_PER_POOP * 2
    for name in STAT_NAMES:
        lost_clean = STAT_MAX - clean.stats[name]
        lost_dirty = STAT_MAX - dirty.stats[name]
        if name in ("fun", "affection"):
            assert lost_dirty == pytest.approx(lost_clean * factor)
        else:
            assert lost_dirty == pytest.approx(lost_clean)
    assert dirty.do(CLEAN, 600.0)
    assert dirty.poops == 0
    assert not dirty.attention
    before = dirty.stats["fun"]
    dirty.tick(1200.0)
    assert before - dirty.stats["fun"] == pytest.approx(600.0 * decay_per_second("fun"))


def test_a_low_need_comes_before_cleaning_in_what_it_wants():
    pet = full_pet()
    pet.poop(0.0)
    assert pet.wants == CLEAN
    pet.stats["thirst"] = LOW_THRESHOLD - 1
    pet.tick(1.0)
    assert pet.wants == "drink"
    pet.do("drink", 1.0)
    assert pet.wants == CLEAN
    assert pet.clean() == 1
    assert pet.wants is None


def test_one_long_step_with_poops_matches_many_short_ones():
    one = full_pet(rng=Rng(0.3))
    many = full_pet(rng=Rng(0.3))
    end = poop_seconds(POOP_MINUTES, 0.3) * 2.5
    one.tick(end)
    t = 0.0
    while t < end:
        t = min(t + 13.0, end)
        many.tick(t)
    assert one.poops == many.poops == 2
    for name in STAT_NAMES:
        assert one.stats[name] == pytest.approx(many.stats[name])


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
