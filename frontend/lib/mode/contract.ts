export const APP_MODES = ['faze', 'odyssey'] as const;
export type AppMode = (typeof APP_MODES)[number];

export const SUPPORTED_PATHS = ['/', '/bots', '/scenes', '/leaderboard', '/play', '/studio'] as const;
export type SupportedPath = (typeof SUPPORTED_PATHS)[number];

const FAZE_BOTS = new Set(['donk', 'broky', 'sparg0']);
const FAZE_SCENES = new Set([
  'upload',
  'dust2-a-retake',
  'mirage-mid',
  'dust2-awp-long',
  'mirage-b-anchor',
  'smash-last-stock',
  'smash-edgeguard',
]);
const ODYSSEY_BOTS = new Set(['atlas', 'echo']);
const ODYSSEY_SCENES = new Set(['launch-bay', 'deep-space']);

export type QueryInput = URLSearchParams | Record<string, string | string[] | undefined>;

function first(input: QueryInput, key: string): string | undefined {
  if (input instanceof URLSearchParams) return input.get(key) ?? undefined;
  const value = input[key];
  return Array.isArray(value) ? value[0] : value;
}

/** Explicit, validated URL mode wins. Missing or invalid values deterministically resolve to FaZe. */
export function resolveMode(input: QueryInput | string | null | undefined): AppMode {
  const value = typeof input === 'string' || input == null ? input : first(input, 'mode');
  return value === 'odyssey' ? 'odyssey' : 'faze';
}

export function isSupportedPath(pathname: string): pathname is SupportedPath {
  return (SUPPORTED_PATHS as readonly string[]).includes(pathname);
}

/** Keep only parameters understood by the destination mode and current route. */
export function validModeParams(mode: AppMode, pathname: string, input: QueryInput): URLSearchParams {
  const out = new URLSearchParams({ mode });
  const bot = first(input, 'bot');
  const scene = first(input, 'scene');
  const tab = first(input, 'tab');

  if (pathname === '/scenes' && (tab === 'upload' || tab === 'famous')) out.set('tab', tab);
  const bots = mode === 'faze' ? FAZE_BOTS : ODYSSEY_BOTS;
  const scenes = mode === 'faze' ? FAZE_SCENES : ODYSSEY_SCENES;
  if (bot && bots.has(bot) && ['/bots', '/scenes', '/play', '/studio'].includes(pathname)) out.set('bot', bot);
  if (scene && scenes.has(scene) && ['/play', '/studio'].includes(pathname)) out.set('scene', scene);
  return out;
}

export function modeHref(pathname: string, mode: AppMode, input: QueryInput = {}): string {
  const params = validModeParams(mode, pathname, input);
  return `${pathname}?${params.toString()}`;
}

