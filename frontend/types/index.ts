export type CharacterId = 'cs2' | 'smash' | 'fortnite' | 'fifa' | 'halo';

export interface CharacterConfig {
  id: CharacterId;
  name: string;
  url: string;
  scale: [number, number, number];
  position: [number, number, number];
  idleAnimationName: string;
  /** HUD accent (active pill, signal bar, locked dot) + cool fill light. */
  accentColor: string;
  /** Key rim light color for the OLED stage. */
  rimColor: string;
}

export interface AssetCacheEntry {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  gltf: any; // GLTF result from GLTFLoader
  refCount: number;
  lastAccessed: number;
}
