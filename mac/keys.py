"""Keyboard cancel handling for the Mac CLI.

windows/main.py uses msvcrt.kbhit()/getwch() to poll for 'Q' — Windows-only.
The mouse is busy driving the game while the loop runs, so a keyboard
shortcut is the most practical way to cancel from the CLI (the GUI, in
mac/gui.py, has its own Stop button / Space-bar binding instead).

This used to read raw stdin via termios/tty cbreak mode, but that only works
while the terminal itself is the frontmost/key app. input.py's activate_app()
makes Epic Seven frontmost on every click/scroll, which steals keyboard focus
away from the terminal — so a terminal-stdin read never sees the key once the
bot loop starts clicking. wait_for_quit() now uses mac/hotkey.py's
system-wide CGEventTap listener instead, which works regardless of which
app is frontmost. Space bar is used rather than 'Q' since its keycode isn't
layout-remapped, and it's the same key already used to cancel elsewhere.
"""

from __future__ import annotations

import asyncio

from hotkey import wait_for_space_blocking


async def wait_for_quit() -> None:
    """Block (off the event loop) until Space is pressed anywhere on the system."""
    await asyncio.to_thread(wait_for_space_blocking)
