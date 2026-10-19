#!/usr/bin/env python3
"""Read the board's serial console for a few seconds and exit non-zero on a traceback.

Usage: .venv/bin/python scripts/serial_log.py [SECONDS] [--no-reload]

By default sends Ctrl-C then Ctrl-D first, so the board soft-reloads and the full
boot output of code.py is captured (otherwise a traceback that already scrolled by
would be missed).
"""

import glob
import sys
import time

import serial


def find_port():
    ports = sorted(glob.glob("/dev/cu.usbmodem*"))
    if not ports:
        sys.exit("no /dev/cu.usbmodem* port found. Is the board on its USB port (not COM)?")
    return ports[0]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    seconds = float(args[0]) if args else 10.0
    reload_first = "--no-reload" not in sys.argv

    port = find_port()
    print(f"# {port}, reading for {seconds:g}s" + (" after soft reload" if reload_first else ""))
    captured = []
    with serial.Serial(port, 115200, timeout=0.2) as ser:
        if reload_first:
            ser.write(b"\x03")  # Ctrl-C: interrupt running code (or enter REPL if idle)
            time.sleep(0.3)
            ser.reset_input_buffer()
            ser.write(b"\x04")  # Ctrl-D: soft reload, runs code.py from the top
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            data = ser.read(4096)
            if data:
                text = data.decode("utf-8", "replace")
                captured.append(text)
                sys.stdout.write(text)
                sys.stdout.flush()
    print()
    if "Traceback" in "".join(captured):
        print("# traceback seen", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
