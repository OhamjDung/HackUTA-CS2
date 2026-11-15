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
  /** Portrait photo URL. Resolved server-side from public/images/bots/<id>.(svg|webp|png|jpg); monogram when absent. */
  avatarUrl?: string;
}

/** Roster order = arc order (top to bottom). */
export const BOTS: Bot[] = [
  { id: 'donk', name: 'donk', game: 'CS2', modelId: 'cs2', tags: ['Rifler', 'Entry'] },
  { id: 'broky', name: 'broky', game: 'CS2', modelId: 'cs2', tags: ['AWPer', 'Anchor'] },
  { id: 'sparg0', name: 'Sparg0', game: 'Smash Bros', modelId: 'smash', tags: ['Mario', 'Brawler'] },
];

export const DEFAULT_BOT_ID = 'sparg0';

/** Portrait photos live in public/images/bots/<bot id>.<ext>; the user photo at public/images/avatars/user.<ext>. */
export const AVATAR_EXTENSIONS = ['webp', 'jpg', 'jpeg', 'png'] as const;

export const GAME_FILTERS: { id: 'all' | BotGame; label: string }[] = [
  { id: 'all', label: 'All games' },
  { id: 'CS2', label: 'CS2' },
  { id: 'Smash Bros', label: 'Smash Bros' },
];

export const SCENES: { id: string; title: string; subtitle: string; image: StaticImageData; alt: string; href: string }[] = [
  { id: 'yours', title: 'Your games', subtitle: 'Upload a clip or demo', image: dust2, alt: 'Dust II bombsite', href: '/scenes?tab=upload' },
  { id: 'famous', title: 'Famous games', subtitle: 'Explore curated moments', image: mirage, alt: 'Mirage', href: '/scenes?tab=famous' },
];

/** Placeholder rows until the leaderboard service is wired. */
export const LEADERBOARD_SAMPLE = [
  { rank: 1, name: 'Player One', score: null as number | null },
  { rank: 2, name: 'Player Two', score: null as number | null },
  { rank: 3, name: 'Player Three', score: null as number | null },
];

/** Curated scene browser (Scenes → Famous games). Placeholder set until the scene catalogue ships. */
export interface CuratedScene {
  id: string;
  title: string;
  game: BotGame;
  setting: string;
  blurb: string;
  image?: StaticImageData;
}

export const CURATED_SCENES: CuratedScene[] = [
  { id: 'dust2-a-retake', title: 'A-site retake', game: 'CS2', setting: 'Dust II', blurb: '3v2 retake through Long and Short.', image: dust2 },
  { id: 'mirage-mid', title: 'Mid control', game: 'CS2', setting: 'Mirage', blurb: 'Win the Window duel, then split B.', image: mirage },
  { id: 'dust2-awp-long', title: 'Long A AWP duel', game: 'CS2', setting: 'Dust II', blurb: 'Hold the doors against an aggressive push.', image: dust2 },
  { id: 'mirage-b-anchor', title: 'B anchor hold', game: 'CS2', setting: 'Mirage', blurb: 'Survive the Apartments rush alone.', image: mirage },
];

export const LEADERBOARD_FULL = Array.from({ length: 10 }, (_, i) => ({
  rank: i + 1,
  name: `Player ${['One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten'][i]}`,
  botId: BOTS[i % BOTS.length].id,
  score: null as number | null,
}));
