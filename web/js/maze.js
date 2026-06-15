/* Maze data model + generation — a faithful JS port of maze.py.
 * Grid is graph-friendly: open cells are nodes, valid moves are edges,
 * weighted cells affect entry cost. Origin is bottom-left (y grows upward).
 */

const DIRECTIONS = ["N", "E", "S", "W"];
const DIRECTION_VECTORS = {
  N: [0, 1],
  E: [1, 0],
  S: [0, -1],
  W: [-1, 0],
};

const key = (x, y) => x + "," + y;
const fromKey = (k) => k.split(",").map(Number);

// Mirror Python's round() (banker's rounding, half-to-even) so the JS port
// produces the same weighted-cell count as maze.py. Math.round rounds halves
// up, which diverges from Python at exact .5 values (e.g. 14.5 -> 14 not 15).
function pyRound(n) {
  const floor = Math.floor(n);
  const frac = n - floor;
  if (frac < 0.5) return floor;
  if (frac > 0.5) return floor + 1;
  return floor % 2 === 0 ? floor : floor + 1;
}

class Maze {
  constructor(width, height, opts = {}) {
    if (width <= 0 || height <= 0) throw new Error("Maze dimensions must be positive");
    this.width = width;
    this.height = height;
    this.blocked = new Set(opts.blocked || []);        // Set of "x,y"
    this.horizontalWalls = new Set(opts.horizontalWalls || []);
    this.verticalWalls = new Set(opts.verticalWalls || []);
    this.weights = new Map(opts.weights || []);        // Map "x,y" -> cost
    this.start = opts.start || [0, 0];
    this.goal = opts.goal || [width - 1, height - 1];
    this._addOuterWalls();
    this._validateCells();
  }

  // Mirror maze.py's _validate_cells so a malformed file fails fast and
  // identically across both implementations, instead of silently producing a
  // broken maze that only errors later at solve time.
  _validateCells() {
    for (const c of [...this.blocked, ...this.weights.keys()]) {
      const [x, y] = fromKey(c);
      if (!this.inBounds([x, y])) throw new Error("Cell outside maze bounds: " + c);
    }
    for (const cost of this.weights.values()) {
      if (cost < 1) throw new Error("Movement cost must be >= 1: " + cost);
    }
    if (!this.isOpen(this.start)) throw new Error("Start cell is blocked or outside bounds: " + this.start);
    if (this.goal && !this.isOpen(this.goal)) throw new Error("Goal cell is blocked or outside bounds: " + this.goal);
  }

  _addOuterWalls() {
    for (let x = 0; x < this.width; x++) {
      this.horizontalWalls.add(key(x, 0));
      this.horizontalWalls.add(key(x, this.height));
    }
    for (let y = 0; y < this.height; y++) {
      this.verticalWalls.add(key(0, y));
      this.verticalWalls.add(key(this.width, y));
    }
  }

  get openCellCount() {
    return this.width * this.height - this.blocked.size;
  }

  inBounds([x, y]) {
    return x >= 0 && x < this.width && y >= 0 && y < this.height;
  }

  isOpen(pos) {
    return this.inBounds(pos) && !this.blocked.has(key(pos[0], pos[1]));
  }

  movementCost(pos) {
    return this.weights.get(key(pos[0], pos[1])) || 1;
  }

  hasWallBetween(first, second) {
    if (!this.isOpen(first) || !this.isOpen(second)) return true;
    const [x1, y1] = first;
    const [x2, y2] = second;
    const dx = x2 - x1, dy = y2 - y1;
    if (Math.abs(dx) + Math.abs(dy) !== 1) throw new Error("Wall checks require adjacent cells");
    if (dx === 1) return this.verticalWalls.has(key(x2, y1));
    if (dx === -1) return this.verticalWalls.has(key(x1, y1));
    if (dy === 1) return this.horizontalWalls.has(key(x1, y2));
    return this.horizontalWalls.has(key(x1, y1));
  }

  neighbours(pos) {
    const result = [];
    for (const d of DIRECTIONS) {
      const [dx, dy] = DIRECTION_VECTORS[d];
      const cand = [pos[0] + dx, pos[1] + dy];
      if (this.isOpen(cand) && !this.hasWallBetween(pos, cand)) result.push(cand);
    }
    return result;
  }

  getWalls(x, y) {
    const walls = [];
    for (const d of DIRECTIONS) {
      const [dx, dy] = DIRECTION_VECTORS[d];
      const cand = [x + dx, y + dy];
      walls.push(!this.isOpen(cand) || this.hasWallBetween([x, y], cand));
    }
    return walls; // [N, E, S, W]
  }

  addHorizontalWall(x, line) {
    this.horizontalWalls.add(key(x, line));
  }
  addVerticalWall(y, line) {
    this.verticalWalls.add(key(line, y));
  }

  clearCell(pos, removeAdjacentWalls = false) {
    if (!this.inBounds(pos)) return;
    this.blocked.delete(key(pos[0], pos[1]));
    this.weights.delete(key(pos[0], pos[1]));
    if (removeAdjacentWalls) this.removeAdjacentWalls(pos);
  }

  removeAdjacentWalls(pos) {
    if (!this.inBounds(pos)) return;
    const [x, y] = pos;
    if (y > 0) this.horizontalWalls.delete(key(x, y));
    if (y < this.height - 1) this.horizontalWalls.delete(key(x, y + 1));
    if (x > 0) this.verticalWalls.delete(key(x, y));
    if (x < this.width - 1) this.verticalWalls.delete(key(x + 1, y));
  }

  clone() {
    const m = new Maze(this.width, this.height);
    m.blocked = new Set(this.blocked);
    m.horizontalWalls = new Set(this.horizontalWalls);
    m.verticalWalls = new Set(this.verticalWalls);
    m.weights = new Map(this.weights);
    m.start = [...this.start];
    m.goal = this.goal ? [...this.goal] : null;
    return m;
  }

  toJSON() {
    return {
      format: "graph-maze-pathfinder",
      width: this.width,
      height: this.height,
      blocked: [...this.blocked].map(fromKey),
      horizontal_walls: [...this.horizontalWalls].map(fromKey),
      vertical_walls: [...this.verticalWalls].map(fromKey),
      weights: [...this.weights].map(([k, cost]) => {
        const [x, y] = fromKey(k);
        return { x, y, cost };
      }),
      start: [...this.start],
      goal: this.goal ? [...this.goal] : null,
    };
  }
}

/* ── Seeded RNG (mulberry32) so seeds are reproducible like random.Random ── */
function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function createPerfectMaze(width, height, seed) {
  const rng = mulberry32(seed == null ? (Math.random() * 1e9) | 0 : seed);
  const maze = new Maze(width, height);

  // Fill all internal walls, then carve.
  for (let x = 0; x < width; x++)
    for (let y = 1; y < height; y++) maze.addHorizontalWall(x, y);
  for (let y = 0; y < height; y++)
    for (let x = 1; x < width; x++) maze.addVerticalWall(y, x);

  const start = [0, 0];
  const visited = new Set([key(0, 0)]);
  const stack = [start];

  const removeWallBetween = (first, second, direction) => {
    const [x1, y1] = first, [x2, y2] = second;
    if (direction === "E") maze.verticalWalls.delete(key(x2, y1));
    else if (direction === "W") maze.verticalWalls.delete(key(x1, y1));
    else if (direction === "N") maze.horizontalWalls.delete(key(x1, y2));
    else if (direction === "S") maze.horizontalWalls.delete(key(x1, y1));
  };

  while (stack.length) {
    const current = stack[stack.length - 1];
    const candidates = [];
    for (const d of DIRECTIONS) {
      const [dx, dy] = DIRECTION_VECTORS[d];
      const nxt = [current[0] + dx, current[1] + dy];
      if (maze.inBounds(nxt) && !visited.has(key(nxt[0], nxt[1]))) candidates.push([d, nxt]);
    }
    if (!candidates.length) { stack.pop(); continue; }
    const [direction, nxt] = candidates[Math.floor(rng() * candidates.length)];
    removeWallBetween(current, nxt, direction);
    visited.add(key(nxt[0], nxt[1]));
    stack.push(nxt);
  }

  maze.start = [0, 0];
  maze.goal = [width - 1, height - 1];
  return maze;
}

function addRandomWeights(maze, { density = 0.2, minimum = 2, maximum = 9, seed } = {}) {
  const rng = mulberry32(seed == null ? (Math.random() * 1e9) | 0 : seed);
  density = Math.min(1, Math.max(0, density));
  const sk = key(maze.start[0], maze.start[1]);
  const gk = maze.goal ? key(maze.goal[0], maze.goal[1]) : null;
  const candidates = [];
  for (let y = 0; y < maze.height; y++)
    for (let x = 0; x < maze.width; x++) {
      const k = key(x, y);
      if (k !== sk && k !== gk && maze.isOpen([x, y])) candidates.push([x, y]);
    }
  // Fisher-Yates with seeded rng
  for (let i = candidates.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [candidates[i], candidates[j]] = [candidates[j], candidates[i]];
  }
  let target = pyRound(candidates.length * density);
  if (density > 0 && candidates.length) target = Math.max(1, target);
  for (const [x, y] of candidates.slice(0, target)) {
    maze.weights.set(key(x, y), minimum + Math.floor(rng() * (maximum - minimum + 1)));
  }
  return maze;
}

/* ── ASCII .mz parsing (for the embedded samples) ── */
function parseAsciiMaze(text) {
  const lines = text.split("\n").map((l) => l.replace(/\n$/, "")).filter((l) => l.trim().length);
  if (!lines.length) throw new Error("Maze file is empty");
  const w0 = lines[0].length;
  if (lines.some((l) => l.length !== w0)) {
    // pad ragged rows with spaces (open) so sample files stay tolerant
    for (let i = 0; i < lines.length; i++) lines[i] = lines[i].padEnd(w0, " ");
  }

  const solidBorder =
    lines.length >= 3 && lines[0].length >= 3 &&
    [...lines[0]].every((c) => c === "#") &&
    [...lines[lines.length - 1]].every((c) => c === "#") &&
    lines.every((l) => l[0] === "#" && l[l.length - 1] === "#");

  let rows = solidBorder ? lines.slice(1, -1).map((r) => r.slice(1, -1)) : lines;
  const height = rows.length;
  const width = rows.length ? rows[0].length : 0;
  const blocked = [];
  const weights = [];
  let start = null, goal = null;

  rows.forEach((row, fileY) => {
    const y = height - 1 - fileY;
    [...row].forEach((char, x) => {
      const k = key(x, y);
      if (char === "#") blocked.push(k);
      else if (char === "S") start = [x, y];
      else if (char === "G") goal = [x, y];
      // Only 2-9 are weighted terrain; '0'/'1' cost the same as an open cell.
      else if (/[2-9]/.test(char)) weights.push([k, parseInt(char, 10)]);
    });
  });

  return new Maze(width, height, {
    blocked,
    weights,
    start: start || [0, 0],
    goal: goal || [width - 1, height - 1],
  });
}

function mazeFromJSON(data) {
  if (data.format !== "graph-maze-pathfinder") throw new Error("Unsupported maze JSON format");
  return new Maze(data.width, data.height, {
    blocked: (data.blocked || []).map(([x, y]) => key(x, y)),
    horizontalWalls: (data.horizontal_walls || []).map(([x, y]) => key(x, y)),
    verticalWalls: (data.vertical_walls || []).map(([x, y]) => key(x, y)),
    weights: (data.weights || []).map((it) => [key(it.x, it.y), it.cost]),
    start: data.start || [0, 0],
    goal: data.goal || null,
  });
}

/* ── Embedded sample mazes (from sample_mazes/) ── */
const SAMPLE_MAZES = {
  "small_maze1.mz": `#########
#S..#...#
#.#.#.#.#
#.#...#.#
#.#####.#
#......G#
#########`,
  "maze1.mz": `#####################
#.....#.#...#.....#.#
###.###.#.#####.###.#
#.....#...#.....#...#
#####.#.###.#.#.###.#
#...#.#.....#.#.....#
###.#.#.#####.#.#.###
#.......#.....#.#.#.#
#.###.#.#####.#####.#
#...#.#.....#.......#
#.#.#.#####.#.#######
#.#.#.#.....#.......#
###.###.#####.#####.#
#.#.#.#.#...#.#...#.#
#.#.#.#####.#####.#.#
#...#...#...#.....#.#
#.#####.###.#.#####.#
#...#.........#.#.#.#
###.#.#####.###.#.#.#
#.......#...#.......#
#####################`,
  "maze2.mz": `###############
#S....#......#
#.###.#.####.#
#...#.#.#..#.#
###.#.#.#.##.#
#.#...#.#....#
#.#####.####.#
#.....#....#G#
#.###.####.#.#
#...#......#.#
###############`,
  "weighted_maze.mz": `###############
#S..2....#...G#
###.####.#.#..#
#...#..3...#..#
#.###.#####...#
#.....#...4...#
###############`,
};

function loadSampleMaze(name) {
  return parseAsciiMaze(SAMPLE_MAZES[name]);
}

window.MazeLib = {
  Maze, DIRECTIONS, DIRECTION_VECTORS, key, fromKey,
  createPerfectMaze, addRandomWeights, parseAsciiMaze, mazeFromJSON,
  SAMPLE_MAZES, loadSampleMaze,
};
