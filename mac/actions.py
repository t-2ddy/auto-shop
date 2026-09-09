import asyncio

import config
from input import click_rel, scroll_down
from ocr import OcrLine
from window import GameWindow


async def do_refresh(win: GameWindow) -> None:
    """Click the shop Refresh button then confirm the dialog."""
    click_rel(win, *config.COORD_REFRESH)
    await asyncio.sleep(config.DELAY_CLICK)
    click_rel(win, *config.COORD_REFRESH_CONFIRM)
    await asyncio.sleep(config.DELAY_AFTER_REFRESH)


async def do_buy(win: GameWindow, item_line: OcrLine) -> None:
    """Click the in-game Buy button for the given item row, then confirm.

    The Buy button sits at a fixed relative X (BUY_BUTTON_RX) but at the same
    relative Y as the item text row. item_line.rect is normalized (0.0-1.0)
    relative to the OCR crop (config.OCR_RY1..OCR_RY2), so it's mapped back
    to a window-relative Y before clicking. Coordinates calibrated via
    mac/ut/test_capture.py + mac/ut/test_click.py.
    """
    rect = item_line.rect
    item_center_frac = rect.y + rect.height / 2
    ry = config.OCR_RY1 + item_center_frac * (config.OCR_RY2 - config.OCR_RY1) + .04

    click_rel(win, config.BUY_BUTTON_RX, ry)
    await asyncio.sleep(config.DELAY_CLICK)
    click_rel(win, *config.COORD_BUY_CONFIRM)
    await asyncio.sleep(config.DELAY_AFTER_BUY)


async def do_scroll(win: GameWindow) -> None:
    """Scroll the shop item list down one page."""
    scroll_down(win)
    await asyncio.sleep(config.DELAY_AFTER_SCROLL)
