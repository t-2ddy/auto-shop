"""Pin the Epic Seven window to a fixed size via the Accessibility (AX) API.

All coordinates in mac/config.py and the drag defaults in mac/input.py's
scroll_down() are relative fractions (0.0-1.0) of whatever size the window
happens to be, so calibration is only valid as long as the window stays a
consistent size. This lets mac/main.py resize the window to a known size on
startup so calibrated coordinates keep working run to run.

Uses the same Accessibility permission already granted for mac/input.py's
synthetic clicks and mac/hotkey.py's global listener — no new permission
prompt expected.
"""

from __future__ import annotations

from ApplicationServices import (
    AXUIElementCopyAttributeValue,
    AXUIElementCreateApplication,
    AXUIElementSetAttributeValue,
    AXValueCreate,
    AXValueGetValue,
    kAXPositionAttribute,
    kAXSizeAttribute,
    kAXValueCGPointType,
    kAXValueCGSizeType,
    kAXWindowsAttribute,
)
from Quartz import CGSizeMake

from window import GameWindow

_AX_ERROR_SUCCESS = 0


def _ax_point(ax_value) -> tuple[float, float] | None:
    """Unpack an AXValue (kAXValueCGPointType) into (x, y), or None on failure."""
    try:
        ok, point = AXValueGetValue(ax_value, kAXValueCGPointType, None)
    except (TypeError, ValueError):
        return None
    if not ok or point is None:
        return None
    return (point.x, point.y)


def _find_ax_window(pid: int, approx_x: float, approx_y: float):
    """Return the AXUIElement window closest to (approx_x, approx_y).

    Epic Seven is expected to have a single standard window, but this
    matches by position against the GameWindow bounds we already have from
    CGWindowListCopyWindowInfo, in case of extra AX windows (dialogs, etc).
    """
    app_ref = AXUIElementCreateApplication(pid)
    err, ax_windows = AXUIElementCopyAttributeValue(app_ref, kAXWindowsAttribute, None)
    if err != _AX_ERROR_SUCCESS or not ax_windows:
        return None

    if len(ax_windows) == 1:
        return ax_windows[0]

    best_window = None
    best_dist = None
    for ax_window in ax_windows:
        pos_err, pos_value = AXUIElementCopyAttributeValue(ax_window, kAXPositionAttribute, None)
        if pos_err != _AX_ERROR_SUCCESS or pos_value is None:
            continue
        point = _ax_point(pos_value)
        if point is None:
            continue
        dist = (point[0] - approx_x) ** 2 + (point[1] - approx_y) ** 2
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_window = ax_window

    return best_window if best_window is not None else ax_windows[0]


def set_window_size(win: GameWindow, width: float, height: float) -> bool:
    """Resize win's window in place. Returns False if the AX window can't be found
    or the OS rejects the resize."""
    ax_window = _find_ax_window(win.pid, win.x, win.y)
    if ax_window is None:
        return False

    size_value = AXValueCreate(kAXValueCGSizeType, CGSizeMake(width, height))
    if size_value is None:
        return False

    err = AXUIElementSetAttributeValue(ax_window, kAXSizeAttribute, size_value)
    return err == _AX_ERROR_SUCCESS
