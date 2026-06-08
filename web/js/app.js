/* Maze Lab — application controller (vanilla). Wires the redesigned UI to the
 * ported maze model + algorithms and the canvas renderer.
 */
(function () {
  const { Maze, createPerfectMaze, addRandomWeights, parseAsciiMaze, mazeFromJSON,
          loadSampleMaze, SAMPLE_MAZES, key } = window.MazeLib;
  const { solveMaze } = window.MazeAlgorithms;
  const Renderer = window.MazeRenderer;
  const $ = (id) => document.getElementById(id);

  const ALGORITHMS = {
    "A*": "astar", "Dijkstra": "dijkstra", "Bellman-Ford": "bellmanford",
    "Greedy Best-First": "greedy", "Bidirectional BFS": "bidirectional",
    "BFS": "bfs", "DFS": "dfs",
  };
  const NON_COST_OPTIMAL = new Set(["bfs", "dfs", "bidirectional", "greedy"]);
  const ALGO_INFO = {
    "A*": { meta: "O(E log V) · space O(V) · optimal",
      about: "Combines cost-so-far with a Manhattan heuristic (f = g + h). The gold standard for grid pathfinding — optimal and far faster than Dijkstra." },
    "Dijkstra": { meta: "O(E log V) · space O(V) · optimal",
      about: "Expands cells by cumulative cost via a min-heap. No heuristic, so it explores every candidate within the cost boundary." },
    "Bellman-Ford": { meta: "O(V · E) · space O(V) · optimal (incl. negatives)",
      about: "Relaxes every edge V−1 times. Handles negative-weight edges where Dijkstra fails; slower on all-positive grids." },
    "Greedy Best-First": { meta: "O(E log V) · space O(V) · not optimal",
      about: "Rushes toward the goal using only the heuristic, ignoring path cost. Very fast in open corridors, not cost-optimal." },
    "Bidirectional BFS": { meta: "O(b^(d/2)) · space O(b^(d/2)) · optimal (unweighted)",
      about: "Two BFS frontiers expand from start and goal simultaneously and meet in the middle, halving the search space." },
    "BFS": { meta: "O(V + E) · space O(V) · optimal (unweighted)",
      about: "Explores layer-by-layer in hop-count order. Shortest unweighted path guaranteed; ignores weighted terrain costs." },
    "DFS": { meta: "O(V + E) · space O(V) · not optimal",
      about: "Dives as deep as possible before backtracking. Finds a path quickly but rarely the shortest — great for visualising exploration." },
  };
  const EDIT_MODES = [
    ["navigate", "Navigate", '<path d="M5 4l13 6-5 2-2 5z" fill="currentColor"/>'],
    ["draw_wall", "Draw", '<path d="M4 16L14 6l4 4L8 20H4z" fill="currentColor"/>'],
    ["erase", "Erase", '<rect x="5" y="11" width="11" height="8" rx="1.5" transform="rotate(-40 10 15)" fill="currentColor"/>'],
    ["set_start", "Start", '<circle cx="12" cy="12" r="6" fill="currentColor"/>'],
    ["set_goal", "Goal", '<path d="M6 3v18M6 4h11l-2 4 2 4H6" stroke="currentColor" stroke-width="2" fill="none" stroke-linejoin="round"/>'],
    ["add_weight", "Weight", '<path d="M5 19h14l-3-9H8z" fill="currentColor"/><circle cx="12" cy="6" r="2.4" fill="currentColor"/>'],
  ];

  // ── State ──
  const S = {
    maze: null, algo: "A*", result: null,
    visited: [], path: [], runner: null, dir: "N",
    heatmap: false, editMode: "navigate", dragBlocking: null,
    noPath: false, stepResult: null, stepIndex: 0,
    animTimer: null, lastSeed: "—",
  };

  const renderer = new Renderer($("maze"));

  function display() {
    return {
      visited: S.visited, path: S.path, runner: S.runner, dir: S.dir,
      heatmap: S.heatmap, noPath: S.noPath, result: S.result,
    };
  }
  function draw() { renderer.draw(S.maze, display()); }

  // ── Status / chips / stats ──
  function setStatus(text, kind = "info") {
    const el = $("status");
    el.className = "status " + kind;
    $("status-txt").textContent = text;
  }
  function setBadge(t) { $("insp-badge").textContent = t; }

  function updateChips(r) {
    $("kpi-algo").textContent = r ? r.algorithm : "—";
    $("kpi-explored").textContent = r ? r.exploredCount : "—";
    $("kpi-length").textContent = r ? r.pathLength : "—";
    $("kpi-cost").textContent = r && r.found ? fmt(r.cost) : "—";
    $("kpi-weights").textContent = S.maze.weights.size;
  }
  function clearChips() {
    ["algo", "explored", "length", "cost"].forEach((k) => ($("kpi-" + k).textContent = "—"));
    $("kpi-weights").textContent = S.maze.weights.size;
  }
  const fmt = (n) => (Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/\.?0+$/, ""));

  function statLines(rows) {
    $("statgrid").innerHTML = rows.map(([k, v, big]) =>
      `<div class="statline"><span class="sk">${k}</span><span class="sv${big ? " big" : ""}">${v}</span></div>`
    ).join("");
  }
  function setNote(html) { $("insp-note").innerHTML = html; }

  function mazeSummary() {
    statLines([
      ["Size", `${S.maze.width} × ${S.maze.height}`],
      ["Open cells", S.maze.openCellCount],
      ["Weighted", S.maze.weights.size],
      ["Start", `(${S.maze.start.join(", ")})`],
      ["Goal", S.maze.goal ? `(${S.maze.goal.join(", ")})` : "—"],
    ]);
  }

  function updateTopMeta() {
    $("tb-size").textContent = `${S.maze.width}×${S.maze.height}`;
    $("tb-open").textContent = S.maze.openCellCount;
    $("tb-seed").textContent = S.lastSeed;
  }

  // ── Algorithm info ──
  function algoKey() { return ALGORITHMS[S.algo]; }
  function weightedWarning(name) {
    if (!S.maze.weights.size || !NON_COST_OPTIMAL.has(algoKey())) return "";
    return `${name || S.algo} is not cost-optimal on weighted graphs. Use Dijkstra, A*, or Bellman-Ford for cheapest paths.`;
  }
  function refreshAlgoInfo() {
    const info = ALGO_INFO[S.algo] || {};
    $("algo-meta").textContent = info.meta || "";
    $("algo-about").textContent = info.about || "";
    const warn = weightedWarning();
    const w = $("algo-warn");
    if (warn) { w.textContent = warn; w.classList.add("show"); }
    else w.classList.remove("show");
  }

  // ── Reset / invalidate ──
  function reset(msg = "Ready.") {
    cancelAnim();
    S.stepResult = null; S.stepIndex = 0; S.result = null; S.noPath = false;
    S.visited = []; S.path = []; S.runner = null;
    setStatus(msg, "info"); setBadge("idle");
    refreshAlgoInfo(); mazeSummary(); clearChips();
    setNote('Pick an algorithm and press <b>Solve</b>, or <b>Animate</b> to watch the search expand cell by cell.');
    updateTopMeta();
    draw();
  }

  function invalidate() {
    cancelAnim();
    S.result = null; S.stepResult = null; S.stepIndex = 0; S.noPath = false;
    S.visited = []; S.path = []; S.runner = null;
    clearChips();
    setStatus("Maze edited — press Solve or Animate.", "info"); setBadge("edited");
    mazeSummary(); updateTopMeta();
    draw();
  }

  // ── Solve / Step / Animate / Compare ──
  function solve() {
    cancelAnim(); S.stepResult = null; S.noPath = false;
    let r;
    try { r = solveMaze(S.maze, algoKey()); }
    catch (e) { setStatus(e.message, "error"); return; }
    S.result = r;
    S.visited = r.visitedOrder.slice();
    S.path = r.path.slice(); S.runner = null;
    showResult();
    draw();
  }

  function step() {
    cancelAnim();
    if (!S.stepResult) {
      S.noPath = false;
      try { S.stepResult = solveMaze(S.maze, algoKey()); }
      catch (e) { setStatus(e.message, "error"); return; }
      S.stepIndex = 0; S.visited = []; S.path = []; S.runner = null;
      updateChips(S.stepResult); setBadge("stepping");
    }
    const r = S.stepResult;
    const total = r.visitedOrder.length;
    if (S.stepIndex < total) {
      S.stepIndex++;
      S.visited = r.visitedOrder.slice(0, S.stepIndex);
      if (S.stepIndex === total) {
        S.result = r; S.path = r.path.slice(); showResult();
      } else {
        S.path = [];
        setStatus(`Step ${S.stepIndex}/${total} — ${r.algorithm}.  Space = next.`, "running");
        statLines([
          ["Mode", "Step"],
          ["Algorithm", r.algorithm],
          ["Visited", `${S.stepIndex} / ${total}`],
        ]);
        setNote("<b>Space</b> → advance one cell · <b>S</b> → jump to full result");
      }
    } else {
      S.result = r; S.path = r.path.slice(); showResult();
    }
    draw();
  }

  function animate() {
    cancelAnim(); S.stepResult = null; S.noPath = false;
    let r;
    try { r = solveMaze(S.maze, algoKey()); }
    catch (e) { setStatus(e.message, "error"); return; }
    S.result = r; S.visited = []; S.path = []; S.runner = null;
    updateChips(r); setBadge("running");
    setStatus(`Animating ${r.algorithm}…`, "running");
    setNote("Cyan cells are nodes the algorithm visits, in discovery order.");
    statLines([["Mode", "Animate"], ["Algorithm", r.algorithm], ["Frontier", `0 / ${r.visitedOrder.length}`]]);
    animVisit(0);
  }

  function animVisit(i) {
    if (!S.result) return;
    const r = S.result;
    S.visited = r.visitedOrder.slice(0, i);
    S.path = []; S.runner = null;
    if (i < r.visitedOrder.length) {
      statLines([["Mode", "Animate"], ["Algorithm", r.algorithm], ["Frontier", `${i} / ${r.visitedOrder.length}`]]);
      draw();
      S.animTimer = setTimeout(() => animVisit(i + 1), delay());
    } else if (r.found) {
      draw();
      animRunner(0);
    } else {
      S.visited = r.visitedOrder.slice();
      showResult(); draw();
    }
  }

  function animRunner(i) {
    if (!S.result) return;
    const path = S.result.path;
    S.visited = S.result.visitedOrder.slice();
    S.path = path.slice(0, i + 1);
    S.runner = path[Math.min(i, path.length - 1)];
    S.dir = dirAt(path, i);
    draw();
    if (i < path.length - 1) {
      S.animTimer = setTimeout(() => animRunner(i + 1), delay());
    } else {
      S.path = path.slice(); S.runner = path[path.length - 1];
      showResult(); draw();
    }
  }

  function showResult() {
    const r = S.result;
    if (!r) return;
    updateChips(r);
    if (!r.found) {
      S.noPath = true;
      setStatus(`${r.algorithm} — no path found. The goal is walled off.`, "error");
      setBadge("no path");
      statLines([
        ["Result", "✗ No path"],
        ["Algorithm", r.algorithm],
        ["Explored", `${r.exploredCount} cells`],
      ]);
      setNote("The goal is sealed off from the start. Try <b>Erase</b> to open a wall, or <b>Generate</b> a new maze.");
      return;
    }
    S.noPath = false;
    const warn = weightedWarning(r.algorithm);
    setStatus(warn ? `${r.algorithm} solved it — not cost-optimal on weighted graphs.` : `${r.algorithm} solved it.`, "success");
    setBadge("solved");
    statLines([
      ["Algorithm", r.algorithm],
      ["Discovered", `${r.exploredCount} cells`],
      ["Path length", r.pathLength],
      ["Path cost", fmt(r.cost), true],
      ["Weighted", `${S.maze.weights.size} cells`],
      ["Open cells", S.maze.openCellCount],
    ]);
    setNote(warn
      ? `<span style="color:oklch(0.8 0.12 30)">${warn}</span>`
      : "Amber ribbon traces the recovered path. Toggle <b>Heatmap</b> to colour cells by discovery order.");
  }

  function compareAll() {
    cancelAnim(); S.stepResult = null; S.noPath = false;
    let results;
    try { results = Object.values(ALGORITHMS).map((k) => solveMaze(S.maze, k)); }
    catch (e) { setStatus(e.message, "error"); return; }
    const labels = Object.keys(ALGORITHMS);
    let best = null;
    results.forEach((r) => { if (r.found && (!best || r.cost < best.cost)) best = r; });

    S.result = best; S.visited = [];
    S.path = best ? best.path.slice() : []; S.runner = null;
    if (best) {
      setStatus("Compared all algorithms — best-cost path shown.", "success"); setBadge("compared");
      $("kpi-algo").textContent = best.algorithm;
      $("kpi-cost").textContent = fmt(best.cost);
      $("kpi-length").textContent = best.pathLength;
      $("kpi-explored").textContent = best.exploredCount;
      $("kpi-weights").textContent = S.maze.weights.size;
    } else {
      S.noPath = true;
      setStatus("Compared all — none could reach the goal.", "error"); setBadge("no path");
      clearChips();
    }
    // inspector compact list
    const rows = labels.map((label, i) => {
      const r = results[i];
      const isBest = best && r.algorithm === best.algorithm && r.found;
      const cost = r.found ? fmt(r.cost) : "∞";
      return `<div class="cmp-row${isBest ? " best" : ""}"><span class="cn">${label}${isBest ? " ◂ best" : ""}</span><span class="cs">${r.exploredCount}c · ${cost}</span></div>`;
    }).join("");
    $("statgrid").innerHTML = `<div class="cmp-list">${rows}</div>`;
    setNote("Bar chart shows cells explored per algorithm. Fewer explored cells = more efficient search.");
    draw();
    showCompareModal(labels, results, best);
  }

  // ── Compare modal ──
  function showCompareModal(labels, results, best) {
    $("modal-sub").textContent = `Maze ${S.maze.width}×${S.maze.height} · ${S.maze.weights.size} weighted cells`;
    const found = results.map((r, i) => ({ r, label: labels[i] })).filter((x) => x.r.found);
    const body = $("modal-body");
    if (!found.length) {
      body.innerHTML = `<div style="text-align:center;color:var(--dim);padding:40px 0">No algorithm could reach the goal.</div>`;
    } else {
      const maxE = Math.max(...found.map((x) => x.r.exploredCount)) || 1;
      const colors = ["var(--accent)", "var(--c-start)", "var(--c-path)", "var(--c-goal)", "var(--c-frontier)", "var(--c-weight)", "var(--dim)"];
      body.innerHTML = found.map((x, i) => {
        const w = Math.max(4, (x.r.exploredCount / maxE) * 100);
        const isBest = best && x.r.algorithm === best.algorithm;
        return `<div class="bar-row">
          <div class="bn">${x.label}${isBest ? ' <span style="color:var(--accent-lt);font-family:var(--mono);font-size:10px">★</span>' : ""}</div>
          <div class="bar-track">
            <div class="bar-fill" style="width:0%;background:${colors[i % colors.length]}" data-w="${w}"></div>
            <div class="bar-stat">${x.r.exploredCount} cells · cost ${fmt(x.r.cost)} · len ${x.r.pathLength}</div>
          </div></div>`;
      }).join("");
    }
    $("modal-bg").classList.add("show");
    requestAnimationFrame(() => body.querySelectorAll(".bar-fill").forEach((el) => (el.style.width = el.dataset.w + "%")));
  }

  // ── Maze ops ──
  function readSize() {
    return [Math.max(5, +$("m-w").value || 18), Math.max(5, +$("m-h").value || 12)];
  }
  function seedValue() {
    const t = $("m-seed").value.trim();
    if (t && /^-?\d+$/.test(t)) return +t;
    const s = ((Math.random() * 99999) | 0) + 1;
    $("m-seed").value = String(s);
    return s;
  }
  function generate(weighted) {
    cancelAnim();
    const [w, h] = readSize();
    const seed = seedValue();
    S.maze = createPerfectMaze(w, h, seed);
    if (weighted) addRandomWeights(S.maze, { density: (+$("density").value) / 100, minimum: 2, maximum: 9, seed: seed + 101 });
    S.lastSeed = String(seed);
    reset(`${weighted ? "Weighted maze" : "Maze"}  ${w}×${h},  seed ${seed}.`);
  }
  function newBlank() {
    const [w, h] = readSize();
    S.maze = new Maze(w, h);
    S.lastSeed = "—";
    reset(`Blank ${w}×${h} grid — use Draw to add walls.`);
  }
  function loadSample() {
    const name = $("samples").value;
    try { S.maze = loadSampleMaze(name); S.lastSeed = "—"; reset(`Loaded  ${name}.`); }
    catch (e) { setStatus(e.message, "error"); }
  }

  // ── Editing ──
  function setMode(m) {
    S.editMode = m;
    document.querySelectorAll(".tool").forEach((t) => t.classList.toggle("active", t.dataset.mode === m));
    $("maze").style.cursor = m === "navigate" ? "default" : "crosshair";
  }
  function block(pos) {
    const k = key(pos[0], pos[1]);
    if (k === key(S.maze.start[0], S.maze.start[1]) || (S.maze.goal && k === key(S.maze.goal[0], S.maze.goal[1]))) return;
    S.maze.blocked.add(k); S.maze.weights.delete(k); invalidate();
  }
  function unblock(pos) { S.maze.clearCell(pos, true); invalidate(); }
  function setStart(pos) {
    if (S.maze.goal && pos[0] === S.maze.goal[0] && pos[1] === S.maze.goal[1]) return;
    S.maze.clearCell(pos); S.maze.start = pos; invalidate();
  }
  function setGoal(pos) {
    if (pos[0] === S.maze.start[0] && pos[1] === S.maze.start[1]) return;
    S.maze.clearCell(pos); S.maze.goal = pos; invalidate();
  }
  function cycleWeight(pos) {
    const k = key(pos[0], pos[1]);
    if (!S.maze.isOpen(pos) || k === key(S.maze.start[0], S.maze.start[1]) ||
        (S.maze.goal && k === key(S.maze.goal[0], S.maze.goal[1]))) return;
    const cur = S.maze.weights.get(k) || 1;
    if (cur < 9) S.maze.weights.set(k, Math.max(2, cur + 1));
    else S.maze.weights.delete(k);
    invalidate();
  }
  function applyEdit(pos, drag) {
    if (!pos) return;
    const m = S.editMode;
    if (m === "navigate") return;
    if (m === "draw_wall") { if (drag && S.dragBlocking === false) return; block(pos); }
    else if (m === "erase") unblock(pos);
    else if (m === "set_start" && !drag) setStart(pos);
    else if (m === "set_goal" && !drag) setGoal(pos);
    else if (m === "add_weight" && !drag) cycleWeight(pos);
  }

  // ── Files: export / save / open ──
  function download(name, content, type) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = name; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function exportRun() {
    if (!S.result) { setStatus("Solve or animate first, then export.", "error"); return; }
    const r = S.result;
    let csv = "Step,x,y,Event\n";
    r.visitedOrder.forEach((p, i) => {
      const ev = (p[0] === r.goal[0] && p[1] === r.goal[1]) ? "goal" : "visited";
      csv += `${i + 1},${p[0]},${p[1]},${ev}\n`;
    });
    const stats = `Algorithm: ${r.algorithm}\nMaze: ${S.maze.width} x ${S.maze.height}\nStart: (${r.start.join(", ")})    Goal: (${r.goal.join(", ")})\nFound: ${r.found}\nDiscovered: ${r.exploredCount} cells\nPath length: ${r.pathLength}\nPath cost: ${fmt(r.cost)}\nWeighted cells: ${S.maze.weights.size}\nPath: ${JSON.stringify(r.path)}\n`;
    download("exploration.csv", csv, "text/csv");
    setTimeout(() => download("statistics.txt", stats, "text/plain"), 250);
    setStatus("Exported  exploration.csv + statistics.txt.", "success");
  }
  function saveMaze() {
    download("maze.maze", JSON.stringify(S.maze.toJSON(), null, 2), "application/json");
    setStatus("Saved  maze.maze.", "success");
  }
  function openFile() { $("file-input").click(); }
  function onFile(e) {
    const f = e.target.files[0];
    if (!f) return;
    const rd = new FileReader();
    rd.onload = () => {
      try {
        const txt = rd.result.trim();
        S.maze = txt.startsWith("{") ? mazeFromJSON(JSON.parse(txt)) : parseAsciiMaze(rd.result);
        S.lastSeed = "—";
        reset(`Loaded  ${f.name}.`);
      } catch (err) { setStatus("Load failed: " + err.message, "error"); }
    };
    rd.readAsText(f);
    e.target.value = "";
  }

  // ── helpers ──
  function dirAt(path, i) {
    if (path.length < 2) return "N";
    const [a, b] = i <= 0 ? [path[0], path[1]] : [path[i - 1], path[Math.min(i, path.length - 1)]];
    const d = `${b[0] - a[0]},${b[1] - a[1]}`;
    return { "0,1": "N", "1,0": "E", "0,-1": "S", "-1,0": "W" }[d] || "N";
  }
  function delay() { return Math.max(5, 135 - (+$("speed").value)); }
  function cancelAnim() { if (S.animTimer) { clearTimeout(S.animTimer); S.animTimer = null; } }

  // ── Tweaks ──
  const ACCENTS = {
    Violet: [0.66, 0.19, 290], Emerald: [0.70, 0.15, 162],
    Amber: [0.76, 0.15, 70], Cyan: [0.70, 0.13, 222], Rose: [0.66, 0.20, 14],
  };
  function suppressTransitions() {
    const root = document.documentElement;
    root.classList.add("no-anim");
    void root.offsetWidth; // reflow re-resolves var()-based colours
    requestAnimationFrame(() => requestAnimationFrame(() => root.classList.remove("no-anim")));
  }
  function setAccent(name) {
    const [l, c, h] = ACCENTS[name];
    const r = document.documentElement.style;
    r.setProperty("--accent", `oklch(${l} ${c} ${h})`);
    r.setProperty("--accent-2", `oklch(${(l - 0.06).toFixed(3)} ${c} ${h})`);
    r.setProperty("--accent-lt", `oklch(${(l + 0.14).toFixed(3)} ${(c - 0.09).toFixed(3)} ${h})`);
    r.setProperty("--accent-soft", `oklch(${l} ${c} ${h} / 0.14)`);
    document.querySelectorAll("#tw-accent .swatch").forEach((s) => s.classList.toggle("sel", s.dataset.name === name));
    localStorage.setItem("ml.accent", name);
    suppressTransitions();
    renderer.refreshColors(); draw();
  }
  function setTheme(v) {
    document.documentElement.classList.toggle("theme-light", v === "light");
    document.querySelectorAll("#tw-theme button").forEach((b) => b.classList.toggle("sel", b.dataset.v === v));
    localStorage.setItem("ml.theme", v);
    suppressTransitions();
    renderer.refreshColors(); draw();
  }
  function setCellStyle(v) {
    renderer.cellStyle = v;
    document.querySelectorAll("#tw-cellstyle button").forEach((b) => b.classList.toggle("sel", b.dataset.v === v));
    localStorage.setItem("ml.cellstyle", v);
    draw();
  }

  // ── Build dynamic UI bits ──
  function buildTools() {
    $("tools").innerHTML = EDIT_MODES.map(([mode, label, svg]) =>
      `<button class="tool${mode === "navigate" ? " active" : ""}" data-mode="${mode}"><svg viewBox="0 0 24 24">${svg}</svg>${label}</button>`
    ).join("");
    document.querySelectorAll(".tool").forEach((t) => t.addEventListener("click", () => setMode(t.dataset.mode)));
  }
  function buildSamples() {
    $("samples").innerHTML = Object.keys(SAMPLE_MAZES).map((n) => `<option>${n}</option>`).join("");
  }
  function buildAccentSwatches() {
    $("tw-accent").innerHTML = Object.entries(ACCENTS).map(([name, [l, c, h]]) =>
      `<div class="swatch" data-name="${name}" title="${name}" style="background:oklch(${l} ${c} ${h})"></div>`
    ).join("");
    document.querySelectorAll("#tw-accent .swatch").forEach((s) => s.addEventListener("click", () => setAccent(s.dataset.name)));
  }

  // ── Events ──
  function bind() {
    $("algo").addEventListener("change", (e) => { S.algo = e.target.value; refreshAlgoInfo(); S.stepResult = null; reset("Algorithm changed."); });
    $("b-solve").addEventListener("click", solve);
    $("b-animate").addEventListener("click", animate);
    $("b-step").addEventListener("click", step);
    $("b-compare").addEventListener("click", compareAll);
    $("b-reset").addEventListener("click", () => reset("View reset."));
    $("b-generate").addEventListener("click", () => generate(false));
    $("b-weighted").addEventListener("click", () => generate(true));
    $("b-blank").addEventListener("click", newBlank);
    $("b-load").addEventListener("click", loadSample);
    $("b-open").addEventListener("click", openFile);
    $("b-save").addEventListener("click", saveMaze);
    $("b-export").addEventListener("click", exportRun);
    $("file-input").addEventListener("change", onFile);

    $("speed").addEventListener("input", (e) => ($("speed-val").textContent = e.target.value));
    $("density").addEventListener("input", (e) => ($("dens-val").textContent = e.target.value + "%"));
    $("heat-toggle").addEventListener("click", () => {
      S.heatmap = !S.heatmap;
      $("heat-toggle").classList.toggle("on", S.heatmap);
      draw();
    });

    // canvas editing
    const cv = $("maze");
    cv.addEventListener("mousedown", (e) => {
      const pos = cellAt(e);
      if (!pos) return;
      if (S.editMode === "draw_wall") S.dragBlocking = !S.maze.blocked.has(key(pos[0], pos[1]));
      else if (S.editMode === "erase") S.dragBlocking = true;
      S.dragging = true;
      applyEdit(pos, false);
    });
    cv.addEventListener("mousemove", (e) => { if (S.dragging) applyEdit(cellAt(e), true); });
    window.addEventListener("mouseup", () => { S.dragging = false; S.dragBlocking = null; });
    cv.addEventListener("contextmenu", (e) => { e.preventDefault(); rightClick(e); });

    // modal
    $("modal-close").addEventListener("click", () => $("modal-bg").classList.remove("show"));
    $("modal-bg").addEventListener("click", (e) => { if (e.target === $("modal-bg")) $("modal-bg").classList.remove("show"); });

    // tweaks
    $("tweaks-fab").addEventListener("click", () => $("tweaks").classList.toggle("show"));
    $("tweaks-close").addEventListener("click", () => $("tweaks").classList.remove("show"));
    document.querySelectorAll("#tw-theme button").forEach((b) => b.addEventListener("click", () => setTheme(b.dataset.v)));
    document.querySelectorAll("#tw-cellstyle button").forEach((b) => b.addEventListener("click", () => setCellStyle(b.dataset.v)));

    // keyboard
    window.addEventListener("keydown", (e) => {
      const tag = (e.target.tagName || "").toLowerCase();
      if (["input", "select", "textarea"].includes(tag)) return;
      const k = e.key.toLowerCase();
      if (k === " " || e.code === "Space") { e.preventDefault(); step(); }
      else if (k === "s") solve();
      else if (k === "a") animate();
      else if (k === "r") reset("View reset.");
      else if (e.key === "Escape") { cancelAnim(); $("modal-bg").classList.remove("show"); }
    });

    window.addEventListener("resize", () => { clearTimeout(S._rz); S._rz = setTimeout(draw, 80); });
  }

  function cellAt(e) {
    const r = $("maze").getBoundingClientRect();
    return renderer.pxToCell(e.clientX - r.left, e.clientY - r.top, S.maze);
  }
  function rightClick(e) { // quick set start/goal via right-drag-less menu → cycle through
    const pos = cellAt(e); if (!pos) return;
    // simple behaviour: shift sets goal, plain sets start
    if (e.shiftKey) setGoal(pos); else setStart(pos);
  }

  // ── Init ──
  function init() {
    buildTools(); buildSamples(); buildAccentSwatches();
    // create the maze before any tweak setter (they call draw())
    S.maze = createPerfectMaze(18, 12, 7);
    S.lastSeed = "7"; $("m-seed").value = "";
    setAccent(localStorage.getItem("ml.accent") || "Violet");
    setTheme(localStorage.getItem("ml.theme") || "dark");
    setCellStyle(localStorage.getItem("ml.cellstyle") || "tile");
    bind();
    setMode("navigate");
    reset("Ready — solve, animate, or step through the search.");
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
