'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import CharacterCanvas from '@/components/canvas/CharacterCanvas';
import GlitchOverlay from '@/components/ui/GlitchOverlay';
import NavigationDeck from '@/components/ui/NavigationDeck';
import {
  AUTO_SWAP_ENABLED_DEFAULT,
  AUTO_SWAP_INTERVAL_MS,
  CHARACTERS,
  GLITCH_SWAP_DELAY_MS,
  GLITCH_TOTAL_MS,
  INITIAL_CHARACTER_ID,
} from '@/lib/constants';
import type { CharacterId } from '@/types';

export default function HomePage() {
  const [activeId, setActiveId] = useState<CharacterId>(INITIAL_CHARACTER_ID);
  const [pendingId, setPendingId] = useState<CharacterId | null>(null);
  const [glitchIntensity, setGlitchIntensity] = useState(0);
  const [backend, setBackend] = useState<'webgpu' | 'webgl2' | null>(null);
  const [autoPlay, setAutoPlay] = useState(AUTO_SWAP_ENABLED_DEFAULT);
  // Bumped on every completed swap trigger so the auto-cycle timer restarts
  // after manual selections too — auto and manual can never collide mid-glitch.
  const [cycleKey, setCycleKey] = useState(0);
  const timers = useRef<number[]>([]);

  // Refs mirror state for use inside timers without stale closures.
  const activeIdRef = useRef(activeId);
  activeIdRef.current = activeId;
  const pendingRef = useRef(pendingId);
  pendingRef.current = pendingId;

  useEffect(() => () => {
    timers.current.forEach((t) => window.clearTimeout(t));
    timers.current = [];
  }, []);

  const triggerSwap = useCallback((id: CharacterId) => {
    if (id === activeIdRef.current || pendingRef.current !== null) return;
    setPendingId(id);
    setGlitchIntensity(1);
    // Swap the scene-graph model reference mid-glitch (HLD stage 4).
    timers.current.push(
      window.setTimeout(() => setActiveId(id), GLITCH_SWAP_DELAY_MS),
    );
    timers.current.push(
      window.setTimeout(() => {
        setGlitchIntensity(0);
        setPendingId(null);
      }, GLITCH_TOTAL_MS),
    );
    setCycleKey((k) => k + 1);
  }, []);

  const handleSelect = useCallback(
    (id: CharacterId) => {
      triggerSwap(id);
    },
    [triggerSwap],
  );

  const goToNext = useCallback(() => {
    const order = CHARACTERS.map((c) => c.id);
    const next = order[(order.indexOf(activeIdRef.current) + 1) % order.length];
    triggerSwap(next);
  }, [triggerSwap]);

  // Autonomous showcase loop (Node B4): advance every AUTO_SWAP_INTERVAL_MS.
  // Any swap (auto or manual) bumps cycleKey and restarts this timer, so a
  // manual click can never land inside an auto-swap glitch. Mid-glitch ticks
  // are skipped by triggerSwap's pending guard.
  useEffect(() => {
    if (!autoPlay) return;
    const t = window.setTimeout(goToNext, AUTO_SWAP_INTERVAL_MS);
    return () => window.clearTimeout(t);
  }, [autoPlay, cycleKey, goToNext]);

  return (
    <main className="relative h-screen w-full overflow-hidden bg-black">
      <CharacterCanvas activeId={activeId} glitchIntensity={glitchIntensity} onBackendReady={setBackend} />
      <GlitchOverlay
        activeCharacter={CHARACTERS.find((c) => c.id === activeId)!}
        intensity={glitchIntensity}
        backend={backend}
      />
      <NavigationDeck
        characters={CHARACTERS}
        activeId={pendingId ?? activeId}
        onSelect={handleSelect}
        disabled={pendingId !== null}
        autoPlay={autoPlay}
        onToggleAutoPlay={() => setAutoPlay((v) => !v)}
      />
    </main>
  );
}
