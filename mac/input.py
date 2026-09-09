"""Click + scroll primitives for the Mac build.

Epic Seven's Mac (iOS-wrapper) build only reacts to real HID-level input
events (CGEventPost via kCGHIDEventTap), not process-local events
(CGEventPostToPid) — confirmed via mac/ut/test_click.py. That means every
click/scroll here visibly moves the real cursor and requires the game to be
foreground/key first, unlike windows/input.py's PostMessage approach which
posts invisibly to a background window.
"""

from __future__ import annotations

import time

from AppKit import NSApplicationActivateIgnoringOtherApps, NSRunningApplication
from Quartz import (
    CGEventCreateMouseEvent,
    CGEventPost,
    CGEventSetIntegerValueField,
    CGPointMake,
    CGWarpMouseCursorPosition,
    kCGEventLeftMouseDown,
    kCGEventLeftMouseDragged,
    kCGEventLeftMouseUp,
    kCGEventMouseMoved,
    kCGHIDEventTap,
    kCGMouseButtonLeft,
    kCGMouseEventClickState,
)

from window import GameWindow

DRAG_STEPS = 2
DRAG_STEP_DELAY = 0.02


def activate_app(pid: int, wait: float = 0.3) -> bool:
    """Bring the app to the foreground (key/frontmost) so it accepts input.

    Both click_rel and scroll_down need this — the game only processes
    synthetic input once its window is actually key, not just visible.
    """
    app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
    if app is None:
        return False
    ok = app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
    time.sleep(wait)
    return bool(ok)


def click_rel(win: GameWindow, rx: float, ry: float) -> None:
    """Click at a position given as fractions of the window (0.0-1.0).

    Activates the app, warps the real cursor to the target point, then posts
    a left-click (move + down + up) via the system-wide HID event tap. This
    moves your actual mouse — don't touch it mid-click.
    """
    activate_app(win.pid)

    x = win.x + rx * win.width
    y = win.y + ry * win.height
    point = CGPointMake(x, y)

    # Move the real cursor first; engines often key off the last known HID
    # cursor position rather than trusting the event's embedded location.
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


def scroll_down(
    win: GameWindow,
    rx: float = 0.7,
    ry_start: float = 0.75,
    ry_end: float = 0.5,
) -> None:
    """Scroll the shop list downward via a click-and-hold drag gesture.

    Epic Seven's Mac build is an iOS-wrapper (UIKit) app, and its shop list
    is a UIScrollView, which only responds to touch-drag (pan) gestures —
    scroll-wheel events (the previous implementation) don't move it at all,
    confirmed via mac/ut/test_scroll_methods.py. This clicks and holds at
    (rx, ry_start), drags the cursor upward to (rx, ry_end) over several
    steps, then releases: dragging the content up on screen scrolls the
    list down, exactly like a touch drag would on the phone/iPad original.
    """
    activate_app(win.pid)

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
