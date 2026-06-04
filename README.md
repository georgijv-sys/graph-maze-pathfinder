# graph-maze-pathfinder

A Python maze solver that models the maze as a graph and demonstrates several
pathfinding algorithms:

- BFS for the shortest unweighted route.
- Bidirectional BFS for two-front unweighted search.
- DFS for depth-first exploration.
- Dijkstra for weighted shortest paths.
- Bellman-Ford for weighted shortest paths by edge relaxation.
- Greedy Best-First Search for heuristic-driven exploration.
- A* for heuristic shortest paths using Manhattan distance.

The main experience is a Tkinter GUI. It lets a user load sample files, generate
new mazes, choose weighted terrain, compare algorithms, solve, animate, save
maze files, and export exploration statistics without using the command line.

## Run the GUI

```bash
python maze_gui.py
```

or:

```bash
python maze_runner.py sample_mazes/maze1.mz --gui
```

The app shows file-based sample mazes in a selector, has controls for generated
maze size and seed, and has separate buttons for normal and weighted generation.
Generated mazes stay unsolved until Solve or Animate is clicked. The legend
explains the visual result: blue cells are discovered cells, yellow is the final
path, green is the start, red is the goal, and numbered cells are weighted
terrain.

## Run from the command line

```bash
python maze_runner.py sample_mazes/maze1.mz --algorithm astar
python maze_runner.py sample_mazes/maze1.mz --algorithm bidirectional
python maze_runner.py sample_mazes/maze2.mz --algorithm bfs
python maze_runner.py sample_mazes/weighted_maze.mz --algorithm dijkstra
python maze_runner.py sample_mazes/weighted_maze.mz --algorithm bellmanford
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

Generated mazes can also be saved from the GUI as `.maze` files. Those files use
JSON so internal walls and weighted cells can be loaded back exactly as they
were generated.

## Project structure

- `maze.py`: maze model, parser, wall helpers, and practice-maze generation.
- `graph_algorithms.py`: BFS, Bidirectional BFS, DFS, Dijkstra, Bellman-Ford,
  Greedy Best-First, A*, and shared result objects.
- `runner.py`: runner orientation, movement, exploration, and action conversion.
- `maze_runner.py`: command-line interface and output file writer.
- `maze_gui.py`: real-time visualiser.
