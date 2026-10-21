"""Hardware for the AYWHP ESP32-S3 (DevKitC-1 layout). Pins per docs/WIRING.md.

Screen: HiLetgo 2.8" ILI9341, 320x240, SPI.
  SCK  -> IO12    MOSI -> IO11    CS -> IO10
  DC   -> IO9     RST  -> IO8     LED -> IO7 (PWM backlight)
Buttons: one leg to the GPIO, the other to a shared GND. Internal pull-ups.
  A -> IO4        B -> IO5        C -> IO6
"""

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

# ---- Pins -------------------------------------------------------------------

BUTTON_PINS = (board.IO4, board.IO5, board.IO6)
BUTTON_NAMES = ("A", "B", "C")
BACKLIGHT_PIN = board.IO7

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

    Returns a list of (name, pressed) tuples in the order they happened, where
    name is "A", "B" or "C" and pressed is True for a press, False for a
    release. Empty list if nothing happened. Call this every loop iteration;
    the queue holds 64 events and drops the oldest when full.
    """
    keys = get_keys()
    events = []
    while True:
        event = keys.events.get()
        if event is None:
            return events
        events.append((BUTTON_NAMES[event.key_number], event.pressed))


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
