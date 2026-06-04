"""Command line entry point for the graph maze pathfinder."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List, Optional

from graph_algorithms import SearchResult, solve_maze
from maze import Maze, Position, create_perfect_maze, get_dimensions, load_maze
from runner import ActionStep, positions_to_actions


DEFAULT_OUTPUT_DIR = Path("sample_output")


def maze_reader(maze_file: str) -> Maze:
    return load_maze(maze_file)


def shortest_path(
    maze: Maze,
    starting: Optional[Position] = None,
    goal: Optional[Position] = None,
    exploration_steps: Optional[List[ActionStep]] = None,
    algorithm: str = "bfs",
) -> List[ActionStep]:
    del exploration_steps
    result = solve_maze(maze, algorithm=algorithm, start=starting, goal=goal)
    return positions_to_actions(result.path)


def parse_position(text: str) -> Position:
    try:
        x_text, y_text = text.split(",", 1)
        return int(x_text.strip()), int(y_text.strip())
    except Exception as exc:
        raise argparse.ArgumentTypeError(
            f"Positions must be in the form 'x, y', got '{text}'"
        ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Solve, analyse, and visualise grid mazes with graph algorithms."
    )
    parser.add_argument(
        "maze",
        nargs="?",
        default="sample_mazes/maze1.mz",
        help="Path to a .mz maze file. Defaults to sample_mazes/maze1.mz.",
    )
    parser.add_argument(
        "--algorithm",
        choices=["astar", "dijkstra", "bellmanford", "greedy", "bidirectional", "bfs", "dfs"],
        default="astar",
        help="Search algorithm to use.",
    )
    parser.add_argument("--starting", type=parse_position, help='Starting cell, e.g. "2, 1".')
    parser.add_argument("--goal", type=parse_position, help='Goal cell, e.g. "8, 8".')
    parser.add_argument(
        "--generate",
        nargs=2,
        metavar=("WIDTH", "HEIGHT"),
        type=int,
        help="Generate a connected practice maze instead of reading a file.",
    )
    parser.add_argument("--seed", type=int, default=7, help="Seed for generated practice mazes.")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for exploration.csv and statistics.txt.",
    )
    parser.add_argument("--gui", action="store_true", help="Open the real-time maze visualiser.")

    args = parser.parse_args()

    if args.gui:
        from maze_gui import run_gui

        run_gui(args.maze)
        return

    maze = (
        create_perfect_maze(args.generate[0], args.generate[1], seed=args.seed)
        if args.generate
        else maze_reader(args.maze)
    )
    start = args.starting or maze.start
    goal = args.goal or maze.goal
    result = solve_maze(maze, algorithm=args.algorithm, start=start, goal=goal)
    action_steps = positions_to_actions(result.path)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_exploration_csv(output_dir / "exploration.csv", result)
    write_statistics(output_dir / "statistics.txt", args.maze, maze, result, action_steps)

    print_summary(result, output_dir)


def write_exploration_csv(path: Path | str, result: SearchResult) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(["Step", "x-coordinate", "y-coordinate", "Event"])
        for step_index, (x, y) in enumerate(result.visited_order, start=1):
            event = "goal" if (x, y) == result.goal else "visited"
            writer.writerow([step_index, x, y, event])


def write_statistics(
    path: Path | str,
    maze_filename: str,
    maze: Maze,
    result: SearchResult,
    action_steps: List[ActionStep],
) -> None:
    path_positions = result.path
    score = (result.explored_count / 4) + result.path_length
    width_height = get_dimensions(maze)

    with Path(path).open("w", encoding="utf-8") as file:
        file.write(f"Maze: {maze_filename}\n")
        file.write(f"Algorithm: {result.algorithm}\n")
        file.write(f"Dimensions: {width_height[0]} x {width_height[1]}\n")
        file.write(f"Start: {result.start}\n")
        file.write(f"Goal: {result.goal}\n")
        file.write(f"Found: {result.found}\n")
        file.write(f"Explored cells: {result.explored_count}\n")
        file.write(f"Path length: {result.path_length}\n")
        file.write(f"Path cost: {result.cost}\n")
        file.write(f"Coursework score estimate: {score}\n")
        file.write(f"Path positions: {path_positions}\n")
        file.write(f"Runner actions: {action_steps}\n")
def print_summary(result: SearchResult, output_dir: Path) -> None:
    if not result.found:
        print(f"{result.algorithm} could not find a path from {result.start} to {result.goal}.")
        return
    print(
        f"{result.algorithm}: path length {result.path_length}, "
        f"cost {result.cost:g}, explored {result.explored_count} cells."
    )
    print(f"Results written to {output_dir / 'exploration.csv'} and {output_dir / 'statistics.txt'}.")


if __name__ == "__main__":
    main()
