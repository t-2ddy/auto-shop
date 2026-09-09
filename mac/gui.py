import asyncio
import os
import sys
import threading
import time

import customtkinter as ctk
from PIL import Image

import config
from hotkey import GlobalQuitListener
from loop import run_loop
from resize import set_window_size
from window import GameWindow, find_game_window

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def _resource(rel: str) -> str:
    """Resolve a bundled resource path, working both from source and inside a
    PyInstaller-built app (where files are unpacked to sys._MEIPASS).

    Icons live at the repo root (one level above this file) when running from
    source; the frozen build unpacks them next to the app payload.
    """
    if getattr(sys, "_MEIPASS", None):
        return os.path.join(sys._MEIPASS, rel)
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(repo_root, rel)

_FONT         = ("Helvetica", 13)
_FONT_BOLD    = ("Helvetica", 13, "bold")
_FONT_TITLE   = ("Helvetica", 18, "bold")
_FONT_SMALL   = ("Helvetica", 11)
_FONT_STATUS  = ("Helvetica", 14, "bold")

SKYSTONES_PER_REFRESH = 3


class BotStats:
    """Shared mutable state between the GUI thread and the bot's asyncio thread."""

    def __init__(self) -> None:
        self.refresh_count = 0
        self.refresh_limit = 0  # 0 = unlimited
        self.purchases: dict[str, int] = {k: 0 for k in config.ITEM_KEYWORDS}
        self.gold = 0
        self.gold_limiter_enabled = True
        self.running = False
        self.stop_reason = ""


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title("E7 Secret Shop Bot")
        self.geometry("360x460")
        self.minsize(320, 400)
        self.resizable(True, True)

        icon_img = Image.open(_resource("LuaShakeicon.png"))
        icon_w, icon_h = 32, round(32 * icon_img.height / icon_img.width)
        self._title_icon = ctk.CTkImage(light_image=icon_img, dark_image=icon_img, size=(icon_w, icon_h))

        self.stats = BotStats()
        self._bot_thread: threading.Thread | None = None
        self._loop_task: asyncio.Task | None = None
        self._async_loop: asyncio.AbstractEventLoop | None = None
        self._quit_listener: GlobalQuitListener | None = None

        self._build_widgets()
        # Local Tk binding: only fires while this window itself is
        # frontmost/key, so it covers Start (pressed before the bot has
        # stolen focus) and skips typing in the numeric entry fields.
        self.bind("<space>", self._on_space_key)
        self.after(500, self._refresh_ui)

    def _build_widgets(self) -> None:
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(pady=(16, 8))

        ctk.CTkLabel(title_frame, image=self._title_icon, text="").pack(side="left", padx=(0, 8))
        ctk.CTkLabel(title_frame, text="E7 Secret Shop Bot", font=_FONT_TITLE).pack(side="left")

        status_frame = ctk.CTkFrame(self)
        status_frame.pack(fill="x", padx=16, pady=(0, 8))

        self.status_label = ctk.CTkLabel(
            status_frame, text="\u25cf Idle", font=_FONT_STATUS
        )
        self.status_label.pack(side="left", padx=12, pady=8)

        self.start_button = ctk.CTkButton(
            status_frame,
            text="Start",
            font=_FONT_BOLD,
            fg_color="#A78BFA",
            hover_color="#8B5CF6",
            command=self._on_start_stop,
        )
        self.start_button.pack(side="right", padx=12, pady=8)

        stones_frame = ctk.CTkFrame(self)
        stones_frame.pack(fill="x", padx=16, pady=(0, 8))

        stones_row = ctk.CTkFrame(stones_frame, fg_color="transparent")
        stones_row.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(stones_row, text="Skystones to spend", font=_FONT).pack(side="left")
        self.skystones_var = ctk.StringVar(value="300")
        self.skystones_var.trace_add("write", self._on_skystones_change)
        self.skystones_entry = ctk.CTkEntry(stones_row, width=90, textvariable=self.skystones_var, font=_FONT)
        self.skystones_entry.pack(side="right")

        allowed_row = ctk.CTkFrame(stones_frame, fg_color="transparent")
        allowed_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(allowed_row, text="Total refreshes", font=_FONT).pack(side="left")
        self.refreshes_allowed_label = ctk.CTkLabel(allowed_row, text="0", font=_FONT)
        self.refreshes_allowed_label.pack(side="right")
        self._on_skystones_change()

        done_row = ctk.CTkFrame(stones_frame, fg_color="transparent")
        done_row.pack(fill="x", padx=12, pady=(2, 10))
        ctk.CTkLabel(done_row, text="Refreshes done", font=_FONT).pack(side="left")
        self.refreshes_done_label = ctk.CTkLabel(done_row, text="0", font=_FONT)
        self.refreshes_done_label.pack(side="right")

        purchases_frame = ctk.CTkFrame(self)
        purchases_frame.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(
            purchases_frame, text="Purchases", font=_FONT_BOLD
        ).pack(anchor="w", padx=12, pady=(10, 4))

        self.purchase_labels: dict[str, ctk.CTkLabel] = {}
        for keyword in config.ITEM_KEYWORDS:
            row = ctk.CTkFrame(purchases_frame, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=2)
            ctk.CTkLabel(row, text=keyword.title(), font=_FONT).pack(side="left")
            count_label = ctk.CTkLabel(row, text="0", font=_FONT)
            count_label.pack(side="right")
            self.purchase_labels[keyword] = count_label

        ctk.CTkFrame(purchases_frame, fg_color="transparent", height=6).pack()

        limiter_frame = ctk.CTkFrame(self)
        limiter_frame.pack(fill="x", padx=16, pady=(0, 16))

        self.gold_limiter_var = ctk.BooleanVar(value=True)
        gold_check = ctk.CTkCheckBox(
            limiter_frame,
            text="Gold limiter",
            font=_FONT,
            variable=self.gold_limiter_var,
            command=self._on_gold_limiter_toggle,
        )
        gold_check.pack(anchor="w", padx=12, pady=(10, 0))

        ctk.CTkLabel(
            limiter_frame,
            text=f"Stops at {config.GOLD_MIN:,} gold",
            font=_FONT_SMALL,
            text_color="gray60",
        ).pack(anchor="w", padx=36, pady=(0, 4))

        gold_row = ctk.CTkFrame(limiter_frame, fg_color="transparent")
        gold_row.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(gold_row, text="Starting gold", font=_FONT).pack(side="left")
        self.starting_gold_var = ctk.StringVar(value="1000000")
        self.starting_gold_entry = ctk.CTkEntry(
            gold_row, width=90, textvariable=self.starting_gold_var, font=_FONT
        )
        self.starting_gold_entry.pack(side="right")

    def _on_skystones_change(self, *_args) -> None:
        raw = self.skystones_var.get().strip()
        try:
            skystones = int(raw) if raw else 0
        except ValueError:
            skystones = 0
        self.stats.refresh_limit = skystones // SKYSTONES_PER_REFRESH
        self.refreshes_allowed_label.configure(text=str(self.stats.refresh_limit))

    def _on_gold_limiter_toggle(self) -> None:
        self.stats.gold_limiter_enabled = self.gold_limiter_var.get()

    def _on_space_key(self, event) -> None:
        if self.focus_get() in (self.skystones_entry, self.starting_gold_entry):
            return
        self._on_start_stop()

    def _on_start_stop(self) -> None:
        if self.stats.running:
            self._stop_bot()
        else:
            self._start_bot()

    def _start_bot(self) -> None:
        win = find_game_window()
        if win is None:
            self.status_label.configure(
                text="\u25cf Window not found", text_color="red"
            )
            return

        if set_window_size(win, config.WINDOW_WIDTH, config.WINDOW_HEIGHT):
            time.sleep(0.3)  # let the resize settle before re-reading bounds
            resized_win = find_game_window()  # re-fetch: bounds changed after resize
            if resized_win is not None:
                win = resized_win

        raw_gold = self.starting_gold_var.get().strip()
        try:
            starting_gold = int(raw_gold) if raw_gold else 0
        except ValueError:
            starting_gold = 0

        self.stats.refresh_count = 0
        self.stats.purchases = {k: 0 for k in config.ITEM_KEYWORDS}
        self.stats.gold = starting_gold
        self.stats.stop_reason = ""
        self.stats.running = True

        self._bot_thread = threading.Thread(
            target=self._run_bot_thread, args=(win,), daemon=True
        )
        self._bot_thread.start()

        # activate_app() (mac/input.py) makes Epic Seven frontmost/key on every
        # click/scroll, which steals keyboard focus away from this window —
        # so the local <space> binding above stops seeing keystrokes once the
        # bot starts clicking. This system-wide listener (same mechanism the
        # CLI uses, mac/hotkey.py) catches Space regardless of which app is
        # frontmost; polled in _refresh_ui alongside the rest of the bot state.
        self._quit_listener = GlobalQuitListener()
        self._quit_listener.start()

        self.start_button.configure(text="Stop")
        self.status_label.configure(text="\u25cf Running", text_color="#2ecc71")

    def _run_bot_thread(self, win: GameWindow) -> None:
        self._async_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._async_loop)
        try:
            self._loop_task = self._async_loop.create_task(run_loop(win, self.stats))
            self._async_loop.run_until_complete(self._loop_task)
        finally:
            self.stats.running = False
            self._async_loop.close()

    def _stop_bot(self) -> None:
        if self._async_loop is not None and self._loop_task is not None:
            self._async_loop.call_soon_threadsafe(self._loop_task.cancel)
        self.stats.stop_reason = self.stats.stop_reason or "user"
        self._stop_quit_listener()

    def _stop_quit_listener(self) -> None:
        if self._quit_listener is not None:
            self._quit_listener.stop()
            self._quit_listener = None

    def _refresh_ui(self) -> None:
        self.refreshes_done_label.configure(text=str(self.stats.refresh_count))
        for keyword, label in self.purchase_labels.items():
            label.configure(text=str(self.stats.purchases.get(keyword, 0)))

        # System-wide Space press (see _start_bot) — checked here since the
        # listener's CGEventTap callback runs on its own background thread
        # and shouldn't touch Tk widgets directly.
        if (
            self.stats.running
            and self._quit_listener is not None
            and self._quit_listener.quit_event.is_set()
        ):
            self._stop_bot()

        if not self.stats.running and self.start_button.cget("text") == "Stop":
            self.start_button.configure(text="Start")
            self._stop_quit_listener()
            if self.stats.stop_reason == "gold limit":
                self.status_label.configure(text="\u25cf Stopped (gold limit)", text_color="pink")
            elif self.stats.stop_reason == "refresh limit":
                self.status_label.configure(text="\u25cf Stopped (refresh limit)", text_color="violet")
            else:
                self.status_label.configure(text="\u25cf Idle", text_color="gray60")

        self.after(500, self._refresh_ui)


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
