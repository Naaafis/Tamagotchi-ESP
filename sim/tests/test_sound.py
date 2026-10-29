"""Tunes and the sound policy in firmware/pet/sound.py."""

import pytest

from pet import sound
from pet.game import MENU_ITEMS, Game
from pet.sound import (
    BLIP,
    CHIRP,
    CUES,
    HAPPY,
    REFUSE,
    REMINDER_SECONDS,
    SAD,
    STARTUP,
    TICK,
    TUNES,
    Sounds,
)
from pet.state import LOW_THRESHOLD

SAMPLE_RATE = 16_000  # hw.board_esp32s3.AUDIO_SAMPLE_RATE


class Recorder:
    def __init__(self):
        self.played = []

    def play(self, tune):
        self.played.append(tune)


@pytest.mark.parametrize("tune", TUNES, ids=[sound.name(t) for t in TUNES])
def test_tunes_are_hz_ms_pairs_the_board_can_render(tune):
    assert isinstance(tune, tuple) and tune
    for hz, ms in tune:
        assert isinstance(hz, int) and isinstance(ms, int)
        assert hz == 0 or 100 <= hz <= SAMPLE_RATE // 4  # at least 4 samples per cycle
        assert ms > 0
    assert tune[0][0] > 0 and tune[-1][0] > 0  # no dead air at either end
    assert sound.duration_ms(tune) <= 1500


def test_every_tune_has_a_distinct_name():
    names = [sound.name(t) for t in TUNES]
    assert len(set(names)) == len(TUNES)
    assert "tune" not in names
    assert sound.name(((440, 100),)) == "tune"


def test_tick_is_short_and_chirp_is_three_beeps():
    assert sound.duration_ms(TICK) <= 50
    assert len([n for n in CHIRP if n[0] > 0]) == 3


def test_each_event_plays_its_tune():
    rec = Recorder()
    s = Sounds(rec)
    for event, tune in ((s.button, TICK), (s.attention, CHIRP), (s.sulk, SAD)):
        event()
        assert s.update(1.0, False) == tune
    assert rec.played == [TICK, CHIRP, SAD]
    assert s.update(2.0, False) is None  # nothing new asked for
    assert rec.played == [TICK, CHIRP, SAD]


def test_every_cue_the_animations_use_has_a_tune():
    from pet import anim, minigame

    used = set()
    frame_sets = list(anim.ACTIONS.values()) + list(anim.REFUSALS.values())
    frame_sets += [anim.clean_frames(1), anim.DIE]
    frame_sets += [minigame.MATCH, minigame.MISS, minigame.WIN, minigame.LOSE]
    for frames in frame_sets:
        for f in frames:
            if f[anim.CUE] is not None:
                used.add(f[anim.CUE])
    used.add("plop")  # the game's own cue when a poop appears
    assert used == set(CUES)
    for tune in CUES.values():
        assert tune in TUNES
    rec = Recorder()
    s = Sounds(rec)
    s.cue("bite")
    s.update(0.0, False)
    s.cue("refuse")
    s.update(1.0, False)
    s.cue("no such cue")
    s.update(2.0, False)
    assert rec.played == [BLIP, REFUSE]


def test_at_most_one_tune_per_frame_and_the_tick_yields():
    rec = Recorder()
    s = Sounds(rec)
    s.button()
    s.cue("happy")  # a tick, then the jingle, in one frame
    s.update(1.0, False)
    s.cue("happy")
    s.button()  # a tick after the jingle in the same frame doesn't replace it
    s.update(2.0, False)
    s.button()
    s.button()
    s.update(3.0, False)
    assert rec.played == [HAPPY, HAPPY, TICK]


def test_chirp_repeats_while_attention_stays_on():
    rec = Recorder()
    s = Sounds(rec)
    s.attention()
    s.update(100.0, True)
    s.update(100.0 + REMINDER_SECONDS - 0.1, True)
    assert rec.played == [CHIRP]
    s.update(100.0 + REMINDER_SECONDS, True)
    assert rec.played == [CHIRP, CHIRP]
    s.update(100.0 + 2 * REMINDER_SECONDS, True)
    assert rec.played == [CHIRP, CHIRP, CHIRP]


def test_a_button_press_restarts_the_reminder():
    rec = Recorder()
    s = Sounds(rec)
    s.attention()
    s.update(0.0, True)
    s.button()
    s.update(15.0, True)
    s.update(15.0 + REMINDER_SECONDS - 0.1, True)
    assert rec.played == [CHIRP, TICK]
    s.update(15.0 + REMINDER_SECONDS, True)
    assert rec.played == [CHIRP, TICK, CHIRP]


def test_no_reminder_once_attention_is_off():
    rec = Recorder()
    s = Sounds(rec)
    s.attention()
    s.update(0.0, True)
    s.update(5.0, False)
    s.update(5.0 + 10 * REMINDER_SECONDS, False)
    assert rec.played == [CHIRP]


def test_mute_reaches_no_player_but_still_reports():
    rec = Recorder()
    s = Sounds(rec, mute=True)
    s.play(STARTUP)
    assert s.update(0.0, False) == STARTUP
    s.attention()
    s.update(1.0, True)
    assert s.update(1.0 + REMINDER_SECONDS, True) == CHIRP
    assert rec.played == []


def wired_game():
    g = Game(now=0.0, build_ui=False)
    rec = Recorder()
    s = Sounds(rec)
    g.on_button = lambda name: s.button()
    g.on_attention = s.attention
    g.on_sulk = s.sulk
    g.on_cue = s.cue

    def step(now, presses=()):
        g.update(now, presses)
        s.update(now, g.pet.attention)

    return g, rec, step


def run(step, start, end, presses=None):
    """Step every 50 ms from start to end; presses maps a time to its presses."""
    presses = presses or {}
    now = start
    while now < end:
        step(now, presses.get(round(now, 2), ()))
        now = round(now + 0.05, 2)


def test_game_events_play_the_right_tunes():
    g, rec, step = wired_game()
    g.pet.stats["hunger"] = 50
    step(1.0, ["A"])  # move: tick
    run(step, 2.0, 7.0, {2.0: ["B"], 3.0: ["A"]})  # eat; the A mid-animation is ignored
    assert rec.played == [TICK, TICK, BLIP, BLIP, BLIP, HAPPY]
    run(step, 7.0, 10.0, {7.0: ["B"]})  # full now: refused
    assert rec.played[6:] == [TICK, REFUSE]
    g.pet.stats["fun"] = LOW_THRESHOLD + 0.001
    step(11.0)  # attention edge
    assert rec.played[-1] == CHIRP
    g.pet.stats["fun"] = 0.001
    step(12.0)  # runs out: sulk
    assert rec.played[-1] == SAD
    count = len(rec.played)
    step(11.0 + REMINDER_SECONDS)  # still asking: reminder chirp
    assert rec.played[count:] == [CHIRP]
