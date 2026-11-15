/** The player's Steam ID, kept in this browser so the Play pages fill it in next time. There are no accounts. */

/** A 17-digit SteamID64, the form the match service accepts. */
export const STEAM_ID_RE = /^7656119\d{10}$/;

const KEY = 'doppelgamer.steamId';

export function getSavedSteamId(): string {
  try {
    return window.localStorage.getItem(KEY) ?? '';
  } catch {
    return '';
  }
}

/** Keeps the ID once it is a valid Steam ID; a half-typed or wrong value is not saved. */
export function saveSteamId(id: string): void {
  const value = id.trim();
  if (!STEAM_ID_RE.test(value)) return;
  try {
    window.localStorage.setItem(KEY, value);
  } catch {
    /* storage unavailable: the ID is not kept */
  }
}
