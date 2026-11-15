'use client';

import { useEffect, useRef } from 'react';

/**
 * Home-page DoppelGamer sign, drawn as a 14-segment LED panel in SVG.
 *
 * The glyphs are drawn here rather than taken from the LED font so two letters
 * can be shaped for the sign: the D fills the whole cell (as wide as an O) with
 * cut right-hand corners so it never reads as an O, and the R has a closed
 * bowl with a diagonal leg. The sign is one word on one line.
 *
 * - Ghost layer: every segment of every cell drawn faintly (unlit segments).
 * - Lit layer: white core; the glow comes from CSS in the live character
 *   colours (`--rim` / `--accent`).
 * - Slight cursor parallax (a few px), off under prefers-reduced-motion.
 */

// Cell geometry (viewBox units).
const W = 100;
const H = 172;
const T = 17; // segment thickness
const GAP = 4.5; // gap at segment joints
const CELL_GAP = 26;
const LINE_GAP = 40;
const PAD = T;

type Pt = [number, number];
type Seg = [Pt, Pt];

const TL: Pt = [0, 0];
const TC: Pt = [W / 2, 0];
const TR: Pt = [W, 0];
const ML: Pt = [0, H / 2];
const MC: Pt = [W / 2, H / 2];
const MR: Pt = [W, H / 2];
const BL: Pt = [0, H];
const BC: Pt = [W / 2, H];
const BR: Pt = [W, H];

const SEGMENTS: Record<string, Seg> = {
  a: [TL, TR],
  b: [TR, MR],
  c: [MR, BR],
  d: [BL, BR],
  e: [ML, BL],
  f: [TL, ML],
  g1: [ML, MC],
  g2: [MC, MR],
  h: [TL, MC],
  i: [TC, MC],
  j: [TR, MC],
  k: [BL, MC],
  l: [MC, BC],
  m: [MC, BR],
};
const DIAGONAL = new Set(['h', 'j', 'k', 'm']);

// D: full-width like an O, with chamfered right corners so it stays a D.
const CH_X = W * 0.64;
const CH_Y = H * 0.2;
const D_SEGS: Seg[] = [
  [TL, [CH_X, 0]],
  [[CH_X, 0], [W, CH_Y]],
  [[W, CH_Y], [W, H - CH_Y]],
  [[W, H - CH_Y], [CH_X, H]],
  [[CH_X, H], BL],
  SEGMENTS.f,
  SEGMENTS.e,
];

const GLYPHS: Record<string, string[]> = {
  O: ['a', 'b', 'c', 'd', 'e', 'f'],
  P: ['a', 'b', 'e', 'f', 'g1', 'g2'],
  E: ['a', 'd', 'e', 'f', 'g1'],
  L: ['d', 'e', 'f'],
  G: ['a', 'c', 'd', 'e', 'f', 'g2'],
  A: ['a', 'b', 'c', 'e', 'f', 'g1', 'g2'],
  M: ['b', 'c', 'e', 'f', 'h', 'j'],
  R: ['a', 'b', 'e', 'f', 'g1', 'g2', 'm'],
};

/** Hexagonal LED segment (pointed ends) between two points. */
function segPoints([p1, p2]: Seg, shrink: number, dx: number, dy: number): string {
  const vx = p2[0] - p1[0];
  const vy = p2[1] - p1[1];
  const len = Math.hypot(vx, vy);
  const ux = vx / len;
  const uy = vy / len;
  const nx = -uy;
  const ny = ux;
  const h = T / 2;
  const ax = p1[0] + ux * shrink + dx;
  const ay = p1[1] + uy * shrink + dy;
  const bx = p2[0] - ux * shrink + dx;
  const by = p2[1] - uy * shrink + dy;
  const pts: Pt[] = [
    [ax, ay],
    [ax + ux * h + nx * h, ay + uy * h + ny * h],
    [bx - ux * h + nx * h, by - uy * h + ny * h],
    [bx, by],
    [bx - ux * h - nx * h, by - uy * h - ny * h],
    [ax + ux * h - nx * h, ay + uy * h - ny * h],
  ];
  return pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
}

const shrinkFor = (name: string) => (DIAGONAL.has(name) ? T * 0.95 + GAP : GAP);

function cellSegments(ch: string, dx: number, dy: number, ghost: boolean): string[] {
  if (ghost) return Object.entries(SEGMENTS).map(([n, s]) => segPoints(s, shrinkFor(n), dx, dy));
  if (ch === 'D') return D_SEGS.map((s) => segPoints(s, GAP, dx, dy));
  return (GLYPHS[ch] ?? []).map((n) => segPoints(SEGMENTS[n], shrinkFor(n), dx, dy));
}

const LINES = ['DOPPELGAMER'];
const lineWidth = (n: number) => n * W + (n - 1) * CELL_GAP;
const VB_W = lineWidth(Math.max(...LINES.map((l) => l.length))) + PAD * 2;
const VB_H = LINES.length * H + (LINES.length - 1) * LINE_GAP + PAD * 2;

function layer(ghost: boolean): string[] {
  const out: string[] = [];
  LINES.forEach((line, row) => {
    const x0 = PAD + (VB_W - PAD * 2 - lineWidth(line.length)) / 2; // centre each line
    const y0 = PAD + row * (H + LINE_GAP);
    [...line].forEach((ch, col) => out.push(...cellSegments(ch, x0 + col * (W + CELL_GAP), y0, ghost)));
  });
  return out;
}

const GHOST = layer(true);
const LIT = layer(false);

export default function HeroSign({ className = '' }: { className?: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const target = { x: 0, y: 0 };
    const cur = { x: 0, y: 0 };
    let raf = 0;
    const tick = () => {
      cur.x += (target.x - cur.x) * 0.06;
      cur.y += (target.y - cur.y) * 0.06;
      el.style.setProperty('--sign-x', `${cur.x.toFixed(2)}px`);
      el.style.setProperty('--sign-y', `${cur.y.toFixed(2)}px`);
      if (Math.abs(target.x - cur.x) > 0.05 || Math.abs(target.y - cur.y) > 0.05) raf = requestAnimationFrame(tick);
      else raf = 0;
    };
    const onMove = (e: PointerEvent) => {
      target.x = ((e.clientX / window.innerWidth) * 2 - 1) * 8;
      target.y = ((e.clientY / window.innerHeight) * 2 - 1) * 5;
      if (!raf) raf = requestAnimationFrame(tick);
    };
    window.addEventListener('pointermove', onMove, { passive: true });
    return () => {
      window.removeEventListener('pointermove', onMove);
      cancelAnimationFrame(raf);
    };
  }, []);

  const viewBox = `0 0 ${VB_W} ${VB_H}`;
  return (
    <div ref={ref} className={`hero-sign ${className}`} role="img" aria-label="DoppelGamer">
      <span className="hero-sign-spill" aria-hidden />
      <svg className="hero-sign-ghost" viewBox={viewBox} aria-hidden>
        {GHOST.map((p, i) => (
          <polygon key={i} points={p} />
        ))}
      </svg>
      <svg className="hero-sign-lit" viewBox={viewBox} aria-hidden>
        {LIT.map((p, i) => (
          <polygon key={i} points={p} />
        ))}
      </svg>
    </div>
  );
}
