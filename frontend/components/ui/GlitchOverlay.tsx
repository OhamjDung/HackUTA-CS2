'use client';

import type { CharacterConfig } from '@/types';

interface GlitchOverlayProps {
  activeCharacter: CharacterConfig;
  /** 0.0 (clean) → 1.0 (full glitch). Mirrors the GPU uniform. */
  intensity: number;
  /** Backend that actually initialized; null until the canvas reports it. */
  backend: 'webgpu' | 'webgl2' | null;
}

export default function GlitchOverlay({ activeCharacter, intensity, backend }: GlitchOverlayProps) {
  const glitching = intensity > 0.05;
  const accent = activeCharacter.accentColor;

  return (
    <div className="pointer-events-none absolute inset-0 z-10 flex flex-col justify-between p-6">
      {/* Scanline film over the whole viewport */}
      <div
        className="hud-scanlines absolute inset-0 opacity-60"
        style={{ opacity: glitching ? 0.9 : 0.6 }}
        aria-hidden
      />

      <header className="relative flex items-start justify-between">
        <div>
          <p className="text-[11px] uppercase tracking-[0.35em] text-white/50">
            FaZe // Character Deck
          </p>
          <h1
            key={activeCharacter.id}
            className={`mt-1 text-4xl font-black uppercase tracking-tight ${
              glitching ? 'hud-glitching' : ''
            }`}
          >
            {activeCharacter.name}
          </h1>
        </div>
        <div className="text-right text-[11px] uppercase tracking-[0.25em] text-white/50">
          <p>{backend === 'webgl2' ? 'WebGL2 / 60fps' : 'WebGPU / 60fps'}</p>
          <p
            className={glitching ? 'text-red-500' : undefined}
            style={glitching ? undefined : { color: accent }}
          >
            {glitching ? '● swapping' : '● locked'}
          </p>
        </div>
      </header>

      {/* Bottom signal bar that spikes with glitch intensity */}
      <footer className="relative">
        <div className="h-[3px] w-full overflow-hidden bg-white/10">
          <div
            className="h-full transition-[width] duration-150"
            style={{ width: `${glitching ? 100 : 12}%`, backgroundColor: accent }}
          />
        </div>
        <p className="mt-2 text-[11px] uppercase tracking-[0.3em] text-white/40">
          {glitching ? 'signal interrupted — hot-swap in progress' : 'signal clean'}
        </p>
      </footer>
    </div>
  );
}
