'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { call, type Mistake, type Outline, type PuzzleDoc, type Sample } from '@/lib/puzzles';

const COLORS = { CT: '#5aa7ff', T: '#f0a93b' } as const;

function sampleAt(track: Sample[], t: number): Sample | null {
  if (!track.length) return null;
  if (t <= track[0].t) return track[0];
  for (let i = 1; i < track.length; i++) {
    if (track[i].t >= t) {
      const a = track[i - 1];
      const b = track[i];
      const f = b.t > a.t ? (t - a.t) / (b.t - a.t) : 0;
      return { ...b, x: a.x + (b.x - a.x) * f, y: a.y + (b.y - a.y) * f, hp: a.hp };
    }
  }
  return track[track.length - 1];
}

/** Top-down replay of a saved moment: every player's path, the hero ringed, deaths crossed, mistakes marked. */
export default function MapReplay({ puzzle, mistakes = [] }: { puzzle: PuzzleDoc; mistakes?: Mistake[] }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [outline, setOutline] = useState<Outline | null>(null);
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(false);
  const length = Math.max(1, ...puzzle.players.map((p) => p.track[p.track.length - 1]?.t ?? 0));

  useEffect(() => {
    call<Outline>('/replay/outline').then(setOutline).catch(() => setOutline(null));
  }, []);

  useEffect(() => {
    if (!playing) return;
    let last = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const dt = (now - last) / 1000;
      last = now;
      setT((cur) => {
        const next = cur + dt;
        if (next >= length) {
          setPlaying(false);
          return length;
        }
        return next;
      });
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing, length]);

  // View box: every sample of every player, with padding.
  const view = useMemo(() => {
    const pts = puzzle.players.flatMap((p) => p.track.map((s) => [s.x, s.y] as const));
    const xs = pts.map((p) => p[0]);
    const ys = pts.map((p) => p[1]);
    const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
    const span = Math.max(x1 - x0, y1 - y0, 400) + 360;
    return { x: (x0 + x1) / 2 - span / 2, y: (y0 + y1) / 2 - span / 2, span };
  }, [puzzle]);

  useEffect(() => {
    const el = canvas.current;
    if (!el) return;
    const dpr = window.devicePixelRatio || 1;
    const w = Math.round(el.clientWidth * dpr);
    if (el.width !== w) {
      el.width = w;
      el.height = w;
    }
    const ctx = el.getContext('2d');
    if (!ctx) return;
    const s = w / 700;
    const px = (x: number, y: number): [number, number] => [((x - view.x) / view.span) * w, w - ((y - view.y) / view.span) * w];
    ctx.clearRect(0, 0, w, w);

    if (outline) {
      ctx.fillStyle = '#1a1a1f';
      const c = (outline.cell / view.span) * w;
      for (const [cx, cy] of outline.cells) {
        const [x, y] = px(cx * outline.cell, (cy + 1) * outline.cell);
        if (x > -c && y > -c && x < w && y < w) ctx.fillRect(x, y, c + 0.6, c + 0.6);
      }
    }

    for (const p of puzzle.players) {
      const color = COLORS[p.side];
      const done = p.track.filter((q) => q.t <= t);
      const here = sampleAt(p.track, t);
      if (!here) continue;
      ctx.lineCap = ctx.lineJoin = 'round';
      ctx.strokeStyle = color;
      ctx.globalAlpha = p.hero ? 0.9 : 0.45;
      ctx.lineWidth = (p.hero ? 4 : 2.5) * s;
      ctx.beginPath();
      [...done, here].forEach((q, i) => {
        const [x, y] = px(q.x, q.y);
        if (i) ctx.lineTo(x, y);
        else ctx.moveTo(x, y);
      });
      ctx.stroke();

      const [x, y] = px(here.x, here.y);
      const dead = here.hp <= 0;
      ctx.globalAlpha = dead ? 0.8 : 1;
      if (dead) {
        ctx.lineWidth = 3 * s;
        ctx.beginPath();
        ctx.moveTo(x - 7 * s, y - 7 * s);
        ctx.lineTo(x + 7 * s, y + 7 * s);
        ctx.moveTo(x + 7 * s, y - 7 * s);
        ctx.lineTo(x - 7 * s, y + 7 * s);
        ctx.stroke();
      } else {
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(x, y, (p.hero ? 9 : 6.5) * s, 0, Math.PI * 2);
        ctx.fill();
        if (p.hero) {
          ctx.strokeStyle = '#ffffff';
          ctx.lineWidth = 2 * s;
          ctx.stroke();
        }
        if (here.fire) {
          ctx.strokeStyle = '#ffffff';
          ctx.lineWidth = 1.5 * s;
          ctx.beginPath();
          ctx.arc(x, y, 14 * s, 0, Math.PI * 2);
          ctx.stroke();
        }
      }
      ctx.globalAlpha = 1;
      ctx.fillStyle = '#e8e8ec';
      ctx.font = `600 ${Math.round(13 * s)}px system-ui, sans-serif`;
      ctx.fillText(p.name, x + 11 * s, y - 9 * s);
    }
  }, [puzzle, outline, t, view]);

  const kills = puzzle.events.filter((e) => e.type === 'kill' && e.t <= t);

  return (
    <div>
      <canvas
        ref={canvas}
        role="img"
        aria-label={`Top-down replay of ${puzzle.title} at ${t.toFixed(1)} seconds`}
        className="block aspect-square w-full rounded-[12px] border border-white/[0.16] bg-[#0b0b0d]"
      />
      <div className="mt-[14px] flex items-center gap-[14px]">
        <button
          type="button"
          onClick={() => {
            if (t >= length) setT(0);
            setPlaying((p) => !p);
          }}
          className="flex h-[40px] min-w-[96px] cursor-pointer items-center justify-center rounded-full bg-[#F5F4F0] px-[18px] text-[15px] font-bold text-[#111111]"
        >
          {playing ? 'Pause' : t >= length ? 'Replay' : 'Play'}
        </button>
        <div className="relative flex-1">
          <input
            type="range"
            min={0}
            max={1000}
            value={Math.round((t / length) * 1000)}
            aria-label="Replay time"
            aria-valuetext={`${t.toFixed(1)} of ${length.toFixed(0)} seconds`}
            onChange={(e) => {
              setPlaying(false);
              setT((Number(e.target.value) / 1000) * length);
            }}
            className="w-full accent-[#E4002B]"
          />
          {mistakes.map((m) => (
            <span
              key={m.id}
              title={m.title}
              aria-hidden
              className="pointer-events-none absolute top-[-6px] h-[8px] w-[8px] -translate-x-1/2 rounded-full bg-[#E4002B]"
              style={{ left: `${Math.min(100, (m.t / length) * 100)}%` }}
            />
          ))}
        </div>
        <span className="min-w-[78px] text-right font-mono text-[13px] text-[#B8B8C2]">
          {t.toFixed(1)} / {length.toFixed(0)} s
        </span>
      </div>
      <ul className="mt-[10px] min-h-[22px] font-mono text-[12.5px] text-[#B8B8C2]" aria-live="off">
        {kills.slice(-3).map((e, i) => (
          <li key={`${e.t}-${i}`}>
            {e.t.toFixed(1)} s · {e.attacker} killed {e.victim}
            {e.weapon ? ` (${e.weapon})` : ''}
          </li>
        ))}
      </ul>
    </div>
  );
}
