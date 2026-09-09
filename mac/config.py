# iOS-on-Mac wrapper installed from the App Store / iPhone apps on Mac.
# Inner bundle name is Epic7; the launcher users see is "Epic Seven".
BUNDLE_ID = "com.stove.epic7.ios"
APP_NAME = "Epic Seven"
INNER_APP_NAME = "Epic7"

# Known install locations (wrapper .app, not the inner Epic7.app).
APP_PATHS = [
    "/Applications/Epic Seven.app",
]

# Ignore title-bar / overlay windows when picking the game surface.
MIN_WINDOW_HEIGHT = 80
MIN_WINDOW_AREA = 50_000

# Fixed window size the bot resizes Epic Seven to on startup (mac/resize.py),
# so calibrated click/scroll/OCR coordinates below stay valid run-to-run
# regardless of whatever size the window was left at. Set these to your
# current window size (mac/find_window.py prints it) before calibrating the
# rest of this file. If the resize fails (e.g. the app rejects arbitrary
# sizes), the bot falls back to whatever size the window already is.
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 550

# --- Bot behavior below is seeded from windows/config.py's values as a ---
# --- starting point. The Mac window's aspect ratio/chrome differs from  ---
# --- Windows, so these WILL need recalibration via mac/ut/ scripts      ---
# --- against a real, live Epic Seven window before relying on them.     ---

# Click coordinates (relative, 0.0-1.0 of the window)
COORD_REFRESH         = (0.2,  0.9)
COORD_REFRESH_CONFIRM = (0.6,  0.65)
COORD_BUY_CONFIRM     = (0.6,  0.7)

# X position of the in-game Buy button to the right of each item row.
BUY_BUTTON_RX = 0.9

# OCR scan region (relative to the window)
OCR_RX1, OCR_RY1 = 0.0, 0.0
OCR_RX2, OCR_RY2 = 1.0, 1.0

# Target item keywords (lowercase); order determines buy priority when both present
ITEM_KEYWORDS = ["mystic medal", "covenant bookmark"]

# Hardcoded gold cost per item (used to track remaining gold locally)
ITEM_COSTS = {
    "mystic medal": 280_000,
    "covenant bookmark": 184_000,
}

# Stop the bot if tracked gold drops below this threshold
GOLD_MIN = 300_000

# Timing (seconds)
DELAY_AFTER_REFRESH = 2.0
DELAY_AFTER_BUY     = 1.0
DELAY_AFTER_SCROLL  = 1.0
DELAY_CLICK         = 0.5
