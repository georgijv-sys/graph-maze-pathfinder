"""Interactive Tkinter GUI for the graph maze pathfinder."""

from __future__ import annotations

import csv
from pathlib import Path
import random
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional, Tuple

from graph_algorithms import SearchResult, solve_maze
from maze import (
    Maze,
    Position,
    add_random_weights,
    create_perfect_maze,
    get_walls,
    load_maze,
    save_maze,
)


ROOT = Path(__file__).resolve().parent
SAMPLE_FILES = [
    ROOT / "sample_mazes" / "small_maze1.mz",
    ROOT / "sample_mazes" / "maze1.mz",
    ROOT / "sample_mazes" / "maze2.mz",
    ROOT / "sample_mazes" / "weighted_maze.mz",
]
ALGORITHMS: Dict[str, str] = {
    "A*":                "astar",
    "Dijkstra":          "dijkstra",
    "Bellman-Ford":      "bellmanford",
    "Greedy Best-First": "greedy",
    "Bidirectional BFS": "bidirectional",
    "BFS":               "bfs",
    "DFS":               "dfs",
}
NON_COST_OPTIMAL_WEIGHTED = {"bfs", "dfs", "bidirectional", "greedy"}
ALGORITHM_INFO: Dict[str, Dict[str, str]] = {
    "A*": {
        "meta": "O(E log V)  ·  space O(V)  ·  optimal",
        "about": "Combines cost-so-far with a Manhattan heuristic (f = g + h). "
                 "Gold standard for grid pathfinding — optimal and much faster than Dijkstra.",
    },
    "Dijkstra": {
        "meta": "O(E log V)  ·  space O(V)  ·  optimal",
        "about": "Expands cells by cumulative cost via a min-heap. No heuristic, "
                 "so it explores every candidate within the cost boundary.",
    },
    "Bellman-Ford": {
        "meta": "O(V · E)  ·  space O(V)  ·  optimal",
        "about": "Relaxes every edge V−1 times. The textbook method that also "
                 "handles negative edges in general graphs — though this grid's "
                 "cell costs are always positive, so here it matches Dijkstra's "
                 "result, just slower.",
    },
    "Greedy Best-First": {
        "meta": "O(E log V)  ·  space O(V)  ·  not optimal",
        "about": "Rushes toward the goal using only the heuristic, ignoring "
                 "path cost. Very fast in open corridors, not cost-optimal.",
    },
    "Bidirectional BFS": {
        "meta": "O(b^(d/2))  ·  space O(b^(d/2))  ·  optimal (unweighted)",
        "about": "Two BFS frontiers expand from start and goal simultaneously "
                 "and meet in the middle, halving the search space.",
    },
    "BFS": {
        "meta": "O(V + E)  ·  space O(V)  ·  optimal (unweighted)",
        "about": "Explores layer-by-layer in order of hop count. Shortest "
                 "unweighted path guaranteed; ignores weighted terrain costs.",
    },
    "DFS": {
        "meta": "O(V + E)  ·  space O(V)  ·  not optimal",
        "about": "Dives as deep as possible before backtracking. Finds a path "
                 "quickly but rarely the shortest — great for visualising exploration.",
    },
}
EDIT_MODES: List[Tuple[str, str]] = [
    ("navigate",   "Navigate"),
    ("draw_wall",  "Draw"),
    ("erase",      "Erase"),
    ("set_start",  "Start"),
    ("set_goal",   "Goal"),
    ("add_weight", "Weight"),
]


# ── Design tokens ─────────────────────────────────────────────────────────────
#
# Colours follow the Tailwind CSS "Slate + Indigo" system used across shadcn/ui
# and most modern developer tools; the layout follows Refactoring UI principles
# (Adam Wathan & Steve Schoger): a constrained spacing scale, generous
# whitespace, hierarchy through size/weight/colour, and a single restrained
# accent.  Typography uses two families — a clean UI sans and a mono for stats.

UI_FONT   = "Helvetica Neue"   # ships on every macOS; crisp neutral sans
MONO_FONT = "Menlo"            # for column-aligned statistics

# Constrained spacing scale (px): 4 · 8 · 12 · 16 · 20 · 24
SIDE_PAD  = 18                 # horizontal breathing room inside the sidebar


class P:
    # ── Content surfaces (light) ─────────────────────────────────────────────
    page         = "#eef2f7"   # app background, a cool slate tint
    card_bg      = "#ffffff"   # raised cards (maze, stats, chips)
    card_border  = "#e2e8f0"   # slate-200 hairline borders
    ink          = "#0f172a"   # slate-900 primary text
    ink_muted    = "#64748b"   # slate-500 secondary text
    ink_soft     = "#94a3b8"   # slate-400 tertiary text
    shadow       = "#d4dbe6"   # soft drop-shadow tone

    # ── Sidebar (dark slate) ─────────────────────────────────────────────────
    side         = "#0f172a"   # slate-900 sidebar background
    side2        = "#1e293b"   # slate-800 inputs / raised surface
    side_border  = "#334155"   # slate-700 input borders
    side_line    = "#1e293b"   # subtle separators
    side_hover   = "#334155"   # slate-700 hover
    text         = "#f1f5f9"   # slate-100
    muted        = "#94a3b8"   # slate-400
    dim          = "#64748b"   # slate-500

    # ── Accent (indigo) ──────────────────────────────────────────────────────
    accent       = "#6366f1"   # indigo-500
    accent_dk    = "#4f46e5"   # indigo-600 (hover / pressed)
    accent_lt    = "#a5b4fc"   # indigo-300 (meta text on dark)

    # ── Canvas / maze ────────────────────────────────────────────────────────
    canvas_bg    = "#ffffff"
    cell_open    = "#f8fafc"   # slate-50
    cell_grid    = "#e2e8f0"
    cell_blocked = "#334155"   # slate-700 solid obstacles
    wall_color   = "#334155"   # slate-700 maze walls
    # Algorithmic colours
    discovered   = "#bfdbfe"   # blue-200 explored frontier
    path_fill    = "#fde68a"   # amber-200 path cells
    path_line    = "#d97706"   # amber-600 path ribbon
    start_fill   = "#10b981"   # emerald-500
    goal_fill    = "#ef4444"   # red-500
    weighted_bg  = "#ede9fe"   # violet-100 weighted terrain
    runner_fill  = "#6366f1"   # indigo-500
    white        = "#ffffff"
    black        = "#000000"

    # ── KPI chips (light) ────────────────────────────────────────────────────
    chip_bg      = "#ffffff"
    chip_border  = "#e2e8f0"
    chip_label   = "#64748b"
    chip_value   = "#0f172a"

    # ── Status text states ───────────────────────────────────────────────────
    status_info    = "#64748b"
    status_running = "#4f46e5"
    status_success = "#059669"
    status_error   = "#dc2626"


# ── App ───────────────────────────────────────────────────────────────────────

class MazeApp:
    def __init__(self, root: tk.Tk, initial_maze_path: Optional[str] = None):
        self.root = root
        self.root.title("Maze Lab")
        self.root.minsize(1180, 820)
        self._set_initial_window_size(1280, 880)
        self.root.configure(bg=P.page)

        # State vars
        self.algo_var    = tk.StringVar(value="A*")
        self.sample_var  = tk.StringVar(value=SAMPLE_FILES[0].name if SAMPLE_FILES else "")
        self.width_var   = tk.IntVar(value=18)
        self.height_var  = tk.IntVar(value=12)
        self.seed_var    = tk.StringVar(value="")
        self.density_var = tk.IntVar(value=25)
        self.speed_var   = tk.IntVar(value=65)
        self.heatmap_var = tk.BooleanVar(value=False)
        self.edit_mode   = tk.StringVar(value="navigate")
        self.status_var  = tk.StringVar(value="")

        # Runtime state
        self.last_path: Optional[Path] = None
        self.maze         = self._load_initial_maze(initial_maze_path)
        self.result:       Optional[SearchResult] = None
        self.animation_id: Optional[str] = None

        self.display_visited: List[Position] = []
        self.display_path:    List[Position] = []
        self.display_runner:  Optional[Position] = None
        self.display_dir      = "N"

        self._step_result:   Optional[SearchResult] = None
        self._step_index     = 0
        self._drag_blocking: Optional[bool] = None
        self._no_path_banner = False

        self.cell_size = 28
        self.margin    = 18
        self.origin_x  = self.margin
        self.origin_y  = self.margin

        self._edit_btns: Dict[str, tk.Label] = {}
        self.metric_chips: Dict[str, tk.Label] = {}

        self._configure_styles()
        self._build_ui()
        self._bind_keys()
        self._reset("Ready — load or generate a maze, then solve or animate.")

    # ── TTK style ─────────────────────────────────────────────────────────────

    def _configure_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")

        # Combobox: dark field, comfortable padding, indigo focus.
        style.configure("Sidebar.TCombobox",
                        fieldbackground=P.side2,
                        background=P.side2,
                        foreground=P.text,
                        selectbackground=P.side2,
                        selectforeground=P.text,
                        bordercolor=P.side_border,
                        lightcolor=P.side_border,
                        darkcolor=P.side_border,
                        arrowcolor=P.muted,
                        padding=7)
        style.map("Sidebar.TCombobox",
                  fieldbackground=[("readonly", P.side2)],
                  bordercolor=[("focus", P.accent), ("hover", P.side_hover)],
                  arrowcolor=[("active", P.text)])

        # Matching dark dropdown list for both comboboxes.
        self.root.option_add("*TCombobox*Listbox.background", P.side2)
        self.root.option_add("*TCombobox*Listbox.foreground", P.text)
        self.root.option_add("*TCombobox*Listbox.selectBackground", P.accent)
        self.root.option_add("*TCombobox*Listbox.selectForeground", P.white)
        self.root.option_add("*TCombobox*Listbox.font", (UI_FONT, 10))
        self.root.option_add("*TCombobox*Listbox.borderWidth", 0)

        # Slim sidebar scrollbar.
        style.configure("Sidebar.Vertical.TScrollbar",
                        background=P.side_border, troughcolor=P.side,
                        bordercolor=P.side, arrowcolor=P.side,
                        relief="flat", width=9)
        style.map("Sidebar.Vertical.TScrollbar",
                  background=[("active", P.side_hover)])
        # Spinbox and Scale use tk widgets directly — no ttk style needed

    def _set_initial_window_size(self, width: int, height: int) -> None:
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = min(width, max(1060, screen_width - 80))
        height = min(height, max(760, screen_height - 100))
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = tk.Frame(self.root, bg=P.page)
        outer.pack(fill="both", expand=True)

        # Sidebar — fixed width, vertically scrollable so nothing ever clips.
        side = tk.Frame(outer, bg=P.side, width=270)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        scroll_body = self._make_scrollable(side)

        # Stage (canvas area)
        stage = tk.Frame(outer, bg=P.page)
        stage.pack(side="left", fill="both", expand=True)

        self._build_sidebar(scroll_body)
        self._build_stage(stage)

    def _make_scrollable(self, parent: tk.Frame) -> tk.Frame:
        """Return an inner frame that scrolls vertically inside ``parent``."""
        canvas = tk.Canvas(parent, bg=P.side, highlightthickness=0, bd=0)
        vsb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview,
                            style="Sidebar.Vertical.TScrollbar")
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=P.side)
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))
        inner.bind("<Configure>",
                   lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))

        def _wheel(event: tk.Event) -> str:
            canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
            return "break"   # don't also bubble to spinboxes / comboboxes

        canvas.bind("<MouseWheel>", _wheel)
        self._scroll_canvas = canvas
        self._wheel_handler = _wheel
        return inner

    def _bind_mousewheel(self, widget: tk.Widget) -> None:
        """Recursively route mouse-wheel events on the sidebar to its scroller."""
        widget.bind("<MouseWheel>", self._wheel_handler)
        for child in widget.winfo_children():
            self._bind_mousewheel(child)

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self, p: tk.Frame) -> None:
        # ── App header ───────────────────────────────────────────────────────
        hdr = tk.Frame(p, bg=P.side)
        hdr.pack(fill="x", padx=SIDE_PAD, pady=(24, 4))
        title_row = tk.Frame(hdr, bg=P.side)
        title_row.pack(anchor="w")
        # Small accent mark next to the wordmark.
        mark = tk.Canvas(title_row, width=22, height=22, bg=P.side,
                         highlightthickness=0)
        mark.create_rectangle(2, 2, 20, 20, fill=P.accent, outline="")
        mark.create_line(6, 15, 11, 15, 11, 7, 16, 7,
                         fill=P.white, width=2, capstyle="round", joinstyle="round")
        mark.pack(side="left", padx=(0, 9))
        tk.Label(title_row, text="Maze Lab", font=(UI_FONT, 18, "bold"),
                 bg=P.side, fg=P.text).pack(side="left")
        tk.Label(hdr, text="graph pathfinding visualiser",
                 font=(UI_FONT, 9), bg=P.side, fg=P.dim).pack(anchor="w", pady=(3, 0))

        # ── Algorithm ────────────────────────────────────────────────────────
        self._sh(p, "ALGORITHM")
        algo_combo = ttk.Combobox(
            p, textvariable=self.algo_var,
            values=list(ALGORITHMS), state="readonly",
            font=(UI_FONT, 11), style="Sidebar.TCombobox",
        )
        algo_combo.pack(fill="x", padx=SIDE_PAD, pady=(0, 8))
        algo_combo.bind("<<ComboboxSelected>>", self._on_algo_change)

        self._algo_meta = tk.Label(p, text="", bg=P.side, fg=P.accent_lt,
                                    font=(MONO_FONT, 8), wraplength=222, justify="left")
        self._algo_meta.pack(anchor="w", padx=SIDE_PAD)
        self._algo_desc = tk.Label(p, text="", bg=P.side, fg=P.muted,
                                    font=(UI_FONT, 9), wraplength=222, justify="left")
        self._algo_desc.pack(anchor="w", padx=SIDE_PAD, pady=(4, 0))
        self._refresh_algo_info()

        # ── Run (primary actions, surfaced near the top) ─────────────────────
        self._sh(p, "RUN")
        self._btn(p, "Solve", self.solve, primary=True, accel="S").pack(
            fill="x", padx=SIDE_PAD, pady=(0, 7))

        r2 = tk.Frame(p, bg=P.side)
        r2.pack(fill="x", padx=SIDE_PAD, pady=(0, 6))
        self._btn(r2, "Animate", self.animate, accel="A").pack(
            side="left", expand=True, fill="x")
        self._btn(r2, "Step", self.step, accel="Space").pack(
            side="left", expand=True, fill="x", padx=(6, 0))

        r3 = tk.Frame(p, bg=P.side)
        r3.pack(fill="x", padx=SIDE_PAD, pady=(0, 10))
        self._btn(r3, "Compare", self.compare_all).pack(
            side="left", expand=True, fill="x")
        self._btn(r3, "Reset", lambda: self._reset("View reset."), accel="R").pack(
            side="left", expand=True, fill="x", padx=(6, 0))

        self._slider(p, "Animation speed", 10, 120, self.speed_var)

        hm = tk.Frame(p, bg=P.side)
        hm.pack(fill="x", padx=SIDE_PAD - 2, pady=(8, 0))
        tk.Checkbutton(hm, text="  Heatmap (discovery order)",
                       variable=self.heatmap_var, command=self.draw,
                       bg=P.side, fg=P.muted, activebackground=P.side,
                       activeforeground=P.text, selectcolor=P.side2,
                       highlightthickness=0, bd=0,
                       font=(UI_FONT, 9)).pack(side="left")

        # ── Maze generation ──────────────────────────────────────────────────
        self._sh(p, "MAZE")
        sz = tk.Frame(p, bg=P.side)
        sz.pack(fill="x", padx=SIDE_PAD, pady=(0, 8))
        for lbl, var, hi in [("W", self.width_var, 40), ("H", self.height_var, 26)]:
            tk.Label(sz, text=lbl, bg=P.side, fg=P.dim,
                     font=(UI_FONT, 9, "bold")).pack(side="left", padx=(0, 4))
            self._spin(sz, 5, hi, var).pack(side="left", padx=(0, 12))
        tk.Label(sz, text="Seed", bg=P.side, fg=P.dim,
                 font=(UI_FONT, 9, "bold")).pack(side="left", padx=(0, 4))
        tk.Entry(sz, textvariable=self.seed_var, width=6,
                 bg=P.side2, fg=P.text, insertbackground=P.accent,
                 font=(UI_FONT, 10), relief="flat", bd=0,
                 highlightthickness=1, highlightbackground=P.side_border,
                 highlightcolor=P.accent).pack(side="left", ipady=4)

        r = tk.Frame(p, bg=P.side)
        r.pack(fill="x", padx=SIDE_PAD, pady=(0, 4))
        self._btn(r, "Generate", lambda: self.generate(False)).pack(
            side="left", expand=True, fill="x")
        self._btn(r, "+ Weighted", lambda: self.generate(True)).pack(
            side="left", expand=True, fill="x", padx=(6, 0))

        self._slider(p, "Weight density", 5, 70, self.density_var, suffix="%")

        # ── Draw tools ───────────────────────────────────────────────────────
        self._sh(p, "DRAW", hint="click or drag on the maze")
        eg = tk.Frame(p, bg=P.side)
        eg.pack(fill="x", padx=SIDE_PAD, pady=(0, 4))
        for col in range(3):
            eg.columnconfigure(col, weight=1, uniform="draw")
        for i, (mode, label) in enumerate(EDIT_MODES):
            row, col = divmod(i, 3)
            b = self._click_label(
                eg, label,
                lambda _event, m=mode: self._set_mode(m),
                bg=P.side2, hover_bg=P.side_hover,
                font=(UI_FONT, 9), padx=4, pady=7,
            )
            b.grid(row=row, column=col,
                   padx=(0 if col == 0 else 6, 0), pady=(0, 6), sticky="ew")
            self._edit_btns[mode] = b
        self._set_mode("navigate")

        # ── Files ────────────────────────────────────────────────────────────
        self._sh(p, "FILES")
        samples = [f.name for f in SAMPLE_FILES if f.exists()]
        sample_combo = ttk.Combobox(p, textvariable=self.sample_var,
                                    values=samples, state="readonly",
                                    font=(UI_FONT, 10), style="Sidebar.TCombobox")
        sample_combo.pack(fill="x", padx=SIDE_PAD, pady=(0, 8))

        r4 = tk.Frame(p, bg=P.side)
        r4.pack(fill="x", padx=SIDE_PAD, pady=(0, 6))
        self._btn(r4, "Load Sample", self.load_sample).pack(
            side="left", expand=True, fill="x")
        self._btn(r4, "Open…", self.browse).pack(
            side="left", expand=True, fill="x", padx=(6, 0))

        r5 = tk.Frame(p, bg=P.side)
        r5.pack(fill="x", padx=SIDE_PAD, pady=(0, 6))
        self._btn(r5, "New Blank", self.new_blank).pack(
            side="left", expand=True, fill="x")
        self._btn(r5, "Save…", self.save_maze_file).pack(
            side="left", expand=True, fill="x", padx=(6, 0))

        self._btn(p, "Export Run", self.export_run).pack(
            fill="x", padx=SIDE_PAD, pady=(0, 18))

        # Route trackpad / wheel scrolling on every control to the scroller.
        self._bind_mousewheel(p)

    # ── Stage ─────────────────────────────────────────────────────────────────

    def _build_stage(self, p: tk.Frame) -> None:
        # ── Top bar: status on the left, KPI chips on the right ──────────────
        topbar = tk.Frame(p, bg=P.page, height=84)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        self._status_lbl = tk.Label(
            topbar, textvariable=self.status_var,
            bg=P.page, fg=P.status_info,
            font=(UI_FONT, 12), wraplength=440, justify="left")
        self._status_lbl.pack(side="left", padx=22, pady=20)

        chips = tk.Frame(topbar, bg=P.page)
        chips.pack(side="right", padx=18, pady=16)
        for key, label in [("algorithm", "Algorithm"), ("explored", "Explored"),
                            ("length", "Length"), ("cost", "Cost"), ("weights", "Weights")]:
            card = tk.Frame(chips, bg=P.chip_bg,
                            highlightthickness=1, highlightbackground=P.chip_border)
            card.pack(side="left", padx=(0, 8))
            tk.Label(card, text=label.upper(), bg=P.chip_bg, fg=P.chip_label,
                     font=(UI_FONT, 7, "bold")).pack(padx=13, pady=(8, 0), anchor="w")
            val = tk.Label(card, text="—", bg=P.chip_bg, fg=P.chip_value,
                           font=(UI_FONT, 15, "bold"))
            val.pack(padx=13, pady=(0, 8), anchor="w")
            self.metric_chips[key] = val

        # Divider under the top bar.
        tk.Frame(p, bg=P.card_border, height=1).pack(fill="x")

        content = tk.Frame(p, bg=P.page)
        content.pack(fill="both", expand=True)

        # ── Maze canvas, presented as a floating white card ──────────────────
        card = tk.Frame(content, bg=P.canvas_bg,
                        highlightthickness=1, highlightbackground=P.card_border)
        card.pack(side="left", fill="both", expand=True, padx=(18, 9), pady=16)
        self.canvas = tk.Canvas(card, bg=P.canvas_bg, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _e: self.draw())
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>", self._on_right_click)

        # ── Run-stats card on the right ──────────────────────────────────────
        stats_panel = tk.Frame(content, bg=P.card_bg, width=252,
                               highlightthickness=1, highlightbackground=P.card_border)
        stats_panel.pack(side="right", fill="y", padx=(9, 18), pady=16)
        stats_panel.pack_propagate(False)
        tk.Label(stats_panel, text="Run Stats", bg=P.card_bg, fg=P.ink,
                 font=(UI_FONT, 13, "bold")).pack(anchor="w", padx=18, pady=(18, 10))
        tk.Frame(stats_panel, bg=P.card_border, height=1).pack(
            fill="x", padx=18, pady=(0, 12))
        self._stats_lbl = tk.Label(
            stats_panel, text="", bg=P.card_bg, fg="#475569",
            font=(MONO_FONT, 9), wraplength=210, justify="left",
        )
        self._stats_lbl.pack(anchor="nw", fill="x", padx=18, pady=(0, 16))

    # ── Sidebar widget helpers ────────────────────────────────────────────────

    def _sh(self, p: tk.Widget, text: str, hint: Optional[str] = None) -> None:
        """Section header: an accent tick, an uppercase label, an optional hint."""
        row = tk.Frame(p, bg=P.side)
        row.pack(fill="x", padx=SIDE_PAD, pady=(20, 9))
        tick = tk.Canvas(row, width=3, height=13, bg=P.accent, highlightthickness=0)
        tick.pack(side="left", padx=(0, 9), pady=1)
        tk.Label(row, text=text, bg=P.side, fg=P.muted,
                 font=(UI_FONT, 9, "bold")).pack(side="left")
        if hint:
            tk.Label(row, text=hint, bg=P.side, fg=P.dim,
                     font=(UI_FONT, 8)).pack(side="left", padx=(8, 0))

    def _btn(self, parent: tk.Widget, text: str, command,
             *, primary: bool = False, accel: Optional[str] = None) -> tk.Frame:
        """A filled button.  ``primary`` uses the accent; ``accel`` adds a keycap."""
        bg     = P.accent    if primary else P.side2
        hover  = P.accent_dk if primary else P.side_hover
        cap_bg = P.accent_dk if primary else P.side
        cap_fg = P.accent_lt if primary else P.muted
        weight = "bold" if primary else "normal"

        frame = tk.Frame(parent, bg=bg, cursor="hand2")
        label = tk.Label(frame, text=text, bg=bg, fg=P.white,
                         font=(UI_FONT, 11, weight), pady=10)
        label.pack(side="left", fill="both", expand=True)
        cap = None
        if accel:
            cap = tk.Label(frame, text=accel, bg=cap_bg, fg=cap_fg,
                           font=(UI_FONT, 8, "bold"), padx=6, pady=2)
            cap.pack(side="right", padx=8)

        targets = [frame, label] + ([cap] if cap else [])
        for w in targets:
            w.bind("<Button-1>", lambda _e: command())
            w.bind("<Enter>", lambda _e: (frame.configure(bg=hover),
                                          label.configure(bg=hover)))
            w.bind("<Leave>", lambda _e: (frame.configure(bg=bg),
                                          label.configure(bg=bg)))
        return frame

    def _spin(self, parent: tk.Widget, frm: int, to: int, var: tk.Variable) -> tk.Spinbox:
        return tk.Spinbox(
            parent, from_=frm, to=to, textvariable=var, width=4,
            bg=P.side2, fg=P.text, insertbackground=P.accent,
            buttonbackground=P.side2, readonlybackground=P.side2,
            relief="flat", bd=0, highlightthickness=1,
            highlightbackground=P.side_border, highlightcolor=P.accent,
            font=(UI_FONT, 10),
        )

    def _slider(self, parent: tk.Widget, label: str, frm: int, to: int,
                var: tk.IntVar, suffix: str = "") -> None:
        """A labelled slider with a live numeric read-out on the right."""
        head = tk.Frame(parent, bg=P.side)
        head.pack(fill="x", padx=SIDE_PAD, pady=(8, 0))
        tk.Label(head, text=label, bg=P.side, fg=P.dim,
                 font=(UI_FONT, 8, "bold")).pack(side="left")
        value = tk.Label(head, text=f"{var.get()}{suffix}", bg=P.side,
                         fg=P.muted, font=(MONO_FONT, 9))
        value.pack(side="right")
        tk.Scale(
            parent, from_=frm, to=to, variable=var, orient="horizontal",
            bg=P.side, fg=P.muted, troughcolor=P.side_border,
            activebackground=P.accent, highlightthickness=0, bd=0,
            sliderrelief="flat", showvalue=False, width=12, sliderlength=20,
            command=lambda v: value.configure(text=f"{int(float(v))}{suffix}"),
        ).pack(fill="x", padx=SIDE_PAD, pady=(3, 0))

    def _click_label(
        self,
        parent: tk.Widget,
        text: str,
        command,
        *,
        bg: str = P.side_border,
        hover_bg: str = P.side_hover,
        font=(UI_FONT, 10),
        padx: int = 10,
        pady: int = 8,
    ) -> tk.Label:
        label = tk.Label(
            parent,
            text=text,
            bg=bg,
            fg=P.white,
            font=font,
            padx=padx,
            pady=pady,
            cursor="hand2",
        )
        label.bind("<Button-1>", command)
        label.bind("<Enter>", lambda _event: label.configure(bg=hover_bg))
        label.bind("<Leave>", lambda _event: label.configure(bg=bg))
        return label

    # ── Edit mode ─────────────────────────────────────────────────────────────

    def _set_mode(self, mode: str) -> None:
        self.edit_mode.set(mode)
        for key, btn in self._edit_btns.items():
            active = key == mode
            bg    = P.accent    if active else P.side2
            hover = P.accent_dk if active else P.side_hover
            btn.configure(bg=bg, fg=P.white if active else P.text)
            # Rebind both Enter and Leave so the active button keeps a sensible
            # highlight instead of reverting to the inactive grey on hover.
            btn.bind("<Enter>", lambda _event, b=btn, c=hover: b.configure(bg=c))
            btn.bind("<Leave>", lambda _event, b=btn, c=bg: b.configure(bg=c))
        if hasattr(self, "canvas"):
            self.canvas.configure(cursor="crosshair" if mode != "navigate" else "")

    def _on_click(self, e: tk.Event) -> None:
        pos = self._px_to_cell(e.x, e.y)
        if pos is None:
            return
        mode = self.edit_mode.get()
        if mode == "draw_wall":
            self._drag_blocking = pos not in self.maze.blocked
        elif mode == "erase":
            self._drag_blocking = True
        self._apply_edit(pos)

    def _on_drag(self, e: tk.Event) -> None:
        self._apply_edit(self._px_to_cell(e.x, e.y), drag=True)

    def _on_release(self, _: tk.Event) -> None:
        self._drag_blocking = None

    def _on_right_click(self, e: tk.Event) -> None:
        pos = self._px_to_cell(e.x, e.y)
        if pos is None:
            return
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Set as Start", command=lambda: self._set_start(pos))
        menu.add_command(label="Set as Goal",  command=lambda: self._set_goal(pos))
        menu.add_separator()
        menu.add_command(label="Block cell",   command=lambda: self._block(pos))
        menu.add_command(label="Clear cell",   command=lambda: self._unblock(pos))
        cw = self.maze.weights.get(pos, 1)
        menu.add_command(label=f"Cycle weight (now {cw}×)",
                         command=lambda: self._cycle_weight(pos))
        menu.tk_popup(e.x_root, e.y_root)

    def _apply_edit(self, pos: Optional[Position], drag: bool = False) -> None:
        if pos is None:
            return
        mode = self.edit_mode.get()
        if mode == "navigate":
            return
        if mode == "draw_wall":
            if drag and self._drag_blocking is False:
                return
            self._block(pos)
        elif mode == "erase":
            self._unblock(pos)
        elif mode == "set_start" and not drag:
            self._set_start(pos)
        elif mode == "set_goal" and not drag:
            self._set_goal(pos)
        elif mode == "add_weight" and not drag:
            self._cycle_weight(pos)

    def _block(self, pos: Position) -> None:
        if pos in {self.maze.start, self.maze.goal}:
            return
        self.maze.blocked.add(pos)
        self.maze.weights.pop(pos, None)
        self._invalidate()

    def _unblock(self, pos: Position) -> None:
        self.maze.clear_cell(pos, remove_adjacent_walls=True)
        self._invalidate()

    def _set_start(self, pos: Position) -> None:
        if pos == self.maze.goal:
            return
        self.maze.clear_cell(pos)
        self.maze.start = pos
        self._invalidate()

    def _set_goal(self, pos: Position) -> None:
        if pos == self.maze.start:
            return
        self.maze.clear_cell(pos)
        self.maze.goal = pos
        self._invalidate()

    def _cycle_weight(self, pos: Position) -> None:
        if not self.maze.is_open(pos) or pos in {self.maze.start, self.maze.goal}:
            return
        cur = self.maze.weights.get(pos, 1)
        if cur < 9:
            self.maze.weights[pos] = max(2, cur + 1)
        else:
            self.maze.weights.pop(pos, None)
        self._invalidate()

    def _invalidate(self) -> None:
        self._cancel_anim()
        self.result = self._step_result = None
        self._step_index = 0
        self._no_path_banner = False
        self.display_visited = self.display_path = []
        self.display_runner = None
        self._clear_chips()
        self._set_status("Maze edited — press Solve or Animate.", kind="info")
        self._update_stats(self._maze_summary())
        self.draw()

    def _px_to_cell(self, px: int, py: int) -> Optional[Position]:
        if self.cell_size <= 0:
            return None
        x  = (px - self.origin_x) // self.cell_size
        sy = (py - self.origin_y) // self.cell_size
        y  = self.maze.height - 1 - sy
        if 0 <= x < self.maze.width and 0 <= y < self.maze.height:
            return (x, y)
        return None

    # ── Algorithm info ────────────────────────────────────────────────────────

    def _on_algo_change(self, _=None) -> None:
        self._refresh_algo_info()
        self._step_result = None
        self._step_index = 0
        self._reset("Algorithm changed.")

    def _refresh_algo_info(self) -> None:
        info = ALGORITHM_INFO.get(self.algo_var.get(), {})
        self._algo_meta.configure(text=info.get("meta", ""))
        about = info.get("about", "")
        warning = self._weighted_warning()
        if warning:
            about = f"{about}\n\n{warning}"
        self._algo_desc.configure(text=about)

    # ── File ops ──────────────────────────────────────────────────────────────

    def load_sample(self) -> None:
        sample = next((f for f in SAMPLE_FILES if f.name == self.sample_var.get()), None)
        if sample:
            self._load_file(sample)

    def browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Open maze file",
            initialdir=ROOT / "sample_mazes",
            filetypes=(("Maze files", "*.mz *.maze *.json"), ("All files", "*.*")),
        )
        if path:
            self._load_file(path)

    def _load_file(self, path) -> None:
        try:
            p = Path(path)
            self.maze = load_maze(p)
            self.last_path = p
            self._reset(f"Loaded  {p.name}.")
        except Exception as exc:
            messagebox.showerror("Load failed", str(exc))

    def new_blank(self) -> None:
        w = max(5, int(self.width_var.get()))
        h = max(5, int(self.height_var.get()))
        self.maze = Maze(width=w, height=h)
        self.last_path = None
        self._reset(f"Blank {w}×{h} grid — use Draw to add walls.")

    def generate(self, weighted: bool) -> None:
        self._cancel_anim()
        w    = max(5, int(self.width_var.get()))
        h    = max(5, int(self.height_var.get()))
        seed = self._seed()
        self.maze = create_perfect_maze(w, h, seed=seed)
        if weighted:
            add_random_weights(self.maze, density=self.density_var.get() / 100,
                               minimum=2, maximum=9, seed=seed + 101)
        self.last_path = None
        label = "Weighted maze" if weighted else "Maze"
        self._reset(f"{label}  {w}×{h},  seed {seed}.")

    def save_maze_file(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save maze", initialdir=ROOT / "sample_mazes",
            initialfile="maze.maze", defaultextension=".maze",
            filetypes=(("Maze files", "*.maze"), ("JSON", "*.json"), ("All", "*.*")),
        )
        if not path:
            return
        try:
            save_maze(self.maze, path)
            self.last_path = Path(path)
            self._set_status(f"Saved  {self.last_path.name}.", kind="success")
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))

    def export_run(self) -> None:
        if self.result is None:
            messagebox.showinfo("Nothing to export", "Solve or animate first.")
            return
        directory = filedialog.askdirectory(title="Export folder",
                                            initialdir=ROOT / "sample_output")
        if not directory:
            return
        out = Path(directory)
        out.mkdir(parents=True, exist_ok=True)
        csv_path = out / "exploration.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["Step", "x", "y", "Event"])
            for i, (x, y) in enumerate(self.result.visited_order, 1):
                w.writerow([i, x, y, "goal" if (x, y) == self.result.goal else "visited"])
        (out / "statistics.txt").write_text(self._stats_text(self.result), encoding="utf-8")
        self._set_status("Exported  exploration.csv + statistics.txt.", kind="success")

    # ── Solve / Step / Animate / Compare ─────────────────────────────────────

    def solve(self) -> None:
        self._cancel_anim()
        self._step_result = None
        self._no_path_banner = False
        try:
            self.result = solve_maze(self.maze, self._algo_key())
        except Exception as exc:
            self._set_status(str(exc), kind="error")
            return
        self.display_visited = list(self.result.visited_order)
        self.display_path    = list(self.result.path)
        self.display_runner  = None
        self._show_result()
        self.draw()

    def step(self) -> None:
        """Advance the algorithm one cell at a time.  Press Space repeatedly."""
        self._cancel_anim()
        if self._step_result is None:
            self._no_path_banner = False
            try:
                self._step_result = solve_maze(self.maze, self._algo_key())
            except Exception as exc:
                self._set_status(str(exc), kind="error")
                return
            self._step_index = 0
            self.display_visited = self.display_path = []
            self.display_runner = None
            self._update_chips(self._step_result)

        r     = self._step_result
        total = len(r.visited_order)

        if self._step_index < total:
            self._step_index += 1
            self.display_visited = r.visited_order[:self._step_index]
            if self._step_index == total:
                self.result = r
                self.display_path = list(r.path)
                self._show_result()
            else:
                self.display_path = []
                self._set_status(
                    f"Step {self._step_index}/{total} — {r.algorithm}.  Space = next step.",
                    kind="running")
                self._update_stats(
                    f"Step mode: {r.algorithm}\n"
                    f"Visited {self._step_index} / {total} cells\n\n"
                    f"Space → advance one step\n"
                    f"S → jump to full result"
                )
        else:
            self.result = r
            self.display_path = list(r.path)
            self._show_result()
        self.draw()

    def animate(self) -> None:
        self._cancel_anim()
        self._step_result = None
        self._no_path_banner = False
        try:
            self.result = solve_maze(self.maze, self._algo_key())
        except Exception as exc:
            self._set_status(str(exc), kind="error")
            return
        self.display_visited = self.display_path = []
        self.display_runner  = None
        self._update_chips(self.result)
        if self.result.found:
            self._set_status(f"Animating {self.result.algorithm}…", kind="running")
            self._update_stats("Animation running.\n\nBlue cells = nodes the algorithm visits.")
        else:
            self._set_status(f"{self.result.algorithm} searching…", kind="running")
            self._update_stats(
                "Searching every reachable cell…\n\n"
                "Blue cells = nodes the algorithm visits."
            )
        self._anim_visit(0)

    def compare_all(self) -> None:
        self._cancel_anim()
        self._step_result = None
        self._no_path_banner = False
        try:
            results: List[SearchResult] = [
                solve_maze(self.maze, key) for key in ALGORITHMS.values()
            ]
        except Exception as exc:
            self._set_status(str(exc), kind="error")
            return
        lines: List[str] = []
        for label, r in zip(ALGORITHMS, results):
            cost = f"{r.cost:g}" if r.found else "∞"
            lines.append(f"{label}:  {r.explored_count} cells,  cost {cost},  len {r.path_length}")

        best = min((r for r in results if r.found), key=lambda r: r.cost, default=None)
        if best:
            lines += ["", f"Best cost:  {best.algorithm}"]

        self.result = best
        self.display_visited = []
        self.display_path    = list(best.path) if best else []
        self.display_runner  = None
        if best:
            self._set_status("Compared all algorithms — best-cost path shown.", kind="success")
        else:
            self._no_path_banner = True
            self._set_status(
                "Compared all algorithms — none could reach the goal.", kind="error")
        self._update_stats("\n".join(lines))
        self._clear_chips()
        if best:
            self.metric_chips["algorithm"].configure(text=best.algorithm)
            self.metric_chips["cost"].configure(text=f"{best.cost:g}")
            self.metric_chips["length"].configure(text=str(best.path_length))
            self.metric_chips["weights"].configure(text=str(len(self.maze.weights)))
        self.draw()
        self._show_compare_chart(results)

    def _reset(self, msg: str = "Ready.") -> None:
        self._cancel_anim()
        self._step_result = None
        self._step_index  = 0
        self.result       = None
        self._no_path_banner = False
        self.display_visited = self.display_path = []
        self.display_runner  = None
        self._set_status(msg, kind="info")
        if hasattr(self, "_algo_desc"):
            self._refresh_algo_info()
        self._update_stats(self._maze_summary())
        self._clear_chips()
        self.draw()

    # ── Comparison chart ──────────────────────────────────────────────────────

    def _show_compare_chart(self, results: List[SearchResult]) -> None:
        win = tk.Toplevel(self.root)
        win.title("Algorithm Comparison")
        win.geometry("660x400")
        win.configure(bg=P.side)
        win.resizable(True, True)

        cv = tk.Canvas(win, bg=P.side2, highlightthickness=0)
        cv.pack(fill="both", expand=True, padx=1, pady=1)

        bar_colors = [P.accent, P.start_fill, "#f59e0b", P.goal_fill,
                      "#38bdf8", "#a78bfa", "#94a3b8"]

        def redraw(_=None) -> None:
            cv.delete("all")
            cw = cv.winfo_width()  or 660
            ch = cv.winfo_height() or 400
            pl, pr, pt, pb = 152, 20, 54, 28

            cv.create_text(cw // 2, 20, text="Cells Explored per Algorithm",
                           font=(UI_FONT, 13, "bold"), fill=P.text)
            cv.create_text(cw // 2, 37, fill=P.muted, font=(UI_FONT, 9),
                           text=f"Maze {self.maze.width}×{self.maze.height}"
                                f"  ·  {len(self.maze.weights)} weighted cells")

            found = [r for r in results if r.found]
            if not found:
                cv.create_text(cw // 2, ch // 2, text="No path found.",
                               fill=P.muted, font=(UI_FONT, 12))
                return

            max_e = max(r.explored_count for r in found) or 1
            n     = len(found)
            gap   = 7
            bar_h = max(22, (ch - pt - pb - (n + 1) * gap) // n)

            for i, r in enumerate(found):
                yt   = pt + i * (bar_h + gap) + gap
                bw   = max(4, int((cw - pl - pr) * r.explored_count / max_e))
                col  = bar_colors[i % len(bar_colors)]
                # Drop shadow
                cv.create_rectangle(pl + 2, yt + 2, pl + bw + 2, yt + bar_h + 2,
                                    fill=P.side, outline="")
                # Bar
                cv.create_rectangle(pl, yt, pl + bw, yt + bar_h, fill=col, outline="")
                # Algorithm name
                cv.create_text(pl - 10, yt + bar_h // 2, text=r.algorithm,
                               anchor="e", fill=P.text, font=(UI_FONT, 9, "bold"))
                # Stats
                stat = f"{r.explored_count} cells  ·  cost {r.cost:g}  ·  len {r.path_length}"
                cv.create_text(pl + bw + 8, yt + bar_h // 2, text=stat,
                               anchor="w", fill=P.muted, font=(UI_FONT, 9))

        cv.bind("<Configure>", redraw)
        win.after(60, redraw)

    # ── Drawing ───────────────────────────────────────────────────────────────

    def draw(self) -> None:
        if not hasattr(self, "canvas"):
            return
        self.canvas.delete("all")
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 4 or ch < 4:
            return

        m = self.margin
        self.cell_size = max(12, min(52,
            (cw - m * 2) // self.maze.width,
            (ch - m * 2) // self.maze.height,
        ))
        cs = self.cell_size
        gw = self.maze.width  * cs
        gh = self.maze.height * cs
        self.origin_x = max(m, (cw - gw) // 2)
        self.origin_y = max(m, (ch - gh) // 2)

        # Outer grid shadow
        ox, oy = self.origin_x, self.origin_y
        self.canvas.create_rectangle(
            ox + 4, oy + 4, ox + gw + 4, oy + gh + 4,
            fill=P.shadow, outline="",
        )
        # Outer border
        self.canvas.create_rectangle(
            ox - 1, oy - 1, ox + gw + 1, oy + gh + 1,
            fill="", outline=P.card_border, width=1,
        )

        visited_set = set(self.display_visited)
        path_set    = set(self.display_path)
        use_heat    = self.heatmap_var.get() and self.display_visited
        heat_idx    = ({p: i for i, p in enumerate(self.display_visited)}
                       if use_heat else {})
        total_v     = len(self.display_visited)

        gap = max(1, cs // 20)   # 1-2 px gap between cells

        # ── 1. Cell fills ────────────────────────────────────────────────────
        for y in range(self.maze.height):
            for x in range(self.maze.width):
                pos = (x, y)
                x1, y1, x2, y2 = self._cell_box(pos)

                if pos in self.maze.blocked:
                    fill = P.cell_blocked
                else:
                    fill = P.cell_open
                    if pos in self.maze.weights:
                        fill = P.weighted_bg
                    if pos in visited_set:
                        fill = (self._heat_color(heat_idx[pos], total_v)
                                if use_heat and pos in heat_idx else P.discovered)
                    if pos in path_set:
                        fill = P.path_fill
                    # start/goal drawn separately as circles

                self.canvas.create_rectangle(
                    x1 + gap, y1 + gap, x2 - gap, y2 - gap,
                    fill=fill, outline="",
                )

                # Weight label
                if pos not in self.maze.blocked and pos in self.maze.weights:
                    self.canvas.create_text(
                        (x1 + x2) / 2, (y1 + y2) / 2,
                        text=str(self.maze.weights[pos]),
                        fill="#5b21b6",
                        font=(UI_FONT, max(8, cs // 3), "bold"),
                    )

        # ── 2. Walls ────────────────────────────────────────────────────────
        self._draw_walls(gap)

        # ── 3. Path line (through cell centres, drawn over fills) ────────────
        if len(self.display_path) > 1:
            pts: List[float] = []
            for pos in self.display_path:
                x1, y1, x2, y2 = self._cell_box(pos)
                pts += [(x1 + x2) / 2, (y1 + y2) / 2]
            lw = max(3, cs // 6)
            self.canvas.create_line(
                pts, fill=P.path_line, width=lw,
                capstyle="round", joinstyle="round", smooth=True,
            )

        # ── 4. Start / Goal markers ──────────────────────────────────────────
        self._draw_marker(self.maze.start, P.start_fill, "S")
        if self.maze.goal is not None:
            self._draw_marker(self.maze.goal, P.goal_fill, "G")

        # ── 5. Runner ────────────────────────────────────────────────────────
        if self.display_runner is not None:
            self._draw_runner(self.display_runner, self.display_dir)

        # ── 6. No-path banner (overlay, drawn last so nothing hides it) ──────
        if self._no_path_banner:
            self._draw_no_path_banner(cw, ch)

    def _draw_marker(self, pos: Position, color: str, letter: str) -> None:
        x1, y1, x2, y2 = self._cell_box(pos)
        cs  = self.cell_size
        gap = max(1, cs // 20)
        pad = max(2, cs * 0.14)
        # White backing circle for contrast
        self.canvas.create_oval(
            x1 + gap + pad - 1, y1 + gap + pad - 1,
            x2 - gap - pad + 1, y2 - gap - pad + 1,
            fill=P.white, outline="",
        )
        # Coloured circle
        self.canvas.create_oval(
            x1 + gap + pad, y1 + gap + pad,
            x2 - gap - pad, y2 - gap - pad,
            fill=color, outline="",
        )
        if cs >= 16:
            self.canvas.create_text(
                (x1 + x2) / 2, (y1 + y2) / 2,
                text=letter, fill=P.white,
                font=(UI_FONT, max(8, int(cs * 0.40)), "bold"),
            )

    def _draw_walls(self, gap: int) -> None:
        ww = max(2, int(self.cell_size * 0.14))
        for y in range(self.maze.height):
            for x in range(self.maze.width):
                if (x, y) in self.maze.blocked:
                    continue
                N, E, S, W = get_walls(self.maze, x, y)
                x1, y1, x2, y2 = self._cell_box((x, y))
                if N:
                    self.canvas.create_line(x1, y1 + gap, x2, y1 + gap,
                                            fill=P.wall_color, width=ww)
                if E:
                    self.canvas.create_line(x2 - gap, y1, x2 - gap, y2,
                                            fill=P.wall_color, width=ww)
                if S:
                    self.canvas.create_line(x1, y2 - gap, x2, y2 - gap,
                                            fill=P.wall_color, width=ww)
                if W:
                    self.canvas.create_line(x1 + gap, y1, x1 + gap, y2,
                                            fill=P.wall_color, width=ww)

    def _draw_runner(self, pos: Position, direction: str) -> None:
        x1, y1, x2, y2 = self._cell_box(pos)
        cs  = self.cell_size
        pad = max(4, cs * 0.22)
        # Glow ring
        self.canvas.create_oval(
            x1 + pad - 2, y1 + pad - 2, x2 - pad + 2, y2 - pad + 2,
            fill="#c7d2fe", outline="",
        )
        # Body
        self.canvas.create_oval(
            x1 + pad, y1 + pad, x2 - pad, y2 - pad,
            fill=P.runner_fill, outline="",
        )
        # Direction arrow
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        L = cs * 0.28
        dx, dy = {"N": (0, -L), "E": (L, 0), "S": (0, L), "W": (-L, 0)}[direction]
        self.canvas.create_line(cx, cy, cx + dx, cy + dy,
                                fill=P.white, width=max(2, cs // 10),
                                capstyle="round")

    def _round_rect(self, x1, y1, x2, y2, r, **kwargs):
        """Draw a rounded rectangle on the canvas and return its item id."""
        r = min(r, abs(x2 - x1) / 2, abs(y2 - y1) / 2)
        points = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, **kwargs)

    def _draw_no_path_banner(self, cw: int, ch: int) -> None:
        """A bold, centred banner so the user can't miss an unsolvable maze."""
        explored = self.result.explored_count if self.result else 0
        algo = self.result.algorithm if self.result else "Search"
        subtitle = f"{algo} explored {explored} cells — the goal is walled off."

        bw = min(440, max(280, cw - 60))
        bh = 104
        cx, cy = cw // 2, ch // 2
        x1, y1 = cx - bw // 2, cy - bh // 2
        x2, y2 = cx + bw // 2, cy + bh // 2

        # Soft drop shadow, then the card and its accent border.
        self._round_rect(x1 + 4, y1 + 6, x2 + 4, y2 + 6, 20,
                         fill="#cbd5e1", outline="")
        self._round_rect(x1, y1, x2, y2, 20,
                         fill="#fef2f2", outline="#ef4444", width=2)
        # Red accent stripe down the left edge.
        self._round_rect(x1, y1, x1 + 12, y2, 20, fill="#ef4444", outline="")
        self.canvas.create_rectangle(x1 + 8, y1, x1 + 12, y2,
                                     fill="#ef4444", outline="")

        self.canvas.create_text(
            cx + 6, cy - 16, text="⚠  No path found",
            fill="#b91c1c", font=(UI_FONT, 17, "bold"),
        )
        self.canvas.create_text(
            cx + 6, cy + 16, text=subtitle,
            fill="#991b1b", font=(UI_FONT, 10),
        )

    def _heat_color(self, index: int, total: int) -> str:
        t = index / max(total - 1, 1)
        # Pale blue (#dbeafe) → deep indigo (#1e40af)
        r = int(219 + (30  - 219) * t)
        g = int(234 + (64  - 234) * t)
        b = int(254 + (175 - 254) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _cell_box(self, pos: Position) -> Tuple[float, float, float, float]:
        x, y = pos
        sy   = self.maze.height - 1 - y
        x1   = self.origin_x + x  * self.cell_size
        y1   = self.origin_y + sy * self.cell_size
        return x1, y1, x1 + self.cell_size, y1 + self.cell_size

    # ── Animation ─────────────────────────────────────────────────────────────

    def _anim_visit(self, index: int) -> None:
        if self.result is None:
            return
        self.display_visited = self.result.visited_order[:index]
        self.display_path    = []
        self.display_runner  = None
        self.draw()
        if index < len(self.result.visited_order):
            self.animation_id = self.root.after(self._delay(), self._anim_visit, index + 1)
        elif self.result.found:
            self._anim_runner(0)
        else:
            # Search finished with no route — keep the explored cells on screen
            # and reveal the prominent "no path" banner.
            self.display_visited = list(self.result.visited_order)
            self._show_result()
            self.draw()

    def _anim_runner(self, index: int) -> None:
        if self.result is None:
            return
        path = self.result.path
        self.display_visited = list(self.result.visited_order)
        self.display_path    = path[:index + 1]
        self.display_runner  = path[min(index, len(path) - 1)]
        self.display_dir     = self._dir_at(path, index)
        self.draw()
        if index < len(path) - 1:
            self.animation_id = self.root.after(self._delay(), self._anim_runner, index + 1)
        else:
            self.display_path   = list(path)
            self.display_runner = path[-1]
            self._show_result()
            self.draw()

    # ── Result helpers ────────────────────────────────────────────────────────

    def _show_result(self) -> None:
        if self.result is None:
            return
        self._update_chips(self.result)
        if not self.result.found:
            self._no_path_banner = True
            self._set_status(
                f"{self.result.algorithm} — no path found. "
                f"The goal is walled off from the start.",
                kind="error",
            )
            self._update_stats(
                "✗  NO PATH FOUND\n\n"
                f"{self.result.algorithm} searched the whole reachable area\n"
                f"({self.result.explored_count} cells) but the goal is\n"
                "sealed off from the start.\n\n"
                "Try Erase to open a wall, or Generate a\nnew maze."
            )
            return
        self._no_path_banner = False
        note = ""
        warning = self._weighted_warning(self.result.algorithm)
        if warning:
            note = f"\n\n{warning}"
        self._set_status(
            f"{self.result.algorithm} solved it."
            if not warning
            else f"{self.result.algorithm} solved it — not cost-optimal on weighted graphs.",
            kind="success",
        )
        self._update_stats(
            f"Algorithm:  {self.result.algorithm}\n"
            f"Discovered: {self.result.explored_count} cells\n"
            f"Path length: {self.result.path_length}\n"
            f"Path cost:   {self.result.cost:g}\n"
            f"Weighted:    {len(self.maze.weights)} cells\n"
            f"Open cells:  {self.maze.open_cell_count}"
            f"{note}"
        )

    def _update_chips(self, r: SearchResult) -> None:
        self.metric_chips["algorithm"].configure(text=r.algorithm)
        self.metric_chips["explored"].configure(text=str(r.explored_count))
        self.metric_chips["length"].configure(text=str(r.path_length))
        self.metric_chips["cost"].configure(text=f"{r.cost:g}" if r.found else "—")
        self.metric_chips["weights"].configure(text=str(len(self.maze.weights)))

    def _clear_chips(self) -> None:
        if not hasattr(self, "metric_chips"):
            return
        for c in self.metric_chips.values():
            c.configure(text="—")
        self.metric_chips["weights"].configure(text=str(len(self.maze.weights)))

    def _weighted_warning(self, algorithm_name: Optional[str] = None) -> str:
        if not self.maze.weights or self._algo_key() not in NON_COST_OPTIMAL_WEIGHTED:
            return ""
        name = algorithm_name or self.algo_var.get()
        return (
            f"{name} is not optimal for weighted graphs. "
            "Use Dijkstra, A*, or Bellman-Ford for cheapest paths."
        )

    def _set_status(self, text: str, kind: str = "info") -> None:
        colors = {
            "info":    P.status_info,
            "running": P.status_running,
            "success": P.status_success,
            "error":   P.status_error,
        }
        self.status_var.set(text)
        if hasattr(self, "_status_lbl"):
            self._status_lbl.configure(fg=colors.get(kind, P.status_info))

    def _update_stats(self, text: str) -> None:
        if hasattr(self, "_stats_lbl"):
            self._stats_lbl.configure(text=text)

    def _maze_summary(self) -> str:
        return (
            f"Size:     {self.maze.width}×{self.maze.height}\n"
            f"Open:     {self.maze.open_cell_count} cells\n"
            f"Weighted: {len(self.maze.weights)} cells\n"
            f"Start:    {self.maze.start}\n"
            f"Goal:     {self.maze.goal}\n\n"
            f"Tip: use DRAW tools to\nbuild your own maze."
        )

    def _stats_text(self, r: SearchResult) -> str:
        return (
            f"Algorithm: {r.algorithm}\n"
            f"Maze: {self.maze.width}×{self.maze.height}\n"
            f"Start: {r.start}    Goal: {r.goal}\n"
            f"Found: {r.found}\n"
            f"Discovered: {r.explored_count} cells\n"
            f"Path length: {r.path_length}\n"
            f"Path cost: {r.cost:g}\n"
            f"Weighted cells: {len(self.maze.weights)}\n"
            f"Path: {r.path}\n"
        )

    # ── Misc helpers ──────────────────────────────────────────────────────────

    def _dir_at(self, path: List[Position], index: int) -> str:
        if len(path) < 2:
            return "N"
        a, b = (path[0], path[1]) if index <= 0 else (
            path[index - 1], path[min(index, len(path) - 1)]
        )
        return {(0, 1): "N", (1, 0): "E", (0, -1): "S", (-1, 0): "W"}.get(
            (b[0] - a[0], b[1] - a[1]), "N"
        )

    def _algo_key(self) -> str:
        return ALGORITHMS[self.algo_var.get()]

    def _seed(self) -> int:
        t = self.seed_var.get().strip()
        if t:
            try:
                return int(t)
            except ValueError:
                messagebox.showwarning("Seed", "Seed must be an integer — using random.")
        seed = random.randint(1, 99999)
        self.seed_var.set(str(seed))
        return seed

    def _delay(self) -> int:
        return max(5, 135 - int(self.speed_var.get()))

    def _cancel_anim(self) -> None:
        if self.animation_id:
            self.root.after_cancel(self.animation_id)
            self.animation_id = None

    def _load_initial_maze(self, path: Optional[str]) -> Maze:
        candidates = ([Path(path)] if path else []) + [f for f in SAMPLE_FILES if f.exists()]
        for p in candidates:
            if p and p.exists():
                self.last_path = p
                return load_maze(p)
        return create_perfect_maze(14, 10, seed=4)

    def _bind_keys(self) -> None:
        self.root.bind("<space>", lambda event: self.step() if self._shortcut_allowed(event) else None)
        for k in ("r", "R"):
            self.root.bind(k, lambda event: self._reset("View reset.") if self._shortcut_allowed(event) else None)
        for k in ("s", "S"):
            self.root.bind(k, lambda event: self.solve() if self._shortcut_allowed(event) else None)
        for k in ("a", "A"):
            self.root.bind(k, lambda event: self.animate() if self._shortcut_allowed(event) else None)
        self.root.bind("<Escape>", lambda event: self._cancel_anim())

    def _shortcut_allowed(self, event: tk.Event) -> bool:
        widget_class = event.widget.winfo_class()
        return widget_class not in {"Entry", "Spinbox", "TSpinbox", "TCombobox"}


# ── Entry point ───────────────────────────────────────────────────────────────

def run_gui(initial_maze_path: Optional[str] = None) -> None:
    root = tk.Tk()
    MazeApp(root, initial_maze_path=initial_maze_path)
    root.mainloop()


if __name__ == "__main__":
    run_gui()
