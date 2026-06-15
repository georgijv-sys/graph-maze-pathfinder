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
        "bidirectional": bidirectional_breadth_first_search,
        "dfs": depth_first_search,
        "dijkstra": dijkstra_search,
        "greedy": greedy_best_first_search,
        "bellmanford": bellman_ford_search,
        "astar": a_star_search,
    }
    return functions[name](maze, start=start, goal=goal)


def normalise_algorithm_name(name: str) -> str:
    cleaned = name.lower().replace("*", "star").replace("-", "").replace("_", "")
    aliases = {
        "breadthfirst": "bfs",
        "breadthfirstsearch": "bfs",
        "bibfs": "bidirectional",
        "bidirectionalbfs": "bidirectional",
        "bidirectionalbreadthfirst": "bidirectional",
        "bidirectionalbreadthfirstsearch": "bidirectional",
        "depthfirst": "dfs",
        "depthfirstsearch": "dfs",
        "a": "astar",
        "astarsearch": "astar",
        "greedybestfirst": "greedy",
        "greedybestfirstsearch": "greedy",
        "bestfirst": "greedy",
        "bellman": "bellmanford",
        "bellmanfordsearch": "bellmanford",
    }
    cleaned = aliases.get(cleaned, cleaned)
    if cleaned not in {"bfs", "bidirectional", "dfs", "dijkstra", "greedy", "bellmanford", "astar"}:
        raise ValueError(
            "Algorithm must be one of: bfs, bidirectional, dfs, dijkstra, greedy, bellmanford, astar"
        )
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


def bidirectional_breadth_first_search(
    maze: Maze,
    start: Optional[Position] = None,
    goal: Optional[Position] = None,
) -> SearchResult:
    start, goal = _resolve_endpoints(maze, start, goal)
    if start == goal:
        return _result("Bidirectional BFS", maze, start, goal, [start], [start])

    front_start: deque[Position] = deque([start])
    front_goal: deque[Position] = deque([goal])
    parent_start: Dict[Position, Optional[Position]] = {start: None}
    parent_goal: Dict[Position, Optional[Position]] = {goal: None}
    visited_order: List[Position] = []
    meeting: Optional[Position] = None

    while front_start and front_goal and meeting is None:
        meeting = _expand_bidirectional_frontier(
            maze, front_start, parent_start, parent_goal, visited_order
        )
        if meeting is not None:
            break
        meeting = _expand_bidirectional_frontier(
            maze, front_goal, parent_goal, parent_start, visited_order
        )

    path = _reconstruct_bidirectional_path(parent_start, parent_goal, start, goal, meeting)
    return _result("Bidirectional BFS", maze, start, goal, path, visited_order)


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


def greedy_best_first_search(
    maze: Maze,
    start: Optional[Position] = None,
    goal: Optional[Position] = None,
    heuristic: Optional[Heuristic] = None,
) -> SearchResult:
    start, goal = _resolve_endpoints(maze, start, goal)
    heuristic = heuristic or manhattan_distance
    frontier: List[Tuple[float, Position]] = [(heuristic(start, goal), start)]
    came_from: Dict[Position, Optional[Position]] = {start: None}
    visited_order: List[Position] = []
    expanded: Set[Position] = set()

    while frontier:
        _priority, current = heapq.heappop(frontier)
        if current in expanded:
            continue
        expanded.add(current)
        visited_order.append(current)
        if current == goal:
            break
        for nxt in maze.neighbours(current):
            if nxt not in came_from:
                came_from[nxt] = current
                heapq.heappush(frontier, (heuristic(nxt, goal), nxt))

    path = _reconstruct_path(came_from, start, goal)
    return _result("Greedy Best-First", maze, start, goal, path, visited_order)


def bellman_ford_search(
    maze: Maze,
    start: Optional[Position] = None,
    goal: Optional[Position] = None,
) -> SearchResult:
    start, goal = _resolve_endpoints(maze, start, goal)
    open_cells = [
        (x, y)
        for y in range(maze.height)
        for x in range(maze.width)
        if maze.is_open((x, y))
    ]
    distances: Dict[Position, float] = {cell: math.inf for cell in open_cells}
    parents: Dict[Position, Optional[Position]] = {start: None}
    distances[start] = 0
    visited_order: List[Position] = []
    visited_seen: Set[Position] = set()

    for _ in range(max(0, len(open_cells) - 1)):
        changed = False
        for current in open_cells:
            if distances[current] == math.inf:
                continue
            if current not in visited_seen:
                visited_seen.add(current)
                visited_order.append(current)
            for nxt in maze.neighbours(current):
                candidate = distances[current] + maze.movement_cost(nxt)
                if candidate < distances[nxt]:
                    distances[nxt] = candidate
                    parents[nxt] = current
                    changed = True
        if not changed:
            break

    path = _reconstruct_path(parents, start, goal)
    return _result("Bellman-Ford", maze, start, goal, path, visited_order)


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


def _expand_bidirectional_frontier(
    maze: Maze,
    frontier: deque[Position],
    own_parent: Dict[Position, Optional[Position]],
    other_parent: Dict[Position, Optional[Position]],
    visited_order: List[Position],
) -> Optional[Position]:
    # Expand exactly one BFS layer (the queue length captured up front), so the
    # two searches advance in lock-step. Returning on the first node that the
    # other side has already reached is shortest-path-optimal for unweighted
    # graphs: both frontiers grow by one layer per call, so the first contact
    # happens on the minimal-sum layer boundary.
    for _ in range(len(frontier)):
        current = frontier.popleft()
        visited_order.append(current)
        for nxt in maze.neighbours(current):
            if nxt not in own_parent:
                own_parent[nxt] = current
                if nxt in other_parent:
                    return nxt
                frontier.append(nxt)
    return None


def _reconstruct_bidirectional_path(
    parent_start: Dict[Position, Optional[Position]],
    parent_goal: Dict[Position, Optional[Position]],
    start: Position,
    goal: Position,
    meeting: Optional[Position],
) -> List[Position]:
    if meeting is None:
        return []

    first_half: List[Position] = []
    current: Optional[Position] = meeting
    while current is not None:
        first_half.append(current)
        current = parent_start[current]
    first_half.reverse()
    if first_half[0] != start:
        return []

    second_half: List[Position] = []
    current = parent_goal[meeting]
    while current is not None:
        second_half.append(current)
        current = parent_goal[current]

    path = first_half + second_half
    return path if path and path[-1] == goal else []


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
