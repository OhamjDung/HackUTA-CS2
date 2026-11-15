import type { StaticImageData } from 'next/image';
import dust2 from '@/components/img/dust2.jpeg';
import mirage from '@/components/img/De_mirage_cs2.webp';
import type { CharacterId } from '@/types';

export type BotGame = 'CS2' | 'Smash Bros';

export interface Bot {
  id: string;
  /** Display name (player-inspired). */
  name: string;
  game: BotGame;
  /** Which stage model renders this bot (shared WebGPU stage). */
  modelId: CharacterId;
  /** Playstyle chips under the tagline. */
  tags: string[];
  /** Portrait photo URL. Resolved server-side from public/bots/<id>.(jpg|jpeg|png|webp); silhouette when absent. */
  avatarUrl?: string;
}

/** Roster order = arc order (top to bottom). */
export const BOTS: Bot[] = [
  { id: 'donk', name: 'donk', game: 'CS2', modelId: 'cs2', tags: ['Rifler', 'Entry'] },
  { id: 'broky', name: 'broky', game: 'CS2', modelId: 'cs2', tags: ['AWPer', 'Anchor'] },
  { id: 'sparg0', name: 'Sparg0', game: 'Smash Bros', modelId: 'smash', tags: ['Mario', 'Brawler'] },
];

export const DEFAULT_BOT_ID = 'sparg0';

/** Portrait photos: drop files in public/bots/<bot id>.<ext>; the user photo at public/profile.<ext>. */
export const AVATAR_EXTENSIONS = ['webp', 'jpg', 'jpeg', 'png'] as const;

export const GAME_FILTERS: { id: 'all' | BotGame; label: string }[] = [
  { id: 'all', label: 'All games' },
  { id: 'CS2', label: 'CS2' },
  { id: 'Smash Bros', label: 'Smash Bros' },
];

export const SCENES: { id: string; title: string; subtitle: string; image: StaticImageData; alt: string; href: string }[] = [
  { id: 'yours', title: 'Your games', subtitle: 'Upload a clip or demo', image: dust2, alt: 'Dust II bombsite', href: '#' },
  { id: 'famous', title: 'Famous games', subtitle: 'Explore curated moments', image: mirage, alt: 'Mirage', href: '#' },
];

/** Placeholder rows until the leaderboard service is wired. */
export const LEADERBOARD_SAMPLE = [
  { rank: 1, name: 'Player One', score: null as number | null },
  { rank: 2, name: 'Player Two', score: null as number | null },
  { rank: 3, name: 'Player Three', score: null as number | null },
];
