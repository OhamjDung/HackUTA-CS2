'use client';

import { useEffect, useRef } from 'react';
import { stageInput } from '@/lib/stageInput';

/**
 * Colour-reactive stage behind the WebGPU canvas (pure DOM/CSS + one 2D canvas).
 *
 * Reads `--rim` / `--accent` (registered, animatable colours set on the page
 * root per character) and `--anchor-x` (the character's measured position), so
 * a swap washes the whole room in the new character's colours.
 *
 * Layers, back to front: tinted base, hero glow, drifting accent auroras,
 * soft overhead light beam, rising embers, vignette, grain.
 */
export default function StageBackdrop() {
  return (
    <div className="stage-backdrop" aria-hidden>
      <div className="sb-base" />
      <div className="sb-aurora sb-aurora-a" />
      <div className="sb-aurora sb-aurora-b" />
      <div className="sb-glow" />
      <div className="sb-beam" />
      <Embers />
      <div className="sb-vignette" />
      <div className="sb-grain" />
    </div>
  );
}

interface Ember {
  x: number;
  y: number;
  r: number;
  vy: number;
  vx: number;
  life: number;
  max: number;
  hueMix: number;
  twinkle: number;
}

/** Rising light motes around the character, tinted with the live rim/accent colours. */
function Embers() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let w = 0;
    let h = 0;
    let dpr = 1;
    let raf = 0;
    let visible = true;
    const motes: Ember[] = [];
    const COUNT = reduced ? 14 : 44;

    const resize = () => {
      dpr = Math.min(2, window.devicePixelRatio || 1);
      w = canvas.clientWidth;
      h = canvas.clientHeight;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
    };
    const spawn = (m?: Ember, initial = false): Ember => {
      const cx = stageInput.anchorX * w;
      const spread = Math.min(w * 0.32, 520);
      const e = m ?? ({} as Ember);
      e.x = cx + (Math.random() - 0.5) * 2 * spread * Math.pow(Math.random(), 0.6);
      e.y = initial ? Math.random() * h : h * (0.75 + Math.random() * 0.3);
      e.r = 0.6 + Math.random() * 2.2;
      e.vy = -(12 + Math.random() * 38);
      e.vx = (Math.random() - 0.5) * 10;
      e.max = 4 + Math.random() * 6;
      e.life = initial ? Math.random() * e.max : 0;
      e.hueMix = Math.random();
      e.twinkle = Math.random() * Math.PI * 2;
      return e;
    };

    resize();
    for (let i = 0; i < COUNT; i++) motes.push(spawn(undefined, true));

    let rim = '#f59e0b';
    let accent = '#38bdf8';
    let colourCheck = 0;

    let last = performance.now();
    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      if (!visible) return;
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      if (now - colourCheck > 120) {
        // The registered custom properties interpolate during a swap; sample them.
        const host = canvas.parentElement ?? document.documentElement;
        const cs = getComputedStyle(host);
        rim = cs.getPropertyValue('--rim').trim() || rim;
        accent = cs.getPropertyValue('--accent').trim() || accent;
        colourCheck = now;
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      ctx.globalCompositeOperation = 'lighter';
      for (const m of motes) {
        m.life += dt;
        m.y += m.vy * dt;
        m.x += (m.vx + Math.sin(m.life * 1.3 + m.twinkle) * 8) * dt;
        if (m.life > m.max || m.y < -10) spawn(m);
        const fade = Math.sin(Math.PI * Math.min(1, m.life / m.max));
        const tw = 0.6 + 0.4 * Math.sin(now / 280 + m.twinkle);
        const a = fade * tw * 0.85;
        const col = m.hueMix < 0.6 ? rim : accent;
        const g = ctx.createRadialGradient(m.x, m.y, 0, m.x, m.y, m.r * 5);
        g.addColorStop(0, col);
        g.addColorStop(1, 'transparent');
        ctx.globalAlpha = a * 0.5;
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(m.x, m.y, m.r * 5, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = a;
        ctx.fillStyle = '#fff';
        ctx.beginPath();
        ctx.arc(m.x, m.y, m.r * 0.55, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    };
    raf = requestAnimationFrame(frame);

    const ro = new ResizeObserver(resize);
    ro.observe(canvas);
    const onVis = () => {
      visible = document.visibilityState === 'visible';
      last = performance.now();
    };
    document.addEventListener('visibilitychange', onVis);
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      document.removeEventListener('visibilitychange', onVis);
    };
  }, []);

  return <canvas ref={ref} className="sb-embers" />;
}
