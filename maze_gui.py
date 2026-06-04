"""Tkinter visualiser for real-time maze pathfinding."""

from __future__ import annotations

from pathlib import Path
import random
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

from graph_algorithms import SearchResult, solve_maze
from maze import DIRECTIONS, Maze, Position, create_perfect_maze, get_walls, load_maze


ROOT = Path(__file__).resolve().parent
SAMPLE_FILES = [
    ROOT / "sample_mazes" / "small_maze1.mz",
    ROOT / "sample_mazes" / "maze1.mz",
    ROOT / "sample_mazes" / "maze2.mz",
    ROOT / "sample_mazes" / "weighted_maze.mz",
]


class MazeApp:
    def __init__(self, root: tk.Tk, initial_maze_path: Optional[str] = None):
        self.root = root
        self.root.title("Graph Maze Pathfinder")
        self.root.minsize(980, 680)

        self.algorithm = tk.StringVar(value="astar")
        self.maze_choice = tk.StringVar(value=str(SAMPLE_FILES[0]))
        self.speed = tk.IntVar(value=35)
        self.status = tk.StringVar(value="")

        self.maze = self._load_initial_maze(initial_maze_path)
        self.result: Optional[SearchResult] = None
        self.animation_id: Optional[str] = None
        self.cell_size = 28
        self.margin = 26

        self._build_layout()
        self.solve()

    def _build_layout(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f4f2ee")
        style.configure("Toolbar.TFrame", background="#e7e1d6")
        style.configure("TLabel", background="#f4f2ee", foreground="#24211d", font=("Helvetica", 12))
        style.configure("Toolbar.TLabel", background="#e7e1d6", foreground="#24211d", font=("Helvetica", 11))
        style.configure("TButton", font=("Helvetica", 11), padding=(10, 6))
        style.configure("TCombobox", padding=4)

        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True)

        toolbar = ttk.Frame(container, style="Toolbar.TFrame", padding=(14, 10))
        toolbar.pack(fill="x")

        ttk.Label(toolbar, text="Algorithm", style="Toolbar.TLabel").pack(side="left", padx=(0, 6))
        algorithm_box = ttk.Combobox(
            toolbar,
            textvariable=self.algorithm,
            values=("astar", "dijkstra", "bfs", "dfs"),
            width=10,
            state="readonly",
        )
        algorithm_box.pack(side="left", padx=(0, 14))
        algorithm_box.bind("<<ComboboxSelected>>", lambda _event: self.solve())

        ttk.Label(toolbar, text="Maze", style="Toolbar.TLabel").pack(side="left", padx=(0, 6))
        maze_box = ttk.Combobox(
            toolbar,
            textvariable=self.maze_choice,
            values=tuple(str(path) for path in SAMPLE_FILES if path.exists()),
            width=38,
            state="readonly",
        )
        maze_box.pack(side="left", padx=(0, 8))
        ttk.Button(toolbar, text="Load", command=self.load_selected).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="Browse", command=self.browse).pack(side="left", padx=(0, 14))
        ttk.Button(toolbar, text="Generate", command=self.generate).pack(side="left", padx=(0, 14))
        ttk.Button(toolbar, text="Solve", command=self.solve).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="Animate", command=self.animate).pack(side="left", padx=(0, 14))

        ttk.Label(toolbar, text="Speed", style="Toolbar.TLabel").pack(side="left", padx=(0, 4))
        ttk.Scale(toolbar, from_=5, to=120, variable=self.speed, orient="horizontal", length=120).pack(
            side="left"
        )

        self.canvas = tk.Canvas(container, bg="#faf9f4", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=14, pady=(14, 8))
        self.canvas.bind("<Configure>", lambda _event: self.draw())

        footer = ttk.Frame(container, padding=(14, 0, 14, 12))
        footer.pack(fill="x")
        ttk.Label(footer, textvariable=self.status).pack(side="left")

    def _load_initial_maze(self, initial_maze_path: Optional[str]) -> Maze:
        candidates = [Path(initial_maze_path)] if initial_maze_path else []
        candidates.extend(path for path in SAMPLE_FILES if path.exists())
        for path in candidates:
            if path and path.exists():
                self.maze_choice.set(str(path))
                return load_maze(path)
        return create_perfect_maze(14, 10, seed=4)

    def load_selected(self) -> None:
        try:
            self.maze = load_maze(self.maze_choice.get())
            self.solve()
        except Exception as exc:
            messagebox.showerror("Maze load failed", str(exc))

    def browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose a maze file",
            filetypes=(("Maze files", "*.mz"), ("Text files", "*.txt"), ("All files", "*.*")),
        )
        if path:
            self.maze_choice.set(path)
            self.load_selected()

    def generate(self) -> None:
        seed = random.randint(1, 10000)
        self.maze = create_perfect_maze(20, 13, seed=seed)
        self.maze_choice.set(f"Generated practice maze (seed {seed})")
        self.solve()

    def solve(self) -> None:
        self._cancel_animation()
        try:
            self.result = solve_maze(self.maze, self.algorithm.get())
            if self.result.found:
                self.status.set(
                    f"{self.result.algorithm}: explored {self.result.explored_count} cells, "
                    f"path length {self.result.path_length}, cost {self.result.cost:g}"
                )
            else:
                self.status.set(f"{self.result.algorithm}: no path found")
            self.draw(visited=self.result.visited_order, path=self.result.path)
        except Exception as exc:
            self.result = None
            self.status.set(str(exc))
            self.draw()

    def animate(self) -> None:
        if self.result is None:
            self.solve()
        if self.result is None or not self.result.found:
            return

        self._cancel_animation()
        self._animate_visit(0)

    def _animate_visit(self, index: int) -> None:
        assert self.result is not None
        visited = self.result.visited_order[:index]
        self.draw(visited=visited)
        if index <= len(self.result.visited_order):
            self.animation_id = self.root.after(self._delay(), self._animate_visit, index + 1)
        else:
            self._animate_runner(0)

    def _animate_runner(self, index: int) -> None:
        assert self.result is not None
        path = self.result.path
        visible_path = path[: index + 1]
        runner_position = path[min(index, len(path) - 1)]
        orientation = self._orientation_at(path, index)
        self.draw(
            visited=self.result.visited_order,
            path=visible_path,
            runner=runner_position,
            orientation=orientation,
        )
        if index < len(path) - 1:
            self.animation_id = self.root.after(self._delay(), self._animate_runner, index + 1)

    def draw(
        self,
        visited: Optional[List[Position]] = None,
        path: Optional[List[Position]] = None,
        runner: Optional[Position] = None,
        orientation: str = "N",
    ) -> None:
        self.canvas.delete("all")
        width = max(1, self.canvas.winfo_width() - self.margin * 2)
        height = max(1, self.canvas.winfo_height() - self.margin * 2)
        self.cell_size = max(12, min(42, width // self.maze.width, height // self.maze.height))
        grid_width = self.maze.width * self.cell_size
        grid_height = self.maze.height * self.cell_size
        self.origin_x = max(self.margin, (self.canvas.winfo_width() - grid_width) // 2)
        self.origin_y = max(self.margin, (self.canvas.winfo_height() - grid_height) // 2)

        visited_set = set(visited or [])
        path_set = set(path or [])

        for y in range(self.maze.height):
            for x in range(self.maze.width):
                position = (x, y)
                x1, y1, x2, y2 = self._cell_box(position)
                fill = "#262626" if position in self.maze.blocked else "#f7f4ea"
                if position in visited_set:
                    fill = "#a8d8ea"
                if position in path_set:
                    fill = "#f8d46b"
                if position == self.maze.start:
                    fill = "#5fbf8f"
                if position == self.maze.goal:
                    fill = "#ef767a"

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline="#ddd7ca", width=1)
                if position in self.maze.weights and position not in self.maze.blocked:
                    self.canvas.create_text(
                        (x1 + x2) / 2,
                        (y1 + y2) / 2,
                        text=str(self.maze.weights[position]),
                        fill="#4b463f",
                        font=("Helvetica", max(8, self.cell_size // 3), "bold"),
                    )

        self._draw_walls()
        if runner is not None:
            self._draw_runner(runner, orientation)

    def _draw_walls(self) -> None:
        for y in range(self.maze.height):
            for x in range(self.maze.width):
                if (x, y) in self.maze.blocked:
                    continue
                north, east, south, west = get_walls(self.maze, x, y)
                x1, y1, x2, y2 = self._cell_box((x, y))
                if north:
                    self.canvas.create_line(x1, y1, x2, y1, fill="#211f1c", width=3)
                if east:
                    self.canvas.create_line(x2, y1, x2, y2, fill="#211f1c", width=3)
                if south:
                    self.canvas.create_line(x1, y2, x2, y2, fill="#211f1c", width=3)
                if west:
                    self.canvas.create_line(x1, y1, x1, y2, fill="#211f1c", width=3)

    def _draw_runner(self, position: Position, orientation: str) -> None:
        x1, y1, x2, y2 = self._cell_box(position)
        pad = max(3, self.cell_size * 0.2)
        self.canvas.create_oval(x1 + pad, y1 + pad, x2 - pad, y2 - pad, fill="#304c89", outline="")
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        length = self.cell_size * 0.28
        dx, dy = {
            "N": (0, -length),
            "E": (length, 0),
            "S": (0, length),
            "W": (-length, 0),
        }[orientation]
        self.canvas.create_line(cx, cy, cx + dx, cy + dy, fill="#ffffff", width=3)

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
        delta = (second[0] - first[0], second[1] - first[1])
        return {
            (0, 1): "N",
            (1, 0): "E",
            (0, -1): "S",
            (-1, 0): "W",
        }.get(delta, "N")

    def _delay(self) -> int:
        return max(5, 130 - int(self.speed.get()))

    def _cancel_animation(self) -> None:
        if self.animation_id is not None:
            self.root.after_cancel(self.animation_id)
            self.animation_id = None


def run_gui(initial_maze_path: Optional[str] = None) -> None:
    root = tk.Tk()
    MazeApp(root, initial_maze_path=initial_maze_path)
    root.mainloop()


if __name__ == "__main__":
    run_gui()
