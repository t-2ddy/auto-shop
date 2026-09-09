"""Send a synthetic click to the Epic Seven game window.

Two delivery modes are supported:

  pid    CGEventPostToPid delivers the event directly to the target process's
         Quartz event queue, without touching the real cursor. CONFIRMED NOT
         TO WORK for this game — Epic Seven's Mac build only reacts to real
         HID-level events. Kept here for reference/regression checking only.

  global CGEventPost(kCGHIDEventTap, ...) injects into the system-wide HID
         event stream, like a real click would arrive. This *does* move your
         actual mouse cursor first (CGWarpMouseCursorPosition). CONFIRMED
         WORKING — this is what mac/input.py's click_rel() uses.

Usage (run from repo root):
    python mac/ut/test_click.py 0.25 0.8               # pid mode (won't work)
    python mac/ut/test_click.py 0.25 0.8 --mode global  # global/HID mode
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from AppKit import NSApplicationActivateIgnoringOtherApps, NSRunningApplication
from Quartz import (
    CGEventCreateMouseEvent,
    CGEventPost,
    CGEventPostToPid,
    CGEventSetIntegerValueField,
    CGPointMake,
    CGWarpMouseCursorPosition,
    kCGEventLeftMouseDown,
    kCGEventLeftMouseUp,
    kCGEventMouseMoved,
    kCGHIDEventTap,
    kCGMouseButtonLeft,
    kCGMouseEventClickState,
)

from window import find_game_window


def activate_app(pid: int, wait: float = 0.3) -> bool:
    """Bring the app to the foreground (key/frontmost) so it accepts input.

    Both delivery modes below need this — the game only seems to process
    clicks once its window is actually key, not just visible/on-screen.
    """
    app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
    if app is None:
        return False
    ok = app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
    time.sleep(wait)
    return bool(ok)


def click_at_pid(pid: int, x: float, y: float) -> None:
    """Post a left-click (move + down + up) to `pid` at global point (x, y).

    Does not move the real cursor.
    """
    point = CGPointMake(x, y)

    move = CGEventCreateMouseEvent(None, kCGEventMouseMoved, point, kCGMouseButtonLeft)
    down = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, point, kCGMouseButtonLeft)
    up = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, point, kCGMouseButtonLeft)
    CGEventSetIntegerValueField(down, kCGMouseEventClickState, 1)
    CGEventSetIntegerValueField(up, kCGMouseEventClickState, 1)

    CGEventPostToPid(pid, move)
    time.sleep(0.025)
    CGEventPostToPid(pid, down)
    time.sleep(0.075)
    CGEventPostToPid(pid, up)


def click_at_global(x: float, y: float) -> None:
    """Warp the real cursor to (x, y) and post a left-click via the system-wide
    HID event tap. This moves your actual mouse — don't touch it mid-click.
    """
    point = CGPointMake(x, y)

    # Move the real cursor first; GLFW/engine input often keys off the last
    # known HID cursor position rather than trusting event lParam/location.
    CGWarpMouseCursorPosition(point)
    time.sleep(0.05)

    move = CGEventCreateMouseEvent(None, kCGEventMouseMoved, point, kCGMouseButtonLeft)
    down = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, point, kCGMouseButtonLeft)
    up = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, point, kCGMouseButtonLeft)
    CGEventSetIntegerValueField(down, kCGMouseEventClickState, 1)
    CGEventSetIntegerValueField(up, kCGMouseEventClickState, 1)

    CGEventPost(kCGHIDEventTap, move)
    time.sleep(0.025)
    CGEventPost(kCGHIDEventTap, down)
    time.sleep(0.075)
    CGEventPost(kCGHIDEventTap, up)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rx", nargs="?", type=float, default=0.5, help="fraction of window width")
    parser.add_argument("ry", nargs="?", type=float, default=0.5, help="fraction of window height")
    parser.add_argument(
        "--mode",
        choices=["pid", "global"],
        default="global",
        help="'pid' = CGEventPostToPid (does not work), 'global' = CGEventPost via HID tap (default)",
    )
    args = parser.parse_args()

    win = find_game_window()
    if win is None:
        print("window: not found (launch Epic Seven first)")
        return

    x = win.x + args.rx * win.width
    y = win.y + args.ry * win.height
    print(
        f"mode={args.mode} pid={win.pid} window={win.width:.0f}x{win.height:.0f} "
        f"@ ({win.x:.0f},{win.y:.0f}) -> global point ({x:.0f},{y:.0f})"
    )

    activated = activate_app(win.pid)
    print(f"activated: {activated}")

    if args.mode == "global":
        print("clicking in 2s (moves your real cursor, don't touch the mouse)...")
        time.sleep(2)
        click_at_global(x, y)
    else:
        click_at_pid(win.pid, x, y)
    print("done")


if __name__ == "__main__":
    main()
