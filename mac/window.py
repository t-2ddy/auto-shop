"""Locate the Epic Seven iOS-on-Mac app and its game window.

Windows uses FindWindow("GLFW30", "Epic Seven"). On Mac the store build is an
iOS wrapper (bundle id com.stove.epic7.ios) whose CG windows have empty titles,
so we match by bundle id / owner name and pick the largest on-screen surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from AppKit import NSRunningApplication, NSWorkspace
from Quartz import (
    CGWindowListCopyWindowInfo,
    kCGNullWindowID,
    kCGWindowListExcludeDesktopElements,
    kCGWindowListOptionAll,
)

import config


@dataclass(frozen=True)
class RunningApp:
    pid: int
    bundle_id: str
    name: str
    path: Optional[str]


@dataclass(frozen=True)
class GameWindow:
    pid: int
    window_id: int
    x: float
    y: float
    width: float
    height: float
    owner_name: str
    title: str
    onscreen: bool
    layer: int
    sharing_state: int


def find_installed_app() -> Optional[Path]:
    """Return the wrapper .app path if Epic Seven is installed."""
    workspace = NSWorkspace.sharedWorkspace()
    url = workspace.URLForApplicationWithBundleIdentifier_(config.BUNDLE_ID)
    if url is not None:
        return Path(url.path())

    for raw in config.APP_PATHS:
        path = Path(raw)
        if path.exists():
            return path
    return None


def find_running_app() -> Optional[RunningApp]:
    """Return the running Epic Seven process, or None if it is not launched."""
    apps = NSRunningApplication.runningApplicationsWithBundleIdentifier_(
        config.BUNDLE_ID
    )
    if not apps:
        workspace = NSWorkspace.sharedWorkspace()
        apps = [
            app
            for app in workspace.runningApplications()
            if (app.localizedName() or "") == config.APP_NAME
        ]
    if not apps:
        return None

    app = apps[0]
    bundle_url = app.bundleURL()
    return RunningApp(
        pid=int(app.processIdentifier()),
        bundle_id=app.bundleIdentifier() or config.BUNDLE_ID,
        name=app.localizedName() or config.APP_NAME,
        path=str(bundle_url.path()) if bundle_url is not None else None,
    )


def list_windows(pid: int) -> list[GameWindow]:
    """All CoreGraphics windows owned by pid (including off-screen)."""
    raw = CGWindowListCopyWindowInfo(
        kCGWindowListOptionAll | kCGWindowListExcludeDesktopElements,
        kCGNullWindowID,
    )
    found: list[GameWindow] = []
    for w in raw or []:
        if int(w.get("kCGWindowOwnerPID") or 0) != pid:
            continue
        bounds = w.get("kCGWindowBounds") or {}
        found.append(
            GameWindow(
                pid=pid,
                window_id=int(w.get("kCGWindowNumber") or 0),
                x=float(bounds.get("X") or 0),
                y=float(bounds.get("Y") or 0),
                width=float(bounds.get("Width") or 0),
                height=float(bounds.get("Height") or 0),
                owner_name=str(w.get("kCGWindowOwnerName") or ""),
                title=str(w.get("kCGWindowName") or ""),
                onscreen=bool(w.get("kCGWindowIsOnscreen")),
                layer=int(w.get("kCGWindowLayer") or 0),
                sharing_state=int(w.get("kCGWindowSharingState") or 0),
            )
        )
    found.sort(key=lambda win: win.width * win.height, reverse=True)
    return found


def _is_game_surface(win: GameWindow) -> bool:
    if win.layer != 0:
        return False
    if win.height < config.MIN_WINDOW_HEIGHT:
        return False
    if win.width * win.height < config.MIN_WINDOW_AREA:
        return False
    return True


def find_game_window() -> Optional[GameWindow]:
    """Pick the on-screen game surface, falling back to the largest off-screen one."""
    app = find_running_app()
    if app is None:
        return None

    windows = [w for w in list_windows(app.pid) if _is_game_surface(w)]
    if not windows:
        return None

    onscreen = [w for w in windows if w.onscreen]
    return onscreen[0] if onscreen else windows[0]
