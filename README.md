# Graph Maze Pathfinder

Graph Maze Pathfinder is a Python application for building, solving, and
visualising mazes as graphs. The project includes a Tkinter desktop interface,
a command-line runner, deterministic maze generation, weighted terrain, export
files, and a small test suite covering the core pathfinding behaviour.

The main goal of the project is to make shortest-path algorithms visible. A
maze is represented as a graph: cells are nodes, valid moves are edges, and
weighted cells change the cost of entering a node.

## Highlights

- Interactive GUI for loading sample mazes, generating new mazes, solving,
  animating, comparing algorithms, saving mazes, and exporting results.
- Seven pathfinding algorithms implemented in plain Python.
- Weighted and unweighted maze support.
- Deterministic maze generation using a seed, which makes examples repeatable.
- File support for both simple text mazes and JSON-backed generated mazes.
- CSV and text exports for explored cells, final path, cost, and runner actions.
- Unit tests for parsing, generation, weighted search, save/load, and movement
  command conversion.
- No third-party runtime dependencies.

## Algorithms

| Algorithm | Best use in this project | Guarantee |
| --- | --- | --- |
| BFS | Shortest route by number of steps in an unweighted maze | Optimal for unweighted paths |
| Bidirectional BFS | Unweighted shortest path from both start and goal | Optimal for unweighted paths |
| DFS | Demonstrates depth-first exploration behaviour | Not shortest-path optimal |
| Dijkstra | Weighted shortest path | Optimal with non-negative costs |
| Bellman-Ford | Weighted pathfinding by repeated relaxation | Optimal with non-negative costs used here |
| Greedy Best-First | Heuristic-driven exploration toward the goal | Fast, not guaranteed optimal |
| A* | Weighted search using Manhattan distance | Optimal here because movement costs are positive |

## Requirements

- Python 3.10 or newer.
- Tkinter for the GUI. It is included with most standard Python installations.

The project uses only the Python standard library.

## Quick Start

Run the GUI:

```bash
python3 maze_gui.py
```

From the GUI you can:

1. Pick an algorithm.
2. Load a sample maze or open a maze file.
3. Generate a normal maze or a weighted maze.
4. Click `Solve` to show the explored cells and final path.
5. Click `Animate` to watch the search and runner movement.
6. Use `Compare` to run every algorithm on the same maze.
7. Save generated mazes or export the latest run.

## Command-Line Usage

Solve a sample maze:

```bash
python3 maze_runner.py sample_mazes/maze1.mz --algorithm astar
```

Run a weighted algorithm:

```bash
python3 maze_runner.py sample_mazes/weighted_maze.mz --algorithm dijkstra
python3 maze_runner.py sample_mazes/weighted_maze.mz --algorithm bellmanford
```

Generate and solve a deterministic maze:

```bash
python3 maze_runner.py --generate 20 12 --seed 42 --algorithm bidirectional
```

Open the GUI through the CLI:

```bash
python3 maze_runner.py sample_mazes/maze1.mz --gui
```

Supported command-line algorithm names:

```text
astar, dijkstra, bellmanford, greedy, bidirectional, bfs, dfs
```

The CLI writes results to `sample_output/` by default:

- `exploration.csv`: cells visited by the selected algorithm.
- `statistics.txt`: algorithm name, maze size, start/goal, path length, path
  cost, final route, and runner actions.

## Optional Installation

The project can also be installed in editable mode:

```bash
python3 -m pip install -e .
```

After that, these commands are available:

```bash
maze-gui
maze-runner sample_mazes/maze1.mz --algorithm astar
```

## Running Tests

```bash
python3 -m unittest discover -s tests
```

The tests cover:

- ASCII maze parsing.
- Generated maze save/load round trips.
- BFS shortest paths.
- Weighted path choice with Dijkstra, A*, and Bellman-Ford.
- Generated maze connectivity across all algorithms.
- Density-based weighted-cell generation.
- Conversion from coordinate paths to runner movement actions.

## Maze File Formats

### Text `.mz` Files

Text maze files are easy to read and edit by hand.

```text
#######
#S..2G#
#.###.#
#.....#
#######
```

Characters:

- `#`: blocked cell.
- `.` or a space: open cell.
- `S`: start.
- `G`: goal.
- `1` to `9`: open weighted cell with that movement cost.

If `S` or `G` is missing, the default start is bottom-left and the default goal
is top-right.

### Saved `.maze` Files

Generated mazes can contain internal wall segments that cannot be represented
perfectly by the simple text format. The GUI saves these as JSON-backed `.maze`
files so generated walls, weighted cells, start, and goal can be loaded back
exactly.

## Project Structure

```text
graph-maze-pathfinder/
├── graph_algorithms.py     # BFS, DFS, Dijkstra, A*, Bellman-Ford, Greedy, Bi-BFS
├── maze.py                 # Maze model, parsing, generation, save/load
├── maze_gui.py             # Tkinter desktop application
├── maze_runner.py          # Command-line interface and export writer
├── runner.py               # Runner orientation and movement action conversion
├── sample_mazes/           # Hand-written sample maze files
├── sample_output/          # Example exported results
├── tests/                  # Unit tests
└── pyproject.toml          # Project metadata and console entry points
```

## Design Notes

- The maze model is separated from the algorithms and UI. This keeps the search
  code testable without opening the GUI.
- Search functions return a `SearchResult` containing the final path, explored
  order, total cost, and metadata. The GUI and CLI both use the same result
  object.
- Weighted algorithms use the cost of entering a cell. Unweighted algorithms
  still run on weighted mazes, but the GUI explains when they are not guaranteed
  to find the cheapest weighted route.
- Generated mazes are connected by construction using randomized DFS carving.
- The runner layer converts graph paths into orientation-aware actions such as
  `F`, `RF`, and `LF`.

## Current Limitations

- The GUI is intentionally built with Tkinter to avoid external dependencies;
  it is functional rather than custom-rendered with a game engine.
- Bellman-Ford is included for algorithmic comparison, although all generated
  terrain costs are positive and Dijkstra/A* are more efficient for this use
  case.
- The project currently supports rectangular grid mazes with four-directional
  movement.

## Possible Next Steps

- Add diagonal movement as an optional mode.
- Add heuristic selection for A* and Greedy Best-First Search.
- Add maze editing directly on the canvas.
- Export screenshots of solved mazes from the GUI.
- Add performance charts comparing algorithms over multiple generated mazes.
