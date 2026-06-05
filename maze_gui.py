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
        "meta": "O(V · E)  ·  space O(V)  ·  optimal (incl. negative weights)",
        "about": "Relaxes every edge V−1 times. Handles negative-weight edges "
                 "where Dijkstra fails; slower on all-positive-cost graphs.",
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


# ── Palette ──────────────────────────────────────────────────────────────────

class P:
    # Page / chrome
    page        = "#f0f4f8"
    # Sidebar
    side        = "#1a2332"
    side2       = "#243044"
    side_border = "#2e3d54"
    side_hover  = "#354863"
    text        = "#e8edf5"
    muted       = "#8899b4"
    dim         = "#566680"
    # Accent (indigo)
    accent      = "#5b6ef5"
    accent_dk   = "#4554d4"
    accent_lt   = "#a5b4fc"
    # Canvas
    canvas_bg   = "#ffffff"
    cell_open   = "#f8faff"
    cell_grid   = "#dde3f0"
    cell_blocked = "#2e3d54"
    # Algorithmic colours
    discovered  = "#c7dffe"
    path_fill   = "#fff0b3"
    path_line   = "#e8a800"
    start_fill  = "#22c55e"
    goal_fill   = "#ef4444"
    weighted_bg = "#ede9fe"
    runner_fill = "#5b6ef5"
    wall_color  = "#1a2332"
    white       = "#ffffff"
    black       = "#000000"


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
        style.configure("Sidebar.TCombobox",
                        fieldbackground=P.side2,
                        background=P.side2,
                        foreground=P.text,
                        selectbackground=P.accent,
                        selectforeground=P.white,
                        arrowcolor=P.muted)
        style.map("Sidebar.TCombobox",
                  fieldbackground=[("readonly", P.side2)],
                  selectbackground=[("readonly", P.accent)])
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

        # Sidebar
        side = tk.Frame(outer, bg=P.side, width=248)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        # Stage (canvas area)
        stage = tk.Frame(outer, bg=P.page)
        stage.pack(side="left", fill="both", expand=True)

        self._build_sidebar(side)
        self._build_stage(stage)

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self, p: tk.Frame) -> None:
        # App header
        hdr = tk.Frame(p, bg=P.side)
        hdr.pack(fill="x", padx=20, pady=(22, 0))
        tk.Label(hdr, text="Maze Lab", font=("Helvetica", 19, "bold"),
                 bg=P.side, fg=P.text).pack(anchor="w")
        tk.Label(hdr, text="graph pathfinding visualiser",
                 font=("Helvetica", 9), bg=P.side, fg=P.dim).pack(anchor="w", pady=(1, 0))

        # ── Algorithm ──────────────────────────────────────────────────────────
        self._sep(p)
        self._sh(p, "ALGORITHM")

        algo_combo = ttk.Combobox(
            p, textvariable=self.algo_var,
            values=list(ALGORITHMS), state="readonly",
            font=("Helvetica", 10), style="Sidebar.TCombobox",
        )
        algo_combo.pack(fill="x", padx=16, pady=(0, 6))
        algo_combo.bind("<<ComboboxSelected>>", self._on_algo_change)

        self._algo_meta = tk.Label(p, text="", bg=P.side, fg=P.accent_lt,
                                    font=("Helvetica", 8), wraplength=212, justify="left")
        self._algo_meta.pack(anchor="w", padx=16)
        self._algo_desc = tk.Label(p, text="", bg=P.side, fg=P.muted,
                                    font=("Helvetica", 9), wraplength=212, justify="left")
        self._algo_desc.pack(anchor="w", padx=16, pady=(2, 0))
        self._refresh_algo_info()

        # ── Maze ───────────────────────────────────────────────────────────────
        self._sep(p)
        self._sh(p, "MAZE")

        sz = tk.Frame(p, bg=P.side)
        sz.pack(fill="x", padx=16, pady=(0, 8))
        for lbl, var, hi in [("W", self.width_var, 40), ("H", self.height_var, 26)]:
            tk.Label(sz, text=lbl, bg=P.side, fg=P.muted,
                     font=("Helvetica", 9)).pack(side="left")
            tk.Spinbox(sz, from_=5, to=hi, textvariable=var, width=4,
                       bg=P.side2, fg=P.text, insertbackground=P.text,
                       buttonbackground=P.side_border, relief="flat", bd=0,
                       font=("Helvetica", 10)).pack(side="left", padx=(3, 10))
        tk.Label(sz, text="Seed", bg=P.side, fg=P.muted,
                 font=("Helvetica", 9)).pack(side="left")
        tk.Entry(sz, textvariable=self.seed_var, width=6,
                 bg=P.side2, fg=P.text, insertbackground=P.text,
                 font=("Helvetica", 10), relief="flat", bd=3,
                 highlightthickness=0).pack(side="left", padx=(3, 0))

        r = tk.Frame(p, bg=P.side)
        r.pack(fill="x", padx=16, pady=(0, 6))
        self._btn(r, "Generate", lambda: self.generate(False)).pack(
            side="left", expand=True, fill="x")
        self._btn(r, "+ Weighted", lambda: self.generate(True)).pack(
            side="left", expand=True, fill="x", padx=(5, 0))

        tk.Label(p, text="Weight density", bg=P.side, fg=P.dim,
                 font=("Helvetica", 8)).pack(anchor="w", padx=16, pady=(4, 0))
        tk.Scale(p, from_=5, to=70, variable=self.density_var,
                 orient="horizontal", bg=P.side, fg=P.muted,
                 troughcolor=P.side_border, highlightthickness=0,
                 sliderrelief="flat", bd=1, showvalue=False).pack(
            fill="x", padx=16, pady=(2, 2))

        # ── Run ────────────────────────────────────────────────────────────────
        self._sep(p)
        self._sh(p, "RUN")

        r2 = tk.Frame(p, bg=P.side)
        r2.pack(fill="x", padx=16, pady=(0, 5))
        self._btn(r2, "Solve  [S]", self.solve, primary=True).pack(
            side="left", expand=True, fill="x")
        self._btn(r2, "Step  [Space]", self.step).pack(
            side="left", expand=True, fill="x", padx=(5, 0))

        r3 = tk.Frame(p, bg=P.side)
        r3.pack(fill="x", padx=16, pady=(0, 5))
        self._btn(r3, "Animate", self.animate).pack(side="left", expand=True, fill="x")
        self._btn(r3, "Compare", self.compare_all).pack(
            side="left", expand=True, fill="x", padx=(5, 0))

        self._btn(p, "Reset  [R]", lambda: self._reset("View reset."),
                  full=True).pack(fill="x", padx=16, pady=(0, 8))

        tk.Label(p, text="Animation speed", bg=P.side, fg=P.dim,
                 font=("Helvetica", 8)).pack(anchor="w", padx=16)
        tk.Scale(p, from_=10, to=120, variable=self.speed_var,
                 orient="horizontal", bg=P.side, fg=P.muted,
                 troughcolor=P.side_border, highlightthickness=0,
                 sliderrelief="flat", bd=1, showvalue=False).pack(
            fill="x", padx=16, pady=(2, 4))

        hm = tk.Frame(p, bg=P.side)
        hm.pack(fill="x", padx=14, pady=(4, 0))
        tk.Checkbutton(hm, text="Heatmap  (discovery order)",
                       variable=self.heatmap_var, command=self.draw,
                       bg=P.side, fg=P.muted, activebackground=P.side,
                       selectcolor=P.side_border,
                       font=("Helvetica", 9)).pack(side="left")

        # ── Draw ───────────────────────────────────────────────────────────────
        self._sep(p)
        self._sh(p, "DRAW  (click or drag on the maze)")

        eg = tk.Frame(p, bg=P.side)
        eg.pack(fill="x", padx=16, pady=(0, 6))
        for col in range(3):
            eg.columnconfigure(col, weight=1)
        for i, (mode, label) in enumerate(EDIT_MODES):
            row, col = divmod(i, 3)
            b = self._click_label(
                eg,
                label,
                lambda _event, m=mode: self._set_mode(m),
                font=("Helvetica", 9),
                padx=4,
                pady=5,
            )
            b.grid(row=row, column=col, padx=(0, 4), pady=(0, 4), sticky="ew")
            self._edit_btns[mode] = b
        self._set_mode("navigate")

        # ── Files ──────────────────────────────────────────────────────────────
        self._sep(p)
        self._sh(p, "FILES")

        samples = [f.name for f in SAMPLE_FILES if f.exists()]
        sample_combo = ttk.Combobox(p, textvariable=self.sample_var,
                                    values=samples, state="readonly",
                                    font=("Helvetica", 9), style="Sidebar.TCombobox")
        sample_combo.pack(fill="x", padx=16, pady=(0, 6))

        r4 = tk.Frame(p, bg=P.side)
        r4.pack(fill="x", padx=16, pady=(0, 5))
        self._btn(r4, "Load Sample", self.load_sample).pack(
            side="left", expand=True, fill="x")
        self._btn(r4, "Open…", self.browse).pack(
            side="left", expand=True, fill="x", padx=(5, 0))

        r5 = tk.Frame(p, bg=P.side)
        r5.pack(fill="x", padx=16, pady=(0, 5))
        self._btn(r5, "New Blank", self.new_blank).pack(
            side="left", expand=True, fill="x")
        self._btn(r5, "Save…", self.save_maze_file).pack(
            side="left", expand=True, fill="x", padx=(5, 0))

        self._btn(p, "Export Run", self.export_run,
                  full=True).pack(fill="x", padx=16, pady=(0, 6))

    # ── Stage ─────────────────────────────────────────────────────────────────

    def _build_stage(self, p: tk.Frame) -> None:
        # Top bar: status left, metric chips right
        topbar = tk.Frame(p, bg=P.page, height=70)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        tk.Label(topbar, textvariable=self.status_var,
                 bg=P.page, fg="#64748b",
                 font=("Helvetica", 10), wraplength=430, justify="left").pack(
                     side="left", padx=18, pady=16)

        chips = tk.Frame(topbar, bg=P.page)
        chips.pack(side="right", padx=14, pady=10)
        for key, label in [("algorithm", "Algorithm"), ("explored", "Explored"),
                            ("length", "Length"), ("cost", "Cost"), ("weights", "Weights")]:
            card = tk.Frame(chips, bg="#eef2ff",
                            highlightthickness=1, highlightbackground="#c7d2fe")
            card.pack(side="left", padx=(0, 6))
            tk.Label(card, text=label, bg="#eef2ff", fg="#6366f1",
                     font=("Helvetica", 7, "bold")).pack(padx=9, pady=(4, 0))
            val = tk.Label(card, text="—", bg="#eef2ff", fg="#312e81",
                           font=("Helvetica", 11, "bold"))
            val.pack(padx=9, pady=(0, 4))
            self.metric_chips[key] = val

        # Divider
        tk.Frame(p, bg="#dde3f0", height=1).pack(fill="x")

        content = tk.Frame(p, bg=P.page)
        content.pack(fill="both", expand=True)

        # Canvas frame
        cf = tk.Frame(content, bg=P.canvas_bg)
        cf.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(cf, bg=P.canvas_bg, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _e: self.draw())
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>", self._on_right_click)

        stats_panel = tk.Frame(content, bg="#f8faff", width=230,
                               highlightthickness=1, highlightbackground="#dde3f0")
        stats_panel.pack(side="right", fill="y")
        stats_panel.pack_propagate(False)
        tk.Label(stats_panel, text="Run Stats", bg="#f8faff", fg=P.side,
                 font=("Helvetica", 12, "bold")).pack(anchor="w", padx=16, pady=(18, 8))
        self._stats_lbl = tk.Label(
            stats_panel, text="", bg="#f8faff", fg="#475569",
            font=("Helvetica", 10), wraplength=190, justify="left",
        )
        self._stats_lbl.pack(anchor="nw", fill="x", padx=16, pady=(0, 16))

    # ── Sidebar widget helpers ────────────────────────────────────────────────

    def _sep(self, p: tk.Widget) -> None:
        tk.Frame(p, bg=P.side_border, height=1).pack(fill="x", padx=16, pady=9)

    def _sh(self, p: tk.Widget, text: str) -> None:
        tk.Label(p, text=text, bg=P.side, fg=P.dim,
                 font=("Helvetica", 8, "bold")).pack(anchor="w", padx=16, pady=(0, 6))

    def _btn(self, parent: tk.Widget, text: str, command,
             primary: bool = False, full: bool = False) -> tk.Label:
        bg  = P.accent    if primary else P.side_border
        abg = P.accent_dk if primary else P.side_hover
        return self._click_label(
            parent,
            text,
            lambda _event: command(),
            bg=bg,
            hover_bg=abg,
            font=("Helvetica", 10, "bold" if primary else "normal"),
            padx=10,
            pady=8,
        )

    def _click_label(
        self,
        parent: tk.Widget,
        text: str,
        command,
        *,
        bg: str = P.side_border,
        hover_bg: str = P.side_hover,
        font=("Helvetica", 10),
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
            bg = P.accent if key == mode else P.side_border
            btn.configure(
                bg=bg,
                fg=P.white,
            )
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
        self.display_visited = self.display_path = []
        self.display_runner = None
        self._clear_chips()
        self.status_var.set("Maze edited — press Solve or Animate.")
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
            self.status_var.set(f"Saved  {self.last_path.name}.")
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
        self.status_var.set("Exported  exploration.csv + statistics.txt.")

    # ── Solve / Step / Animate / Compare ─────────────────────────────────────

    def solve(self) -> None:
        self._cancel_anim()
        self._step_result = None
        try:
            self.result = solve_maze(self.maze, self._algo_key())
        except Exception as exc:
            self.status_var.set(str(exc))
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
            try:
                self._step_result = solve_maze(self.maze, self._algo_key())
            except Exception as exc:
                self.status_var.set(str(exc))
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
                self.status_var.set(
                    f"Step {self._step_index}/{total} — {r.algorithm}.  Space = next step.")
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
        try:
            self.result = solve_maze(self.maze, self._algo_key())
        except Exception as exc:
            self.status_var.set(str(exc))
            return
        if not self.result.found:
            self._show_result()
            self.draw()
            return
        self.display_visited = self.display_path = []
        self.display_runner  = None
        self._update_chips(self.result)
        self.status_var.set(f"Animating {self.result.algorithm}…")
        self._update_stats("Animation running.\n\nBlue cells = nodes the algorithm visits.")
        self._anim_visit(0)

    def compare_all(self) -> None:
        self._cancel_anim()
        self._step_result = None
        results: List[SearchResult] = []
        lines:   List[str]          = []
        for label, key in ALGORITHMS.items():
            r = solve_maze(self.maze, key)
            results.append(r)
            cost = f"{r.cost:g}" if r.found else "∞"
            lines.append(f"{label}:  {r.explored_count} cells,  cost {cost},  len {r.path_length}")

        best = min((r for r in results if r.found), key=lambda r: r.cost, default=None)
        if best:
            lines += ["", f"Best cost:  {best.algorithm}"]

        self.result = best
        self.display_visited = []
        self.display_path    = list(best.path) if best else []
        self.display_runner  = None
        self.status_var.set("Compared all algorithms — best-cost path shown.")
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
        self.display_visited = self.display_path = []
        self.display_runner  = None
        self.status_var.set(msg)
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

        bar_colors = [P.accent, "#22c55e", "#f59e0b", "#ef4444",
                      "#38bdf8", "#a78bfa", "#94a3b8"]

        def redraw(_=None) -> None:
            cv.delete("all")
            cw = cv.winfo_width()  or 660
            ch = cv.winfo_height() or 400
            pl, pr, pt, pb = 152, 20, 54, 28

            cv.create_text(cw // 2, 20, text="Cells Explored per Algorithm",
                           font=("Helvetica", 13, "bold"), fill=P.text)
            cv.create_text(cw // 2, 37, fill=P.muted, font=("Helvetica", 9),
                           text=f"Maze {self.maze.width}×{self.maze.height}"
                                f"  ·  {len(self.maze.weights)} weighted cells")

            found = [r for r in results if r.found]
            if not found:
                cv.create_text(cw // 2, ch // 2, text="No path found.",
                               fill=P.muted, font=("Helvetica", 12))
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
                               anchor="e", fill=P.text, font=("Helvetica", 9, "bold"))
                # Stats
                stat = f"{r.explored_count} cells  ·  cost {r.cost:g}  ·  len {r.path_length}"
                cv.create_text(pl + bw + 8, yt + bar_h // 2, text=stat,
                               anchor="w", fill=P.muted, font=("Helvetica", 9))

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
            fill="#dde3f0", outline="",
        )
        # Outer border
        self.canvas.create_rectangle(
            ox - 1, oy - 1, ox + gw + 1, oy + gh + 1,
            fill="", outline="#c5cee0", width=1,
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
                        font=("Helvetica", max(8, cs // 3), "bold"),
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
                font=("Helvetica", max(8, int(cs * 0.40)), "bold"),
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
        else:
            self._anim_runner(0)

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
            self.status_var.set(f"{self.result.algorithm} — no path found.")
            self._update_stats("No path found.")
            return
        note = ""
        warning = self._weighted_warning(self.result.algorithm)
        if warning:
            note = f"\n\n{warning}"
        self.status_var.set(
            f"{self.result.algorithm} solved it."
            if not warning
            else f"{self.result.algorithm} solved it — not cost-optimal on weighted graphs."
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
