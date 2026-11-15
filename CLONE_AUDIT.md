# Clone audit, 14 Nov 2026

For Arjun, from Tom (with Claude). It checks the clone files in `clones/` against the
real players' held-back matches, and scores the project against the spec's MVP.

## Summary

- **No clone has run in CS2.** The only bots that have played are the bot base's built-in `donk` and
  `broky` presets, which use no player data. Everything below about closeness is measured on the
  clone **files**, not on a bot in a game.
- **The files do carry the player's signal.** In each held-back match I scored the player and his
  four teammates against each clone. The right player came out nearest in 5 of 8 tests and second
  in the other 3 (chance of first is 1 in 5).
- **donk's T side and broky's CT routes are the misses.** T-side position overlap does not separate
  the two players at all.
- **`broky_v1` is a rifler, not a sniper.** Real broky got 10 of 17 kills with the AWP in his
  held-back match. The clone's full buy is an AK-47 or M4A4.
- **A clone's data covers about a quarter of a round.** Routes average 18.5 s; the players stay alive
  about 70 s per round. The rest is the generic bot.
- **Skill against professionals is unmeasured** for every bot. `Skill = 100` is a setting.
- **MVP: none of the four "do not cut" items is done.** Two things block them: the playback gate has
  not been tried, and there is no working way to record a bot match.

## 1. What "the models" are today

| Thing | Built from player data? | Has it run in CS2? |
|---|---|---|
| Stand-in bots (`match-service/sample_clones/`, bot base presets named donk and broky) | No | Yes, on Tom's PC |
| Data-built clones (`clones/donk_v1`, `clones/broky_v1`) | Yes: counted habits and cut routes | No |
| Generating model (CS-NET v4 plus identity vectors) | Would be | Does not exist; no owner |

Nothing is "learned" yet. The clones are statistics and replayed movement from real matches.

## 2. How close are the clone files to the real players?

### 2.1 Method

Ran today. I downloaded both held-back recordings from OpenCS2 (2393242 for donk, 2393024 for broky)
and ran the repository's own `load_match`, `cut_segments`, `stats_block` and `similarity.compare` on
**every player** in each match. Each player's held-back numbers were compared with each clone's
committed `stats.json`. If a clone captures its player, that player should score highest.

- **Comparison group: the four teammates.** They played the same number of rounds on each side as
  the target. The five opponents played the sides in the other proportion (for example 12 T rounds
  against donk's 5), and overlap rises with more rounds, so ranking against them is unfair.
- **What reproduces.** My held-back numbers for the two targets equal the committed
  `similarity.player_vs_self` values (all eight). That confirms the held-back side and the compare
  code. I did not rebuild the build-side `stats.json`.

### 2.2 Does the clone pick out its own player?

Overlap runs from 0 (nothing shared) to 1 (identical). Rank is the target's place among the five
players on his team. Chance of first place is 1 in 5.

| Clone | Side | Held-back rounds | Position overlap | Rank | Route overlap | Rank |
|---|---|---:|---:|---:|---:|---:|
| `donk_v1` | CT | 12 | 0.787 | **1 of 5** | 0.571 | **1 of 5** |
| `donk_v1` | T | 5 | 0.621 | 2 of 5 | 0.421 | 2 of 5 |
| `broky_v1` | T | 10 | 0.705 | **1 of 5** | 0.579 | **1 of 5** |
| `broky_v1` | CT | 12 | 0.733 | **1 of 5** | 0.297 | 2 of 5 |

- **donk, CT:** clear on position (next is SH1R0 at 0.627). Closer on routes (SH1R0 at 0.517).
- **donk, T:** SH1R0 edges him on both (0.638 and 0.457), on 5 rounds. Too few rounds to call.
- **broky, T:** clear on both (next best 0.557 and 0.491).
- **broky, CT:** clear on position (karrigan 0.621). On routes Twistzz beats him, 0.359 to 0.297.

First place in 5 of 8 and second in 3 of 8 is well above chance, on small samples.

### 2.3 Swap test: can the two clones be told apart?

Each row scores one clone against one player's held-back rounds. Rank is that player's place among
his own team.

| Scored on | Side | Clone used | Position overlap (rank) | Route overlap (rank) |
|---|---|---|---|---|
| broky's rounds | T | `broky_v1` (own) | 0.705 (1 of 5) | 0.579 (1 of 5) |
| broky's rounds | T | `donk_v1` | 0.753 (1 of 5) | 0.253 (4 of 5) |
| broky's rounds | CT | `broky_v1` (own) | 0.733 (1 of 5) | 0.297 (2 of 5) |
| broky's rounds | CT | `donk_v1` | 0.546 (4 of 5) | 0.172 (4 of 5) |
| donk's rounds | CT | `donk_v1` (own) | 0.787 (1 of 5) | 0.571 (1 of 5) |
| donk's rounds | CT | `broky_v1` | 0.591 (2 of 5) | 0.493 (1 of 5) |

- **T-side position overlap does not separate them.** On broky's T rounds the donk clone scores
  higher (0.753) than broky's own clone (0.705).
- **Routes separate them on broky's rounds:** T is 0.579 own against 0.253; CT is 0.297 against 0.172.
- **On donk's CT rounds the own clone wins both measures,** but by a small margin on routes (0.571
  against 0.493).
- donk's T rounds are left out of this table: 5 rounds.

For the pitch: use route overlap, and donk's CT side. Do not quote T-side position overlap as
evidence of identity.

### 2.4 Weapons and purchases: broky is the wrong kind of player

Real broky, held-back match 2393024 (22 rounds): 17 kills, **10 with the AWP (59%)**, 12% headshots.

| `broky_v1` setting | Value | Problem |
|---|---|---|
| Weapon order | `m4a1`, `ak47`, `awp`, … | Ordered by shots fired, which under-counts a sniper rifle |
| Full buy, T (27 build rounds) | AK-47, armor, flash, smoke, molotov | AWP bought in 19% of those rounds, so it misses the 50% cut |
| Full buy, CT (33 build rounds) | M4A4, armor, smoke, flash, HE, incendiary | AWP bought in 12% |

He bought an AWP in only 3 of the 22 held-back rounds and still made most of his kills with it,
because he keeps it between rounds. Purchase counts cannot see that. Counting the weapon used for
kills, or the weapon carried per round, would. The spec picked broky so his clone "looks clearly
different from donk's"; as built, it would not.

donk's list (`ak47`, `m4a1`, `galilar`) agrees with his held-back kills (5 M4, 3 AK, no AWP).

### 2.5 How much of a round is the player's data?

| | `donk_v1` | `broky_v1` |
|---|---:|---:|
| Route files | 80 | 79 |
| Average route length | 18.5 s | 18.3 s |
| Average time alive per round, held-back match | 68.9 s | 76.9 s |
| Share of alive time the route covers | 27% | 24% |
| Routes cut off by the 20 s limit | 61 of 80 | 58 of 79 |
| T-side routes cut off by the limit | 27 of 32 | 27 of 38 |

donk's median time to first contact on T is 52 s. So on T the clone walks 20 s of donk's path and
then the generic bot plays the next 30 s before any fight. The position overlap numbers above cover
the whole round for the real player; a clone bot can only reproduce the first quarter.

### 2.6 Route file check

`donk_v1_t_2393226_r13.json.br` against the parsed recording of match 2393226, round 13:

- 1,278 ticks in both; position and yaw differ by 0.0 on every tick. The converter copies the path
  exactly.
- 19.98 s, ended by the time limit, about 2,080 units from start to end.
- `Subticks` is empty, as `HANDOFF.md` says. Whether the game plays the file is still untested.

This is one file of 159.

## 3. How good are they compared with professionals?

Not measured, for any bot. A number needs a recorded bot match, and there is none.

What the real players did, for reference:

| Player, match | Rounds | Kills–deaths | Headshot share of kills | Damage per round (approx.) |
|---|---:|---:|---:|---:|
| donk, held-back 2393242 | 17 | 12–10 | 67% | 108 |
| broky, held-back 2393024 | 22 | 17–14 | 12% | 83 |
| donk, build match 2393226 | 18 | 4–16 | 75% | 46 |

- Ran today from the recordings. donk's 4–16 is consistent with the full scoreboard in that file.
- Damage per round sums damage events capped at 100 each; it may overcount overkill damage.
- donk's two matches differ by a factor of two. One match is not a skill reading.
- `Skill = 100` and `aim_skill = 1.0` are bot settings. `reaction_ms` is null, `Teamwork` is fixed.
- The stand-in bots visibly move, buy and fight on Tom's PC. Nobody has measured them.

## 4. How close is the MVP?

### 4.1 Phase exit tests (spec section 11)

| Test | State | Evidence |
|---|---|---|
| Phase 0: a bot replays a hand-recorded walk | Not tried | Needs `!record` / `!replay` on Tom's PC |
| Phase 0: one donk round parses | Pass | Ran again today on three recordings |
| Phase 0: CS-NET generates one path | Not tried | No model work started |
| Phase 1: `clone_add donk t` adds a bot that buys what donk buys | Not tried | The spec says CloneDirector compiles and passes 26 tests (I did not run them); not installed in CS2 |
| 6-hour gate: a bot replays a converted donk route | Not tried | Same |
| Phase 2: replay page shows real round next to clone round, with commentary | Not started | No replay page, no clone recording |

### 4.2 The four items the spec says not to cut

| Item | State | Blocked by |
|---|---|---|
| Replay page | Not started, no owner | Needs a recorded clone round |
| Habit clone in the game | Files built, never run | CloneDirector untested in CS2 |
| Similarity score (clone and default bot against held-back) | Ceiling only | No way to record a bot match yet |
| Identity swap test | Not started | Generating model not started |

### 4.3 What does work

- CS2 with the bot base in Bot Mode on Tom's PC.
- The match service starting a stand-in match over the network console.
- The clone pipeline, both clone bundles, and exact route conversion at file level.

### 4.4 The two blockers

1. **Playback gate.** Untested. Tom's PC is the only machine with the bot base running.
2. **Recording.** The console `record` command froze the client clock and crashed CS2 once (seen on
   Tom's PC). Per Ash's commit `3e690c3`, it is now off and there is a `tv` option; not yet tried. Without a recording there is no clone-side
   replay and no similarity score.

## 5. Suggested order

1. Run the playback gate on Tom's PC (`HANDOFF.md` 5.1): `!record`, `!replay`, send back the real
   `test.json.br`, then replay one converted donk route.
2. Test `tv` recording through the match service.
3. Fix broky's weapon ranking and full buy so the AWP comes first. Rank by kills or by weapon
   carried per round.
4. Lengthen T-side routes, or cut at first contact with a higher cap. 27 of 32 donk T routes hit the
   20 s limit.
5. Report rank among teammates, and route overlap, in place of raw position overlap.
6. Decide whether the generating model stays in scope. It has no owner and two of the four must-keep
   items depend on it or on recordings.

## 6. Limits of this audit

- Three of the ten recordings were downloaded: both held-back matches and one donk build match. The
  clone side of every comparison is the committed `stats.json`; I did not rebuild the clones.
- Samples are small: 5 to 12 held-back rounds per side. donk's T side is 5 rounds.
- The four teammates are a convenience comparison group. They have different roles, and none of
  them is in the clone's build matches as the target.
- One route file was checked tick by tick.
- Nothing here was measured in the game.

**Evidence labels.** Sections 2 and 3 were run today on Tom's PC. Section 4 states come from
`SPEC.md` and `HANDOFF.md` as read, plus what was seen in CS2 on Tom's PC earlier today.

Script and raw results are on Tom's PC in `data/audit/` (ignored by git): `audit.py`,
`audit_results.json`. Data: OpenCS2 by Julien Blanchon, CC BY 4.0.
