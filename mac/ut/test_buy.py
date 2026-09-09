"""OCR a shop row and click its Buy button — buy-location calibration.

Looks for Friendship Points (a common, cheap Secret Shop listing) rather
than Mystic Medal / Covenant Bookmark, so you can test the Buy-button Y
mapping against a live window without waiting for a rare drop.

Uses the same Y formula as actions.do_buy() (OCR line center mapped through
the OCR crop, then BUY_BUTTON_RX). Clicks Buy only — it does not confirm —
so a confirm dialog popping up means the location is right; cancel it if
you don't want to spend the gold.

Run from the repo root:
    python mac/ut/test_buy.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from capture import capture_window
from input import click_rel
from ocr import find_items, ocr_region
from window import find_game_window

TARGET = "friendship points"


def _buy_ry(item_line) -> float:
    """Window-relative Y of the Buy button for an OCR line.

    Must stay in lockstep with actions.do_buy() — that is the mapping this
    harness is meant to verify.
    """
    rect = item_line.rect
    item_center_frac = rect.y + rect.height / 2
    return config.OCR_RY1 + item_center_frac * (config.OCR_RY2 - config.OCR_RY1) + 0


async def main() -> None:
    win = find_game_window()
    if win is None:
        sys.exit("ERROR: game window not found (launch Epic Seven first)")

    print(f"window: pid={win.pid} id={win.window_id} {win.width:.0f}x{win.height:.0f}")

    img = capture_window(win.window_id, config.OCR_RX1, config.OCR_RY1, config.OCR_RX2, config.OCR_RY2)
    img.save("capture.png")
    print(f"Screenshot saved to capture.png ({img.size[0]}x{img.size[1]})")

    print("Running Vision OCR...")
    lines = await ocr_region(win, config.OCR_RX1, config.OCR_RY1, config.OCR_RX2, config.OCR_RY2)
    print(f"Found {len(lines)} line(s):")
    for line in lines:
        r = line.rect
        print(
            f"  {line.text!r}  rect=(x={r.x:.3f}, y={r.y:.3f}, "
            f"w={r.width:.3f}, h={r.height:.3f})"
        )

    found = find_items(lines, [TARGET])
    item_line = found[TARGET]
    if item_line is None:
        print(f"'{TARGET}' not found.")
        return

    ry = _buy_ry(item_line)
    r = item_line.rect
    print(f"Found '{TARGET}': {item_line.text!r}")
    print(
        f"  rect=(x={r.x:.3f}, y={r.y:.3f}, w={r.width:.3f}, h={r.height:.3f}) "
        f"-> click rx={config.BUY_BUTTON_RX}, ry={ry:.4f}"
    )
    print("Clicking Buy (moves your real cursor; confirm dialog = location is right).")

    click_rel(win, config.BUY_BUTTON_RX, ry)
    print("done")


if __name__ == "__main__":
    asyncio.run(main())
