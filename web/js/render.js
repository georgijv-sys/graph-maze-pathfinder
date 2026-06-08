/* Canvas renderer for the maze. Origin is bottom-left (y grows upward),
 * mirroring the Python GUI geometry. Reads theme colours from CSS vars so
 * accent / light-dark / cell-style tweaks reflect immediately.
 */
(function () {
  const { key } = window.MazeLib;

  class Renderer {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.cellSize = 28;
      this.margin = 22;
      this.originX = this.margin;
      this.originY = this.margin;
      this.cellStyle = "tile";
      this.refreshColors();
    }

    refreshColors() {
      const cs = getComputedStyle(document.documentElement);
      const g = (n) => cs.getPropertyValue(n).trim();
      this.col = {
        mazeBg: g("--maze-bg"),
        open: g("--c-open"),
        block: g("--c-block"),
        wall: g("--c-wall"),
        frontier: g("--c-frontier"),
        path: g("--c-path"),
        pathLine: g("--c-path-line"),
        start: g("--c-start"),
        goal: g("--c-goal"),
        weight: g("--c-weight"),
        accent: g("--accent"),
        line: g("--line-2"),
        text: g("--text"),
        dim: g("--dim"),
      };
    }

    resize() {
      const r = this.canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      this.canvas.width = Math.round(r.width * dpr);
      this.canvas.height = Math.round(r.height * dpr);
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      this.cw = r.width;
      this.ch = r.height;
    }

    layout(maze) {
      const m = this.margin;
      this.cellSize = Math.max(12, Math.min(54,
        Math.floor((this.cw - m * 2) / maze.width),
        Math.floor((this.ch - m * 2) / maze.height)));
      const gw = maze.width * this.cellSize;
      const gh = maze.height * this.cellSize;
      this.originX = Math.max(m, Math.floor((this.cw - gw) / 2));
      this.originY = Math.max(m, Math.floor((this.ch - gh) / 2));
    }

    cellBox(x, y, maze) {
      const sy = maze.height - 1 - y;
      const x1 = this.originX + x * this.cellSize;
      const y1 = this.originY + sy * this.cellSize;
      return [x1, y1, x1 + this.cellSize, y1 + this.cellSize];
    }

    pxToCell(px, py, maze) {
      const cs = this.cellSize;
      if (cs <= 0) return null;
      const x = Math.floor((px - this.originX) / cs);
      const sy = Math.floor((py - this.originY) / cs);
      const y = maze.height - 1 - sy;
      if (x >= 0 && x < maze.width && y >= 0 && y < maze.height) return [x, y];
      return null;
    }

    heatColor(index, total) {
      // cyan → indigo ramp following discovery order
      const t = index / Math.max(total - 1, 1);
      const h = 228 + (296 - 228) * t;
      const l = 0.74 - 0.16 * t;
      const c = 0.13 + 0.07 * t;
      return `oklch(${l.toFixed(3)} ${c.toFixed(3)} ${h.toFixed(0)})`;
    }

    draw(maze, st) {
      const ctx = this.ctx;
      this.resize();
      if (this.cw < 4 || this.ch < 4) return;
      this.layout(maze);
      ctx.clearRect(0, 0, this.cw, this.ch);

      const cs = this.cellSize;
      const gap = Math.max(1, Math.floor(cs / 18));
      const visitedSet = new Set(st.visited.map((p) => key(p[0], p[1])));
      const pathSet = new Set(st.path.map((p) => key(p[0], p[1])));
      const useHeat = st.heatmap && st.visited.length;
      const heatIdx = {};
      if (useHeat) st.visited.forEach((p, i) => { heatIdx[key(p[0], p[1])] = i; });
      const totalV = st.visited.length;
      const startK = key(maze.start[0], maze.start[1]);
      const goalK = maze.goal ? key(maze.goal[0], maze.goal[1]) : null;
      const flat = this.cellStyle === "flat";

      // ── 1. Cell fills ──
      for (let y = 0; y < maze.height; y++) {
        for (let x = 0; x < maze.width; x++) {
          const k = key(x, y);
          const [x1, y1, x2, y2] = this.cellBox(x, y, maze);
          let fill = null, isWeight = false;

          if (maze.blocked.has(k)) {
            fill = this.col.block;
          } else {
            fill = flat ? "transparent" : this.col.open;
            if (maze.weights.has(k)) { fill = this.col.weight; isWeight = true; }
            if (visitedSet.has(k)) fill = (useHeat && k in heatIdx) ? this.heatColor(heatIdx[k], totalV) : this.col.frontier;
            if (pathSet.has(k)) fill = this.col.path;
          }

          if (fill && fill !== "transparent") {
            const a = (isWeight && !visitedSet.has(k) && !pathSet.has(k)) ? 0.34 : 1;
            ctx.globalAlpha = a;
            this.roundRect(x1 + gap, y1 + gap, cs - gap * 2, cs - gap * 2, Math.max(1, cs * 0.14));
            ctx.fillStyle = fill;
            ctx.fill();
            ctx.globalAlpha = 1;
          }

          // weight label
          if (!maze.blocked.has(k) && maze.weights.has(k) && cs >= 16) {
            ctx.fillStyle = (visitedSet.has(k) || pathSet.has(k)) ? "oklch(0.18 0.02 300)" : this.col.weight;
            ctx.font = `600 ${Math.max(9, Math.floor(cs / 2.6))}px JetBrains Mono, monospace`;
            ctx.textAlign = "center"; ctx.textBaseline = "middle";
            ctx.fillText(String(maze.weights.get(k)), (x1 + x2) / 2, (y1 + y2) / 2 + 0.5);
          }
        }
      }

      // ── 2. Walls ──
      this.drawWalls(maze, gap);

      // ── 3. Path ribbon (glow) ──
      if (st.path.length > 1) {
        const pts = st.path.map((p) => {
          const [x1, y1, x2, y2] = this.cellBox(p[0], p[1], maze);
          return [(x1 + x2) / 2, (y1 + y2) / 2];
        });
        const lw = Math.max(3, Math.floor(cs / 5.5));
        ctx.save();
        ctx.shadowColor = this.col.pathLine;
        ctx.shadowBlur = Math.max(6, cs * 0.4);
        ctx.strokeStyle = this.col.pathLine;
        ctx.lineWidth = lw;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.beginPath();
        pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
        ctx.stroke();
        ctx.restore();
      }

      // ── 4. Start / Goal ──
      this.drawMarker(maze.start, this.col.start, "S", maze);
      if (maze.goal) this.drawMarker(maze.goal, this.col.goal, "G", maze);

      // ── 5. Runner ──
      if (st.runner) this.drawRunner(st.runner, st.dir, maze);

      // ── 6. No-path banner ──
      if (st.noPath) this.drawNoPath(st.result);
    }

    drawWalls(maze, gap) {
      const ctx = this.ctx;
      const cs = this.cellSize;
      const ww = Math.max(2, cs * 0.11);
      ctx.strokeStyle = this.col.wall;
      ctx.lineWidth = ww;
      ctx.lineCap = "round";
      for (let y = 0; y < maze.height; y++) {
        for (let x = 0; x < maze.width; x++) {
          if (maze.blocked.has(key(x, y))) continue;
          const [N, E, S, W] = maze.getWalls(x, y);
          const [x1, y1, x2, y2] = this.cellBox(x, y, maze);
          ctx.beginPath();
          if (N) { ctx.moveTo(x1 + gap, y1 + gap); ctx.lineTo(x2 - gap, y1 + gap); }
          if (E) { ctx.moveTo(x2 - gap, y1 + gap); ctx.lineTo(x2 - gap, y2 - gap); }
          if (S) { ctx.moveTo(x1 + gap, y2 - gap); ctx.lineTo(x2 - gap, y2 - gap); }
          if (W) { ctx.moveTo(x1 + gap, y1 + gap); ctx.lineTo(x1 + gap, y2 - gap); }
          ctx.stroke();
        }
      }
    }

    drawMarker(pos, color, letter, maze) {
      const ctx = this.ctx;
      const [x1, y1, x2, y2] = this.cellBox(pos[0], pos[1], maze);
      const cs = this.cellSize;
      const cx = (x1 + x2) / 2, cy = (y1 + y2) / 2;
      const r = (cs / 2) - Math.max(3, cs * 0.16);
      ctx.save();
      ctx.shadowColor = color;
      ctx.shadowBlur = cs * 0.45;
      ctx.fillStyle = color;
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fill();
      ctx.restore();
      if (cs >= 16) {
        ctx.fillStyle = "oklch(0.16 0.01 285)";
        ctx.font = `700 ${Math.max(9, Math.floor(cs * 0.42))}px Space Grotesk, sans-serif`;
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        ctx.fillText(letter, cx, cy + 0.5);
      }
    }

    drawRunner(pos, dir, maze) {
      const ctx = this.ctx;
      const [x1, y1, x2, y2] = this.cellBox(pos[0], pos[1], maze);
      const cs = this.cellSize;
      const cx = (x1 + x2) / 2, cy = (y1 + y2) / 2;
      const r = (cs / 2) - Math.max(4, cs * 0.24);
      ctx.save();
      ctx.shadowColor = this.col.accent;
      ctx.shadowBlur = cs * 0.6;
      ctx.fillStyle = this.col.accent;
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fill();
      ctx.restore();
      const L = cs * 0.26;
      const v = { N: [0, -L], E: [L, 0], S: [0, L], W: [-L, 0] }[dir] || [0, -L];
      ctx.strokeStyle = "white";
      ctx.lineWidth = Math.max(2, cs / 10);
      ctx.lineCap = "round";
      ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + v[0], cy + v[1]); ctx.stroke();
    }

    drawNoPath(result) {
      const ctx = this.ctx;
      const explored = result ? result.exploredCount : 0;
      const algo = result ? result.algorithm : "Search";
      const bw = Math.min(440, Math.max(300, this.cw - 60));
      const bh = 96;
      const cx = this.cw / 2, cy = this.ch / 2;
      const x1 = cx - bw / 2, y1 = cy - bh / 2;
      ctx.save();
      ctx.shadowColor = "oklch(0 0 0 / 0.5)";
      ctx.shadowBlur = 40; ctx.shadowOffsetY = 14;
      this.roundRect(x1, y1, bw, bh, 16);
      ctx.fillStyle = "oklch(0.24 0.05 22)";
      ctx.fill();
      ctx.restore();
      this.roundRect(x1, y1, bw, bh, 16);
      ctx.strokeStyle = this.col.goal; ctx.lineWidth = 1.5; ctx.stroke();
      // accent stripe
      ctx.save();
      this.roundRect(x1, y1, 6, bh, 3);
      ctx.fillStyle = this.col.goal; ctx.fill();
      ctx.restore();
      ctx.fillStyle = "oklch(0.92 0.06 25)";
      ctx.font = "700 17px Space Grotesk, sans-serif";
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText("⚠  No path found", cx + 4, cy - 14);
      ctx.fillStyle = "oklch(0.78 0.06 25)";
      ctx.font = "400 12px JetBrains Mono, monospace";
      ctx.fillText(`${algo} explored ${explored} cells — the goal is walled off.`, cx + 4, cy + 14);
    }

    roundRect(x, y, w, h, r) {
      const ctx = this.ctx;
      r = Math.min(r, w / 2, h / 2);
      ctx.beginPath();
      ctx.moveTo(x + r, y);
      ctx.arcTo(x + w, y, x + w, y + h, r);
      ctx.arcTo(x + w, y + h, x, y + h, r);
      ctx.arcTo(x, y + h, x, y, r);
      ctx.arcTo(x, y, x + w, y, r);
      ctx.closePath();
    }
  }

  window.MazeRenderer = Renderer;
})();
