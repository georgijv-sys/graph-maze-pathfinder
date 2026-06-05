import tempfile
import unittest
from pathlib import Path

from graph_algorithms import solve_maze
from maze import (
    Maze,
    add_random_weights,
    create_perfect_maze,
    load_maze,
    parse_ascii_maze,
    save_maze,
)
from runner import positions_to_actions


class MazeParsingTests(unittest.TestCase):
    def test_ascii_parser_reads_start_goal_walls_and_weights(self):
        maze = parse_ascii_maze(
            """
#####
#S2G#
#.#.#
#####
"""
        )

        self.assertEqual(maze.width, 3)
        self.assertEqual(maze.height, 2)
        self.assertEqual(maze.start, (0, 1))
        self.assertEqual(maze.goal, (2, 1))
        self.assertIn((1, 0), maze.blocked)
        self.assertEqual(maze.weights[(1, 1)], 2)

    def test_generated_maze_round_trips_through_saved_file(self):
        maze = create_perfect_maze(8, 6, seed=42)
        add_random_weights(maze, density=0.25, seed=99)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "maze.maze"
            save_maze(maze, path)
            loaded = load_maze(path)

        self.assertEqual(loaded.width, maze.width)
        self.assertEqual(loaded.height, maze.height)
        self.assertEqual(loaded.horizontal_walls, maze.horizontal_walls)
        self.assertEqual(loaded.vertical_walls, maze.vertical_walls)
        self.assertEqual(loaded.weights, maze.weights)

    def test_clear_cell_can_open_generated_wall_segments(self):
        maze = create_perfect_maze(6, 5, seed=1)
        before = len(maze.horizontal_walls) + len(maze.vertical_walls)

        maze.clear_cell((2, 2), remove_adjacent_walls=True)

        after = len(maze.horizontal_walls) + len(maze.vertical_walls)
        self.assertLess(after, before)
        self.assertNotIn((2, 2), maze.blocked)


class AlgorithmTests(unittest.TestCase):
    def test_bfs_finds_shortest_unweighted_path(self):
        maze = parse_ascii_maze(
            """
S..
...
..G
"""
        )

        result = solve_maze(maze, "bfs")

        self.assertTrue(result.found)
        self.assertEqual(result.path_length, 4)
        self.assertEqual(result.path[0], maze.start)
        self.assertEqual(result.path[-1], maze.goal)

    def test_weighted_algorithms_choose_cheaper_route(self):
        maze = Maze(width=3, height=2, weights={(1, 0): 9}, start=(0, 0), goal=(2, 0))

        dijkstra = solve_maze(maze, "dijkstra")
        astar = solve_maze(maze, "astar")
        bellman_ford = solve_maze(maze, "bellmanford")

        for result in (dijkstra, astar, bellman_ford):
            self.assertTrue(result.found)
            self.assertEqual(result.cost, 4)
            self.assertNotIn((1, 0), result.path)

    def test_all_algorithms_solve_generated_connected_maze(self):
        maze = create_perfect_maze(10, 7, seed=12)
        algorithms = [
            "astar",
            "dijkstra",
            "bellmanford",
            "greedy",
            "bidirectional",
            "bfs",
            "dfs",
        ]

        for algorithm in algorithms:
            with self.subTest(algorithm=algorithm):
                self.assertTrue(solve_maze(maze, algorithm).found)

    def test_random_weights_are_density_based_and_skip_start_goal(self):
        maze = create_perfect_maze(10, 6, seed=7)
        add_random_weights(maze, density=0.25, seed=8)

        expected = round((maze.open_cell_count - 2) * 0.25)
        self.assertEqual(len(maze.weights), expected)
        self.assertNotIn(maze.start, maze.weights)
        self.assertNotIn(maze.goal, maze.weights)


class RunnerActionTests(unittest.TestCase):
    def test_positions_are_converted_to_orientation_actions(self):
        actions = positions_to_actions([(0, 0), (0, 1), (1, 1), (1, 0)])

        self.assertEqual(actions, [(0, 0, "F"), (0, 1, "RF"), (1, 1, "RF")])


if __name__ == "__main__":
    unittest.main()
