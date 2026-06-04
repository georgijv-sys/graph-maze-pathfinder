# graph-maze-pathfinder

A Python maze solver that models the maze as a graph and demonstrates several
pathfinding algorithms:

- BFS for the shortest unweighted route.
- DFS for depth-first exploration.
- Dijkstra for weighted shortest paths.
- A* for heuristic shortest paths using Manhattan distance.

The project also includes a Tkinter GUI that animates the explored cells and
then shows the runner moving along the selected route in real time.

## Run the GUI

```bash
python maze_gui.py
```

or:

```bash
python maze_runner.py sample_mazes/maze1.mz --gui
```

Use the controls at the top to choose an algorithm, load a sample maze, generate
a new practice maze, solve it, and animate the result.

## Run from the command line

```bash
python maze_runner.py sample_mazes/maze1.mz --algorithm astar
python maze_runner.py sample_mazes/maze2.mz --algorithm bfs
python maze_runner.py sample_mazes/weighted_maze.mz --algorithm dijkstra
python maze_runner.py --generate 20 12 --seed 42 --algorithm astar
```

The command writes:

- `sample_output/exploration.csv`: cells explored by the algorithm.
- `sample_output/statistics.txt`: algorithm, path length, path cost, route, and runner actions.

## Maze format

Maze files are plain text. The outer `#` border is optional but supported.

- `#` is a blocked cell.
- `.` or a space is an open cell.
- `S` marks the start.
- `G` marks the goal.
- `1` to `9` are open cells with movement cost, useful for Dijkstra and A*.

If a file does not contain `S` or `G`, the default start is bottom-left `(0, 0)`
and the default goal is top-right.

## Project structure

- `maze.py`: maze model, parser, wall helpers, and practice-maze generation.
- `graph_algorithms.py`: BFS, DFS, Dijkstra, A*, and shared result objects.
- `runner.py`: runner orientation, movement, exploration, and action conversion.
- `maze_runner.py`: command-line interface and output file writer.
- `maze_gui.py`: real-time visualiser.
