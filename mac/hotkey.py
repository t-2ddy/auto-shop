"""System-wide "press Space to quit" listener, independent of app focus.

mac/input.py's activate_app() makes Epic Seven the frontmost/key app on
every click and scroll, which steals keyboard focus away from the terminal —
so a terminal-stdin-based quit key (the old approach) never sees the
keystroke once the loop starts clicking. This listens for keydown events at
the OS/HID level via a CGEventTap, the same mechanism global hotkey tools
(Alfred, screenshot utilities, etc.) use, so it works no matter which app is
frontmost.

Requires the same Accessibility permission already granted for input.py's
synthetic click/scroll events — no additional permission needed.
"""

from __future__ import annotations

import threading

from Quartz import (
    CFMachPortCreateRunLoopSource,
    CFRunLoopAddSource,
    CFRunLoopGetCurrent,
    CFRunLoopRun,
    CFRunLoopStop,
    CGEventGetIntegerValueField,
    CGEventMaskBit,
    CGEventTapCreate,
    CGEventTapEnable,
    kCFRunLoopCommonModes,
    kCGEventKeyDown,
    kCGEventTapOptionListenOnly,
    kCGHeadInsertEventTap,
    kCGKeyboardEventKeycode,
    kCGSessionEventTap,
)

# Space bar's physical keycode (kVK_Space) is the same 49 across virtually all
# keyboard layouts (it's not a remapped letter key), so this doesn't have the
# non-US-layout caveat a letter key like 'Q' would.
SPACE_KEYCODE = 49


class GlobalQuitListener:
    """Runs a CGEventTap on a dedicated background thread and sets an Event on Space."""

    def __init__(self) -> None:
        self.quit_event = threading.Event()
        self._run_loop = None
        self._thread: threading.Thread | None = None

    def _callback(self, proxy, event_type, event, refcon):
        if event_type == kCGEventKeyDown:
            keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
            if keycode == SPACE_KEYCODE:
                self.quit_event.set()
        # Listen-only tap: return value is ignored, but a value must be returned.
        return event

    def _run(self) -> None:
        tap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionListenOnly,
            CGEventMaskBit(kCGEventKeyDown),
            self._callback,
            None,
        )
        if tap is None:
            raise RuntimeError(
                "GlobalQuitListener: CGEventTapCreate failed — check that "
                "Accessibility permission is granted to this process."
            )

        source = CFMachPortCreateRunLoopSource(None, tap, 0)
        self._run_loop = CFRunLoopGetCurrent()
        CFRunLoopAddSource(self._run_loop, source, kCFRunLoopCommonModes)
        CGEventTapEnable(tap, True)
        CFRunLoopRun()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._run_loop is not None:
            CFRunLoopStop(self._run_loop)


def wait_for_space_blocking() -> None:
    """Start a listener and block until Space is pressed anywhere on the system."""
    listener = GlobalQuitListener()
    listener.start()
    try:
        listener.quit_event.wait()
    finally:
        listener.stop()
