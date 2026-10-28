"""Hardware for the AYWHP ESP32-S3 (DevKitC-1 layout). Pins per docs/WIRING.md.

Screen: HiLetgo 2.8" ILI9341, 320x240, SPI.
  SCK  -> IO12    MOSI -> IO11    CS -> IO10
  DC   -> IO9     RST  -> IO8     LED -> IO7 (PWM backlight)
Buttons: 1x3 membrane keypad, common on GND, one GPIO per key. Internal pull-ups.
  A (left) -> IO6   B (middle) -> IO4   C (right) -> IO5
Audio: MAX98357A I2S amp, VIN on 5V, GAIN and SD floating.
  BCLK -> IO15    LRC  -> IO16    DIN -> IO17
"""

import array

import audiobusio
import audiocore
import board
import busio
import displayio
import fourwire
import keypad
import pwmio
import supervisor
import adafruit_ili9341

# ---- Tuning knobs -----------------------------------------------------------

# Drop to 10-20 MHz if the screen shows garbage over the 50cm jumpers (see PLAN.md risks).
SPI_BAUDRATE = 24_000_000

# 0 or 180. Flip if the image is upside down relative to the costume mount.
ROTATION = 0

WIDTH = 320
HEIGHT = 240

# Buttons are sampled every BUTTON_INTERVAL seconds and must read the same new
# state for DEBOUNCE_THRESHOLD samples in a row before an event fires. Raise
# the threshold if a single press double-fires or phantom presses show up over
# the long jumpers (2 = 40 ms, 3 = 60 ms, 5 = 100 ms).
DEBOUNCE_THRESHOLD = 2
BUTTON_INTERVAL = 0.02

# Backlight PWM. 5 kHz is far above visible flicker and well within the LEDC
# range on the S3. If the LED pin is driven through a slow transistor and the
# dim end looks uneven, try 1-2 kHz. If it buzzes, try 20 kHz.
BACKLIGHT_FREQUENCY = 5_000
BACKLIGHT_INITIAL = 1.0  # start fully on so the screen is visible while testing

# Audio sample rate. The ESP32 port preloads 3 DMA buffers of 1023 frames when
# a sound starts and refills them from background callbacks, which wait while
# a display refresh runs. A sound longer than the preload stutters if a
# refresh outlasts the two buffers still queued: at 16 kHz that is ~190 ms
# (22.05 kHz: ~140 ms), and the sleep/wake theme change costs ~200 ms. Square
# waves up to ~4 kHz still sound clean at 16 kHz.
AUDIO_SAMPLE_RATE = 16_000

# ---- Pins -------------------------------------------------------------------

# Which GPIO each physical key of the membrane keypad lands on (plug pin 1 is
# the common, on GND). The plug's key pins are not in left-to-right order, so
# the order is fixed here rather than by rewiring:
#   left key   -> plug pin 4 -> IO6 -> A (cycle)
#   middle key -> plug pin 2 -> IO4 -> B (select)
#   right key  -> plug pin 3 -> IO5 -> C (cancel)
BUTTON_PINS = (board.IO6, board.IO4, board.IO5)
BUTTON_NAMES = ("A", "B", "C")
BACKLIGHT_PIN = board.IO7
AUDIO_BCLK_PIN = board.IO15
AUDIO_LRC_PIN = board.IO16
AUDIO_DIN_PIN = board.IO17

# ---- Display ----------------------------------------------------------------

_display = None


def get_display():
    """Return the ILI9341 as a displayio display, creating it on first call."""
    global _display
    if _display is not None:
        return _display

    displayio.release_displays()
    spi = busio.SPI(clock=board.IO12, MOSI=board.IO11)
    bus = fourwire.FourWire(
        spi,
        command=board.IO9,
        chip_select=board.IO10,
        reset=board.IO8,
        baudrate=SPI_BAUDRATE,
    )
    _display = adafruit_ili9341.ILI9341(
        bus, width=WIDTH, height=HEIGHT, rotation=ROTATION
    )
    return _display


# ---- Buttons ----------------------------------------------------------------

_keys = None


def get_keys():
    """Return the keypad.Keys scanner for A/B/C, creating it on first call."""
    global _keys
    if _keys is None:
        _keys = keypad.Keys(
            BUTTON_PINS,
            value_when_pressed=False,  # pressed = pulled to GND
            pull=True,  # internal pull-ups, no external resistors
            interval=BUTTON_INTERVAL,
            debounce_threshold=DEBOUNCE_THRESHOLD,
        )
    return _keys


def button_events():
    """Drain pending button events.

    Returns a list of (name, pressed, ticks) tuples in the order they happened,
    where name is "A", "B" or "C", pressed is True for a press and False for a
    release, and ticks is the ticks_ms() reading when the scanner saw the
    change (subtract with ticks_diff). Empty list if nothing happened. Call
    this every loop iteration; the queue holds 64 events and drops the oldest
    when full.
    """
    keys = get_keys()
    events = []
    while True:
        event = keys.events.get()
        if event is None:
            return events
        events.append((BUTTON_NAMES[event.key_number], event.pressed, event.timestamp))


# ---- Backlight --------------------------------------------------------------

# supervisor.ticks_ms() wraps at 2**29; these helpers make subtraction safe.
_TICKS_PERIOD = 1 << 29
_TICKS_MAX = _TICKS_PERIOD - 1
_TICKS_HALF = _TICKS_PERIOD // 2


def ticks_ms():
    """Millisecond counter that keeps full precision no matter how long we run."""
    return supervisor.ticks_ms()


def ticks_diff(a, b):
    """a - b in ms, correct across the ticks_ms wraparound."""
    diff = (a - b) & _TICKS_MAX
    return ((diff + _TICKS_HALF) & _TICKS_MAX) - _TICKS_HALF


def _clamp01(value):
    return 0.0 if value < 0.0 else 1.0 if value > 1.0 else float(value)


class Backlight:
    """PWM backlight on BACKLIGHT_PIN with a non-blocking linear fade.

    brightness is 0.0 (off) to 1.0 (full). set_brightness() jumps immediately
    and cancels any fade. fade_to() starts a fade that advances only when
    update() is called, so call update() once per main-loop iteration.
    """

    def __init__(self, initial=BACKLIGHT_INITIAL):
        self._pwm = pwmio.PWMOut(
            BACKLIGHT_PIN, frequency=BACKLIGHT_FREQUENCY, duty_cycle=0
        )
        self._level = 0.0
        self._fade_from = 0.0
        self._fade_to = 0.0
        self._fade_start = 0
        self._fade_ms = 0  # 0 = no fade in progress
        self.set_brightness(initial)

    @property
    def brightness(self):
        """Current level, 0.0-1.0 (mid-fade values included)."""
        return self._level

    @property
    def target(self):
        """Where the backlight is heading: the fade target, or the current level."""
        return self._fade_to if self._fade_ms else self._level

    @property
    def fading(self):
        return self._fade_ms > 0

    def set_brightness(self, level):
        """Jump to level (0.0-1.0) right now and cancel any fade."""
        self._fade_ms = 0
        self._apply(_clamp01(level))

    def fade_to(self, target, duration):
        """Fade from the current level to target (0.0-1.0) over duration seconds.

        Non-blocking: the fade advances on each update() call. Starting a new
        fade mid-fade restarts from wherever the level is right now.
        """
        target = _clamp01(target)
        if duration <= 0:
            self.set_brightness(target)
            return
        self._fade_from = self._level
        self._fade_to = target
        self._fade_start = ticks_ms()
        self._fade_ms = int(duration * 1000)

    def update(self):
        """Advance an in-progress fade. Returns True if the level changed."""
        if not self._fade_ms:
            return False
        elapsed = ticks_diff(ticks_ms(), self._fade_start)
        if elapsed >= self._fade_ms:
            self._fade_ms = 0
            level = self._fade_to
        else:
            frac = elapsed / self._fade_ms
            level = self._fade_from + (self._fade_to - self._fade_from) * frac
        if level == self._level:
            return False
        self._apply(level)
        return True

    def _apply(self, level):
        self._level = level
        self._pwm.duty_cycle = int(level * 65535 + 0.5)

    def deinit(self):
        self._pwm.deinit()


_backlight = None


def get_backlight():
    """Return the Backlight, creating it (at BACKLIGHT_INITIAL) on first call."""
    global _backlight
    if _backlight is None:
        _backlight = Backlight()
    return _backlight


# ---- Audio ------------------------------------------------------------------


def _square(hz, count, amplitude):
    """count samples of a square wave at hz, as a list.

    A period is rarely a whole number of samples (2093 Hz at 16 kHz is 7.64),
    so the wave is built from a block of up to 32 whole cycles whose length
    comes closest to a whole number of samples, which keeps the pitch within
    ~0.1%. The block is then repeated with list multiplication, which runs in
    C. Growing one list run by run is far slower here: MicroPython's
    list.extend() and slice assignment both copy the whole list each time
    (~0.5-1.3 s for a half-second beep on this board).
    """
    period = AUDIO_SAMPLE_RATE / hz
    cycles = 1
    best = 1.0
    for k in range(1, 33):
        error = abs(k * period - int(k * period + 0.5)) / k
        if error < best:
            best = error
            cycles = k
    length = int(cycles * period + 0.5)
    half = length / (2.0 * cycles)
    block = []
    level = amplitude
    for edge in range(1, 2 * cycles + 1):
        block += [level] * (int(edge * half + 0.5) - len(block))
        level = -level
    return block * (count // length) + block[: count % length]


def _render(tune, amplitude):
    """A tune as an array of signed 16-bit square-wave samples.

    tune is a sequence of (hz, ms) notes; 0 Hz is a rest.
    """
    samples = []
    for hz, ms in tune:
        count = AUDIO_SAMPLE_RATE * ms // 1000
        if hz > 0:
            samples += _square(hz, count, amplitude)
        else:
            samples += [0] * count
    return array.array("h", samples)


class Audio:
    """MAX98357A on I2S, playing tunes as square waves.

    play(tune) returns at once: I2SOut preloads a few ms of the sample and
    DMA plays the rest in the background, so the game loop never waits. A
    new play() cuts off whatever is still playing. Each tune is rendered once
    and cached; prepare() renders it ahead of time so the first play() of a
    tune doesn't pay for that.
    """

    def __init__(self, volume=1.0):
        self._i2s = audiobusio.I2SOut(
            bit_clock=AUDIO_BCLK_PIN, word_select=AUDIO_LRC_PIN, data=AUDIO_DIN_PIN
        )
        self._amplitude = int(32767 * _clamp01(volume))
        self._samples = {}  # tune -> RawSample

    @property
    def playing(self):
        return self._i2s.playing

    def prepare(self, tune):
        """Render tune now (if it isn't already) and return its RawSample."""
        sample = self._samples.get(tune)
        if sample is None:
            sample = audiocore.RawSample(
                _render(tune, self._amplitude), sample_rate=AUDIO_SAMPLE_RATE
            )
            self._samples[tune] = sample
        return sample

    def play(self, tune):
        """Start tune now, cutting off anything still playing."""
        self._i2s.play(self.prepare(tune))

    def stop(self):
        self._i2s.stop()

    def deinit(self):
        self._i2s.deinit()


_audio = None


def get_audio(volume=1.0):
    """Return the Audio player, creating it (at volume, 0.0-1.0) on first call."""
    global _audio
    if _audio is None:
        _audio = Audio(volume)
    return _audio
