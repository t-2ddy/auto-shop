"""Window screenshot capture for the Mac build.

Windows uses PrintWindow(PW_RENDERFULLCONTENT) (windows/ocr.py) to grab
GPU-rendered windows on any monitor, even off-screen/behind other windows.
The closest Mac equivalent is CGWindowListCreateImage, which captures a
window by id regardless of occlusion or focus.

Requires the calling process (terminal / python binary) to have the Screen
Recording permission granted under System Settings -> Privacy & Security ->
Screen Recording. Without it, CGWindowListCreateImage returns an empty/black
image rather than raising an error.
"""

from __future__ import annotations

import io

from Foundation import NSMutableData
from PIL import Image
from Quartz import (
    CGImageDestinationAddImage,
    CGImageDestinationCreateWithData,
    CGImageDestinationFinalize,
    CGRectNull,
    CGWindowListCreateImage,
    kCGWindowImageBestResolution,
    kCGWindowImageBoundsIgnoreFraming,
    kCGWindowListOptionIncludingWindow,
)


def capture_window(window_id: int, rx1: float, ry1: float, rx2: float, ry2: float) -> Image.Image:
    """Capture a window-relative sub-region of `window_id`.

    rx1/ry1/rx2/ry2 are fractions (0.0-1.0) of the captured image's width and
    height, mirroring windows/ocr.py's _capture_window crop behavior.

    kCGWindowImageBoundsIgnoreFraming is required so the captured image's
    bounds match window.py's GameWindow.width/height (from
    CGWindowListCopyWindowInfo) exactly. Without it, CGWindowListCreateImage
    pads the image with the window's shadow/frame on all sides — a fixed
    amount regardless of window size — so OCR-derived fractions (computed
    against the padded image) and click_rel's fractions (computed against
    the unpadded window bounds) refer to different rectangles. That padding
    is negligible on a large window but becomes a large, position-dependent
    click offset once the window is pinned to a small fixed size (see
    mac/resize.py) — confirmed via mac/ut/test_capture.py: a 842x509 window
    produced a 1820x1154 capture, i.e. 34pt of extra padding on every edge
    instead of the expected clean 2x Retina 1684x1018.
    """
    cg_image = CGWindowListCreateImage(
        CGRectNull,
        kCGWindowListOptionIncludingWindow,
        window_id,
        kCGWindowImageBestResolution | kCGWindowImageBoundsIgnoreFraming,
    )
    if cg_image is None:
        raise RuntimeError(
            f"capture_window: got no image for window_id={window_id}. "
            "Check that the window still exists and that Screen Recording "
            "permission is granted to this process."
        )

    data = NSMutableData.data()
    dest = CGImageDestinationCreateWithData(data, "public.png", 1, None)
    CGImageDestinationAddImage(dest, cg_image, None)
    if not CGImageDestinationFinalize(dest):
        raise RuntimeError("capture_window: failed to encode captured image as PNG")

    img = Image.open(io.BytesIO(bytes(data))).convert("RGB")

    w, h = img.size
    box = (int(rx1 * w), int(ry1 * h), int(rx2 * w), int(ry2 * h))
    return img.crop(box)
