"""Vision-based OCR for the Mac build.

Windows uses winsdk.windows.media.ocr (windows/ocr.py). The Mac equivalent is
Apple's Vision framework (VNRecognizeTextRequest), accessed via
pyobjc-framework-Vision. Vision's boundingBox is normalized (0.0-1.0) with a bottom-left origin.
OcrLine.rect below is kept normalized (0.0-1.0, fraction of the captured
crop) with the origin flipped to top-left, rather than converted to pixels —
this avoids a resolution mismatch, since CGWindowListCreateImage may capture
at Retina (2x) pixel density while GameWindow.width/height are in points.
Normalized fractions compose directly with config.py's OCR_RX*/RY* region.
"""

from __future__ import annotations

import asyncio
import io
from dataclasses import dataclass
from typing import Optional

from Foundation import NSData
from PIL import Image
from Vision import VNImageRequestHandler, VNRecognizeTextRequest

from capture import capture_window
from window import GameWindow


@dataclass(frozen=True)
class Rect:
    """Bounding box as fractions (0.0-1.0) of the captured crop, top-left origin."""

    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class OcrLine:
    text: str
    rect: Rect


def _run_vision_sync(png_bytes: bytes) -> list:
    """Run VNRecognizeTextRequest on PNG bytes; returns VNRecognizedTextObservations.

    Synchronous — call via asyncio.to_thread from async code.
    """
    data = NSData.dataWithBytes_length_(png_bytes, len(png_bytes))
    handler = VNImageRequestHandler.alloc().initWithData_options_(data, None)

    request = VNRecognizeTextRequest.alloc().init()

    ok, error = handler.performRequests_error_([request], None)
    if not ok:
        raise RuntimeError(f"Vision OCR failed: {error}")

    return list(request.results() or [])


async def ocr_region(
    win: GameWindow,
    rx1: float, ry1: float,
    rx2: float, ry2: float,
) -> list[OcrLine]:
    """Capture a window-relative sub-region and run Vision OCR on it.

    Coordinates are fractions of the window (0.0-1.0).
    """
    img = capture_window(win.window_id, rx1, ry1, rx2, ry2)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    observations = await asyncio.to_thread(_run_vision_sync, png_bytes)

    lines: list[OcrLine] = []
    for obs in observations:
        candidates = obs.topCandidates_(1)
        if not candidates:
            continue
        text = str(candidates[0].string())

        box = obs.boundingBox()
        bx, by = box.origin.x, box.origin.y
        bw, bh = box.size.width, box.size.height

        # Flip from Vision's bottom-left-origin normalized box to a
        # top-left-origin normalized rect (fraction of the crop).
        rect = Rect(x=bx, y=1 - by - bh, width=bw, height=bh)
        lines.append(OcrLine(text=text, rect=rect))

    return lines


def find_items(
    lines: list[OcrLine],
    keywords: list[str],
) -> dict[str, Optional[OcrLine]]:
    """Scan OCR lines for each keyword (case-insensitive).

    Returns a dict mapping each keyword to its matching OcrLine, or None if
    not found. The OcrLine carries a .rect used to locate the Buy button.
    """
    found: dict[str, Optional[OcrLine]] = {k: None for k in keywords}
    for line in lines:
        text_lower = line.text.lower()
        for keyword in keywords:
            if found[keyword] is None and keyword in text_lower:
                found[keyword] = line
    return found
