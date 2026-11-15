import type { CharacterConfig, CharacterId } from '@/types';

export const TRANSCODER_PATH = '/decoders/';
export const TRANSCODER_JS = '/decoders/basis_transcoder.js';
export const TRANSCODER_WASM = '/decoders/basis_transcoder.wasm';

/** Model prefetched first and rendered for time-to-first-frame. */
export const INITIAL_CHARACTER_ID: CharacterId = 'cs2';

// ---------------------------------------------------------------------------
// Motion timings (spec: "01 — IDLE: 6s hold", "02 — GLITCH SWAP: 0.6s")
// ---------------------------------------------------------------------------

/** Clean on-screen hold per character, measured from the end of one glitch to the start of the next. */
export const AUTO_SWAP_INTERVAL_MS = 6000;
/** Full glitch transition length. */
export const GLITCH_DURATION_MS = 600;
/** Model reference swaps at the glitch peak, hidden by the tear. */
export const GLITCH_SWAP_AT_MS = GLITCH_DURATION_MS / 2;
/** Auto-cycle starts enabled so visitors see the full loop hands-free. */
export const AUTO_SWAP_ENABLED_DEFAULT = true;

/** Chunk size for background prefetching (HLD stage 3). */
export const PREFETCH_CONCURRENCY = 2;

// ---------------------------------------------------------------------------
// Studio theme tokens (mirrored as CSS variables in app/globals.css)
// ---------------------------------------------------------------------------

export const STUDIO = {
  bg: '#000000',
  ink: '#F4F3EF',
  inkMuted: '#A3A39D',
  inkSubtle: '#6F6F6A',
  hairline: '#1F1F1E',
  pillInactive: '#333331',
  accent: '#E4002B',
} as const;

// ---------------------------------------------------------------------------
// Stage framing
// ---------------------------------------------------------------------------

/** Camera framing so a 1.85 m character fills ~89% of the hero stage height. */
export const STAGE_CAMERA = {
  position: [0, 0.95, 4.18] as [number, number, number],
  target: [0, 0.9, 0] as [number, number, number],
  fov: 28,
};

/**
 * Horizontal placement of the character as a fraction of the stage width
 * (0.5 = centered). Desktop matches the reference (between headline and HUD);
 * narrower viewports drift toward center so the HUD column never overlaps.
 */
export function stageXFraction(widthPx: number): number {
  if (widthPx < 900) return 0.5;
  const t = Math.min(1, Math.max(0, (widthPx - 900) / (1440 - 900)));
  return 0.55 + t * (0.625 - 0.55);
}

/** Thermal scope lens radius in CSS pixels (shader + SVG reticle share it). */
export const SCOPE_RADIUS_PX = 92;

// ---------------------------------------------------------------------------
// Links (placeholders until the studio/demo routes exist)
// ---------------------------------------------------------------------------

export const STUDIO_URL = '/studio';
export const DEMO_URL = '#';

export const CHARACTERS: CharacterConfig[] = [
  {
    id: 'cs2',
    name: 'CS2',
    displayName: 'CS2',
    url: '/models/01_cs2_blockout.glb',
    scale: [1, 1, 1],
    position: [0, 0, 0],
    idleAnimationName: 'Idle',
    rimColor: '#F59E0B',
    accentColor: '#38BDF8',
  },
  {
    id: 'smash',
    name: 'Smash',
    displayName: 'Smash',
    url: '/models/02_smash_blockout.glb',
    scale: [1, 1, 1],
    position: [0, 0, 0],
    idleAnimationName: 'Idle',
    rimColor: '#EF4444',
    accentColor: '#3B82F6',
  },
  {
    id: 'fortnite',
    name: 'Fortnite',
    displayName: 'Fortnite',
    url: '/models/03_fortnite_blockout.glb',
    scale: [1, 1, 1],
    position: [0, 0, 0],
    idleAnimationName: 'Idle',
    rimColor: '#A855F7',
    accentColor: '#06B6D4',
  },
  {
    id: 'fifa',
    name: 'Valorant',
    displayName: 'Valorant',
    url: '/models/04_fifa_blockout.glb',
    scale: [1, 1, 1],
    position: [0, 0, 0],
    idleAnimationName: 'Idle',
    rimColor: '#10B981',
    accentColor: '#38BDF8',
  },
  {
    id: 'halo',
    name: 'Halo',
    displayName: 'Halo',
    url: '/models/05_halo_blockout.glb',
    scale: [1, 1, 1],
    position: [0, 0, 0],
    idleAnimationName: 'Idle',
    rimColor: '#EAB308',
    accentColor: '#22D3EE',
  },
];

export const CHARACTER_MAP: Record<CharacterId, CharacterConfig> = Object.fromEntries(
  CHARACTERS.map((c) => [c.id, c]),
) as Record<CharacterId, CharacterConfig>;
