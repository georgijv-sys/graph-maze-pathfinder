from typing import Optional, Tuple, List
from maze import get_dimensions
from maze import get_walls


def create_runner(x: int = 0, y: int = 0, orientation: str = "N"):
    """
    The runner is represented as a dict with keys "x", "y"
     and "orientation".
    A dict is easy to mutate in-place and pass to other functions.
    """
    return {"x": x, "y": y, "orientation": orientation}


def get_x(runner):
    return runner["x"]


def get_y(runner):
    return runner["y"]


def get_orientation(runner):
    return runner["orientation"]


def turn(runner, direction: str):
    """turn()/forward() update the runner in-place and also return it."""
    orientation = runner["orientation"]

    if direction == "Left":
        if orientation == "N":
            runner["orientation"] = "W"
        elif orientation == "W":
            runner["orientation"] = "S"
        elif orientation == "S":
            runner["orientation"] = "E"
        elif orientation == "E":
            runner["orientation"] = "N"
    elif direction == "Right":
        if orientation == "N":
            runner["orientation"] = "E"
        elif orientation == "E":
            runner["orientation"] = "S"
        elif orientation == "S":
            runner["orientation"] = "W"
        elif orientation == "W":
            runner["orientation"] = "N"

    return runner


def forward(runner):
    orientation = runner["orientation"]

    if orientation == "N":
        runner["y"] = runner["y"] + 1
    elif orientation == "S":
        runner["y"] = runner["y"] - 1
    elif orientation == "E":
        runner["x"] = runner["x"] + 1
    elif orientation == "W":
        runner["x"] = runner["x"] - 1

    return runner


def sense_walls(runner, maze) -> Tuple[bool, bool, bool]:
    """Checking whether there is a wall on the Left,
    the Front, and the Right of the runner."""
    x = runner["x"]
    y = runner["y"]
    orientation = runner["orientation"]

    """Reusing maze.get_walls() to check for the walls of a specific cell"""
    north, east, south, west = get_walls(maze, x, y)

    """Mapping the walls of a specific cell to a specific direction"""
    if orientation == "N":
        left_wall = west
        front_wall = north
        right_wall = east

    elif orientation == "E":
        left_wall = north
        front_wall = east
        right_wall = south

    elif orientation == "S":
        left_wall = east
        front_wall = south
        right_wall = west

    elif orientation == "W":
        left_wall = south
        front_wall = west
        right_wall = north

    return left_wall, front_wall, right_wall


def go_straight(runner, maze):
    """Checks the front wall, if present raises ValueError."""
    left_wall, front_wall, right_wall = sense_walls(runner, maze)

    if front_wall:
        raise ValueError("There is a wall in front of the runner")

    return forward(runner)


def move(runner, maze):
    """Using a left-hug: checks left, then straight, then right,
    and goes back of all are blocked."""
    left_wall, front_wall, right_wall = sense_walls(runner, maze)

    # L + F
    if not left_wall:
        turn(runner, "Left")
        forward(runner)
        return runner, "LF"

    # F
    if not front_wall:
        forward(runner)
        return runner, "F"

    # 3. R + F
    if not right_wall:
        turn(runner, "Right")
        forward(runner)
        return runner, "RF"

    # 4. "B"
    turn(runner, "Left")
    turn(runner, "Left")
    forward(runner)
    return runner, "B"


def explore(
    runner, maze, goal: Optional[Tuple[int, int]] = None
) -> List[Tuple[int, int, str]]:
    """Explores the maze.
    Stores the position BEFORE the move"""
    width, height = get_dimensions(maze)

    # If goal is not defined, defines it as the top right corner
    if goal is None:
        goal = (width - 1, height - 1)

    path: List[Tuple[int, int, str]] = []

    while (runner["x"], runner["y"]) != goal:
        x, y = runner["x"], runner["y"]
        runner, actions = move(runner, maze)
        path.append((x, y, actions))

    return path
