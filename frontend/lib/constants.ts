import type { CharacterConfig, CharacterId } from '@/types';

export const TRANSCODER_PATH = '/decoders/';
export const TRANSCODER_JS = '/decoders/basis_transcoder.js';
export const TRANSCODER_WASM = '/decoders/basis_transcoder.wasm';

/** Model prefetched first and rendered for time-to-first-frame. */
export const INITIAL_CHARACTER_ID: CharacterId = 'cs2';

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
  },
  {
    id: 'smash',
    name: 'Smash',
    url: '/models/02_smash_blockout.glb',
    scale: [1, 1, 1],
    position: [0, 0, 0],
    idleAnimationName: 'Idle',
  },
  {
    id: 'fortnite',
    name: 'Fortnite',
    url: '/models/03_fortnite_blockout.glb',
    scale: [1, 1, 1],
    position: [0, 0, 0],
    idleAnimationName: 'Idle',
  },
  {
    id: 'fifa',
    name: 'FIFA',
    url: '/models/04_fifa_blockout.glb',
    scale: [1, 1, 1],
    position: [0, 0, 0],
    idleAnimationName: 'Idle',
  },
  {
    id: 'halo',
    name: 'Halo',
    url: '/models/05_halo_blockout.glb',
    scale: [1, 1, 1],
    position: [0, 0, 0],
    idleAnimationName: 'Idle',
  },
];

export const CHARACTER_MAP: Record<CharacterId, CharacterConfig> = Object.fromEntries(
  CHARACTERS.map((c) => [c.id, c]),
) as Record<CharacterId, CharacterConfig>;
