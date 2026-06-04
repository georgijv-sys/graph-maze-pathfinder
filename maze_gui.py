"""Interactive Tkinter GUI for the graph maze pathfinder."""

from __future__ import annotations

import csv
from pathlib import Path
import random
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, Iterable, List, Optional

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
    "A*": "astar",
    "Dijkstra": "dijkstra",
    "Bellman-Ford": "bellmanford",
    "Greedy Best-First": "greedy",
    "Bidirectional BFS": "bidirectional",
    "BFS": "bfs",
    "DFS": "dfs",
}


class Palette:
    app = "#f5f1e8"
    panel = "#fffdf8"
    panel_edge = "#d8d0c1"
    control = "#ece4d6"
    ink = "#1f2328"
    muted = "#68615a"
    accent = "#3157a4"
    accent_hover = "#244682"
    gold = "#f2c94c"
    wall = "#24211d"
    grid = "#ded6c8"
    open_cell = "#faf6ea"
    blocked = "#e6dccb"
    start = "#58bd8f"
    goal = "#ef6f73"
    discovered = "#9ed8e6"
    shortest = "#f7d45b"
    weighted = "#cdbdf6"
    runner = "#3157a4"
    white = "#ffffff"


class MazeApp:
    def __init__(self, root: tk.Tk, initial_maze_path: Optional[str] = None):
        self.root = root
        self.root.title("Graph Maze Pathfinder")
        self.root.minsize(1180, 740)
        self.root.configure(bg=Palette.app)

        self.algorithm_label = tk.StringVar(value="A*")
        self.sample_label = tk.StringVar(value=SAMPLE_FILES[0].name)
        self.width_var = tk.IntVar(value=18)
        self.height_var = tk.IntVar(value=12)
        self.seed_var = tk.StringVar(value="")
        self.density_var = tk.IntVar(value=25)
        self.speed_var = tk.IntVar(value=65)
        self.status = tk.StringVar(value="")
        self.details = tk.StringVar(value="")

        self.maze = self._load_initial_maze(initial_maze_path)
        self.result: Optional[SearchResult] = None
        self.animation_id: Optional[str] = None
        self.last_saved_path: Optional[Path] = None

        self.display_visited: List[Position] = []
        self.display_path: List[Position] = []
        self.display_runner: Optional[Position] = None
        self.display_orientation = "N"

        self.cell_size = 28
        self.margin = 28
        self.origin_x = self.margin
        self.origin_y = self.margin

        self._configure_style()
        self._build_layout()
        self.reset_view("Ready. Load or generate a maze, then solve or animate.")

    def _configure_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=Palette.app)
        style.configure("Panel.TFrame", background=Palette.panel)
        style.configure("TLabel", background=Palette.app, foreground=Palette.ink, font=("Helvetica", 11))
        style.configure("Panel.TLabel", background=Palette.panel, foreground=Palette.ink, font=("Helvetica", 11))
        style.configure("Muted.TLabel", background=Palette.panel, foreground=Palette.muted, font=("Helvetica", 10))
        style.configure("Title.TLabel", background=Palette.panel, foreground=Palette.ink, font=("Helvetica", 20, "bold"))
        style.configure("Section.TLabel", background=Palette.panel, foreground=Palette.accent, font=("Helvetica", 10, "bold"))
        style.configure("TButton", font=("Helvetica", 11), padding=(10, 7))
        style.configure("Accent.TButton", font=("Helvetica", 11, "bold"), padding=(10, 8))
        style.configure("TCombobox", padding=5)
        style.configure("TSpinbox", padding=4)
        style.configure("TScale", background=Palette.panel, troughcolor=Palette.control)

    def _build_layout(self) -> None:
        outer = ttk.Frame(self.root)
        outer.pack(fill="both", expand=True, padx=16, pady=16)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(0, weight=1)

        controls = self._panel(outer, width=282)
        controls.grid(row=0, column=0, sticky="ns", padx=(0, 14))
        controls.grid_propagate(False)

        stage = ttk.Frame(outer)
        stage.grid(row=0, column=1, sticky="nsew")
        stage.columnconfigure(0, weight=1)
        stage.rowconfigure(1, weight=1)

        inspector = self._panel(outer, width=252)
        inspector.grid(row=0, column=2, sticky="ns", padx=(14, 0))
        inspector.grid_propagate(False)

        self._build_controls(controls)
        self._build_stage(stage)
        self._build_inspector(inspector)

    def _panel(self, parent: tk.Widget, width: int) -> tk.Frame:
        frame = tk.Frame(
            parent,
            bg=Palette.panel,
            width=width,
            highlightthickness=1,
            highlightbackground=Palette.panel_edge,
        )
        return frame

    def _build_controls(self, parent: tk.Frame) -> None:
        self._label(parent, "Maze Pathfinder", font=("Helvetica", 22, "bold")).pack(
            anchor="w", padx=18, pady=(18, 2)
        )
        self._label(parent, "Choose, generate, solve, compare.", fg=Palette.muted).pack(
            anchor="w", padx=18, pady=(0, 18)
        )

        self._section(parent, "Algorithm")
        algorithm_box = ttk.Combobox(
            parent,
            textvariable=self.algorithm_label,
            values=tuple(ALGORITHMS.keys()),
            state="readonly",
            width=24,
        )
        algorithm_box.pack(fill="x", padx=18, pady=(0, 8))
        algorithm_box.bind("<<ComboboxSelected>>", lambda _event: self.reset_view("Algorithm changed."))

        self._section(parent, "Files")
        self.sample_box = ttk.Combobox(
            parent,
            textvariable=self.sample_label,
            values=tuple(path.name for path in SAMPLE_FILES if path.exists()),
            state="readonly",
            width=24,
        )
        self.sample_box.pack(fill="x", padx=18, pady=(0, 7))
        row = self._row(parent)
        ttk.Button(row, text="Load Sample", command=self.load_selected_sample).pack(side="left", expand=True, fill="x")
        ttk.Button(row, text="Open File", command=self.browse).pack(side="left", expand=True, fill="x", padx=(8, 0))
        row = self._row(parent)
        ttk.Button(row, text="Save Maze", command=self.save_current_maze).pack(side="left", expand=True, fill="x")
        ttk.Button(row, text="Export Run", command=self.export_run).pack(side="left", expand=True, fill="x", padx=(8, 0))

        self._section(parent, "Generate")
        size = self._row(parent)
        self._label(size, "W", fg=Palette.muted).pack(side="left")
        ttk.Spinbox(size, from_=5, to=40, textvariable=self.width_var, width=5).pack(side="left", padx=(5, 12))
        self._label(size, "H", fg=Palette.muted).pack(side="left")
        ttk.Spinbox(size, from_=5, to=26, textvariable=self.height_var, width=5).pack(side="left", padx=(5, 12))
        self._label(size, "Seed", fg=Palette.muted).pack(side="left")
        ttk.Entry(size, textvariable=self.seed_var, width=7).pack(side="left", padx=(5, 0))

        self._label(parent, "Weighted cell density", fg=Palette.muted).pack(anchor="w", padx=18, pady=(4, 0))
        ttk.Scale(parent, from_=5, to=70, variable=self.density_var, orient="horizontal").pack(
            fill="x", padx=18, pady=(2, 8)
        )
        row = self._row(parent)
        ttk.Button(row, text="Generate Maze", command=lambda: self.generate(False)).pack(
            side="left", expand=True, fill="x"
        )
        ttk.Button(row, text="Generate Weighted", command=lambda: self.generate(True)).pack(
            side="left", expand=True, fill="x", padx=(8, 0)
        )

        self._section(parent, "Run")
        ttk.Button(parent, text="Solve", style="Accent.TButton", command=self.solve).pack(
            fill="x", padx=18, pady=(0, 7)
        )
        ttk.Button(parent, text="Animate", command=self.animate).pack(fill="x", padx=18, pady=(0, 7))
        row = self._row(parent)
        ttk.Button(row, text="Compare", command=self.compare_all).pack(side="left", expand=True, fill="x")
        ttk.Button(row, text="Reset View", command=lambda: self.reset_view("View reset by user.")).pack(
            side="left", expand=True, fill="x", padx=(8, 0)
        )

        self._label(parent, "Animation speed", fg=Palette.muted).pack(anchor="w", padx=18, pady=(10, 0))
        ttk.Scale(parent, from_=10, to=120, variable=self.speed_var, orient="horizontal").pack(
            fill="x", padx=18, pady=(2, 8)
        )

        self.file_label = self._label(parent, "", fg=Palette.muted, font=("Helvetica", 9), wraplength=236)
        self.file_label.pack(anchor="w", padx=18, pady=(6, 14))
        self._refresh_file_label()

    def _build_stage(self, parent: ttk.Frame) -> None:
        header = ttk.Frame(parent)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Maze Lab", font=("Helvetica", 24, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(header, textvariable=self.status, foreground=Palette.muted).grid(row=1, column=0, sticky="w")

        self.metrics: Dict[str, tk.Label] = {}
        metric_frame = ttk.Frame(header)
        metric_frame.grid(row=0, column=1, rowspan=2, sticky="e")
        for key, label in [
            ("algorithm", "Algorithm"),
            ("explored", "Discovered"),
            ("length", "Length"),
            ("cost", "Cost"),
            ("weights", "Weights"),
        ]:
            box = tk.Frame(metric_frame, bg=Palette.panel, highlightthickness=1, highlightbackground=Palette.panel_edge)
            box.pack(side="left", padx=4)
            self._label(box, label, fg=Palette.muted, font=("Helvetica", 9)).pack(padx=10, pady=(7, 0))
            value = self._label(box, "-", font=("Helvetica", 14, "bold"))
            value.pack(padx=10, pady=(0, 7))
            self.metrics[key] = value

        canvas_frame = tk.Frame(parent, bg=Palette.panel, highlightthickness=1, highlightbackground=Palette.panel_edge)
        canvas_frame.grid(row=1, column=0, sticky="nsew")
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(canvas_frame, bg=Palette.panel, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
        self.canvas.bind("<Configure>", lambda _event: self.draw())

    def _build_inspector(self, parent: tk.Frame) -> None:
        self._label(parent, "What You See", font=("Helvetica", 18, "bold")).pack(
            anchor="w", padx=18, pady=(18, 10)
        )
        for color, text in [
            (Palette.discovered, "discovered cells"),
            (Palette.shortest, "shortest path"),
            (Palette.start, "start"),
            (Palette.goal, "goal"),
            (Palette.weighted, "weighted cost"),
            (Palette.runner, "runner"),
        ]:
            self._legend_item(parent, color, text)
        tk.Frame(parent, bg=Palette.panel_edge, height=1).pack(fill="x", padx=18, pady=16)
        self._label(parent, "Run Details", font=("Helvetica", 15, "bold")).pack(anchor="w", padx=18)
        self._label(parent, textvariable=self.details, fg=Palette.ink, wraplength=210, justify="left").pack(
            anchor="nw", fill="both", expand=True, padx=18, pady=(8, 18)
        )

    def _row(self, parent: tk.Widget) -> tk.Frame:
        row = tk.Frame(parent, bg=Palette.panel)
        row.pack(fill="x", padx=18, pady=(0, 8))
        return row

    def _section(self, parent: tk.Widget, text: str) -> None:
        ttk.Label(parent, text=text.upper(), style="Section.TLabel").pack(anchor="w", padx=18, pady=(12, 6))

    def _label(self, parent: tk.Widget, text: str = "", **kwargs) -> tk.Label:
        options = {
            "bg": Palette.panel,
            "fg": Palette.ink,
            "font": ("Helvetica", 11),
        }
        options.update(kwargs)
        return tk.Label(parent, text=text, **options)

    def _legend_item(self, parent: tk.Widget, color: str, text: str) -> None:
        row = tk.Frame(parent, bg=Palette.panel)
        row.pack(fill="x", padx=18, pady=4)
        swatch = tk.Canvas(row, width=18, height=18, bg=Palette.panel, highlightthickness=0)
        swatch.pack(side="left")
        swatch.create_rectangle(2, 2, 16, 16, fill=color, outline="")
        self._label(row, text).pack(side="left", padx=(9, 0))

    def _load_initial_maze(self, initial_maze_path: Optional[str]) -> Maze:
        candidates = [Path(initial_maze_path)] if initial_maze_path else []
        candidates.extend(path for path in SAMPLE_FILES if path.exists())
        for path in candidates:
            if path and path.exists():
                self.last_saved_path = path
                return load_maze(path)
        return create_perfect_maze(14, 10, seed=4)

    def load_selected_sample(self) -> None:
        sample = next((path for path in SAMPLE_FILES if path.name == self.sample_label.get()), None)
        if sample is not None:
            self.load_file(sample)

    def load_file(self, path: Path | str) -> None:
        try:
            resolved = Path(path)
            self.maze = load_maze(resolved)
            self.last_saved_path = resolved
            self.reset_view(f"Loaded {resolved.name}.")
            self._refresh_file_label()
        except Exception as exc:
            messagebox.showerror("Maze load failed", str(exc))

    def browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose a maze file",
            initialdir=ROOT / "sample_mazes",
            filetypes=(
                ("Maze files", "*.mz *.maze *.json"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ),
        )
        if path:
            self.load_file(path)

    def generate(self, weighted: bool) -> None:
        self._cancel_animation()
        width = max(5, int(self.width_var.get()))
        height = max(5, int(self.height_var.get()))
        seed = self._seed()
        self.maze = create_perfect_maze(width, height, seed=seed)
        if weighted:
            add_random_weights(
                self.maze,
                density=self.density_var.get() / 100,
                minimum=2,
                maximum=9,
                seed=seed + 101,
            )
        self.last_saved_path = None
        self.reset_view(
            f"Generated {'weighted ' if weighted else ''}maze: {width} x {height}, seed {seed}."
        )
        self._refresh_file_label(generated=True, seed=seed)

    def solve(self) -> None:
        self._cancel_animation()
        try:
            self.result = solve_maze(self.maze, self._algorithm_key())
        except Exception as exc:
            self.status.set(str(exc))
            return
        self.display_visited = list(self.result.visited_order)
        self.display_path = list(self.result.path)
        self.display_runner = None
        self._show_result()
        self.draw()

    def animate(self) -> None:
        self._cancel_animation()
        try:
            self.result = solve_maze(self.maze, self._algorithm_key())
        except Exception as exc:
            self.status.set(str(exc))
            return
        if not self.result.found:
            self._show_result()
            self.draw()
            return
        self.display_visited = []
        self.display_path = []
        self.display_runner = None
        self._update_metrics(self.result)
        self.status.set(f"Animating {self.result.algorithm}.")
        self.details.set("Animation is running.\n\nBlue cells appear as the algorithm discovers the maze.")
        self._animate_visit(0)

    def compare_all(self) -> None:
        self._cancel_animation()
        lines: List[str] = []
        results: List[SearchResult] = []
        for label, key in ALGORITHMS.items():
            result = solve_maze(self.maze, key)
            results.append(result)
            cost = result.cost if result.found else float("inf")
            lines.append(
                f"{label}: discovered {result.explored_count}, "
                f"length {result.path_length}, cost {cost:g}"
            )
        best = min((result for result in results if result.found), key=lambda item: item.cost, default=None)
        if best is not None:
            lines.append("")
            lines.append(f"Lowest cost: {best.algorithm}")
        self.result = best
        self.display_visited = []
        self.display_path = list(best.path) if best is not None else []
        self.display_runner = None
        self.status.set("Compared every algorithm on this maze.")
        self.details.set("\n".join(lines))
        self._clear_metrics()
        if best is not None:
            self.metrics["algorithm"].configure(text=best.algorithm)
            self.metrics["cost"].configure(text=f"{best.cost:g}")
            self.metrics["length"].configure(text=str(best.path_length))
            self.metrics["weights"].configure(text=str(len(self.maze.weights)))
        self.draw()

    def reset_view(self, message: str = "View reset.") -> None:
        self._cancel_animation()
        self.result = None
        self.display_visited = []
        self.display_path = []
        self.display_runner = None
        self.status.set(message)
        self.details.set(self._maze_summary())
        self._clear_metrics()
        self.draw()

    def save_current_maze(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save maze file",
            initialdir=ROOT / "sample_mazes",
            initialfile="generated_maze.maze",
            defaultextension=".maze",
            filetypes=(("Graph maze files", "*.maze"), ("JSON files", "*.json"), ("All files", "*.*")),
        )
        if not path:
            return
        try:
            save_maze(self.maze, path)
            self.last_saved_path = Path(path)
            self.status.set(f"Saved {self.last_saved_path.name}.")
            self._refresh_file_label()
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))

    def export_run(self) -> None:
        if self.result is None:
            messagebox.showinfo("Nothing to export", "Run Solve, Animate, or Compare before exporting.")
            return
        directory = filedialog.askdirectory(title="Choose export folder", initialdir=ROOT / "sample_output")
        if not directory:
            return
        output = Path(directory)
        output.mkdir(parents=True, exist_ok=True)
        csv_path = output / "exploration.csv"
        stats_path = output / "statistics.txt"
        with csv_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file, lineterminator="\n")
            writer.writerow(["Step", "x-coordinate", "y-coordinate", "Event"])
            for index, (x, y) in enumerate(self.result.visited_order, start=1):
                writer.writerow([index, x, y, "goal" if (x, y) == self.result.goal else "visited"])
        stats_path.write_text(self._stats_export_text(self.result), encoding="utf-8")
        self.status.set(f"Exported exploration.csv and statistics.txt.")

    def _show_result(self) -> None:
        if self.result is None:
            return
        self._update_metrics(self.result)
        if not self.result.found:
            self.status.set(f"{self.result.algorithm} could not reach the goal.")
            self.details.set("No path found.")
            return
        note = ""
        if self.maze.weights and self._algorithm_key() in {"bfs", "dfs", "bidirectional", "greedy"}:
            note = "\n\nThis algorithm does not guarantee the cheapest weighted route. Use Dijkstra, A*, or Bellman-Ford."
        self.status.set(f"{self.result.algorithm} solved it. Yellow stays visible until Reset View.")
        self.details.set(
            f"Algorithm: {self.result.algorithm}\n"
            f"Discovered cells: {self.result.explored_count}\n"
            f"Path length: {self.result.path_length}\n"
            f"Path cost: {self.result.cost:g}\n"
            f"Weighted cells: {len(self.maze.weights)}\n"
            f"Open cells: {self.maze.open_cell_count}"
            f"{note}"
        )

    def _animate_visit(self, index: int) -> None:
        if self.result is None:
            return
        self.display_visited = self.result.visited_order[:index]
        self.display_path = []
        self.display_runner = None
        self.draw()
        if index < len(self.result.visited_order):
            self.animation_id = self.root.after(self._delay(), self._animate_visit, index + 1)
        else:
            self._animate_runner(0)

    def _animate_runner(self, index: int) -> None:
        if self.result is None:
            return
        path = self.result.path
        self.display_visited = list(self.result.visited_order)
        self.display_path = path[: index + 1]
        self.display_runner = path[min(index, len(path) - 1)]
        self.display_orientation = self._orientation_at(path, index)
        self.draw()
        if index < len(path) - 1:
            self.animation_id = self.root.after(self._delay(), self._animate_runner, index + 1)
        else:
            self.display_path = list(path)
            self.display_runner = path[-1]
            self._show_result()
            self.draw()

    def draw(self) -> None:
        if not hasattr(self, "canvas"):
            return
        self.canvas.delete("all")
        width = max(1, self.canvas.winfo_width() - self.margin * 2)
        height = max(1, self.canvas.winfo_height() - self.margin * 2)
        self.cell_size = max(10, min(46, width // self.maze.width, height // self.maze.height))
        grid_width = self.maze.width * self.cell_size
        grid_height = self.maze.height * self.cell_size
        self.origin_x = max(self.margin, (self.canvas.winfo_width() - grid_width) // 2)
        self.origin_y = max(self.margin, (self.canvas.winfo_height() - grid_height) // 2)

        self._draw_board_background(grid_width, grid_height)
        visited = set(self.display_visited)
        path = set(self.display_path)

        for y in range(self.maze.height):
            for x in range(self.maze.width):
                position = (x, y)
                x1, y1, x2, y2 = self._cell_box(position)
                is_blocked = position in self.maze.blocked
                fill = Palette.blocked if is_blocked else Palette.open_cell
                outline = Palette.blocked if is_blocked else Palette.grid
                if not is_blocked and position in self.maze.weights:
                    fill = Palette.weighted
                if position in visited:
                    fill = Palette.discovered
                if position in path:
                    fill = Palette.shortest
                if position == self.maze.start:
                    fill = Palette.start
                if position == self.maze.goal:
                    fill = Palette.goal
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=1)
                if position in self.maze.weights and not is_blocked:
                    self.canvas.create_text(
                        (x1 + x2) / 2,
                        (y1 + y2) / 2,
                        text=str(self.maze.weights[position]),
                        fill="#362d58",
                        font=("Helvetica", max(8, self.cell_size // 3), "bold"),
                    )

        self._draw_walls()
        if self.display_runner is not None:
            self._draw_runner(self.display_runner, self.display_orientation)

    def _draw_board_background(self, grid_width: int, grid_height: int) -> None:
        x1 = self.origin_x
        y1 = self.origin_y
        x2 = x1 + grid_width
        y2 = y1 + grid_height
        self.canvas.create_rectangle(x1 + 5, y1 + 5, x2 + 5, y2 + 5, fill="#d9d1c1", outline="")
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=Palette.open_cell, outline=Palette.wall, width=2)

    def _draw_walls(self) -> None:
        wall_width = max(2, int(self.cell_size * 0.08))
        for y in range(self.maze.height):
            for x in range(self.maze.width):
                if (x, y) in self.maze.blocked:
                    continue
                north, east, south, west = get_walls(self.maze, x, y)
                x1, y1, x2, y2 = self._cell_box((x, y))
                if north:
                    self.canvas.create_line(x1, y1, x2, y1, fill=Palette.wall, width=wall_width)
                if east:
                    self.canvas.create_line(x2, y1, x2, y2, fill=Palette.wall, width=wall_width)
                if south:
                    self.canvas.create_line(x1, y2, x2, y2, fill=Palette.wall, width=wall_width)
                if west:
                    self.canvas.create_line(x1, y1, x1, y2, fill=Palette.wall, width=wall_width)

    def _draw_runner(self, position: Position, orientation: str) -> None:
        x1, y1, x2, y2 = self._cell_box(position)
        pad = max(3, self.cell_size * 0.18)
        self.canvas.create_oval(x1 + pad, y1 + pad, x2 - pad, y2 - pad, fill=Palette.runner, outline="")
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        length = self.cell_size * 0.28
        dx, dy = {
            "N": (0, -length),
            "E": (length, 0),
            "S": (0, length),
            "W": (-length, 0),
        }[orientation]
        self.canvas.create_line(cx, cy, cx + dx, cy + dy, fill=Palette.white, width=3)

    def _cell_box(self, position: Position) -> tuple[float, float, float, float]:
        x, y = position
        screen_y = self.maze.height - 1 - y
        x1 = self.origin_x + x * self.cell_size
        y1 = self.origin_y + screen_y * self.cell_size
        return x1, y1, x1 + self.cell_size, y1 + self.cell_size

    def _orientation_at(self, path: List[Position], index: int) -> str:
        if len(path) < 2:
            return "N"
        if index <= 0:
            first, second = path[0], path[1]
        else:
            first, second = path[index - 1], path[min(index, len(path) - 1)]
        return {
            (0, 1): "N",
            (1, 0): "E",
            (0, -1): "S",
            (-1, 0): "W",
        }.get((second[0] - first[0], second[1] - first[1]), "N")

    def _algorithm_key(self) -> str:
        return ALGORITHMS[self.algorithm_label.get()]

    def _seed(self) -> int:
        text = self.seed_var.get().strip()
        if text:
            try:
                return int(text)
            except ValueError:
                messagebox.showwarning("Seed changed", "Seed must be a number, so a random seed was used.")
        seed = random.randint(1, 99999)
        self.seed_var.set(str(seed))
        return seed

    def _delay(self) -> int:
        return max(5, 135 - int(self.speed_var.get()))

    def _cancel_animation(self) -> None:
        if self.animation_id is not None:
            self.root.after_cancel(self.animation_id)
            self.animation_id = None

    def _update_metrics(self, result: SearchResult) -> None:
        self.metrics["algorithm"].configure(text=result.algorithm)
        self.metrics["explored"].configure(text=str(result.explored_count))
        self.metrics["length"].configure(text=str(result.path_length))
        self.metrics["cost"].configure(text=f"{result.cost:g}" if result.found else "-")
        self.metrics["weights"].configure(text=str(len(self.maze.weights)))

    def _clear_metrics(self) -> None:
        for value in self.metrics.values():
            value.configure(text="-")
        if hasattr(self, "metrics"):
            self.metrics["weights"].configure(text=str(len(self.maze.weights)))

    def _maze_summary(self) -> str:
        return (
            f"Current maze\n"
            f"Size: {self.maze.width} x {self.maze.height}\n"
            f"Open cells: {self.maze.open_cell_count}\n"
            f"Weighted cells: {len(self.maze.weights)}\n"
            f"Start: {self.maze.start}\n"
            f"Goal: {self.maze.goal}\n\n"
            f"Use Generate Weighted to create numbered terrain costs."
        )

    def _stats_export_text(self, result: SearchResult) -> str:
        return (
            f"Algorithm: {result.algorithm}\n"
            f"Dimensions: {self.maze.width} x {self.maze.height}\n"
            f"Start: {result.start}\n"
            f"Goal: {result.goal}\n"
            f"Found: {result.found}\n"
            f"Discovered cells: {result.explored_count}\n"
            f"Path length: {result.path_length}\n"
            f"Path cost: {result.cost:g}\n"
            f"Weighted cells: {len(self.maze.weights)}\n"
            f"Path positions: {result.path}\n"
        )

    def _refresh_file_label(
        self,
        generated: bool = False,
        seed: Optional[int] = None,
    ) -> None:
        if generated:
            self.file_label.configure(
                text=f"Generated in app\nSeed: {seed}\nWeighted cells: {len(self.maze.weights)}"
            )
        elif self.last_saved_path is not None:
            self.file_label.configure(text=f"File: {self.last_saved_path.name}\n{self.last_saved_path}")
        else:
            self.file_label.configure(text="Generated in app")


def run_gui(initial_maze_path: Optional[str] = None) -> None:
    root = tk.Tk()
    MazeApp(root, initial_maze_path=initial_maze_path)
    root.mainloop()


if __name__ == "__main__":
    run_gui()
