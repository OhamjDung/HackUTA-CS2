'use client';

/* eslint-disable @next/next/no-img-element -- optional local avatar files */
import { useEffect, useRef, useState } from 'react';
import type { Bot } from '@/lib/bots';

interface RosterArcProps {
  bots: Bot[];
  selectedId: string;
  onSelect: (id: string) => void;
}

/** Arc geometry (px). Items sit on a large circle whose centre is far to the right. */
const R = 860;
const SPACING = 121;
const VISIBLE = 3;
const STEP_PX = 56; // wheel / drag distance per step

/**
 * Scroll-arc selector. Bots ride a gentle arc; the wheel, a vertical drag or the
 * arrow keys step the selection one bot at a time (snapping, never free-floating).
 * When the roster outgrows the 3-slot window, the window scrolls along the arc
 * to keep the selection in view.
 */
export default function RosterArc({ bots, selectedId, onSelect }: RosterArcProps) {
  const listRef = useRef<HTMLDivElement>(null);
  const acc = useRef(0);
  const drag = useRef<{ y: number; moved: boolean } | null>(null);
  const selIdx = Math.max(0, bots.findIndex((b) => b.id === selectedId));
  const winStart = Math.min(Math.max(0, selIdx - (VISIBLE - 1)), Math.max(0, bots.length - VISIBLE));
  const start = Math.max(0, Math.min(winStart, selIdx));

  const step = (dir: 1 | -1) => {
    const next = Math.min(bots.length - 1, Math.max(0, selIdx + dir));
    if (next !== selIdx) onSelect(bots[next].id);
  };
  const stepRef = useRef(step);
  stepRef.current = step;

  // Wheel needs a non-passive listener to keep the page from scrolling while stepping.
  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      acc.current += e.deltaY;
      if (Math.abs(acc.current) >= STEP_PX) {
        stepRef.current(acc.current > 0 ? 1 : -1);
        acc.current = 0;
      }
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, []);

  const angle = (slot: number) => ((slot - (VISIBLE - 1) / 2) * SPACING) / R;
  const pos = (slot: number) => {
    const a = angle(slot);
    return { x: R * (1 - Math.cos(a)), y: R * Math.sin(a) + ((VISIBLE - 1) / 2) * SPACING };
  };

  // Arc guide spanning the visible slots.
  const a0 = angle(0);
  const a1 = angle(VISIBLE - 1);
  const p0 = pos(0);
  const p1 = pos(VISIBLE - 1);

  return (
    <div
      ref={listRef}
      role="listbox"
      aria-label="Bot roster"
      aria-activedescendant={`bot-${selectedId}`}
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
          e.preventDefault();
          step(1);
        } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
          e.preventDefault();
          step(-1);
        } else if (e.key === 'Home') onSelect(bots[0].id);
        else if (e.key === 'End') onSelect(bots[bots.length - 1].id);
      }}
      onPointerDown={(e) => {
        drag.current = { y: e.clientY, moved: false };
      }}
      onPointerMove={(e) => {
        const d = drag.current;
        if (!d || e.buttons !== 1) return;
        const dy = d.y - e.clientY;
        if (Math.abs(dy) >= STEP_PX) {
          step(dy > 0 ? 1 : -1);
          d.y = e.clientY;
          d.moved = true;
        }
      }}
      onPointerUp={() => {
        drag.current = null;
      }}
      className="relative h-[352px] w-[300px] touch-none select-none outline-none focus-visible:ring-2 focus-visible:ring-brand/40 rounded-2xl"
    >
      <svg className="pointer-events-none absolute left-[47px] top-[47px] overflow-visible" width="1" height="1" aria-hidden>
        <path
          d={`M ${p0.x} ${p0.y} A ${R} ${R} 0 0 ${a1 > a0 ? 0 : 1} ${p1.x} ${p1.y}`}
          fill="none"
          stroke="rgba(255,255,255,0.22)"
          strokeWidth="1.25"
        />
      </svg>

      {bots.map((b, i) => {
        const slot = i - start;
        const inView = slot >= 0 && slot < VISIBLE;
        const p = pos(Math.min(Math.max(slot, -0.6), VISIBLE - 0.4));
        const on = b.id === selectedId;
        // Selected: photo + 2px white inner ring + 2px dark gap + 2.5px #E4002B outer ring; inactive: photo + hairline.
        const size = on ? 104 : 86;
        return (
          <div
            key={b.id}
            id={`bot-${b.id}`}
            role="option"
            aria-selected={on}
            className="absolute left-0 top-0 flex items-center transition-[transform,opacity] duration-500 ease-[cubic-bezier(0.22,1,0.36,1)]"
            style={{
              transform: `translate(${p.x + 47 - size / 2}px, ${p.y + 47 - size / 2}px)`,
              opacity: inView ? 1 : 0,
              pointerEvents: inView ? 'auto' : 'none',
            }}
          >
            <button
              type="button"
              tabIndex={-1}
              onClick={() => {
                if (!drag.current?.moved) onSelect(b.id);
              }}
              className="group flex cursor-pointer items-center gap-[18px] text-left"
              aria-label={`${b.name}, ${b.game}`}
            >
              <span
                className="relative block shrink-0 rounded-full transition-[width,height,box-shadow] duration-500 ease-[cubic-bezier(0.22,1,0.36,1)]"
                style={{
                  width: size,
                  height: size,
                  padding: on ? 6.5 : 0,
                }}
              >
                <span
                  className="block h-full w-full overflow-hidden rounded-full transition-shadow duration-500"
                  style={{
                    boxShadow: on
                      ? '0 0 0 2px rgba(255,255,255,0.9), 0 0 0 4px #0f0f12, 0 0 0 6.5px #E4002B'
                      : '0 0 0 1.5px rgba(255,255,255,0.18)',
                  }}
                >
                  <Avatar url={b.avatarUrl} name={b.name} />
                </span>
              </span>
              <span className="flex flex-col">
                <span className="text-[21.5px] font-bold leading-none tracking-[-0.03em] text-white">
                  {b.name}
                </span>
                <span
                  className="overflow-hidden text-[14.5px] leading-none text-ink-subtle transition-[max-height,opacity,margin] duration-500"
                  style={{ maxHeight: on ? 20 : 0, opacity: on ? 1 : 0, marginTop: on ? 7 : 0 }}
                >
                  {b.game}
                </span>
              </span>
            </button>
          </div>
        );
      })}
    </div>
  );
}

/** Portrait photo (object-cover); a neutral silhouette until the file exists. */
/**
 * Real portrait. If the image fails to load we fall back to a lettered monogram
 * (never a generic silhouette).
 */
export function Avatar({ url, name }: { url?: string; name?: string }) {
  const [failed, setFailed] = useState(false);
  if (url && !failed) {
    return <img src={url} alt="" onError={() => setFailed(true)} className="h-full w-full rounded-full object-cover" />;
  }
  return (
    <span className="flex h-full w-full items-center justify-center rounded-full bg-[#1d1d22] text-[0.9em] font-extrabold uppercase tracking-[-0.02em] text-white/85">
      {(name ?? '?').slice(0, 2)}
    </span>
  );
}
