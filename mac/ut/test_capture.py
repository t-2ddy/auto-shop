"""Capture the Epic Seven window and run Vision OCR on it.

Saves the captured (cropped) image to capture.png and prints every OCR line
found along with its normalized rect, for calibrating config.OCR_RX*/RY* and
sanity-checking Vision's text recognition against the Windows OCR baseline.

Run from the repo root:
    python mac/ut/test_capture.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from capture import capture_window
from config import OCR_RX1, OCR_RX2, OCR_RY1, OCR_RY2
from ocr import ocr_region
from window import find_game_window


async def main() -> None:
    win = find_game_window()
    if win is None:
        sys.exit("ERROR: game window not found (launch Epic Seven first)")

    print(f"window: pid={win.pid} id={win.window_id} {win.width:.0f}x{win.height:.0f}")

    img = capture_window(win.window_id, OCR_RX1, OCR_RY1, OCR_RX2, OCR_RY2)
    img.save("capture.png")
    print(f"Screenshot saved to capture.png ({img.size[0]}x{img.size[1]})")

    print("Running Vision OCR...")
    lines = await ocr_region(win, OCR_RX1, OCR_RY1, OCR_RX2, OCR_RY2)

    if not lines:
        print("No text recognized.")
        return

    print(f"Found {len(lines)} line(s):")
    for line in lines:
        r = line.rect
        print(
            f"  {line.text!r}  rect=(x={r.x:.3f}, y={r.y:.3f}, "
            f"w={r.width:.3f}, h={r.height:.3f})"
        )


if __name__ == "__main__":
    asyncio.run(main())
