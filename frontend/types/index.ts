export type CharacterId = 'cs2' | 'smash' | 'fortnite' | 'fifa' | 'halo';

export interface CharacterConfig {
  id: CharacterId;
  /** Short internal name (legacy HUD / logs). */
  name: string;
  /** Label shown in the studio HUD ("01 / CS2"). */
  displayName: string;
  url: string;
  scale: [number, number, number];
  position: [number, number, number];
  idleAnimationName: string;
  /** Per-character tint for the subtle studio rim light. */
  rimColor: string;
  /** Per-character accent (kept for compatibility with earlier HUDs). */
  accentColor: string;
  /** Optional on-stage size multiplier (applied to the presence root, not the cached scene). */
  stageScale?: number;
}

export interface AssetCacheEntry {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  gltf: any; // GLTF result from GLTFLoader
  refCount: number;
  lastAccessed: number;
}
