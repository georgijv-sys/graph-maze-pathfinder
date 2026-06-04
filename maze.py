from typing import Tuple


def create_maze(width: int = 5, height: int = 5):
    """The maze is represented as a dict which uses keys:
       "width", "height" (int)
       "horizontal_walls", "vertical_walls"
       (sets of coordinate tuples).
    This keeps all maze data in one object and allows
    to pass between functions."""
    horizontal_walls = set()
    vertical_walls = set()

    # adding outer walls
    for x in range(width):
        horizontal_walls.add((x, 0))  # lower
        horizontal_walls.add((x, height))  # upper
    for y in range(height):
        vertical_walls.add((0, y))  # left
        vertical_walls.add((width, y))  # right

    maze = {
        "width": width,
        "height": height,
        "horizontal_walls": horizontal_walls,
        "vertical_walls": vertical_walls,
        # Horizontal_walls and vertical_walls stored as sets. Avoids duplicates.
    }

    return maze


def add_horizontal_wall(maze, x_coordinate: int, horizontal_line: int):
    """Adds a horizontal wall to the maze at the given position."""
    maze["horizontal_walls"].add((x_coordinate, horizontal_line))

    return maze


def add_vertical_wall(maze, y_coordinate: int, vertical_line: int):
    """Adds a vertical wall to the maze at the given position."""
    maze["vertical_walls"].add((vertical_line, y_coordinate))

    return maze


def get_dimensions(maze) -> Tuple[int, int]:
    """Returns the dimensions of the maze as (width, height)."""
    return maze["width"], maze["height"]


def get_walls(
    maze, x_coordinate: int, y_coordinate: int
) -> Tuple[bool, bool, bool, bool]:
    """Returns information about walls around cell (x, y)
    as (N, E, S, W)."""
    horizontal_walls = maze["horizontal_walls"]
    vertical_walls = maze["vertical_walls"]

    north = (x_coordinate, y_coordinate + 1) in horizontal_walls
    south = (x_coordinate, y_coordinate) in horizontal_walls
    west = (x_coordinate, y_coordinate) in vertical_walls
    east = (x_coordinate + 1, y_coordinate) in vertical_walls

    return north, east, south, west
