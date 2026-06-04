"""Runner movement helpers.

The runner keeps position and orientation, while pathfinding operates on graph
cells. This module bridges those ideas by turning cell paths into movement
commands and by retaining the original left-hand exploration behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from maze import DIRECTIONS, DIRECTION_VECTORS, Maze, Position, get_dimensions, get_walls


ActionStep = Tuple[int, int, str]


@dataclass
class Runner:
    x: int = 0
    y: int = 0
    orientation: str = "N"

    @property
    def position(self) -> Position:
        return self.x, self.y


def create_runner(x: int = 0, y: int = 0, orientation: str = "N") -> Runner:
    if orientation not in DIRECTIONS:
        raise ValueError(f"Invalid orientation: {orientation}")
    return Runner(x=x, y=y, orientation=orientation)


def get_x(runner: Runner) -> int:
    return runner.x


def get_y(runner: Runner) -> int:
    return runner.y


def get_orientation(runner: Runner) -> str:
    return runner.orientation


def turn(runner: Runner, direction: str) -> Runner:
    current_index = DIRECTIONS.index(runner.orientation)
    if direction in {"Left", "L"}:
        runner.orientation = DIRECTIONS[(current_index - 1) % 4]
    elif direction in {"Right", "R"}:
        runner.orientation = DIRECTIONS[(current_index + 1) % 4]
    elif direction in {"Back", "B"}:
        runner.orientation = DIRECTIONS[(current_index + 2) % 4]
    else:
        raise ValueError("Turn direction must be Left, Right, Back, L, R, or B")
    return runner


def forward(runner: Runner) -> Runner:
    dx, dy = DIRECTION_VECTORS[runner.orientation]
    runner.x += dx
    runner.y += dy
    return runner


def sense_walls(runner: Runner, maze: Maze) -> Tuple[bool, bool, bool]:
    north, east, south, west = get_walls(maze, runner.x, runner.y)
    by_direction = {"N": north, "E": east, "S": south, "W": west}
    index = DIRECTIONS.index(runner.orientation)
    left = by_direction[DIRECTIONS[(index - 1) % 4]]
    front = by_direction[runner.orientation]
    right = by_direction[DIRECTIONS[(index + 1) % 4]]
    return left, front, right


def go_straight(runner: Runner, maze: Maze) -> Runner:
    _left_wall, front_wall, _right_wall = sense_walls(runner, maze)
    if front_wall:
        raise ValueError("There is a wall in front of the runner")
    return forward(runner)


def move(runner: Runner, maze: Maze) -> Tuple[Runner, str]:
    left_wall, front_wall, right_wall = sense_walls(runner, maze)
    if not left_wall:
        turn(runner, "Left")
        forward(runner)
        return runner, "LF"
    if not front_wall:
        forward(runner)
        return runner, "F"
    if not right_wall:
        turn(runner, "Right")
        forward(runner)
        return runner, "RF"
    turn(runner, "Back")
    forward(runner)
    return runner, "BF"


def explore(
    runner: Runner,
    maze: Maze,
    goal: Optional[Position] = None,
    max_steps: Optional[int] = None,
) -> List[ActionStep]:
    width, height = get_dimensions(maze)
    goal = goal or maze.goal or (width - 1, height - 1)
    max_steps = max_steps or max(50, width * height * 8)
    path: List[ActionStep] = []

    for _ in range(max_steps):
        if runner.position == goal:
            return path
        x, y = runner.position
        runner, actions = move(runner, maze)
        path.append((x, y, actions))

    raise RuntimeError("Exploration did not reach the goal before max_steps")


def positions_to_actions(
    positions: List[Position],
    starting_orientation: str = "N",
) -> List[ActionStep]:
    if len(positions) < 2:
        return []

    result: List[ActionStep] = []
    orientation = starting_orientation

    for current, nxt in zip(positions, positions[1:]):
        dx = nxt[0] - current[0]
        dy = nxt[1] - current[1]
        move_direction = _direction_from_delta(dx, dy)
        diff = (DIRECTIONS.index(move_direction) - DIRECTIONS.index(orientation)) % 4

        if diff == 0:
            turn_code = ""
        elif diff == 1:
            turn_code = "R"
        elif diff == 2:
            turn_code = "B"
        else:
            turn_code = "L"

        result.append((current[0], current[1], f"{turn_code}F"))
        orientation = move_direction

    return result


def _direction_from_delta(dx: int, dy: int) -> str:
    for direction, vector in DIRECTION_VECTORS.items():
        if vector == (dx, dy):
            return direction
    raise ValueError(f"Path contains non-adjacent step: delta {(dx, dy)}")
