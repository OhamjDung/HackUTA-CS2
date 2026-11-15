// Shared code for the demo pages: API calls, the page header, and the 2D map ("radar") drawing.

const API = "";  // same origin: the match service serves these pages at /demo/

async function api(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" }, ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const detail = data && data.detail;
    throw new Error(Array.isArray(detail) ? detail.map(d => d.msg || d).join("\n") : (detail || res.statusText));
  }
  return data;
}

const PAGES = [
  ["index.html", "Demo"],
  ["play.html", "Play vs a bot"],
  ["watch.html", "Bot vs bot"],
  ["replay.html", "Replay"],
  ["proof.html", "Proof"],
];

function header() {
  const here = location.pathname.split("/").pop() || "index.html";
  const el = document.createElement("header");
  el.className = "top";
  el.innerHTML = `<span class="brand">CS2 Clones · demo</span>
    <nav>${PAGES.map(([href, name]) => `<a href="${href}" class="${href === here ? "on" : ""}">${name}</a>`).join("")}</nav>
    <div id="status"><span class="pill">checking service…</span></div>`;
  document.body.prepend(el);
  refreshStatus();
}

let HEALTH = null;
async function refreshStatus() {
  const box = document.getElementById("status");
  try {
    HEALTH = await api("/health");
    const pills = [];
    if (HEALTH.backend === "mock") {
      pills.push(`<span class="pill warn" title="No game: matches are simulated, using real recorded routes">simulated (mock)</span>`);
    } else {
      const c = HEALTH.console || {};
      pills.push(`<span class="pill ${c.reachable ? "good" : "bad"}">CS2 console ${c.reachable ? "connected" : "unreachable"}</span>`);
      pills.push(`<span class="pill ${HEALTH.gsi && HEALTH.gsi.last_update ? "good" : "warn"}">game state ${HEALTH.gsi && HEALTH.gsi.last_update ? "arriving" : "not yet"}</span>`);
      pills.push(HEALTH.bots === "clone"
        ? `<span class="pill good">clones: CloneDirector</span>`
        : `<span class="pill warn" title="Built-in CS2-Bot-Improver bots named donk and broky. Swap to Arjun's clones with CS2_BOTS=clone.">clones: stand-in bots</span>`);
    }
    if (box) box.innerHTML = pills.join("");
  } catch (e) {
    HEALTH = null;
    if (box) box.innerHTML = `<span class="pill bad">match service unreachable</span>`;
  }
  return HEALTH;
}

const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const sleep = ms => new Promise(r => setTimeout(r, ms));
const param = name => new URLSearchParams(location.search).get(name);

// --- The map ------------------------------------------------------------------------------------

let OUTLINE = null;
async function outline() {
  if (!OUTLINE) OUTLINE = await api("/replay/outline").catch(() => ({ cell: 64, cells: [] }));
  return OUTLINE;
}

const COLORS = { CT: "#5aa7ff", T: "#f0a93b" };

// Position at time t along a path of [t, x, y] points.
function at(path, t) {
  if (!path.length) return null;
  if (t <= path[0][0]) return path[0];
  for (let i = 1; i < path.length; i++) {
    if (path[i][0] >= t) {
      const [t0, x0, y0] = path[i - 1], [t1, x1, y1] = path[i];
      const f = t1 > t0 ? (t - t0) / (t1 - t0) : 0;
      return [t, x0 + (x1 - x0) * f, y0 + (y1 - y0) * f];
    }
  }
  return path[path.length - 1];
}

class Radar {
  constructor(canvas, outlineData) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.outline = outlineData;
    const c = outlineData.cell, cells = outlineData.cells;
    let [x0, x1, y0, y1] = [-2600, 1600, -2800, 1000];  // Mirage, if there is no outline
    if (cells.length) {
      x0 = Math.min(...cells.map(p => p[0])) * c; x1 = (Math.max(...cells.map(p => p[0])) + 1) * c;
      y0 = Math.min(...cells.map(p => p[1])) * c; y1 = (Math.max(...cells.map(p => p[1])) + 1) * c;
    }
    const pad = 180, span = Math.max(x1 - x0, y1 - y0) + pad * 2;
    this.view = { x: (x0 + x1) / 2 - span / 2, y: (y0 + y1) / 2 - span / 2, span };
  }

  px(x, y) {
    const { width } = this.canvas, v = this.view;
    return [(x - v.x) / v.span * width, width - (y - v.y) / v.span * width];  // world y points up
  }

  resize() {
    const dpr = window.devicePixelRatio || 1, w = Math.round(this.canvas.clientWidth * dpr);
    if (this.canvas.width !== w) { this.canvas.width = w; this.canvas.height = w; }
  }

  // paths: [{name, team, path, focus, diedAt, dash, color}]; t: seconds into the round.
  // `color` overrides the team color (the replay page's generated paths use it).
  draw(paths, t = Infinity) {
    this.resize();
    const ctx = this.ctx, W = this.canvas.width, s = W / 900;
    ctx.clearRect(0, 0, W, W);

    // Map shape: everywhere a recorded route went.
    const c = this.outline.cell, cellPx = c / this.view.span * W;
    ctx.fillStyle = "#1a212b";
    for (const [cx, cy] of this.outline.cells) {
      const [x, y] = this.px(cx * c, (cy + 1) * c);
      ctx.fillRect(x, y, cellPx + 0.6, cellPx + 0.6);
    }

    const anyFocus = paths.some(p => p.focus);
    for (const p of paths) {
      if (!p.path || !p.path.length) continue;
      const color = p.color || COLORS[p.team] || "#c792ea";
      const dim = anyFocus && !p.focus;
      ctx.lineCap = ctx.lineJoin = "round";

      // The whole path, faint.
      ctx.globalAlpha = dim ? 0.12 : 0.25;
      ctx.strokeStyle = color; ctx.lineWidth = 2 * s;
      ctx.setLineDash(p.dash ? [6 * s, 6 * s] : []);
      this.line(p.path);

      // The part travelled by time t.
      const done = p.path.filter(pt => pt[0] <= t);
      const here = at(p.path, t);
      if (here && t !== Infinity) done.push(here);
      ctx.globalAlpha = dim ? 0.3 : 1;
      ctx.lineWidth = (p.focus ? 4 : 3) * s;
      this.line(done);
      ctx.setLineDash([]);

      // Where the player is now.
      const end = t === Infinity ? p.path[p.path.length - 1] : here;
      const [x, y] = this.px(end[1], end[2]);
      const dead = p.diedAt != null && t >= p.diedAt;
      ctx.globalAlpha = dim ? 0.45 : 1;
      if (dead) {
        ctx.strokeStyle = color; ctx.lineWidth = 3 * s;
        ctx.beginPath(); ctx.moveTo(x - 7 * s, y - 7 * s); ctx.lineTo(x + 7 * s, y + 7 * s);
        ctx.moveTo(x + 7 * s, y - 7 * s); ctx.lineTo(x - 7 * s, y + 7 * s); ctx.stroke();
      } else {
        ctx.fillStyle = color;
        ctx.beginPath(); ctx.arc(x, y, (p.focus ? 9 : 7) * s, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = "#0b0e13"; ctx.lineWidth = 2 * s; ctx.stroke();
      }
      ctx.font = `${600} ${Math.round(15 * s)}px system-ui, sans-serif`;
      ctx.fillStyle = "#e6e9ee";
      ctx.fillText(p.name, x + 12 * s, y - 10 * s);
    }
    ctx.globalAlpha = 1;
  }

  line(points) {
    if (points.length < 2) return;
    const ctx = this.ctx;
    ctx.beginPath();
    points.forEach((pt, i) => { const [x, y] = this.px(pt[1], pt[2]); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
    ctx.stroke();
  }
}

// A play/pause + scrubber that drives one or more radars on the same clock.
class Player {
  constructor(root, onTime) {
    this.onTime = onTime; this.t = 0; this.max = 20; this.speed = 1; this.playing = false;
    root.innerHTML = `<div class="row">
        <button data-play>▶ Play</button>
        <select data-speed aria-label="Playback speed"><option value="1">1×</option><option value="2" selected>2×</option><option value="4">4×</option></select>
        <input type="range" data-scrub min="0" max="1000" value="0" aria-label="Replay time" style="flex:1;min-width:120px">
        <span class="muted small" data-clock aria-live="off" style="min-width:90px;text-align:right">0.0 s</span>
      </div>`;
    this.btn = root.querySelector("[data-play]");
    this.scrub = root.querySelector("[data-scrub]");
    this.clock = root.querySelector("[data-clock]");
    this.speed = 2;
    root.querySelector("[data-speed]").onchange = e => { this.speed = +e.target.value; };
    this.btn.onclick = () => this.toggle();
    this.scrub.oninput = () => { this.set(this.scrub.value / 1000 * this.max); };
    this.loop = this.loop.bind(this);
  }
  setMax(max) { this.max = Math.max(1, max); this.set(Math.min(this.t, this.max)); }
  set(t) {
    this.t = t;
    this.scrub.value = Math.round(t / this.max * 1000);
    this.clock.textContent = `${t.toFixed(1)} / ${this.max.toFixed(0)} s`;
    this.scrub.setAttribute("aria-valuetext", `${t.toFixed(1)} of ${this.max.toFixed(0)} seconds`);
    this.onTime(t);
  }
  toggle() {
    this.playing = !this.playing;
    this.btn.textContent = this.playing ? "❚❚ Pause" : "▶ Play";
    if (this.playing) {
      if (this.t >= this.max) this.set(0);
      this.last = performance.now(); requestAnimationFrame(this.loop);
    }
  }
  loop(now) {
    if (!this.playing) return;
    const dt = (now - this.last) / 1000; this.last = now;
    const t = this.t + dt * this.speed;
    if (t >= this.max) { this.set(this.max); this.toggle(); return; }
    this.set(t);
    requestAnimationFrame(this.loop);
  }
}

function pathEnd(p) { return p.path && p.path.length ? p.path[p.path.length - 1][0] : 0; }

document.addEventListener("DOMContentLoaded", header);
