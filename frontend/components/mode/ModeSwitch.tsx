'use client';

import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { modeHref, validModeParams, type AppMode } from '@/lib/mode/contract';
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

export default function ModeSwitch({ compact = false }: { compact?: boolean }) {
  const { mode, setTransitioning } = useAppMode();
  const pathname = usePathname() ?? '/';
  const searchParams = useSearchParams();
  const router = useRouter();
  const [preferred, setPreferred] = useState<AppMode>(mode);

  useEffect(() => {
    try {
      const saved = sessionStorage.getItem('doppelgamer.preferredMode');
      if (saved === 'faze' || saved === 'odyssey') setPreferred(saved);
    } catch {
      // URL/default remains authoritative when storage is unavailable.
    }
  }, []);

  const switchTo = (target: AppMode) => {
    if (target === mode) return;
    const memory = readMemory();
    memory[mode][pathname] = validModeParams(mode, pathname, searchParams).toString();
    let targetParams = new URLSearchParams(memory[target][pathname] ?? '');
    targetParams.set('mode', target);
    const href = modeHref(pathname, target, targetParams);
    try {
      sessionStorage.setItem(MEMORY_KEY, JSON.stringify(memory));
      sessionStorage.setItem('doppelgamer.preferredMode', target);
    } catch {
      // Navigation remains deterministic without persistence.
    }
    setPreferred(target);
    setTransitioning(true);
    window.setTimeout(() => router.push(href, { scroll: false }), 90);
  };

  return (
    <fieldset className={compact ? 'mode-switch mode-switch--compact' : 'mode-switch'} aria-label="Experience mode">
      <legend className="sr-only">Experience mode</legend>
      {(['faze', 'odyssey'] as const).map((item) => (
        <button
          key={item}
          type="button"
          aria-pressed={mode === item}
          data-preferred={preferred === item || undefined}
          onClick={() => switchTo(item)}
        >
          {item === 'faze' ? 'FaZe' : 'Odyssey'}
        </button>
      ))}
    </fieldset>
  );
}

