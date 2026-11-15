/** Replay puzzles: types and calls to the match service (match-service/match_service/puzzle_routes.py). */

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');

export type Side = 'CT' | 'T';

export interface PuzzleSummary {
  id: string;
  title: string;
  map: string;
  source: 'user' | 'pro';
  side: Side;
  hero: string;
  tags: string[];
  created: string;
  window_seconds: number;
  rating: number;
  plays: number;
  solves: number;
  up: number;
  down: number;
  need_kills: number;
  original: { kills: number; died: boolean; killer: string | null; weapon: string | null };
}

export interface Sample {
  t: number;
  x: number;
  y: number;
  z: number;
  yaw: number;
  hp: number;
  weapon: string;
  fire: boolean;
}

export interface PuzzlePlayer {
  slot: number;
  name: string;
  side: Side;
  hero: boolean;
  start: { health: number; armor: number; money: number; weapons: string[] };
  track: Sample[];
}

export interface PuzzleEvent {
  t: number;
  type: 'kill' | 'throw' | 'plant' | 'defuse';
  attacker: string | null;
  victim: string | null;
  weapon: string | null;
}

export interface PuzzleDoc {
  id: string;
  title: string;
  window_seconds: number;
  players: PuzzlePlayer[];
  events: PuzzleEvent[];
}

export interface Mistake {
  id: string;
  title: string;
  detail: string;
  t: number;
  severity: 1 | 2 | 3;
}

export interface PuzzleDetail extends PuzzleSummary {
  puzzle: PuzzleDoc;
  feedback: Mistake[];
}

export interface DeathDetail {
  id: string;
  puzzle: PuzzleDoc;
  feedback: Mistake[];
}

export interface PlayerStats {
  player: string;
  rating: number;
  streak: number;
  best_streak: number;
  solved: number;
  attempts: number;
}

export interface Attempt {
  id: number;
  puzzle_id: string;
  solved: number;
  survived: number;
  kills: number;
  rating_before: number;
  rating_after: number;
  at: string;
}

export interface AttemptResult {
  solved: boolean;
  survived: boolean;
  kills: number;
  need_kills: number;
  player: PlayerStats;
  rating_change: number;
  puzzle_rating: number;
}

export interface DraftSlot {
  slot: number;
  name: string;
  side: Side;
  offset_seconds: number;
  file: string | null;
  bytes: number;
}

export interface Draft {
  id: string;
  title: string;
  map: string;
  created: string;
  status: 'awaiting_footage' | 'needs_derivation';
  message: string;
  slots: DraftSlot[];
}

export interface Outline {
  cell: number;
  cells: [number, number][];
}

export async function call<T>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const { json, headers, ...rest } = init;
  const res = await fetch(`${API_URL}${path}`, {
    ...rest,
    headers: json === undefined ? headers : { 'Content-Type': 'application/json', ...headers },
    body: json === undefined ? rest.body : JSON.stringify(json),
    cache: 'no-store',
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const detail = data?.detail;
    throw new Error(Array.isArray(detail) ? detail.map((d: { msg?: string }) => d.msg ?? String(d)).join('; ') : (detail ?? res.statusText));
  }
  return data as T;
}

const NAME_KEY = 'doppelgamer.playerName';

/** The name attempts are saved under. Kept in the browser; there are no accounts. */
export function getPlayerName(): string {
  try {
    return window.localStorage.getItem(NAME_KEY) || 'guest';
  } catch {
    return 'guest';
  }
}

export function setPlayerName(name: string): void {
  try {
    window.localStorage.setItem(NAME_KEY, name.trim().slice(0, 40) || 'guest');
  } catch {
    /* storage unavailable: the name is not kept */
  }
}

export const SEVERITY_LABEL: Record<number, string> = { 3: 'Big', 2: 'Medium', 1: 'Small' };

export function ratingBand(rating: number): string {
  if (rating < 1400) return 'Easy';
  if (rating < 1600) return 'Medium';
  return 'Hard';
}
