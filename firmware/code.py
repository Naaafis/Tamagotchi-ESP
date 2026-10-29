"""The pet on the board: pet.game.Game driven by the three buttons.

Buttons A/B/C (hw.board_esp32s3, keypad with internal pull-ups) feed presses,
and which buttons are held, into Game.update(). The backlight comes up to
BRIGHT_LEVEL on every press, whenever the pet starts asking for attention and
for the whole left/right game, then fades down to RESTING_LEVEL after
IDLE_SECONDS without a press, or straight away when the lights go out.

Sound (pet.sound, played through the MAX98357A by hw.board_esp32s3.Audio): a
tick on every press, a three-beep chirp when the pet starts asking for
attention and again every pet.sound.REMINDER_SECONDS while it keeps asking,
the animations' cues (a blip per bite or sip, a double tone when it refuses,
the jingle as it hops, the game's match/miss/win/lose), a low sad tune when
it starts sulking, and a short hello at power-on. The tunes themselves are in
pet/sound.py.

Serial prints every press and release stamped with the keypad scanner's own
time, with the hold time and the gap since that button's last release (a
bounce shows up as a few-ms hold or gap), every attention event, action,
cue, sulk and sound (except the tick), any loop iteration slower than
SLOW_FRAME_MS, and a status line every STATUS_SECONDS with the pet's stats,
the slowest frame and the longest gap between two frames (which includes the
display's background refreshes).
"""

import gc
import time

from hw.board_esp32s3 import (
    HEIGHT,
    WIDTH,
    button_events,
    get_audio,
    get_backlight,
    get_display,
    get_keys,
    ticks_diff,
    ticks_ms,
)
from pet import sound
from pet.game import Game

# ---- Tuning knobs -----------------------------------------------------------

VOLUME = 0.5  # speaker loudness, 0.0-1.0 (square-wave amplitude into the amp)
MUTE = False  # True = no sound at all; everything else works the same

RESTING_LEVEL = 0.15  # backlight while nobody is playing (0.0-1.0)
BRIGHT_LEVEL = 1.00  # backlight after a press or when the pet asks for something
IDLE_SECONDS = 15.0  # seconds after the last press before fading back down
FADE_UP_SECONDS = 0.3
FADE_DOWN_SECONDS = 1.5

FRAME_SECONDS = 1 / 30  # how often the game is updated; the panel refreshes at about this rate
SLOW_FRAME_MS = 50  # one loop iteration slower than this is printed as it happens
STATUS_SECONDS = 30  # how often the stats line is printed

# The display refreshes in the background between Python statements, so its
# cost mostly lands inside time.sleep() and never shows in a frame's own time.
# Measured on this board: a pet frame flip (128x128) costs 58 ms, an icon
# highlight 9 ms, the sleep/wake theme change or the stats page 200-215 ms.
# The status line's "longest gap" is the worst wall-clock interval between two
# consecutive loop iterations, so it does include those refreshes.

# Garbage collection. The game allocates only ~2 KB/s and a collection with
# little garbage costs a few ms, but one that frees a lot (the import-time
# compiler garbage, or a long stretch of play) costs 100-250 ms on this board
# (CircuitPython 10.3.1, 8 MB PSRAM heap). So we collect once right after
# setup, and then whenever the pet has been left alone for GC_IDLE_SECONDS, at
# most every GC_INTERVAL_SECONDS, so the pause lands while nobody is pressing
# anything. Never call gc.mem_alloc()/gc.mem_free() in the loop: each walks
# the whole 8 MB heap and takes ~210 ms.
GC_IDLE_SECONDS = 60
GC_INTERVAL_SECONDS = 300

# ---- Setup ------------------------------------------------------------------

# Backlight first so the screen is lit while the display initialises.
backlight = get_backlight()
display = get_display()
get_keys()  # start scanning now so a press during setup isn't lost
audio = get_audio(VOLUME)
for _tune in sound.TUNES:
    audio.prepare(_tune)  # render every tune now (~100 ms) so no press waits for it
sounds = sound.Sounds(audio, mute=MUTE)

# The game clock: seconds since boot, built from ticks_ms() so it keeps
# millisecond precision all night (time.monotonic() loses precision over time).
_last_ticks = ticks_ms()
_elapsed_ms = 0


def clock_ms():
    """Milliseconds since boot, correct across the ticks_ms() wraparound."""
    global _last_ticks, _elapsed_ms
    ticks = ticks_ms()
    _elapsed_ms += ticks_diff(ticks, _last_ticks)
    _last_ticks = ticks
    return _elapsed_ms


def ticks_to_clock(ticks):
    """Convert a ticks_ms() reading (a keypad event's timestamp) to clock_ms() time."""
    return _elapsed_ms + ticks_diff(ticks, _last_ticks)


def log(text, at_ms=None):
    if at_ms is None:
        at_ms = clock_ms()
    print("[%7d ms] %s" % (at_ms, text))


game = Game(now=0.0, width=WIDTH, height=HEIGHT)
display.root_group = game.root_group


def collect_garbage(reason):
    """Run the collector now and print how long it took. Returns the ms."""
    t0 = clock_ms()
    gc.collect()
    took = clock_ms() - t0
    log("gc (%s): %d ms" % (reason, took))
    return took


collect_garbage("after setup")  # drop the import-time compiler garbage

# ---- Backlight policy -------------------------------------------------------

_last_activity_ms = 0  # when the backlight was last asked to brighten


def brighten(reason):
    """Bring the backlight up and restart the idle timer."""
    global _last_activity_ms
    _last_activity_ms = clock_ms()
    if backlight.target < BRIGHT_LEVEL:
        backlight.fade_to(BRIGHT_LEVEL, FADE_UP_SECONDS)
        log("backlight up (%s)" % reason)


def on_button(name):
    brighten("button " + name)
    sounds.button()


def on_attention():
    log("attention: " + game.pet.summary())
    brighten("attention")
    sounds.attention()


def on_action(action):
    log("action: " + action)


def on_cue(name):
    log("cue: " + name)
    sounds.cue(name)


def on_sulk():
    log("sulk: " + game.pet.summary())
    sounds.sulk()


def on_death():
    log("died: " + game.pet.summary())
    brighten("died")


def on_reset():
    log("reset: new pet: " + game.pet.summary())
    brighten("reset")
    sounds.play(sound.STARTUP)


game.on_button = on_button
game.on_attention = on_attention
game.on_action = on_action
game.on_cue = on_cue
game.on_sulk = on_sulk
game.on_death = on_death
game.on_reset = on_reset

# ---- Main loop --------------------------------------------------------------

log(
    "T11 OK: game on %dx%d, buttons A/B/C on IO6/IO4/IO5, backlight %d%% -> %d%% after %gs idle, sound %s"
    % (
        WIDTH,
        HEIGHT,
        int(BRIGHT_LEVEL * 100),
        int(RESTING_LEVEL * 100),
        IDLE_SECONDS,
        "muted" if MUTE else "volume %g" % VOLUME,
    )
)
log("pet: " + game.pet.summary())
sounds.play(sound.STARTUP)

_idle_ms = int(IDLE_SECONDS * 1000)
_next_status_ms = STATUS_SECONDS * 1000
_frames = 0
_slowest_ms = 0
_slow_frames = 0
_longest_gap_ms = 0
_prev_frame_start = None
_down_ticks = {}  # button name -> ticks when it went down
_held = []  # buttons down right now (holds: C leaves the game, B resets, A poops)
_lights_were_off = False
_release_ticks = {}  # button name -> ticks of its last release
_gc_idle_ms = GC_IDLE_SECONDS * 1000
_gc_interval_ms = GC_INTERVAL_SECONDS * 1000
_last_gc_ms = -_gc_interval_ms  # so the first idle collect isn't held back
_update_ms = 0

while True:
    frame_start = clock_ms()
    if _prev_frame_start is not None and frame_start - _prev_frame_start > _longest_gap_ms:
        _longest_gap_ms = frame_start - _prev_frame_start
    _prev_frame_start = frame_start

    presses = []
    for name, pressed, ticks in button_events():
        # Stamped with the scanner's time, not ours, so the gap between the
        # press and release lines is the real hold time.
        if pressed:
            text = name + " press"
            if name in _release_ticks:
                text += " (%d ms after its last release)" % ticks_diff(ticks, _release_ticks[name])
            _down_ticks[name] = ticks
            presses.append(name)
            if name not in _held:
                _held.append(name)
        else:
            text = name + " release"
            if name in _down_ticks:
                text += " (held %d ms)" % ticks_diff(ticks, _down_ticks[name])
            _release_ticks[name] = ticks
            if name in _held:
                _held.remove(name)
        log(text, ticks_to_clock(ticks))

    game.update(frame_start / 1000.0, presses, _held)
    tune = sounds.update(frame_start / 1000.0, game.pet.attention)
    if tune is not None and tune != sound.TICK:
        log("sound: %s (%d ms)" % (sound.name(tune), sound.duration_ms(tune)))
    _update_ms = clock_ms() - frame_start

    if game.playing:
        brighten("game")  # stays up for the whole game
    lights_off = game.lights_off
    if lights_off and not _lights_were_off:
        _last_activity_ms = frame_start - _idle_ms  # lights out: dim now, not in 15 s
    _lights_were_off = lights_off
    if backlight.target > RESTING_LEVEL and frame_start - _last_activity_ms >= _idle_ms:
        backlight.fade_to(RESTING_LEVEL, FADE_DOWN_SECONDS)
        log("backlight down (%s)" % ("lights off" if lights_off else "idle %gs" % IDLE_SECONDS))
    backlight.update()

    if frame_start - _last_activity_ms >= _gc_idle_ms and frame_start - _last_gc_ms >= _gc_interval_ms:
        _last_gc_ms = frame_start
        collect_garbage("idle")

    frame_ms = clock_ms() - frame_start
    _frames += 1
    if frame_ms > _slowest_ms:
        _slowest_ms = frame_ms
    if frame_ms > SLOW_FRAME_MS:
        _slow_frames += 1
        log("slow frame: %d ms (game.update %d ms)" % (frame_ms, _update_ms))

    if frame_start >= _next_status_ms:
        _next_status_ms += STATUS_SECONDS * 1000
        log(
            "status: %s | backlight %d%% | %d frames, slowest %d ms, %d over %d ms, longest gap %d ms"
            % (
                game.pet.summary(),
                int(backlight.brightness * 100 + 0.5),
                _frames,
                _slowest_ms,
                _slow_frames,
                SLOW_FRAME_MS,
                _longest_gap_ms,
            )
        )
        _frames = 0
        _slowest_ms = 0
        _slow_frames = 0
        _longest_gap_ms = 0

    remaining = FRAME_SECONDS - frame_ms / 1000.0
    if remaining > 0:
        time.sleep(remaining)
