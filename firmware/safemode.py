"""Runs instead of code.py when the board drops into safe mode.

In the costume nobody sees the serial console, and a jostled wire or a power
dip can crash the board into safe mode with a frozen screen. So after a crash
this waits a second and resets straight back into the game; the pet starts
fresh, like an unplug and replug.

It runs before USB starts, so print() goes nowhere. Instead it leaves the
crash's name in microcontroller.nvm (CRASH_NVM_BYTES at offset 0), and
code.py prints it at the next boot ("recovered from safe mode: HARD_FAULT")
and clears it.

Left alone, so they stay in safe mode as usual:
  - safe mode asked for on purpose: holding the buttons for it at boot (this
    file doesn't even run then) or microcontroller.on_next_reset(SAFE_MODE).
    If the game ever crashes on every boot, that is the way out: press RESET,
    then press it again while the status LED blinks.
  - setup problems a reset can't fix (no CIRCUITPY, USB configuration).
"""

import time

import microcontroller
import supervisor

CRASH_NVM_BYTES = 24  # code.py reads the same span

CRASHES = (
    "BROWNOUT",
    "HARD_FAULT",
    "WATCHDOG",
    "INTERRUPT_ERROR",
    "NLR_JUMP_FAIL",
    "STACK_OVERFLOW",
    "GC_ALLOC_OUTSIDE_VM",
    "NO_HEAP",
    "SDK_FATAL_ERROR",
)

reason = supervisor.runtime.safe_mode_reason
for name in CRASHES:
    if reason == getattr(supervisor.SafeModeReason, name, None):
        try:
            note = name.encode()
            microcontroller.nvm[0:CRASH_NVM_BYTES] = note + bytes(CRASH_NVM_BYTES - len(note))
        except Exception:
            pass  # the note is nice to have; getting back into the game is the point
        time.sleep(1.0)  # let a dipped supply recover before trying again
        microcontroller.reset()
