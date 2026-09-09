"""Compare different scroll delivery methods against the real game window.

This was used to diagnose why scrolling wasn't working: Epic Seven's Mac
build is an iOS-wrapper (UIKit) app, and its shop list is very likely a
UIScrollView, which only responds to touch-drag (pan) gestures rather than
scroll-wheel events, the same way it ignored CGEventPostToPid for clicks
(see mac/ut/test_click.py). mac/input.py's scroll_down() now uses the same
click-hold-drag-up approach as the "drag" method below. wheel-line and
wheel-pixel-continuous are kept here for reference/regression checking.

  wheel-line              Discrete mouse-wheel line delta.
  wheel-pixel-continuous  Pixel-unit delta + the "continuous" flag, emulating
                           trackpad momentum scrolling.
  drag                    Simulates an actual pointer drag (mouseDown near
                           the bottom of the list, several mouseDragged steps
                           upward, then mouseUp) — matches a touch-drag/pan
                           gesture, which is what a UIScrollView expects.
                           This is the approach mac/input.py's scroll_down()
                           now uses.

Usage (run from repo root):
    python mac/ut/test_scroll_methods.py --method wheel-line
    python mac/ut/test_scroll_methods.py --method wheel-pixel-continuous
    python mac/ut/test_scroll_methods.py --method drag
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from Quartz import (
    CGEventCreateMouseEvent,
    CGEventCreateScrollWheelEvent,
    CGEventPost,
    CGEventSetIntegerValueField,
    CGPointMake,
    CGWarpMouseCursorPosition,
    kCGEventLeftMouseDown,
    kCGEventLeftMouseDragged,
    kCGEventLeftMouseUp,
    kCGHIDEventTap,
    kCGMouseButtonLeft,
    kCGScrollEventUnitLine,
    kCGScrollEventUnitPixel,
    kCGScrollWheelEventIsContinuous,
)

from input import activate_app
from window import find_game_window

WHEEL_LINES_PER_TICK = 3
WHEEL_PIXELS_PER_TICK = 120
DRAG_STEPS = 2
DRAG_STEP_DELAY = 0.02


def method_wheel_line(win, rx: float, ry: float, ticks: int) -> None:
    """Baseline: today's mac/input.py scroll_down() implementation."""
    x = win.x + rx * win.width
    y = win.y + ry * win.height
    point = CGPointMake(x, y)

    CGWarpMouseCursorPosition(point)
    time.sleep(0.05)

    delta = -(WHEEL_LINES_PER_TICK * ticks)
    event = CGEventCreateScrollWheelEvent(None, kCGScrollEventUnitLine, 1, delta)
    CGEventPost(kCGHIDEventTap, event)


def method_wheel_pixel_continuous(win, rx: float, ry: float, ticks: int) -> None:
    """Pixel-unit delta + continuous flag, emulating trackpad momentum scroll."""
    x = win.x + rx * win.width
    y = win.y + ry * win.height
    point = CGPointMake(x, y)

    CGWarpMouseCursorPosition(point)
    time.sleep(0.05)

    delta = -(WHEEL_PIXELS_PER_TICK * ticks)
    event = CGEventCreateScrollWheelEvent(None, kCGScrollEventUnitPixel, 1, delta)
    CGEventSetIntegerValueField(event, kCGScrollWheelEventIsContinuous, 1)
    CGEventPost(kCGHIDEventTap, event)


def method_drag(win, rx: float, ry_start: float, ry_end: float) -> None:
    """Simulate a pointer drag (mouseDown -> mouseDragged* -> mouseUp).

    Closest equivalent to a touch-drag/pan gesture, which UIScrollView (the
    likely underlying shop list widget) natively expects.
    """
    x = win.x + rx * win.width
    y_start = win.y + ry_start * win.height
    y_end = win.y + ry_end * win.height

    start_point = CGPointMake(x, y_start)
    CGWarpMouseCursorPosition(start_point)
    time.sleep(0.05)

    down = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, start_point, kCGMouseButtonLeft)
    CGEventPost(kCGHIDEventTap, down)
    time.sleep(0.03)

    for i in range(1, DRAG_STEPS + 1):
        frac = i / DRAG_STEPS
        y = y_start + (y_end - y_start) * frac
        point = CGPointMake(x, y)
        drag = CGEventCreateMouseEvent(None, kCGEventLeftMouseDragged, point, kCGMouseButtonLeft)
        CGEventPost(kCGHIDEventTap, drag)
        time.sleep(DRAG_STEP_DELAY)

    end_point = CGPointMake(x, y_end)
    up = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, end_point, kCGMouseButtonLeft)
    CGEventPost(kCGHIDEventTap, up)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--method",
        choices=["wheel-line", "wheel-pixel-continuous", "drag"],
        default="wheel-line",
    )
    parser.add_argument("--rx", type=float, default=0.5, help="fraction of window width")
    parser.add_argument("--ry", type=float, default=0.5, help="fraction of window height (center point / drag start)")
    parser.add_argument("--ry-end", type=float, default=0.2, help="drag end point (drag method only)")
    parser.add_argument("--ticks", type=int, default=3, help="wheel ticks (wheel-* methods only)")
    args = parser.parse_args()

    win = find_game_window()
    if win is None:
        sys.exit("ERROR: game window not found (launch Epic Seven first)")

    print(f"window: pid={win.pid} id={win.window_id} {win.width:.0f}x{win.height:.0f}")
    activated = activate_app(win.pid)
    print(f"activated: {activated}")

    print(f"method={args.method} — scrolling in 2s (watch the shop list)...")
    time.sleep(2)

    if args.method == "wheel-line":
        method_wheel_line(win, args.rx, args.ry, args.ticks)
    elif args.method == "wheel-pixel-continuous":
        method_wheel_pixel_continuous(win, args.rx, args.ry, args.ticks)
    else:
        method_drag(win, args.rx, args.ry, args.ry_end)

    print("done — did the shop list move?")


if __name__ == "__main__":
    main()
