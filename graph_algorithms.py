"""Graph search algorithms for maze pathfinding."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import heapq
import math
from typing import Callable, Dict, List, Optional, Set, Tuple

from maze import Maze, Position


Heuristic = Callable[[Position, Position], float]


@dataclass
class SearchResult:
    algorithm: str
    start: Position
    goal: Position
    path: List[Position]
    visited_order: List[Position]
    cost: float

    @property
    def found(self) -> bool:
        return bool(self.path)

    @property
    def path_length(self) -> int:
        return max(0, len(self.path) - 1)

    @property
    def explored_count(self) -> int:
        return len(self.visited_order)


def solve_maze(
    maze: Maze,
    algorithm: str = "astar",
    start: Optional[Position] = None,
    goal: Optional[Position] = None,
) -> SearchResult:
    name = normalise_algorithm_name(algorithm)
    functions = {
        "bfs": breadth_first_search,
        "dfs": depth_first_search,
        "dijkstra": dijkstra_search,
        "astar": a_star_search,
    }
    return functions[name](maze, start=start, goal=goal)


def normalise_algorithm_name(name: str) -> str:
    cleaned = name.lower().replace("*", "star").replace("-", "").replace("_", "")
    aliases = {
        "breadthfirst": "bfs",
        "breadthfirstsearch": "bfs",
        "depthfirst": "dfs",
        "depthfirstsearch": "dfs",
        "a": "astar",
        "astarsearch": "astar",
    }
    cleaned = aliases.get(cleaned, cleaned)
    if cleaned not in {"bfs", "dfs", "dijkstra", "astar"}:
        raise ValueError("Algorithm must be one of: bfs, dfs, dijkstra, astar")
    return cleaned


def breadth_first_search(
    maze: Maze,
    start: Optional[Position] = None,
    goal: Optional[Position] = None,
) -> SearchResult:
    start, goal = _resolve_endpoints(maze, start, goal)
    frontier: deque[Position] = deque([start])
    came_from: Dict[Position, Optional[Position]] = {start: None}
    visited_order: List[Position] = []

    while frontier:
        current = frontier.popleft()
        visited_order.append(current)
        if current == goal:
            break
        for nxt in maze.neighbours(current):
            if nxt not in came_from:
                came_from[nxt] = current
                frontier.append(nxt)

    path = _reconstruct_path(came_from, start, goal)
    return _result("BFS", maze, start, goal, path, visited_order)


def depth_first_search(
    maze: Maze,
    start: Optional[Position] = None,
    goal: Optional[Position] = None,
) -> SearchResult:
    start, goal = _resolve_endpoints(maze, start, goal)
    stack: List[Position] = [start]
    came_from: Dict[Position, Optional[Position]] = {start: None}
    visited_order: List[Position] = []
    expanded: Set[Position] = set()

    while stack:
        current = stack.pop()
        if current in expanded:
            continue
        expanded.add(current)
        visited_order.append(current)
        if current == goal:
            break
        for nxt in reversed(maze.neighbours(current)):
            if nxt not in came_from:
                came_from[nxt] = current
                stack.append(nxt)

    path = _reconstruct_path(came_from, start, goal)
    return _result("DFS", maze, start, goal, path, visited_order)


def dijkstra_search(
    maze: Maze,
    start: Optional[Position] = None,
    goal: Optional[Position] = None,
) -> SearchResult:
    start, goal = _resolve_endpoints(maze, start, goal)
    frontier: List[Tuple[float, Position]] = [(0, start)]
    came_from: Dict[Position, Optional[Position]] = {start: None}
    cost_so_far: Dict[Position, float] = {start: 0}
    visited_order: List[Position] = []
    settled: Set[Position] = set()

    while frontier:
        _priority, current = heapq.heappop(frontier)
        if current in settled:
            continue
        settled.add(current)
        visited_order.append(current)
        if current == goal:
            break
        for nxt in maze.neighbours(current):
            new_cost = cost_so_far[current] + maze.movement_cost(nxt)
            if nxt not in cost_so_far or new_cost < cost_so_far[nxt]:
                cost_so_far[nxt] = new_cost
                came_from[nxt] = current
                heapq.heappush(frontier, (new_cost, nxt))

    path = _reconstruct_path(came_from, start, goal)
    return _result("Dijkstra", maze, start, goal, path, visited_order)


def a_star_search(
    maze: Maze,
    start: Optional[Position] = None,
    goal: Optional[Position] = None,
    heuristic: Optional[Heuristic] = None,
) -> SearchResult:
    start, goal = _resolve_endpoints(maze, start, goal)
    heuristic = heuristic or manhattan_distance
    frontier: List[Tuple[float, float, Position]] = [(0, 0, start)]
    came_from: Dict[Position, Optional[Position]] = {start: None}
    cost_so_far: Dict[Position, float] = {start: 0}
    visited_order: List[Position] = []
    settled: Set[Position] = set()

    while frontier:
        _priority, current_cost, current = heapq.heappop(frontier)
        if current in settled:
            continue
        settled.add(current)
        visited_order.append(current)
        if current == goal:
            break
        for nxt in maze.neighbours(current):
            new_cost = current_cost + maze.movement_cost(nxt)
            if nxt not in cost_so_far or new_cost < cost_so_far[nxt]:
                cost_so_far[nxt] = new_cost
                came_from[nxt] = current
                priority = new_cost + heuristic(nxt, goal)
                heapq.heappush(frontier, (priority, new_cost, nxt))

    path = _reconstruct_path(came_from, start, goal)
    return _result("A*", maze, start, goal, path, visited_order)


def manhattan_distance(first: Position, second: Position) -> float:
    return abs(first[0] - second[0]) + abs(first[1] - second[1])


def _resolve_endpoints(
    maze: Maze,
    start: Optional[Position],
    goal: Optional[Position],
) -> Tuple[Position, Position]:
    resolved_start = start or maze.start
    resolved_goal = goal or maze.goal
    if resolved_goal is None:
        raise ValueError("Goal is not set")
    if not maze.is_open(resolved_start):
        raise ValueError(f"Start cell is not open: {resolved_start}")
    if not maze.is_open(resolved_goal):
        raise ValueError(f"Goal cell is not open: {resolved_goal}")
    return resolved_start, resolved_goal


def _reconstruct_path(
    came_from: Dict[Position, Optional[Position]],
    start: Position,
    goal: Position,
) -> List[Position]:
    if goal not in came_from:
        return []
    current: Optional[Position] = goal
    path: List[Position] = []
    while current is not None:
        path.append(current)
        current = came_from[current]
    path.reverse()
    return path if path and path[0] == start else []


def _result(
    algorithm: str,
    maze: Maze,
    start: Position,
    goal: Position,
    path: List[Position],
    visited_order: List[Position],
) -> SearchResult:
    cost = _path_cost(maze, path) if path else math.inf
    return SearchResult(
        algorithm=algorithm,
        start=start,
        goal=goal,
        path=path,
        visited_order=visited_order,
        cost=cost,
    )


def _path_cost(maze: Maze, path: List[Position]) -> float:
    return sum(maze.movement_cost(position) for position in path[1:])
