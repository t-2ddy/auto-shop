import asyncio

import config
from actions import do_buy, do_refresh, do_scroll
from ocr import find_items, ocr_region
from window import GameWindow


async def _check_and_buy(win: GameWindow, already_bought: set[str], stats=None) -> None:
    """Run OCR on the shop and buy any found items not already purchased this cycle.

    already_bought is mutated in-place: each keyword bought here is added so it
    won't be attempted again in a subsequent check within the same refresh cycle.
    stats, when provided, has its purchases counter incremented per keyword bought.
    """
    lines = await ocr_region(
        win,
        config.OCR_RX1, config.OCR_RY1,
        config.OCR_RX2, config.OCR_RY2,
    )
    found = find_items(lines, config.ITEM_KEYWORDS)

    matched = {k: v for k, v in found.items() if v is not None}
    if not matched:
        return

    # Buy in keyword priority order; skip anything already bought this cycle
    for keyword in config.ITEM_KEYWORDS:
        if keyword in matched and keyword not in already_bought:
            print(f"[loop] buying: {keyword}")
            await do_buy(win, matched[keyword])
            already_bought.add(keyword)
            if stats is not None:
                stats.purchases[keyword] = stats.purchases.get(keyword, 0) + 1
                stats.gold -= config.ITEM_COSTS.get(keyword, 0)


async def run_loop(win: GameWindow, stats=None) -> None:
    """Main shop refresh loop.

    Flow every cycle:
      1. Refresh the shop.
      2. OCR check top half — buy any found items.
      3. Scroll down.
      4. OCR check bottom half — buy any found items.
      5. Go back to step 1.

    stats, when provided (a gui.BotStats instance), is updated in-place with
    refresh/purchase counts and the reason the loop stopped, and controls
    whether the gold limiter and refresh limit are enforced.

    Gold is tracked locally rather than read from the screen: stats.gold starts
    at a user-entered value and is decremented by config.ITEM_COSTS on each
    purchase. Without stats (e.g. the CLI entry point), there is no gold value
    to track, so the gold limiter has no effect.

    Press Space or Ctrl+C to stop.
    """
    print("[loop] starting")
    try:
        while True:
            if stats is not None and stats.gold_limiter_enabled and stats.gold < config.GOLD_MIN:
                print(f"[loop] gold {stats.gold:,} < {config.GOLD_MIN:,}, stopping")
                stats.stop_reason = "gold limit"
                break

            if stats is not None and stats.refresh_limit > 0 and stats.refresh_count >= stats.refresh_limit:
                print(f"[loop] refresh limit {stats.refresh_limit} reached, stopping")
                stats.stop_reason = "refresh limit"
                break

            print("[loop] refreshing shop")
            await do_refresh(win)
            if stats is not None:
                stats.refresh_count += 1
            bought_this_cycle: set[str] = set()

            await _check_and_buy(win, bought_this_cycle, stats)

            print("[loop] scrolling to check bottom")
            await do_scroll(win)

            await _check_and_buy(win, bought_this_cycle, stats)

    except asyncio.CancelledError:
        print("[loop] cancelled")
        if stats is not None:
            stats.stop_reason = "cancelled"
    except KeyboardInterrupt:
        print("[loop] stopped by user")
        if stats is not None:
            stats.stop_reason = "user"
