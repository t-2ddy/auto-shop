"""Verify that mac/resize.py's set_window_size() actually works against the
live Epic Seven window before relying on it in main.py.

Prints the window's current size, resizes it to config.WINDOW_WIDTH/HEIGHT,
then re-reads and prints the size again so you can confirm whether the app
honored the requested size, snapped to a nearby size, or ignored the resize
entirely.

Run from the repo root:
    python mac/ut/test_resize.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from resize import set_window_size
from window import find_game_window


def main() -> None:
    win = find_game_window()
    if win is None:
        sys.exit("ERROR: game window not found (launch Epic Seven first)")

    print(f"before: {win.width:.0f}x{win.height:.0f} @ ({win.x:.0f},{win.y:.0f})")
    print(f"requesting: {config.WINDOW_WIDTH:.0f}x{config.WINDOW_HEIGHT:.0f}")

    ok = set_window_size(win, config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
    print(f"set_window_size returned: {ok}")

    time.sleep(0.3)  # let the resize settle before re-reading bounds

    after = find_game_window()
    if after is None:
        print("after: window not found (it may have vanished/changed identity)")
        return

    print(f"after:  {after.width:.0f}x{after.height:.0f} @ ({after.x:.0f},{after.y:.0f})")

    got_requested = (
        abs(after.width - config.WINDOW_WIDTH) < 2
        and abs(after.height - config.WINDOW_HEIGHT) < 2
    )
    if got_requested:
        print("result: matches requested size")
    elif (after.width, after.height) != (win.width, win.height):
        print("result: size changed but does not match request exactly (app may snap to fixed sizes)")
    else:
        print("result: size unchanged — resize was likely ignored/rejected")


if __name__ == "__main__":
    main()
