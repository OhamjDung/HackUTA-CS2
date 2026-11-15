'use client';

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import CharacterCanvas from '@/components/canvas/CharacterCanvas';
import HeroStageOverlay from '@/components/ui/HeroStageOverlay';
import RightScaleRuler from '@/components/ui/RightScaleRuler';
import ThermalScopeReticle from '@/components/ui/ThermalScopeReticle';
import CreditsLink from '@/components/ui/CreditsLink';
import SiteNav from '@/components/ui/SiteNav';
import { preload } from 'react-dom';
import {
  AUTO_SWAP_ENABLED_DEFAULT,
  AUTO_SWAP_INTERVAL_MS,
  CHARACTERS,
  GLITCH_DURATION_MS,
  GLITCH_SWAP_AT_MS,
  CHARACTER_MAP,
  INITIAL_CHARACTER_ID,
  TRANSCODER_JS,
  TRANSCODER_WASM,
  stageXFraction,
} from '@/lib/constants';
import { stageInput } from '@/lib/stageInput';
import type { CharacterId } from '@/types';

export default function HomePage() {
  // Basis transcoder + first model binary: preloaded only on the route that renders the stage.
  preload(TRANSCODER_WASM, { as: 'fetch', crossOrigin: 'anonymous' });
  preload(TRANSCODER_JS, { as: 'fetch', crossOrigin: 'anonymous' });
  preload(CHARACTER_MAP[INITIAL_CHARACTER_ID].url, { as: 'fetch', crossOrigin: 'anonymous' });

  const [activeId, setActiveId] = useState<CharacterId>(INITIAL_CHARACTER_ID);
  const [pendingId, setPendingId] = useState<CharacterId | null>(null);
  const [autoPlay] = useState(AUTO_SWAP_ENABLED_DEFAULT);
  const [thermalActive, setThermalActive] = useState(false);
  // Bumped when a glitch completes so the 6 s hold always starts from a clean frame.
  const [cycleKey, setCycleKey] = useState(0);

  const canvasWrapRef = useRef<HTMLDivElement>(null);
  const timers = useRef<number[]>([]);
  const activeIdRef = useRef(activeId);
  activeIdRef.current = activeId;
  const pendingRef = useRef(pendingId);
  pendingRef.current = pendingId;

  useEffect(
    () => () => {
      timers.current.forEach((t) => window.clearTimeout(t));
      timers.current = [];
    },
    [],
  );

  // ---- glitch swap ----------------------------------------------------------
  const triggerSwap = useCallback((id: CharacterId) => {
    if (id === activeIdRef.current || pendingRef.current !== null) return;
    setPendingId(id);
    // The render loop reads this timestamp and drives the 0.6 s GPU envelope.
    stageInput.glitchStartedAt = performance.now();
    timers.current.push(window.setTimeout(() => setActiveId(id), GLITCH_SWAP_AT_MS));
    timers.current.push(
      window.setTimeout(() => {
        setPendingId(null);
        setCycleKey((k) => k + 1);
      }, GLITCH_DURATION_MS),
    );
  }, []);

  const goToNext = useCallback(() => {
    const order = CHARACTERS.map((c) => c.id);
    triggerSwap(order[(order.indexOf(activeIdRef.current) + 1) % order.length]);
  }, [triggerSwap]);

  // Auto-cycle: 6 s clean hold, paused while the thermal scope is open.
  useEffect(() => {
    if (!autoPlay || thermalActive) return;
    const t = window.setTimeout(goToNext, AUTO_SWAP_INTERVAL_MS);
    return () => window.clearTimeout(t);
  }, [autoPlay, thermalActive, cycleKey, goToNext]);

  // ---- thermal scope: press-and-hold ----------------------------------------
  // Holding the left mouse button opens the lens at the cursor and tracks it;
  // releasing ANYWHERE (window pointerup / pointercancel / blur) or Esc closes it
  // on the very next frame. There is no click-to-toggle state. While held, the
  // auto-cycle timer stays paused (it keys off thermalActive) and resumes on release.
  useEffect(() => {
    stageInput.scopeActive = thermalActive;
  }, [thermalActive]);

  useEffect(() => {
    const release = () => setThermalActive(false);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setThermalActive(false);
    };
    window.addEventListener('pointerup', release);
    window.addEventListener('pointercancel', release);
    window.addEventListener('blur', release);
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('pointerup', release);
      window.removeEventListener('pointercancel', release);
      window.removeEventListener('blur', release);
      window.removeEventListener('keydown', onKey);
    };
  }, []);

  const pressThermalAt = useCallback((x: number, y: number) => {
    stageInput.scopeX = x;
    stageInput.scopeY = y;
    stageInput.scopeAnchored = true;
    setThermalActive(true);
  }, []);

  const onStagePointerDown = useCallback(
    (e: React.PointerEvent<HTMLElement>) => {
      if (e.button !== 0) return;
      if ((e.target as HTMLElement).closest('a,button,[role="menu"]')) return;
      const el = canvasWrapRef.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width;
      const y = (e.clientY - r.top) / r.height;
      if (x < 0 || x > 1 || y < 0 || y > 1) return;
      pressThermalAt(x, y);
    },
    [pressThermalAt],
  );

  // ---- stage anchor: centre the character in the gap between headline and HUD
  const sectionRef = useRef<HTMLElement>(null);
  useLayoutEffect(() => {
    const section = sectionRef.current;
    const wrap = canvasWrapRef.current;
    if (!section || !wrap) return;
    const measure = () => {
      const w = wrap.clientWidth;
      if (w < 900) {
        stageInput.anchorX = 0.5;
        stageInput.anchorScale = 1;
        return;
      }
      const base = wrap.getBoundingClientRect().left;
      const h1 = section.querySelector<HTMLElement>('[data-headline]');
      const hud = section.querySelector<HTMLElement>('[data-hud]');
      if (!h1 || !hud) {
        stageInput.anchorX = stageXFraction(w);
        return;
      }
      // The absolutely positioned headline shrink-wraps its longest line.
      const left = h1.getBoundingClientRect().right - base;
      const right = hud.getBoundingClientRect().left - base;
      stageInput.anchorX = Math.min(0.68, Math.max(0.5, (left + (right - left) * 0.42) / w));
      // At the 1536×1024 reference the gap is ~0.48× the stage height; shrink below that.
      const gap = right - left;
      stageInput.anchorScale = Math.min(1, Math.max(0.72, gap / (0.48 * wrap.clientHeight)));
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(wrap);
    document.fonts?.ready.then(measure);
    return () => ro.disconnect();
  }, []);

  const scopeRest = useCallback(() => ({ x: stageInput.anchorX, y: 0.2 }), []);

  const activeIndex = CHARACTERS.findIndex((c) => c.id === (pendingId ?? activeId));

  return (
    <main className="relative min-h-screen w-full overflow-x-hidden">
      <section
        ref={sectionRef}
        className="relative w-full pt-[64px] min-[900px]:pt-0 stage-h-full"
        onPointerDown={onStagePointerDown}
        aria-label="Character stage"
      >
        <div
          ref={canvasWrapRef}
          className={`relative h-[60svh] min-h-[420px] w-full overflow-hidden min-[900px]:absolute min-[900px]:inset-0 min-[900px]:h-auto ${
            thermalActive ? 'cursor-none' : 'cursor-crosshair'
          }`}
        >
          <CharacterCanvas activeId={activeId} />
          <ThermalScopeReticle containerRef={canvasWrapRef} active={thermalActive} restPosition={scopeRest} />
        </div>

        <SiteNav />
        <CreditsLink />

        <HeroStageOverlay
          characters={CHARACTERS}
          shownId={activeId}
          targetId={pendingId ?? activeId}
          glitching={pendingId !== null}
          thermalActive={thermalActive}
          onSelect={triggerSwap}
        />

        <RightScaleRuler activeIndex={activeIndex} count={CHARACTERS.length} />
      </section>

    </main>
  );
}
