# donkL in CS2: what ran, what was measured, and what to retrain

Written 2026-11-15 by Tom (with Claude), for Arjun. Everything below was run on Tom's PC (Windows,
CS2 plus CS2-Bot-Improver v1.4.9 in Bot Mode, the game hosting the match). Evidence labels: **ran** =
seen happen, **measured** = a number from a script, **not run** = never tried.

**Delete this file when you have read it:** `git rm handoffs/arjun-donkL-report.md`.

## 1. Summary

- **The converter works.** A route file converted from the pro data makes a T bot walk the real path.
  This was the biggest open question. (section 2)
- **CloneDirector works in the game, once two bugs are fixed.** `donkL` attached to a bot and played
  one of donk's recorded routes. Nothing else of donkL's behaviour has been measured reliably.
- **donkL's performance is unmeasured.** The one measurement I tried (jump rate, standing-still share)
  is confounded and shows nothing. Do not read the numbers in section 5 as a result.
- **What blocks a real score:** there is no recording of a clone match, so `quirks score` has never
  been run on a bot. `-Record tv` is untried.

## 2. Step 1 of your test: a converted route on a T bot: PASS (ran, measured)

File: `clones/donk_v1/routes/T/donk_v1_t_2393226_r13.json.br` (20.0 s, TSpawn to near TRamp, start
(1216, -211), end (-326, -1598)). Played with `css_replay <slot> donk_v1_t_2393226_r13` from the server
side, at the start of a round, on a T bot, with Tom spectating. Position sampled about 1.6 times a second
with `getpos` and compared with the position stored in the file.

| Run | Mean distance from the route file | Movement |
|---|---|---|
| Control, no replay (a normal T bot) | 790 units | wandered 476 units |
| With the replay | 11 units (0 to 1 unit for the first 12 s) | followed the whole route, 1,939 units |

So the converter's guessed fields (`EntityFlags`, `Fields`, `InputHistory`, `Subticks`, `MouseDx/Dy`,
`MoveType`) are good enough for position. Not checked: the bot's view angles, jumps and crouches during
playback, or the CT-side files. Only one file of 159 was tried.

Note: my first attempt reported a pass wrongly: a parsing slip passed the wrong slot, the console printed
`Usage: !replay <slot> [fileName]`, and the bot I watched was simply following its own AI. The control run
above is what shows the difference. Always run a control.

## 3. Step 3: CloneDirector and donkL in the game (ran)

| Check | Result |
|---|---|
| Plugin loads | Yes, after building with .NET SDK 10 against the installed `BotControllerApi.dll` |
| `clone_add donkL t` attaches a bot | Yes. `clone_list`: `slot=1 clone=donkL side=T route=TSpawn > PalaceAlley > TRamp source=recorded reason=segment ended` |
| `clone_add donk_v1 ct` attaches | Yes (log line `Attached donk_v1 to slot 3, personality=donk. Routes start next round.`) |
| Played a route | Yes for donkL (route above); donk_v1 showed `route=none ... reason=purchases set` in the first round |
| Purchases | Not checked (no round with enough money watched) |
| Hand-over to the bot base | `reason=segment ended` seen once. Combat hand-off not checked |
| donkL's jump-rate quirk | **Not confirmed**, see section 5 |

Two bugs had to be fixed first (both are in commits on `main`):

1. **`ConsoleOnly` refused every command from MatchBridge.** On a listen server (Bot Mode: the game hosts
   the match), `Server.ExecuteCommand` commands arrive attributed to the host in slot 0, not null. Fix
   pushed: also accept `player.Slot == 0 && !player.IsBot`. **A security review flagged this** as too wide
   on a dedicated server. Please tighten it (for example also require the caller's `IpAddress` to be the
   loopback address, or have MatchBridge call CloneDirector through a shared capability).
2. **donk_v1 and donkL could not share a match.** Both used the bot entry `donk`, and the game refuses a
   second bot with a name already in use. Renaming after attach (`PlayerName` plus `SetStateChanged`) did
   not stick. The name comes from an entry in `botprofile.db` inside the bot base's `botprofile.vpk`. Fix
   in the repo: `clone-director/tools/add_clone_bot_entries.py` adds `donk_v1`, `donkL`, `broky_v1` and
   `brokyL` entries (copies of donk and broky), and the four clone profiles now set `stand_in_bot` to their
   own id. With that, donk_v1 (CT) vs donkL (T) ran in one match with those names. The original
   `botprofile.vpk` is saved next to the installed one.

Also found: the built-in `broky` entry is `ProSlow+SniperPro+SniperPersonality`, so broky_v1 and brokyL
play as snipers in the bot base, which matches the real broky (10 of 17 held-back kills with the AWP).

## 4. Matches played (all stand-in `Skill=100` bots; results say nothing about player similarity)

| Match | Setup | Result |
|---|---|---|
| `634c7c1419a5` | donk_v1 CT vs donkL T | stopped by hand at CT 3, T 0 (3 rounds) |
| `59a614cf1036` | broky vs donkL | stopped at CT 1, T 0 |
| `2115628439b8` | donk_v1 CT vs donkL T | still live at CT 2, T 2 (round 4) when measured |

A bot-vs-bot win rate is not a performance measure here: both clones use the same base aim and
personality numbers (`Skill = 100`, `aim_skill = 1.0`).

## 5. The one measurement I tried, and why it is not a result

Method: spectate each bot for 70 s in the live match, `getpos` about 10 times a second, count upward
z-jumps over 20 units, share of samples with speed under 10, share at or above 190.

| Bot | Jumps per minute | Standing still | At running speed | Median speed |
|---|---|---|---|---|
| donkL (sampled first) | 8.6 | 41% | 32% | 108 |
| donk_v1 (sampled second) | 14.6 | 29% | 47% | 150 |
| Targets for donk (your `quirks`): jumps 4.1 per minute, still 11%, population mean 1.7 and 20% | | | | |

Do not use these. Problems: donkL was sampled during the first 70 seconds, which include freeze time and
round starts, and donk_v1 afterwards, so the order is confounded; the jump detector also fires on stairs,
ramps and camera switches after a death, so even donk_v1 reads far above any real rate; the sample is one
bot for 70 seconds. The result runs the opposite way to the quirk (donkL should jump more), but the method
cannot support that either. The only usable way to score a bot is a recording and your `quirks score`.

## 6. What to do next (my recommendations, untested)

1. **Get a recording of a clone match.** Run `-Record tv` (GOTV). It has never been tried; the old `record`
   command froze the game and crashed it once. If it works, a `match_<id>.dem` appears in `game\csgo`.
   Then: `uv run python -m clone_pipeline.quirks score --profile ..\clones\donkL.json --demo <dem> --name donkL`
   and the same for donk_v1 (names in the demo are now `donk_v1` and `donkL`). This gives the first real
   score of a bot against your pass rule.
2. **Check what the plugin actually applies.** Today only the jump rate (and Teamwork, if the personality
   file is edited by hand) is applied. The other distinctive quirks (standing still, turning speed, shots
   per burst, flashbang share, distance from teammates) are measured but not applied, so donkL cannot
   reproduce them yet. Pick the quirks most visible from the demo and apply them first.
3. **Routes cover about a quarter of a round** (18 s of about 70 s alive). After the route the generic bot
   plays, so a clone's whole-round behaviour is the bot base's. Quirks applied only during the route phase
   will not move whole-match rates much.
4. **Fix the quirk application order** before scoring: jump injection runs only while the bot is not in a
   fight and no route is playing, so a higher rate cannot show up during routes.
5. **Keep the pass rule fixed** (your constants at the top of `quirks.py`). Do not change it after seeing a
   bot's score.
6. **Retraining the neural model** is a separate step. Your diagnosis note already covers what to change.
   Nothing here tests a neural model: `donkL` is the quirk-rule clone, not the adapters.

## 7. Things that will bite you on this PC

- `gameinfo.gi` lost its `addons/metamod` line once, so no plugin loaded and matches got no bots. Fix:
  copy `game/csgo/backup/WithBots/gameinfo.gi` over it, restart CS2. (`AGENTS.md` section 7.)
- Low memory (CS2 plus a browser leaves under 2 GiB free) got the match service killed twice. Close
  browser tabs before a run.
- The C# tests cannot run here: Windows Application Control blocks the test DLL. The plugin itself builds
  and loads fine.
- Everything runs with anti-cheat off. Never join an online match in this mode.
