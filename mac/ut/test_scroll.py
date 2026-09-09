"""Repeatedly scroll the Epic Seven shop list until Space is pressed.

Useful for calibrating scroll_down's tick count/position — watch the game
window and see how far each scroll_down() call moves the list.

Run from the repo root:
    python mac/ut/test_scroll.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from hotkey import GlobalQuitListener
from input import scroll_down
from window import find_game_window


def main() -> None:
    win = find_game_window()
    if win is None:
        sys.exit("ERROR: game window not found (launch Epic Seven first)")

    print(f"window: pid={win.pid} id={win.window_id} {win.width:.0f}x{win.height:.0f}")
    print("Scrolling every 1.5s. Press Space to stop (works even while the game is focused).")

    listener = GlobalQuitListener()
    listener.start()

    while not listener.quit_event.is_set():
        print("scroll_down()")
        scroll_down(win)
        time.sleep(1.5)

    listener.stop()
    print("stopped")


if __name__ == "__main__":
    main()
