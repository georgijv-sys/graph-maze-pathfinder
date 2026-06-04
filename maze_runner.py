import argparse
import csv
from typing import Optional, Tuple, List
from collections import deque, defaultdict

from maze import create_maze, add_horizontal_wall, add_vertical_wall, get_dimensions
from runner import create_runner, explore


DIRECTIONS = ["N", "E", "S", "W"]
"""Directions is a fixed list. That allows to compute turns 
("L", "R", "B") using index arithmetic instead of many "if" branches."""


def shortest_path(
    maze,
    starting: Optional[Tuple[int, int]] = None,
    goal: Optional[Tuple[int, int]] = None,
    exploration_steps: Optional[List[Tuple[int, int, str]]] = None,  # part 6
) -> List[Tuple[int, int, str]]:
    """Find a minimal path (no repeated positions)
    from starting to goal using exploration."""

    width, height = get_dimensions(maze)

    if starting is None:
        starting = (0, 0)

    if goal is None:
        goal = (width - 1, height - 1)

    if starting == goal:
        return []

    start_x, start_y = starting

    if exploration_steps is None:
        runner = create_runner(start_x, start_y)
        exploration_steps = explore(runner, maze, goal)
    """Checking if exploration steps were already gotten - run if not. 
    Therefore using the same log for computing the turn steps."""

    positions: List[Tuple[int, int]] = [starting]

    for x, y, _actions in exploration_steps:
        positions.append((x, y))
    """Logging (x,y) while ignoring actions. 
    Because for computing the shortest path,
    only a structure of connected cells matter."""

    if positions[-1] != goal:
        positions.append(goal)

    neighbours = defaultdict(set)  # using set to avoid duplicates

    for i in range(len(positions) - 1):
        a = positions[i]
        b = positions[i + 1]
        if b not in neighbours[a]:
            neighbours[a].add(b)
            neighbours[b].add(a)  # bidirectional movement
    """Checks all consecutive pairs of positions (a,b),
    where runner can move from a to b"""

    queue = deque()
    queue.append(starting)

    parent = {starting: None}  # stores cell from which runner came to nxt

    while queue:
        current = queue.pop()

        if current == goal:
            break

        for nxt in neighbours[current]:
            if nxt not in parent:
                parent[nxt] = current
                queue.append(nxt)
    """Uses  BFS algorithm to find the shortest path from start to goal"""

    if goal not in parent:
        return []
    """If the shortest path from start to goal was found, return it.
     (just in case)"""

    node_path: List[Tuple[int, int]] = []

    cur = goal  # start from the end(goal)
    while cur is not None and cur != starting:  # does not include starting
        node_path.append(cur)
        cur = parent[cur]

    node_path.reverse()  # reverses the path
    """Computes the shortest path from start to goal"""

    result: List[Tuple[int, int, str]] = []

    current_orientation = "N"  # start at north
    current_pos = starting

    for next_pos in node_path:  # iterate the nodes of the shortest path
        x1, y1 = current_pos
        x2, y2 = next_pos

        dx = x2 - x1  # horizontal displacement
        dy = y2 - y1  # vertical displacement

        move_dir = {  # maps the displacement (dx, dy) to a global direction
            (1, 0): "E",
            (-1, 0): "W",
            (0, 1): "N",
            (0, -1): "S",
        }[(dx, dy)]

        # determine how much to rotate to face the desired direction
        current_idx = DIRECTIONS.index(current_orientation)
        target_idx = DIRECTIONS.index(move_dir)
        diff = (target_idx - current_idx) % 4  # find the rotation difference

        # using the rotation difference, rotate
        if diff == 0:
            turn = ""
        elif diff == 1:
            turn = "R"
        elif diff == 2:
            turn = "B"
        else:
            turn = "L"

        actions = turn + "F"
        current_orientation = move_dir  # runner faces a new direction

        result.append((x1, y1, actions))  # saving the step
        current_pos = next_pos  # new position

    return result


"""Part 5"""


from typing import List, Tuple
from maze import create_maze, add_horizontal_wall, add_vertical_wall


def maze_reader(maze_file: str):
    """
    Read a .mz maze file and return a maze object.

    Format:
      - rectangular grid of '#' and '.' characters;
      - outer border is all '#';
      - inside cells: '.' = free cell, '#' = blocked cell.

    The function builds a maze compatible with create_maze/get_walls.
    Raises IOError on file problems and ValueError on invalid format.
    """
    # --- 1. Read file ---
    try:
        with open(maze_file, "r", encoding="utf-8") as f:
            lines = [line.rstrip("\n") for line in f]
    except OSError as exc:
        raise IOError(f"Cannot read maze file: {maze_file}") from exc

    if not lines:
        raise ValueError("Maze file is empty")

    cols = len(lines[0])
    if any(len(line) != cols for line in lines):
        raise ValueError("Maze must be rectangular")

    rows = len(lines)

    # '#'
    if any(ch != "#" for ch in lines[0]) or any(ch != "#" for ch in lines[-1]):
        raise ValueError("Top and bottom borders must be '#'")

    for line in lines:
        if line[0] != "#" or line[-1] != "#":
            raise ValueError("Left and right borders must be '#'")

    # drop the border
    width = cols - 2
    height = rows - 2

    maze = create_maze(width, height)

    # Build matrix of interior cells in our coordinate system
    cells: list[list[str]] = [[None] * width for _ in range(height)]
    for i in range(1, rows - 1):  # file row index
        line = lines[i]
        cy = height - 1 - (i - 1)  # convert "from top" index to y
        for j in range(1, cols - 1):  # file column index
            cx = j - 1
            cells[cy][cx] = line[j]

    # Add internal walls between neighbour cells
    for y in range(height):
        for x in range(width):
            if x < width - 1:
                if not (cells[y][x] == "." and cells[y][x + 1] == "."):
                    add_vertical_wall(maze, y, x + 1)

            if y < height - 1:
                if not (cells[y][x] == "." and cells[y + 1][x] == "."):
                    add_horizontal_wall(maze, x, y + 1)

    return maze


def parse_position(text: str) -> Tuple[int, int]:
    """
    creating a Tuple
    """
    try:
        parts = text.split(",")
        if len(parts) != 2:
            raise ValueError

        x_str, y_str = parts[0].strip(), parts[1].strip()
        x = int(x_str)
        y = int(y_str)
        return x, y
    except Exception:
        raise argparse.ArgumentTypeError(
            f"Positions must be in the form 'x, y', got '{text}'"
        )


def main():
    parser = argparse.ArgumentParser(
        description="ECS Maze Runner - solve a maze from a file."
    )

    parser.add_argument(
        "maze",
        help="The name of the maze file, e.g., maze1.mz",
    )

    # Optional argument
    parser.add_argument(
        "--starting",
        type=parse_position,
        help='The starting position, e.g., "2, 1"',
    )

    # Optional argument
    parser.add_argument(
        "--goal",
        type=parse_position,
        help='The goal position, e.g., "4, 5"',
    )

    args = parser.parse_args()

    maze = maze_reader(args.maze)

    width, height = get_dimensions(maze)

    if args.starting is None:
        starting = (0, 0)
    else:
        starting = args.starting

    if args.goal is None:
        goal = (width - 1, height - 1)
    else:
        goal = args.goal

    start_x, start_y = starting
    runner = create_runner(start_x, start_y)
    exploration_steps = explore(runner, maze, goal)

    write_exploration_csv(exploration_steps)

    path = shortest_path(maze, starting, goal, exploration_steps)

    write_statistics(args.maze, exploration_steps, path)


def write_exploration_csv(exploration_steps: List[Tuple[int, int, str]]):

    with open("exploration.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow(["Step", "x-coordinate", "y-coordinate", "Actions"])

        for step_index, (x, y, actions) in enumerate(exploration_steps, start=1):
            writer.writerow([step_index, x, y, actions])


def write_statistics(
    maze_filename: str,
    exploration_steps: List[Tuple[int, int, str]],
    path: List[Tuple[int, int, str]],
):
    """Creating a statistics file."""
    exploration_count = len(exploration_steps)

    # The path that contains only the coordinates
    path_positions = [(x, y) for (x, y, _actions) in path]
    path_length = len(path_positions)

    # The score
    score = exploration_count / 4 + path_length

    with open("statistics.txt", "w", encoding="utf-8") as f:
        f.write(f"{maze_filename}\n")
        f.write(f"{score}\n")
        f.write(f"{exploration_count}\n")
        f.write(f"{path_positions}\n")
        f.write(f"{path_length}\n")


if __name__ == "__main__":
    main()
