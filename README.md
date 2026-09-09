# E7 Secret Shop Bot

Windows helper for **Epic Seven** that refreshes the in-game **Secret Shop** and buys **Mystic Medal** / **Covenant Bookmark** when they appear. Clicks and scrolls are posted to the game window, so the real mouse never moves.

[Download the prebuilt](https://drive.google.com/file/d/1bpG2I4HBYqQMVKjS-PAUq3GkNtGKlNnp/view?usp=sharing) `.exe`

## Demo (old version demo, features are still the same)

<img width="426" height="240" alt="490850390-c1134679-fed4-495e-ab40-450e05b199a9" src="https://github.com/user-attachments/assets/3234db06-2272-4a28-9a5a-b52b084e96a2" />


## Quick Start
1) Open epic seven and move to secret shop
2) Open app **AS ADMIN** (because stove opens the game with higher permissions)
3) Set the skystones (and gold) and run the bot

## Important To Note
- **Do not minimize the game** It should be open and the text in the shop should be a "readable" size (about 1/4 or 1/5 screen size is good)
- **Do not let your pc fall alseep** OCR uses the physical graphics to know what is in the shop to buy, the bot will continue running if your computer falls asleep and will not buy anything
- E7 can be behind other windows or games and the bot will run fine
- ~~Try not to run an auto farm in the background, e7 sends large data objects to its servers from your client(game) and on run completions stutters which can interupt the bot~~ (fixed with most recent server side only background battles update)


## Requirements for building from source
- Windows 10/11 (Win32 messages + Windows OCR)
- Epic Seven running (window title `Epic Seven`, class `GLFW30`)
- Python 3.10+ if running from source

## Setup

```powershell
cd E7ShopBot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install customtkinter pywin32 winsdk Pillow
```

There is no `requirements.txt` in the repo; those four packages are the runtime deps (`windows/gui.py` plus OCR/input).

## Run

Leave Epic Seven open (NOT minimized, but on another monitor is fine and behind other windows is okay). Then either launch the downloaded `E7ShopBot.exe`, or:

```powershell
python windows/gui.py
```

1. Set **Skystones to spend**. The app divides by 3 (cost per refresh) and shows **Total refreshes**.
2. If you want the gold safety net, leave **Gold limiter** on and enter **Starting gold**.
3. Hit **Start**. The bot refreshes, OCRs the shop, buys matches, scrolls, and repeats.
4. Hit **Stop** (or close the window) to cancel.

Live stats: refreshes done, purchase counts per item, and a stop reason (refresh limit, gold limit, or user).

CLI (no GUI, no gold/refresh limits; press `Q` to stop):

```powershell
python windows/main.py
```

If the game window is not found, the GUI shows "Window not found" and the CLI exits. Run `python windows/find_window.py` to print visible Epic Seven hwnd / title / class.

### Build the exe

```powershell
pip install pyinstaller
pyinstaller windows/E7ShopBot.spec
```

Output: `dist/E7ShopBot.exe` (windowed, icons from `LuaShakeicon.ico` / `LuaShakeicon.png`).

## How it works

```text
Find Epic Seven hwnd
→ refresh (click + confirm)
→ PrintWindow capture → Windows OCR → keyword match
→ buy (row Y from OCR, confirm) if Mystic Medal / Covenant Bookmark
→ scroll shop list
→ OCR + buy again
→ repeat until refresh limit, gold floor, or Stop
```

- **Clicks/scrolls** (`windows/input.py`): `PostMessage` `WM_MOUSEMOVE` + `WM_LBUTTONDOWN/UP` / `WM_MOUSEWHEEL` to the game hwnd. GLFW uses the last posted mouse position, so the physical cursor is left alone.
- **Capture** (`windows/ocr.py`): `PrintWindow(PW_RENDERFULLCONTENT)` so GPU/OpenGL windows work on any monitor (plain screen grab is black).
- **Buy** (`windows/actions.py`): Buy button X is a fixed relative coord (`BUY_BUTTON_RX`); Y comes from the matched OCR line.
- **Gold** is not read from the screen. You enter a starting amount; each buy subtracts a hardcoded cost. Without the GUI `stats` object (CLI), the gold limiter does nothing.


| Item              | Gold cost |
| ----------------- | --------- |
| Mystic Medal      | 280,000   |
| Covenant Bookmark | 184,000   |


Gold limiter default floor: **300,000**. Toggle it off in the GUI if you don't want that stop.

Tunable coords, delays, keywords, and costs live in `windows/config.py` (all click positions are 0.0–1.0 of the client area).

## Harness scripts

Scripts under `windows/ut/` talk to a live Epic Seven window. Run them from the repo root (`python windows/ut/test_buy.py`).


| Script                      | Purpose                                      |
| --------------------------- | -------------------------------------------- |
| `windows/find_window.py`    | List visible Epic Seven hwnd / title / class |
| `windows/ut/test_click.py`  | Calibrate relative clicks                    |
| `windows/ut/test_scroll.py` | Repeat `scroll_down` until `Q`               |
| `windows/ut/test_text.py`   | Capture + OCR the right half of the client   |
| `windows/ut/test_buy.py`    | OCR a target row and click its Buy button    |
| `windows/ut/test_gold.py`   | Experiment: crop/OCR the gold readout        |




## Known limitations

- **Windows only** — depends on Win32, Windows OCR, and the GLFW game window.
- **Layout-sensitive** — relative coords assume the Secret Shop UI; unusual resolutions or UI scale may miss buttons.
- **Gold is a local tally** — if Starting gold is wrong, the limiter stop point is wrong too.
- **OCR language** — Windows OCR uses the user profile languages; English shop text is what the keywords expect.
- **Exclusive fullscreen** — the window must be findable as `Epic Seven` / `GLFW30`; use windowed or borderless if FindWindow fails.



## Project layout

```text
windows/gui.py           # CustomTkinter app (primary entry)
windows/main.py          # CLI entry: find window → run_loop, Q to stop
windows/loop.py          # refresh → OCR/buy → scroll → OCR/buy
windows/actions.py       # do_refresh / do_buy / do_scroll
windows/ocr.py           # PrintWindow capture + Windows OCR
windows/input.py         # Win32 click + scroll primitives
windows/config.py        # coords, timing, keywords, item costs
windows/find_window.py   # list Epic Seven windows
windows/ut/              # live-window calibration harnesses
windows/E7ShopBot.spec   # PyInstaller build (if present)
mac/main.py              # CLI entry: find window → run_loop, Q to stop
mac/loop.py              # refresh → OCR/buy → scroll → OCR/buy (same as windows)
mac/actions.py           # do_refresh / do_buy / do_scroll
mac/capture.py           # CGWindowListCreateImage window screenshot
mac/ocr.py               # Vision-framework OCR
mac/input.py             # CGEventPost (HID tap) click + scroll primitives
mac/keys.py              # POSIX raw-mode "press Q to stop" (no msvcrt on Mac)
mac/config.py            # coords, timing, keywords, item costs
mac/window.py            # find Epic Seven window via CGWindowListCopyWindowInfo
mac/find_window.py       # list Epic Seven windows
mac/ut/                  # live-window calibration harnesses
LuaShakeicon.ico/.png    # app icons (repo root)
```

## Mac build

The Mac build mirrors the Windows pipeline (refresh → OCR/buy → scroll →
OCR/buy → repeat), but the underlying OS primitives are different:

```text
Find Epic Seven window (mac/window.py)
→ activate app (bring to foreground/key)
→ refresh (real HID click + confirm)
→ CGWindowListCreateImage capture → Vision OCR → keyword match
→ buy (row Y from OCR, confirm) if Mystic Medal / Covenant Bookmark
→ real HID scroll-wheel event
→ OCR + buy again
→ repeat until Q is pressed or Ctrl+C
```

**Key difference from Windows:** Epic Seven's Mac (iOS-wrapper) build only
reacts to real HID-level input events (`CGEventPost` via `kCGHIDEventTap`),
not process-local events (`CGEventPostToPid`) — confirmed via
`mac/ut/test_click.py`. That means, unlike the Windows build's invisible
`PostMessage` clicks, **the Mac bot visibly takes over your real mouse
cursor** while it runs, and requires the game window to be activated
(foreground/key) before each interaction. Because the mouse isn't free for
you to use, there's no clickable Stop button — instead, **press Q** in the
terminal running the bot to cancel at any time (`mac/keys.py`, using
POSIX raw-mode stdin reading instead of Windows' `msvcrt`).

### Setup

```bash
cd E7ShopBot/mac
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Permissions

Grant these to your terminal (or the `.venv/bin/python` binary) under
System Settings → Privacy & Security:
- **Accessibility** — required to post synthetic mouse/scroll events.
- **Screen Recording** — required for `CGWindowListCreateImage` to capture
  the game window; without it, captures come back black/empty.

### Run

```bash
python main.py
```

Press **Q** to stop.

### Calibration

The relative coordinates in `mac/config.py` are seeded from the Windows
values but **will need recalibration** — the Mac window's aspect ratio/chrome
differs from the Windows `GLFW30` window. Use:

| Script                     | Purpose                                                   |
| -------------------------- | ---------------------------------------------------------- |
| `mac/find_window.py`       | List the Epic Seven window's pid / bounds                  |
| `mac/ut/test_click.py`     | Fire a single click at a given `rx ry` (`--mode global`)    |
| `mac/ut/test_capture.py`   | Save a screenshot + print Vision OCR lines/rects            |
| `mac/ut/test_scroll.py`    | Repeat `scroll_down` every 1.5s until Q, to gauge scroll distance |

## Known limitations (Mac)

- **Takes over the real mouse** — clicks/scrolls move your actual cursor;
  don't touch the mouse while the bot is running.
- **Uncalibrated coordinates** — `mac/config.py`'s click/OCR regions are
  starting guesses ported from Windows values, not yet verified against a
  live window.
- **Vision OCR differences** — Apple's Vision framework may group/recognize
  shop text differently than Windows OCR did; keyword matches may need
  adjusting in `mac/config.py`.
- **No GUI yet** — `mac/main.py` is CLI-only (no gold/refresh limiter UI);
  press Q to stop.

