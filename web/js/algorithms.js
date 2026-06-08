/* Graph search algorithms — faithful JS port of graph_algorithms.py.
 * Returns SearchResult { algorithm, start, goal, path, visitedOrder, cost,
 * found, pathLength, exploredCount }.
 */
(function () {
  const { key } = window.MazeLib;

  /* Binary min-heap with a comparator (mirrors Python heapq tuple ordering). */
  class Heap {
    constructor(cmp) { this.a = []; this.cmp = cmp; }
    get size() { return this.a.length; }
    push(v) {
      const a = this.a; a.push(v);
      let i = a.length - 1;
      while (i > 0) {
        const p = (i - 1) >> 1;
        if (this.cmp(a[i], a[p]) < 0) { [a[i], a[p]] = [a[p], a[i]]; i = p; }
        else break;
      }
    }
    pop() {
      const a = this.a; const top = a[0]; const last = a.pop();
      if (a.length) {
        a[0] = last; let i = 0; const n = a.length;
        while (true) {
          let l = 2 * i + 1, r = 2 * i + 2, s = i;
          if (l < n && this.cmp(a[l], a[s]) < 0) s = l;
          if (r < n && this.cmp(a[r], a[s]) < 0) s = r;
          if (s === i) break;
          [a[i], a[s]] = [a[s], a[i]]; i = s;
        }
      }
      return top;
    }
  }
  // Compare two positions lexicographically (Python tuple ordering).
  const cmpPos = (p, q) => (p[0] - q[0]) || (p[1] - q[1]);

  function manhattan(a, b) {
    return Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]);
  }

  function resolveEndpoints(maze, start, goal) {
    const s = start || maze.start;
    const g = goal || maze.goal;
    if (!g) throw new Error("Goal is not set");
    if (!maze.isOpen(s)) throw new Error("Start cell is not open: " + s);
    if (!maze.isOpen(g)) throw new Error("Goal cell is not open: " + g);
    return [s, g];
  }

  function reconstructPath(cameFrom, start, goal) {
    const gk = key(goal[0], goal[1]);
    if (!cameFrom.has(gk)) return [];
    let current = goal;
    const path = [];
    while (current) {
      path.push(current);
      current = cameFrom.get(key(current[0], current[1]));
    }
    path.reverse();
    return path.length && path[0][0] === start[0] && path[0][1] === start[1] ? path : [];
  }

  function pathCost(maze, path) {
    let c = 0;
    for (let i = 1; i < path.length; i++) c += maze.movementCost(path[i]);
    return c;
  }

  function makeResult(algorithm, maze, start, goal, path, visitedOrder) {
    const cost = path.length ? pathCost(maze, path) : Infinity;
    return {
      algorithm, start, goal, path, visitedOrder, cost,
      get found() { return this.path.length > 0; },
      get pathLength() { return Math.max(0, this.path.length - 1); },
      get exploredCount() { return this.visitedOrder.length; },
    };
  }

  /* ── BFS ── */
  function bfs(maze, start, goal) {
    [start, goal] = resolveEndpoints(maze, start, goal);
    const frontier = [start]; let head = 0;
    const cameFrom = new Map([[key(start[0], start[1]), null]]);
    const visited = [];
    while (head < frontier.length) {
      const current = frontier[head++];
      visited.push(current);
      if (current[0] === goal[0] && current[1] === goal[1]) break;
      for (const nxt of maze.neighbours(current)) {
        const nk = key(nxt[0], nxt[1]);
        if (!cameFrom.has(nk)) { cameFrom.set(nk, current); frontier.push(nxt); }
      }
    }
    return makeResult("BFS", maze, start, goal, reconstructPath(cameFrom, start, goal), visited);
  }

  /* ── DFS ── */
  function dfs(maze, start, goal) {
    [start, goal] = resolveEndpoints(maze, start, goal);
    const stack = [start];
    const cameFrom = new Map([[key(start[0], start[1]), null]]);
    const visited = [];
    const expanded = new Set();
    while (stack.length) {
      const current = stack.pop();
      const ck = key(current[0], current[1]);
      if (expanded.has(ck)) continue;
      expanded.add(ck);
      visited.push(current);
      if (current[0] === goal[0] && current[1] === goal[1]) break;
      const nbrs = maze.neighbours(current);
      for (let i = nbrs.length - 1; i >= 0; i--) {
        const nxt = nbrs[i]; const nk = key(nxt[0], nxt[1]);
        if (!cameFrom.has(nk)) { cameFrom.set(nk, current); stack.push(nxt); }
      }
    }
    return makeResult("DFS", maze, start, goal, reconstructPath(cameFrom, start, goal), visited);
  }

  /* ── Bidirectional BFS ── */
  function expandFrontier(maze, frontier, ownParent, otherParent, visited) {
    const n = frontier.length;
    for (let i = 0; i < n; i++) {
      const current = frontier.shift();
      visited.push(current);
      for (const nxt of maze.neighbours(current)) {
        const nk = key(nxt[0], nxt[1]);
        if (!ownParent.has(nk)) {
          ownParent.set(nk, current);
          if (otherParent.has(nk)) return nxt;
          frontier.push(nxt);
        }
      }
    }
    return null;
  }
  function bidirectional(maze, start, goal) {
    [start, goal] = resolveEndpoints(maze, start, goal);
    if (start[0] === goal[0] && start[1] === goal[1])
      return makeResult("Bidirectional BFS", maze, start, goal, [start], [start]);
    const fS = [start], fG = [goal];
    const pS = new Map([[key(start[0], start[1]), null]]);
    const pG = new Map([[key(goal[0], goal[1]), null]]);
    const visited = [];
    let meeting = null;
    while (fS.length && fG.length && meeting === null) {
      meeting = expandFrontier(maze, fS, pS, pG, visited);
      if (meeting !== null) break;
      meeting = expandFrontier(maze, fG, pG, pS, visited);
    }
    // reconstruct
    let path = [];
    if (meeting !== null) {
      const firstHalf = [];
      let cur = meeting;
      while (cur) { firstHalf.push(cur); cur = pS.get(key(cur[0], cur[1])); }
      firstHalf.reverse();
      if (firstHalf[0][0] === start[0] && firstHalf[0][1] === start[1]) {
        const secondHalf = [];
        cur = pG.get(key(meeting[0], meeting[1]));
        while (cur) { secondHalf.push(cur); cur = pG.get(key(cur[0], cur[1])); }
        const full = firstHalf.concat(secondHalf);
        if (full.length && full[full.length - 1][0] === goal[0] && full[full.length - 1][1] === goal[1])
          path = full;
      }
    }
    return makeResult("Bidirectional BFS", maze, start, goal, path, visited);
  }

  /* ── Dijkstra ── */
  function dijkstra(maze, start, goal) {
    [start, goal] = resolveEndpoints(maze, start, goal);
    const frontier = new Heap((a, b) => (a[0] - b[0]) || cmpPos(a[1], b[1]));
    frontier.push([0, start]);
    const cameFrom = new Map([[key(start[0], start[1]), null]]);
    const costSoFar = new Map([[key(start[0], start[1]), 0]]);
    const visited = [];
    const settled = new Set();
    while (frontier.size) {
      const [, current] = frontier.pop();
      const ck = key(current[0], current[1]);
      if (settled.has(ck)) continue;
      settled.add(ck);
      visited.push(current);
      if (current[0] === goal[0] && current[1] === goal[1]) break;
      for (const nxt of maze.neighbours(current)) {
        const nk = key(nxt[0], nxt[1]);
        const newCost = costSoFar.get(ck) + maze.movementCost(nxt);
        if (!costSoFar.has(nk) || newCost < costSoFar.get(nk)) {
          costSoFar.set(nk, newCost);
          cameFrom.set(nk, current);
          frontier.push([newCost, nxt]);
        }
      }
    }
    return makeResult("Dijkstra", maze, start, goal, reconstructPath(cameFrom, start, goal), visited);
  }

  /* ── Greedy Best-First ── */
  function greedy(maze, start, goal) {
    [start, goal] = resolveEndpoints(maze, start, goal);
    const frontier = new Heap((a, b) => (a[0] - b[0]) || cmpPos(a[1], b[1]));
    frontier.push([manhattan(start, goal), start]);
    const cameFrom = new Map([[key(start[0], start[1]), null]]);
    const visited = [];
    const expanded = new Set();
    while (frontier.size) {
      const [, current] = frontier.pop();
      const ck = key(current[0], current[1]);
      if (expanded.has(ck)) continue;
      expanded.add(ck);
      visited.push(current);
      if (current[0] === goal[0] && current[1] === goal[1]) break;
      for (const nxt of maze.neighbours(current)) {
        const nk = key(nxt[0], nxt[1]);
        if (!cameFrom.has(nk)) {
          cameFrom.set(nk, current);
          frontier.push([manhattan(nxt, goal), nxt]);
        }
      }
    }
    return makeResult("Greedy Best-First", maze, start, goal, reconstructPath(cameFrom, start, goal), visited);
  }

  /* ── Bellman-Ford ── */
  function bellmanFord(maze, start, goal) {
    [start, goal] = resolveEndpoints(maze, start, goal);
    const openCells = [];
    for (let y = 0; y < maze.height; y++)
      for (let x = 0; x < maze.width; x++)
        if (maze.isOpen([x, y])) openCells.push([x, y]);
    const dist = new Map();
    for (const c of openCells) dist.set(key(c[0], c[1]), Infinity);
    const parents = new Map([[key(start[0], start[1]), null]]);
    dist.set(key(start[0], start[1]), 0);
    const visited = [];
    const visitedSet = new Set();
    for (let iter = 0; iter < Math.max(0, openCells.length - 1); iter++) {
      let changed = false;
      for (const current of openCells) {
        const ck = key(current[0], current[1]);
        if (dist.get(ck) === Infinity) continue;
        if (!visitedSet.has(ck)) { visitedSet.add(ck); visited.push(current); }
        for (const nxt of maze.neighbours(current)) {
          const nk = key(nxt[0], nxt[1]);
          const cand = dist.get(ck) + maze.movementCost(nxt);
          if (cand < dist.get(nk)) {
            dist.set(nk, cand);
            parents.set(nk, current);
            changed = true;
          }
        }
      }
      if (!changed) break;
    }
    return makeResult("Bellman-Ford", maze, start, goal, reconstructPath(parents, start, goal), visited);
  }

  /* ── A* ── */
  function astar(maze, start, goal) {
    [start, goal] = resolveEndpoints(maze, start, goal);
    const frontier = new Heap((a, b) => (a[0] - b[0]) || (a[1] - b[1]) || cmpPos(a[2], b[2]));
    frontier.push([0, 0, start]);
    const cameFrom = new Map([[key(start[0], start[1]), null]]);
    const costSoFar = new Map([[key(start[0], start[1]), 0]]);
    const visited = [];
    const settled = new Set();
    while (frontier.size) {
      const [, currentCost, current] = frontier.pop();
      const ck = key(current[0], current[1]);
      if (settled.has(ck)) continue;
      settled.add(ck);
      visited.push(current);
      if (current[0] === goal[0] && current[1] === goal[1]) break;
      for (const nxt of maze.neighbours(current)) {
        const nk = key(nxt[0], nxt[1]);
        const newCost = currentCost + maze.movementCost(nxt);
        if (!costSoFar.has(nk) || newCost < costSoFar.get(nk)) {
          costSoFar.set(nk, newCost);
          cameFrom.set(nk, current);
          frontier.push([newCost + manhattan(nxt, goal), newCost, nxt]);
        }
      }
    }
    return makeResult("A*", maze, start, goal, reconstructPath(cameFrom, start, goal), visited);
  }

  const ALGO_FNS = {
    bfs, dfs, bidirectional, dijkstra, greedy, bellmanford: bellmanFord, astar,
  };

  function solveMaze(maze, algorithm) {
    const fn = ALGO_FNS[algorithm];
    if (!fn) throw new Error("Unknown algorithm: " + algorithm);
    return fn(maze);
  }

  window.MazeAlgorithms = { solveMaze, manhattan, ALGO_FNS };
})();
