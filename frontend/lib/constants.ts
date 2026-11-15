import type { CharacterConfig, CharacterId } from '@/types';

export const TRANSCODER_PATH = '/decoders/';
export const TRANSCODER_JS = '/decoders/basis_transcoder.js';
export const TRANSCODER_WASM = '/decoders/basis_transcoder.wasm';

/** Model prefetched first and rendered for time-to-first-frame. */
export const INITIAL_CHARACTER_ID: CharacterId = 'cs2';

/** Showcase auto-cycle interval (Node B4). */
export const AUTO_SWAP_INTERVAL_MS = 4000;
/** Auto-cycle starts enabled so judges see the full loop hands-free. */
export const AUTO_SWAP_ENABLED_DEFAULT = true;

/** Chunk size for background prefetching (HLD stage 3). */
export const PREFETCH_CONCURRENCY = 2;

/** Glitch transition timings (ms). */
export const GLITCH_SWAP_DELAY_MS = 220;
export const GLITCH_TOTAL_MS = 650;

export const CHARACTERS: CharacterConfig[] = [
  {
    id: 'cs2',
    name: 'CS2',
    url: '/models/01_cs2_blockout.glb',
    scale: [1, 1, 1],
    position: [0, 0, 0],
    idleAnimationName: 'Idle',
    // Tactical Amber / Counter-Strike Gold key rim, cool blue fill.
    rimColor: '#F59E0B',
    accentColor: '#38BDF8',
  },
  {
    id: 'smash',
    name: 'Smash',
    url: '/models/02_smash_blockout.glb',
    scale: [1, 1, 1],
    position: [0, 0, 0],
    idleAnimationName: 'Idle',
    // Electric Crimson key rim, blue fill.
    rimColor: '#EF4444',
    accentColor: '#3B82F6',
  },
  {
    id: 'fortnite',
    name: 'Fortnite',
    url: '/models/03_fortnite_blockout.glb',
    scale: [1, 1, 1],
    position: [0, 0, 0],
    idleAnimationName: 'Idle',
    // Rift Neon Purple key rim, cyan fill.
    rimColor: '#A855F7',
    accentColor: '#06B6D4',
  },
  {
    id: 'fifa',
    name: 'FIFA',
    url: '/models/04_fifa_blockout.glb',
    scale: [1, 1, 1],
    position: [0, 0, 0],
    idleAnimationName: 'Idle',
    // Pitch Neon Green key rim, sky blue fill.
    rimColor: '#10B981',
    accentColor: '#38BDF8',
  },
  {
    id: 'halo',
    name: 'Halo',
    url: '/models/05_halo_blockout.glb',
    scale: [1, 1, 1],
    position: [0, 0, 0],
    idleAnimationName: 'Idle',
    // Mjolnir Visor Gold key rim, Cortana Cyan fill.
    rimColor: '#EAB308',
    accentColor: '#22D3EE',
  },
];

export const CHARACTER_MAP: Record<CharacterId, CharacterConfig> = Object.fromEntries(
  CHARACTERS.map((c) => [c.id, c]),
) as Record<CharacterId, CharacterConfig>;
