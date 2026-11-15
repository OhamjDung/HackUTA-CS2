// Server-only module (uses node:fs): import from server components / layouts only.
import { existsSync } from 'node:fs';
import path from 'node:path';
import { BOTS } from '@/lib/bots';

/**
 * Brand + portrait assets resolved on the server, so the client only ever
 * requests files that exist (no 404s). Drop-in locations under public/:
 *
 *   images/brand/faze-mark.(svg|png|webp)        Logo 1 (white fill, red bevel) — used at >= 60px
 *   images/brand/faze-mark-1color.(svg|png|webp) 1-colour mark — required between 40 and 59px
 *   images/avatars/user.(jpg|jpeg|png|webp)      signed-in user's photo (nav)
 *   images/bots/<bot id>.(webp|jpg|jpeg|png)     roster portraits
 */
export interface BrandAssets {
  fazeMark?: string;
  fazeMarkMono?: string;
  profile?: string;
  bots: Record<string, string | undefined>;
}

const EXT = ['svg', 'webp', 'png', 'jpg', 'jpeg'];

function find(base: string): string | undefined {
  for (const ext of EXT) {
    const rel = `${base}.${ext}`;
    if (existsSync(path.join(process.cwd(), 'public', rel))) return `/${rel}`;
  }
  return undefined;
}

export function resolveBrandAssets(): BrandAssets {
  return {
    fazeMark: find('images/brand/faze-mark'),
    fazeMarkMono: find('images/brand/faze-mark-1color'),
    profile: find('images/avatars/user'),
    bots: Object.fromEntries(BOTS.map((b) => [b.id, find(`images/bots/${b.id}`)])),
  };
}
