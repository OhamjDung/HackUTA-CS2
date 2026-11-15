'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import CharacterCanvas from '@/components/canvas/CharacterCanvas';
import GlitchOverlay from '@/components/ui/GlitchOverlay';
import NavigationDeck from '@/components/ui/NavigationDeck';
import {
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
  const timers = useRef<number[]>([]);

  useEffect(() => () => {
    timers.current.forEach((t) => window.clearTimeout(t));
    timers.current = [];
  }, []);

  const handleSelect = useCallback(
    (id: CharacterId) => {
      if (id === activeId || pendingId !== null) return;
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
    },
    [activeId, pendingId],
  );

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
      />
    </main>
  );
}
