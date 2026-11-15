import { existsSync } from 'node:fs';
import path from 'node:path';
import BotsHub from '@/components/bots/BotsHub';
import { AVATAR_EXTENSIONS, BOTS } from '@/lib/bots';

/**
 * Server wrapper: resolves which portrait photos exist in public/ so the client
 * only requests real files (no 404s in the console). Drop-in workflow:
 *   public/bots/<bot id>.(webp|jpg|jpeg|png)   e.g. public/bots/sparg0.jpg
 *   public/profile.(webp|jpg|jpeg|png)          signed-in user photo (nav)
 */
function findPublic(base: string): string | undefined {
  for (const ext of AVATAR_EXTENSIONS) {
    const rel = `${base}.${ext}`;
    if (existsSync(path.join(process.cwd(), 'public', rel))) return `/${rel}`;
  }
  return undefined;
}

export default function BotsPage() {
  const avatars = Object.fromEntries(BOTS.map((b) => [b.id, findPublic(`bots/${b.id}`)]));
  return <BotsHub avatars={avatars} profileUrl={findPublic('profile')} />;
}
