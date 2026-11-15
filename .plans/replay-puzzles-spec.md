# Replay puzzles and death feedback: spec

Status: draft from interview, 2026-11-15. Nothing here is built or run yet.
Owner: Tom Pham (HackUTA CS2). Touches CloneDirector (C#), match-service (FastAPI), demo pages.
Per AGENTS.md: update SPEC.md (status board, section for this part, change log) in the same commit as any code.

## 1. Goal

Give judges a reason to come back. When a player dies in a live match, (a) show the key mistakes at once,
and (b) let them rewind 10 seconds and try the moment again. Saved moments become puzzles in a Lichess-style
library, seeded with one or two moments from the pro-demo dataset.

## 2. Decisions from the interview

| Topic | Decision |
|---|---|
| Rewind fidelity | Approximate restore. Positions, view angles, health, armor, weapons, money. Smoke, fire, grenades in flight and dropped weapons are NOT restored. |
| Where state lives | CloneDirector keeps a rolling 10-15 s buffer (sample about every 0.25 s). On a death it writes the last 10 s to a file on disk. That file is the puzzle. GOTV demo is a separate full archive (see open item). |
| Other players during a puzzle | Replay of the recorded movement, deterministic. They do not react to the player. |
| Solve rule | Survive the 10 s window AND kills > original clip's kills, with a floor of 1 kill (a 0-kill clip needs 1 kill). Ties fail. |
| Death feedback | Rule-based detectors, shown right after death as a web overlay on the demo page plus one chat line in game. No LLM. |
| Multi-POV creator | Faded: a visible but disabled "coming soon" entry in the UI. No further work. See 6. |
| Library features, v1 | Rating and difficulty; themes and tags. NOT in v1: streak, daily puzzle, votes, reports, attempt history. |
| Storage | Local files + SQLite. Puzzle JSON and state files under `match-service/data/puzzles/`, index in SQLite. Same interface so Mongo can replace it later. |

## 3. Puzzle format (proposed)

`data/puzzles/<id>.json`:
- `id`, `map`, `source` (`user` | `pro`), `created`, `title`
- `window_seconds` (10), `tick_rate_sampled` (4/s)
- `players[]`: slot, name, side, `start` {pos, angles, health, armor, weapons, money}, `track[]` of samples (t, pos, angles, health, weapon, shooting)
- `hero`: the player the user controls
- `original`: {kills, died, killer, weapon}
- `solve`: {survive: true, min_kills: max(1, original.kills + 1)}
- `tags[]` (map, side, weapon, situation), `difficulty` (initial estimate)
SQLite table `puzzles` indexes id, map, tags, rating, source. Table `ratings` holds a player's rating (see 5).

## 4. Components

1. **Snapshot buffer (CloneDirector).** Ring buffer per player. On the `Death` event of a human player, freeze the last 10 s and write the puzzle file. Reuse the existing `DEATH` log fields.
2. **Restore and playback (CloneDirector).** Command `puzzle_load <id>`: respawn, teleport everyone, strip then give weapons, set health and armor, disable round-win conditions, hand control of the hero to the user, play the others' tracks using the existing route playback. Restore order is untested; borrow position/angle/weapon restore from CS2PracticeMod (MIT, CounterStrikeSharp).
3. **Match-service API.** `GET /puzzles` (filter by tag, map, rating), `GET /puzzles/{id}`, `POST /puzzles` (save from a death), `POST /puzzles/{id}/start` (tells CloneDirector to load), `POST /puzzles/{id}/result` (survived, kills; updates rating). Add to `match-service/README.md`; the API is Ash's interface, so agree changes with Ash first (AGENTS.md section 6).
4. **Feedback detectors.** Run on the frozen 10 s state right after death. Starting list (to validate against real deaths): peeked alone with teammates far away; no utility used before the peek; reloaded or switched weapon in the open; shot while moving; stood still in the open; died within N s of an enemy contact that had already been seen. Output: up to 3 ranked mistakes, each one sentence.
5. **Demo UI** (`match-service/demo/`): death overlay with the mistakes plus "Retry last 10 s" and "Save as puzzle" buttons; a Puzzles page with the library list, filters, and Practice button; a Create page (see 6).

## 5. Rating and difficulty

Simple Elo: puzzle and player both start at 1500; solve adds/subtracts by the standard expected-score formula; K = 32 for players, puzzle rating moves with K = 16. Initial puzzle difficulty is set by hand for seed puzzles and 1500 for user puzzles.

## 6. Multi-POV creator

The Create page shows the intended form (a slot per player: name, side, video, sync offset) as a greyed, non-functional "coming soon" preview. Nothing is uploaded, stored or processed. Reason: Tom said "fade, don't do anymore". Reading used here: leave a visible disabled placeholder, spend no more time. Change this if "fade" meant remove it entirely.

## 7. Seed puzzles

One or two moments from the OpenCS2 pro-demo dataset used for the clones, converted to the puzzle format. Dataset is git-ignored (`data/`), so the seed puzzle JSON is committed but demos are not. How the conversion works is an open item: the existing clone pipeline already extracts routes per round and may be reused.

## 8. Not verified yet (all of it)

- Restore order and whether CounterStrikeSharp can respawn plus teleport plus re-equip reliably in a listen server with bots.
- Whether replaying others' tracks with route playback matches the recorded timing after a teleport.
- Death-time frozen state matching the in-game result (position sampling at 4/s may be too coarse for the fight).
- Detector thresholds. They are guesses until checked against real deaths.
- C# tests cannot run on this PC (Application Control); build compiles only.

## 9. Open items

1. Whether to also keep the GOTV demo per match (recording over netcon crashed CS2; `-Record tv` is untested).
2. Seed puzzle source and conversion path (section 7).
3. Confirm the "fade" reading (section 6).
4. Win condition during a puzzle: spec says disable round end; confirm how without breaking the bot base.
5. Human controlling the hero during a replay needs a human in the listen server; Bot Mode spectator behavior (Tom could not move as spectator earlier) must be handled.
6. Tell Ash about the new endpoints before coding them.

## 10. Suggested build order

1. Snapshot buffer + `DEATH`-triggered file write; check the file against a real death.
2. Restore + playback of one saved moment by hand (`puzzle_load`).
3. Detectors and the death overlay.
4. Puzzle API, SQLite, library page, rating.
5. Seed puzzles.
6. Disabled Create page.
