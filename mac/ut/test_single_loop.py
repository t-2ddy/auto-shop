"""Run exactly one shop cycle (refresh -> OCR/buy -> drag-scroll -> OCR/buy)
against the live game, with verbose logging at each step.

Unlike main.py's run_loop() (infinite, until Q/Ctrl+C), this runs a single
pass and stops — useful for calibrating the whole pipeline end-to-end,
including the click-hold-drag scroll (mac/input.py's scroll_down()), without
risking repeated buys/refreshes while you're still tuning coordinates.

Reuses loop._check_and_buy() directly so behavior exactly matches the real
bot (same OCR region, same keyword matching, same buy sequence).

Run from the repo root:
    python mac/ut/test_single_loop.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from actions import do_refresh
from input import scroll_down
from loop import _check_and_buy
from ocr import find_items, ocr_region
from window import find_game_window


async def _scan(win, label: str) -> None:
    """OCR the shop region and print what was found, without buying."""
    lines = await ocr_region(win, config.OCR_RX1, config.OCR_RY1, config.OCR_RX2, config.OCR_RY2)
    print(f"[{label}] OCR found {len(lines)} line(s):")
    for line in lines:
        print(f"    {line.text!r}")

    found = find_items(lines, config.ITEM_KEYWORDS)
    matched = {k: v for k, v in found.items() if v is not None}
    if matched:
        print(f"[{label}] keyword matches: {list(matched.keys())}")
    else:
        print(f"[{label}] no keyword matches ({config.ITEM_KEYWORDS})")


async def main() -> None:
    win = find_game_window()
    if win is None:
        sys.exit("ERROR: game window not found (launch Epic Seven first)")

    print(f"window: pid={win.pid} id={win.window_id} {win.width:.0f}x{win.height:.0f}")

    print("\n=== step 1: refresh ===")
    await do_refresh(win)

    print("\n=== step 2: OCR + buy (top) ===")
    bought_this_cycle: set[str] = set()
    await _scan(win, "top (pre-buy)")
    await _check_and_buy(win, bought_this_cycle, None)
    print(f"bought so far: {bought_this_cycle or 'none'}")

    print("\n=== step 3: scroll (click-hold-drag-up) ===")
    scroll_down(win)
    await asyncio.sleep(config.DELAY_AFTER_SCROLL)

    print("\n=== step 4: OCR + buy (bottom) ===")
    await _scan(win, "bottom (pre-buy)")
    await _check_and_buy(win, bought_this_cycle, None)
    print(f"bought total this cycle: {bought_this_cycle or 'none'}")

    print("\ndone — single cycle complete.")


if __name__ == "__main__":
    asyncio.run(main())
