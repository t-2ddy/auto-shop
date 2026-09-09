"""Print installed path, running process, and CG windows for Epic Seven.

Run from the repo root:
    python mac/find_window.py
"""

from window import find_game_window, find_installed_app, find_running_app, list_windows


def main() -> None:
    installed = find_installed_app()
    if installed is None:
        print("installed: not found")
    else:
        print(f"installed: {installed}")

    app = find_running_app()
    if app is None:
        print("running: no")
        print("window: not found (launch Epic Seven first)")
        return

    print(
        f"running: yes  pid={app.pid}  name={app.name!r}  "
        f"bundle_id={app.bundle_id!r}"
    )
    if app.path:
        print(f"bundle path: {app.path}")

    windows = list_windows(app.pid)
    if not windows:
        print("windows: none")
        return

    chosen = find_game_window()
    print(f"windows: {len(windows)}")
    for win in windows:
        mark = "  <- game" if chosen is not None and win.window_id == chosen.window_id else ""
        title = win.title or "(untitled)"
        onscreen = "on" if win.onscreen else "off"
        print(
            f"  id={win.window_id}  {win.width:.0f}x{win.height:.0f} "
            f"@ ({win.x:.0f},{win.y:.0f})  {onscreen}screen  "
            f"layer={win.layer}  share={win.sharing_state}  "
            f"title={title!r}{mark}"
        )


if __name__ == "__main__":
    main()
