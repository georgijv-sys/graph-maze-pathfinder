"""Maze data model and file helpers for graph pathfinding.

The maze is stored as a graph-friendly grid. Each open cell is a node, and
valid moves to neighbouring cells are graph edges. The model also keeps the
wall-based helpers used by the original coursework API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import random
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


Position = Tuple[int, int]

DIRECTIONS: Tuple[str, ...] = ("N", "E", "S", "W")
DIRECTION_VECTORS: Dict[str, Position] = {
    "N": (0, 1),
    "E": (1, 0),
    "S": (0, -1),
    "W": (-1, 0),
}


@dataclass
class Maze:
    width: int
    height: int
    blocked: Set[Position] = field(default_factory=set)
    horizontal_walls: Set[Position] = field(default_factory=set)
    vertical_walls: Set[Position] = field(default_factory=set)
    weights: Dict[Position, int] = field(default_factory=dict)
    start: Position = (0, 0)
    goal: Optional[Position] = None

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Maze dimensions must be positive")
        self.goal = self.goal if self.goal is not None else (self.width - 1, self.height - 1)
        self._add_outer_walls()
        self._validate_cells()

    def _add_outer_walls(self) -> None:
        for x in range(self.width):
            self.horizontal_walls.add((x, 0))
            self.horizontal_walls.add((x, self.height))
        for y in range(self.height):
            self.vertical_walls.add((0, y))
            self.vertical_walls.add((self.width, y))

    def _validate_cells(self) -> None:
        for cell in self.blocked | set(self.weights):
            if not self.in_bounds(cell):
                raise ValueError(f"Cell outside maze bounds: {cell}")
        for cell, weight in self.weights.items():
            if weight < 1:
                raise ValueError(f"Movement cost must be >= 1: {cell} = {weight}")
        if not self.is_open(self.start):
            raise ValueError(f"Start cell is blocked or outside bounds: {self.start}")
        if self.goal is not None and not self.is_open(self.goal):
            raise ValueError(f"Goal cell is blocked or outside bounds: {self.goal}")

    @property
    def open_cell_count(self) -> int:
        return self.width * self.height - len(self.blocked)

    def in_bounds(self, position: Position) -> bool:
        x, y = position
        return 0 <= x < self.width and 0 <= y < self.height

    def is_open(self, position: Position) -> bool:
        return self.in_bounds(position) and position not in self.blocked

    def movement_cost(self, position: Position) -> int:
        return self.weights.get(position, 1)

    def has_wall_between(self, first: Position, second: Position) -> bool:
        if not self.is_open(first) or not self.is_open(second):
            return True

        x1, y1 = first
        x2, y2 = second
        dx, dy = x2 - x1, y2 - y1

        if abs(dx) + abs(dy) != 1:
            raise ValueError("Wall checks require adjacent cells")
        if dx == 1:
            return (x2, y1) in self.vertical_walls
        if dx == -1:
            return (x1, y1) in self.vertical_walls
        if dy == 1:
            return (x1, y2) in self.horizontal_walls
        return (x1, y1) in self.horizontal_walls

    def neighbours(self, position: Position) -> List[Position]:
        result: List[Position] = []
        for direction in DIRECTIONS:
            dx, dy = DIRECTION_VECTORS[direction]
            candidate = (position[0] + dx, position[1] + dy)
            if self.is_open(candidate) and not self.has_wall_between(position, candidate):
                result.append(candidate)
        return result

    def get_walls(self, x: int, y: int) -> Tuple[bool, bool, bool, bool]:
        position = (x, y)
        walls: List[bool] = []
        for direction in DIRECTIONS:
            dx, dy = DIRECTION_VECTORS[direction]
            candidate = (x + dx, y + dy)
            walls.append(not self.is_open(candidate) or self.has_wall_between(position, candidate))
        return walls[0], walls[1], walls[2], walls[3]

    def add_horizontal_wall(self, x: int, horizontal_line: int) -> None:
        if not (0 <= x < self.width and 0 <= horizontal_line <= self.height):
            raise ValueError("Horizontal wall outside maze bounds")
        self.horizontal_walls.add((x, horizontal_line))

    def add_vertical_wall(self, y: int, vertical_line: int) -> None:
        if not (0 <= vertical_line <= self.width and 0 <= y < self.height):
            raise ValueError("Vertical wall outside maze bounds")
        self.vertical_walls.add((vertical_line, y))

    def clear_cell(self, position: Position, remove_adjacent_walls: bool = False) -> None:
        """Open a cell and optionally carve through its internal wall borders."""
        if not self.in_bounds(position):
            return
        self.blocked.discard(position)
        self.weights.pop(position, None)
        if remove_adjacent_walls:
            self.remove_adjacent_walls(position)

    def remove_adjacent_walls(self, position: Position) -> None:
        """Remove internal walls around a cell without deleting the outer border."""
        if not self.in_bounds(position):
            return
        x, y = position
        if y > 0:
            self.horizontal_walls.discard((x, y))
        if y < self.height - 1:
            self.horizontal_walls.discard((x, y + 1))
        if x > 0:
            self.vertical_walls.discard((x, y))
        if x < self.width - 1:
            self.vertical_walls.discard((x + 1, y))

    def to_ascii(
        self,
        path: Optional[Iterable[Position]] = None,
        visited: Optional[Iterable[Position]] = None,
    ) -> str:
        path_cells = set(path or [])
        visited_cells = set(visited or [])
        lines: List[str] = []
        for y in range(self.height - 1, -1, -1):
            chars: List[str] = []
            for x in range(self.width):
                position = (x, y)
                if position == self.start:
                    chars.append("S")
                elif position == self.goal:
                    chars.append("G")
                elif position in self.blocked:
                    chars.append("#")
                elif position in path_cells:
                    chars.append("*")
                elif position in visited_cells:
                    chars.append("+")
                elif position in self.weights:
                    chars.append(str(self.weights[position]))
                else:
                    chars.append(".")
            lines.append("".join(chars))
        return "\n".join(lines)


def create_maze(width: int = 5, height: int = 5) -> Maze:
    return Maze(width=width, height=height)


def add_horizontal_wall(maze: Maze, x_coordinate: int, horizontal_line: int) -> Maze:
    maze.add_horizontal_wall(x_coordinate, horizontal_line)
    return maze


def add_vertical_wall(maze: Maze, y_coordinate: int, vertical_line: int) -> Maze:
    maze.add_vertical_wall(y_coordinate, vertical_line)
    return maze


def get_dimensions(maze: Maze) -> Tuple[int, int]:
    return maze.width, maze.height


def get_walls(maze: Maze, x_coordinate: int, y_coordinate: int) -> Tuple[bool, bool, bool, bool]:
    return maze.get_walls(x_coordinate, y_coordinate)


def parse_ascii_maze(text: str) -> Maze:
    lines = [line.rstrip("\n") for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("Maze file is empty")
    if any(len(line) != len(lines[0]) for line in lines):
        raise ValueError("Maze must be rectangular")

    has_border = _has_solid_hash_border(lines)
    rows = lines[1:-1] if has_border else lines
    if has_border:
        rows = [row[1:-1] for row in rows]

    height = len(rows)
    width = len(rows[0]) if rows else 0
    blocked: Set[Position] = set()
    weights: Dict[Position, int] = {}
    start: Optional[Position] = None
    goal: Optional[Position] = None

    for file_y, row in enumerate(rows):
        y = height - 1 - file_y
        for x, char in enumerate(row):
            position = (x, y)
            if char == "#":
                blocked.add(position)
            elif char == "S":
                start = position
            elif char == "G":
                goal = position
            elif char.isdigit():
                # Only 2-9 are weighted terrain; '0' and '1' cost the same as a
                # plain open cell, so storing them would mislabel them as weighted.
                weight = int(char)
                if weight >= 2:
                    weights[position] = weight
            elif char not in {".", " "}:
                raise ValueError(f"Unsupported maze character {char!r} at {(x, y)}")

    return Maze(
        width=width,
        height=height,
        blocked=blocked,
        weights=weights,
        start=start or (0, 0),
        goal=goal or (width - 1, height - 1),
    )


def load_maze(path: str | Path) -> Maze:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise IOError(f"Cannot read maze file: {path}") from exc
    stripped = text.lstrip()
    if stripped.startswith("{"):
        return maze_from_json(json.loads(stripped))
    return parse_ascii_maze(text)


def save_maze(maze: Maze, path: str | Path) -> None:
    Path(path).write_text(json.dumps(maze_to_json(maze), indent=2), encoding="utf-8")


def maze_to_json(maze: Maze) -> Dict[str, Any]:
    return {
        "format": "graph-maze-pathfinder",
        "width": maze.width,
        "height": maze.height,
        "blocked": _positions_to_lists(maze.blocked),
        "horizontal_walls": _positions_to_lists(maze.horizontal_walls),
        "vertical_walls": _positions_to_lists(maze.vertical_walls),
        "weights": [
            {"x": x, "y": y, "cost": cost}
            for (x, y), cost in sorted(maze.weights.items())
        ],
        "start": list(maze.start),
        "goal": list(maze.goal) if maze.goal is not None else None,
    }


def maze_from_json(data: Dict[str, Any]) -> Maze:
    if data.get("format") != "graph-maze-pathfinder":
        raise ValueError("Unsupported maze JSON format")
    return Maze(
        width=int(data["width"]),
        height=int(data["height"]),
        blocked=_lists_to_positions(data.get("blocked", [])),
        horizontal_walls=_lists_to_positions(data.get("horizontal_walls", [])),
        vertical_walls=_lists_to_positions(data.get("vertical_walls", [])),
        weights={
            (int(item["x"]), int(item["y"])): int(item["cost"])
            for item in data.get("weights", [])
        },
        start=tuple(data.get("start", (0, 0))),  # type: ignore[arg-type]
        goal=tuple(data["goal"]) if data.get("goal") is not None else None,
    )


def create_perfect_maze(width: int, height: int, seed: Optional[int] = None) -> Maze:
    """Create a connected maze by carving passages with randomized DFS."""
    rng = random.Random(seed)
    maze = create_maze(width, height)

    for x in range(width):
        for y in range(1, height):
            maze.add_horizontal_wall(x, y)
    for y in range(height):
        for x in range(1, width):
            maze.add_vertical_wall(y, x)

    start = (0, 0)
    visited = {start}
    stack = [start]

    while stack:
        current = stack[-1]
        candidates = []
        for direction, (dx, dy) in DIRECTION_VECTORS.items():
            nxt = (current[0] + dx, current[1] + dy)
            if maze.in_bounds(nxt) and nxt not in visited:
                candidates.append((direction, nxt))
        if not candidates:
            stack.pop()
            continue

        direction, nxt = rng.choice(candidates)
        _remove_wall_between(maze, current, nxt, direction)
        visited.add(nxt)
        stack.append(nxt)

    maze.start = start
    maze.goal = (width - 1, height - 1)
    return maze


def add_random_weights(
    maze: Maze,
    density: float = 0.2,
    minimum: int = 2,
    maximum: int = 9,
    seed: Optional[int] = None,
) -> Maze:
    rng = random.Random(seed)
    density = min(1.0, max(0.0, density))
    candidates = [
        (x, y)
        for y in range(maze.height)
        for x in range(maze.width)
        if (x, y) not in {maze.start, maze.goal} and maze.is_open((x, y))
    ]
    rng.shuffle(candidates)
    target_count = int(round(len(candidates) * density))
    if density > 0 and candidates:
        target_count = max(1, target_count)
    for position in candidates[:target_count]:
        maze.weights[position] = rng.randint(minimum, maximum)
    return maze


def _has_solid_hash_border(lines: List[str]) -> bool:
    if len(lines) < 3 or len(lines[0]) < 3:
        return False
    return (
        all(char == "#" for char in lines[0])
        and all(char == "#" for char in lines[-1])
        and all(line[0] == "#" and line[-1] == "#" for line in lines)
    )


def _remove_wall_between(maze: Maze, first: Position, second: Position, direction: str) -> None:
    x1, y1 = first
    x2, y2 = second
    if direction == "E":
        maze.vertical_walls.discard((x2, y1))
    elif direction == "W":
        maze.vertical_walls.discard((x1, y1))
    elif direction == "N":
        maze.horizontal_walls.discard((x1, y2))
    elif direction == "S":
        maze.horizontal_walls.discard((x1, y1))


def _positions_to_lists(positions: Iterable[Position]) -> List[List[int]]:
    return [[x, y] for x, y in sorted(positions)]


def _lists_to_positions(items: Iterable[Iterable[int]]) -> Set[Position]:
    return {(int(x), int(y)) for x, y in items}
