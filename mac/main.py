import asyncio
import sys
import time

import config
from keys import wait_for_quit
from loop import run_loop
from resize import set_window_size
from window import find_game_window


async def _run(win) -> None:
    loop_task = asyncio.create_task(run_loop(win))
    quit_task = asyncio.create_task(wait_for_quit())

    done, pending = await asyncio.wait(
        [loop_task, quit_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()

    if quit_task in done:
        print("[main] Q pressed — stopping")
        # Give run_loop's CancelledError handler a chance to print/clean up.
        try:
            await loop_task
        except asyncio.CancelledError:
            pass


def main() -> None:
    win = find_game_window()
    if win is None:
        sys.exit("ERROR: game window not found (launch Epic Seven first)")

    if set_window_size(win, config.WINDOW_WIDTH, config.WINDOW_HEIGHT):
        time.sleep(0.3)  # let the resize settle before re-reading bounds
        resized_win = find_game_window()  # re-fetch: bounds changed after resize
        if resized_win is not None:
            win = resized_win
            print(f"Resized window to {win.width:.0f}x{win.height:.0f}")
        else:
            print("WARNING: window vanished after resize, continuing with stale bounds")
    else:
        print("WARNING: could not resize window, continuing with current size")

    print(f"Found window: pid={win.pid} id={win.window_id} {win.width:.0f}x{win.height:.0f}")
    print("Press Space to stop.")
    asyncio.run(_run(win))


if __name__ == "__main__":
    main()
