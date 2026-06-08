"""Native desktop shell for the Maze Lab web UI.

This renders ``web/index.html`` inside a real application window using
`pywebview <https://pywebview.flowrl.com/>`_, so the polished browser design
(gradients, rounded cards, animations, the Tweaks panel) becomes a genuine
desktop app instead of a browser tab.

Design note
-----------
The pure-Python engine (``graph_algorithms`` + ``maze``) still powers the CLI
(``maze_runner.py``), the Tkinter GUI (``maze_gui.py``) and the test-suite.
The web shell ships a faithful JavaScript port of the same seven algorithms,
so this window runs fully offline with no backend process — nothing here calls
out to a server.

Usage
-----
    python3 desktop.py
    # or, once installed as a package:  maze-desktop

Requires the optional dependency::

    python3 -m pip install pywebview
"""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "web" / "index.html"

# Matches the web UI's --bg so there is no white flash before the page paints.
WINDOW_BG = "#16161c"


def run() -> int:
    """Open the Maze Lab desktop window.  Returns a process exit code."""
    try:
        import webview
    except ImportError:
        sys.stderr.write(
            "\nMaze Lab desktop needs the optional 'pywebview' package.\n\n"
            "Install it with:\n"
            "    python3 -m pip install pywebview\n\n"
            "On macOS it uses the built-in WebKit, so no extra browser or\n"
            "driver is required.  (The Tkinter app still works without it:\n"
            "    python3 maze_gui.py)\n\n"
        )
        return 1

    if not INDEX.exists():
        sys.stderr.write(f"Cannot find the web UI at: {INDEX}\n")
        return 1

    webview.create_window(
        "Maze Lab",
        url=INDEX.as_uri(),
        width=1280,
        height=860,
        min_size=(1024, 720),
        background_color=WINDOW_BG,
    )
    webview.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
