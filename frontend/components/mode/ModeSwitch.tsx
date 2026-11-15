'use client';

import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useRef } from 'react';
import { modeHref, validModeParams, type AppMode } from '@/lib/mode/contract';
import { useBrand } from '@/app/providers';
import { useAppMode } from './ModeRoute';

const MEMORY_KEY = 'doppelgamer.modeRouteMemory.v1';

type Memory = Record<AppMode, Record<string, string>>;
const EMPTY: Memory = { faze: {}, odyssey: {} };

function readMemory(): Memory {
  try {
    return { ...EMPTY, ...JSON.parse(sessionStorage.getItem(MEMORY_KEY) ?? '{}') };
  } catch {
    return EMPTY;
  }
}

/**
 * Circular FaZe ↔ Odyssey switch. The active mode comes from the route (useAppMode),
 * so the icon always matches the page on screen. Only the active mode's icon is rendered;
 * the outgoing icon rotates and shrinks while the incoming one follows with a short delay.
 */
export default function ModeSwitch() {
  const { mode, setTransitioning } = useAppMode();
  const brand = useBrand();
  const pathname = usePathname() ?? '/';
  const searchParams = useSearchParams();
  const router = useRouter();
  // Ignores clicks that land while a switch is already navigating, so the icon can't drift.
  const pending = useRef(false);

  useEffect(() => {
    pending.current = false;
  }, [mode]);

  const isFaze = mode === 'faze';
  const target: AppMode = isFaze ? 'odyssey' : 'faze';
  const label = `Switch to ${isFaze ? 'Odyssey' : 'FaZe'} mode`;
  // Only the official one-colour SVG may be used at this size; anything else falls back to a text label.
  const officialMark = brand.fazeMarkMono?.endsWith('.svg') ? brand.fazeMarkMono : undefined;

  const switchTo = () => {
    if (pending.current) return;
    pending.current = true;
    window.setTimeout(() => {
      pending.current = false;
    }, 1200);

    const memory = readMemory();
    memory[mode][pathname] = validModeParams(mode, pathname, searchParams).toString();
    const targetParams = new URLSearchParams(memory[target][pathname] ?? '');
    targetParams.set('mode', target);
    const href = modeHref(pathname, target, targetParams);
    try {
      sessionStorage.setItem(MEMORY_KEY, JSON.stringify(memory));
      sessionStorage.setItem('doppelgamer.preferredMode', target);
    } catch {
      // Navigation remains deterministic without persistence.
    }
    setTransitioning(true);
    window.setTimeout(() => router.push(href, { scroll: false }), 90);
  };

  return (
    <button type="button" className="dg-mode-toggle" data-mode={mode} aria-label={label} title={label} onClick={switchTo}>
      <span className="dg-mode-toggle__icon dg-mode-toggle__icon--faze" data-active={isFaze} aria-hidden="true">
        {officialMark ? (
          // Official one-colour mark, uniform scale only: no outline, gradient, shadow or recolour.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={officialMark} alt="" width={40} height={40} style={{ width: 40, height: 'auto' }} draggable={false} />
        ) : (
          <span className="dg-mode-toggle__placeholder">FaZe</span>
        )}
      </span>
      <span className="dg-mode-toggle__icon dg-mode-toggle__icon--odyssey" data-active={!isFaze} aria-hidden="true">
        <svg width="40" height="40" viewBox="0 0 48 48" fill="#1F4E8C">
          {/* Horsehair crest sweeping over the dome */}
          <path d="M9 15 C13 3 31 -1 43 8 C36 6 30 5 26 8 C21 11 17 12 14 18 Z" />
          {/* Dome, flared cheek guards and visor slit */}
          <path fillRule="evenodd" d="M9 30 C9 17 15 11 24 11 C33 11 39 17 39 30 L45 40 L37 40 L33 35 L15 35 L11 40 L3 40 Z M15 22 H33 V25 H15 Z" />
        </svg>
      </span>
    </button>
  );
}
