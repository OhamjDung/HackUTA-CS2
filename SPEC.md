# CS2 Player Clone: Project Spec (HackUTA 2026)

This file is the team's single source of truth. It says what the project is, how it is built, and
what is done.

**Rule for every person and every coding agent: if you change the project, change this file in the
same commit.** Section 0 says exactly what to update. `AGENTS.md` repeats the rule for agents.

---

## 0. Status board

### 0.1 How to update this file

1. **Before you start work:** read this file. Set your row in the table below to `In progress` and
   put your name on it.
2. **When you commit:** update your row (state, location, date). If you changed how something works,
   also update the section that describes it.
3. **Always:** add one line to the change log in section 19.
4. If the code and this file disagree, say so in your commit or to the team. Do not leave them
   different.

States: `Not started`, `In progress`, `Done`, `Blocked` (say what blocks it).

### 0.2 What is built and what is being built

| Part | Owner | State | Where | Updated |
|---|---|---|---|---|
| MatchBridge Release compilation | Arjun (Codex) | Done. Builds with .NET SDK 10.0.404, zero warnings/errors; targets net8.0. In-game loading and clone commands still untested. | `match-service/plugin/MatchBridge/` | 2026-11-14 |
| Research: which bots, dataset, and model to build on | Arjun | Done | Sections 4, 7, 8 | 2026-11-14 |
| This spec and the agent rules | Arjun | Done | `SPEC.md`, `AGENTS.md`, `CLAUDE.md` | 2026-11-14 |
| Match service, mock version (Server API with a fake CS2 server) | Ashirwad | Done | `match-service/` | 2026-11-14 |
| Match service, real version (starts and controls a real CS2 match) | Ashirwad | In progress. A stand-in Wingman match on Tom's PC finished automatically. At halftime the service inflated the score and emitted six extra `round.ended` events. GOTV and CloneDirector mode still await live checks. | `match-service/match_service/backends/cs2.py` | 2026-11-14 |
| Character showcase viewer (WebGPU hot-swap stage, 5 blockouts, B1-B3) | Nikesh | Done. B1-B3 verified in headless-Chromium GPU QA: real WebGPU backend, initial model ~20ms, 5/5 GLBs cached, clean swaps, zero console errors | `frontend/` | 2026-11-14 |
| Character showcase: auto-cycle loop + AnimationMixer fallback (B4) | Nikesh | Done. Full 5-model auto-loop verified live (CS2→Smash→Fortnite→FIFA→Halo→CS2), pause freeze + manual override verified, mixer path unit-verified, 0 errors, 0 refetches | `frontend/` | 2026-11-14 |
| Character showcase: chromatic lighting/HUD sync + GLB gatekeeper | Nikesh | Done. Per-character rim/accent verified live (artist FIFA rig renders through mixer path, 0 errors); `verify-models.mjs`: 5/5 PASS (Idle clip, skins, meshopt, 0.31MB/10MB) | `frontend/` | 2026-11-14 |
| 3D Character Glitch-Swap Showcase (Nodes A1-A5, B1-B4, C1-C2) | Nikesh | COMPLETE & VERIFIED. Artist KTX2+Meshopt rigs integrated (5/5 gatekeeper PASS, 0.31MB); 5-character live sweep: mixer path, 1.85m framing, chromatic rim/HUD, KTX transcode clean, 0 errors, 0 refetches | `frontend/`, `frontend/scripts/chargen/` | 2026-11-14 |
| Stand-in bots: built-in CS2-Bot-Improver pro bots used in place of clones until CloneDirector works | Ashirwad | In progress. `donk_v1` and `broky_v1` profiles use the `donk` and `broky` bots; not run in CS2 | `match-service/sample_clones/` | 2026-11-14 |
| In-game similarity score: a bot's rounds in CS2 against the real player's held-back match (section 10.2) | Ashirwad | In progress. Scorer, map-area lookup and both held-back references written and tested; served as `GET /matches/{id}/score` and shown on the proof page (run against the mock in a browser); no real CS2 trace scored yet | `clone-pipeline/clone_pipeline/ingame.py`, `clone-pipeline/references/`, `match-service/match_service/scoring.py` | 2026-11-14 |
| Side-by-side page, stand-in version (two synced panels; replay page content replaces it) | Ashirwad (live check by Codex) | In progress. Both live map panels drew bot positions from CS2. Replay played the donk stand-in and a recorded pro donk opening on one clock. The event list showed the service's halftime scoring error. | `match-service/demo/`, `match-service/match_service/replay.py` | 2026-11-14 |
| Demo pages wired to the real CS2 bots, with a seam for learned models | Tom (with Claude) | Done for stand-in bots. With `start-cs2.ps1 -Open`, every demo page was loaded in a browser against a real CS2 match (donk vs broky, 9-4 in 13 rounds, ended by itself) and the Play page started a match with the player on CT. `GET /clones` reports each clone's driver and whether it is playable; `CS2_CLONE_ROUTES=generated` is the hook for a trained model's routes. CloneDirector and generated routes not run in CS2 | `match-service/match_service/drivers.py`, `match-service/demo/`, `match-service/start-cs2.ps1` | 2026-11-14 |
| Lobby page | Tom (named in `match-service/README.md`) | Unknown. Owner: please update. | Not in the repo yet | 2026-11-14 |
| Match page | Nikesh (named in `match-service/README.md`) | Unknown. Owner: please update. | Not in the repo yet | 2026-11-14 |
| CS2 with the bot base installed on the demo laptop | Tom | Done. CS2-Bot-Improver v1.4.9 runs in Bot Mode on Tom's PC. A donk-vs-broky stand-in match on Mirage plays and its score counts through `/gsi`. The bot base's `!record`/`!replay` replays a recorded walk, and a converted donk route file loads and moves a bot; whether it runs the right route is not confirmed. CloneDirector is not installed there yet. | Tom's PC (the demo machine) | 2026-11-14 |
| CS2 base game download on Arjun's current PC | Arjun (Codex) | Done. Steam manifest confirms complete download/staging, update result 0, 74.3 GB installed. Bot base not installed by this agent. | Steam default library on C: | 2026-11-14 |
| Clone pipeline: recording in, clone profile out | Arjun (Codex) | Done. 10 tests pass; purchase order corrected in both clones. | `clone-pipeline/`, `HANDOFF.md` | 2026-11-14 |
| donk clone (`donk_v1`): profile, purchases, grenades, 80 route files | Arjun | Done. Built from 4 matches, 80 rounds. | `clones/` | 2026-11-14 |
| broky clone (`broky_v1`): data-built profile and routes | Arjun (Codex) | Done. Built from 4 matches, 79 rounds/routes; held back 22 rounds. Files load in C#; not run in game. | `clones/broky_v1.json`, `clones/README.md` | 2026-11-14 |
| Route converter: recording data to the bot playback format | Arjun | In progress. Files are written. **Not tested in the game.** Several field values are guesses (`HANDOFF.md` section 5.1). | `clone-pipeline/clone_pipeline/recording.py` | 2026-11-14 |
| CloneDirector plugin: applies a clone to a bot inside CS2 | Arjun (Codex) | In progress. Compiles; 26 C# tests pass, including all 159 donk/broky files. Not run in CS2. | `clone-director/` | 2026-11-14 |
| Generating model: CS-NET v4 plus player identity | Arjun (Codex) | In progress. First A100 experiment trained 600 updates, selected step 400; both held-out identity tests failed. Experimental checkpoints/results preserved; offline review export verified, identity fidelity not established. | `clone-model/` | 2026-11-14 |
| Learned-quirk clones `donkL` and `brokyL`: per-quirk rules fitted from recordings | Arjun (Claude) | Done as files and code; **not run in CS2**. 27 quirks measured, 10 distinctive per player. Jump rate applied by CloneDirector; Teamwork needs a manual personality-file edit; other quirks measured only. 23 pipeline tests and 28 C# tests pass. **Teammates: please add `donkL` and `brokyL` next to `donk_v1` and `broky_v1` so we can compare** (`clones/README.md`). | `clone-pipeline/clone_pipeline/quirks.py`, `clones/donkL.json`, `clones/brokyL.json`, `clone-director/` | 2026-11-14 |
| Quirk test ("who is it?" plus per-quirk checks), looser than the first identity test | Arjun (Claude) | Done. Rule fixed before scoring. Real players pass on their own held-back matches: donk 1st of 5 and 8 of 10 quirks, broky 1st of 5 and 9 of 10. No bot match or model output scored yet. | `clone-pipeline/clone_pipeline/quirks.py`, section 8.8 | 2026-11-14 |
| Diagnosis of the failed neural identity model | Arjun (Claude) | Done. Adapters judged not usable: no change in 64% to 72% of test windows. Not offered as bots. | `clone-model/results/diagnosis-2026-11-14.md` | 2026-11-14 |
| Offline weapon-role and habit audit handoff | Arjun's friend (handoff prepared) | Not started. CPU-only audit/fix handoff ready; recipient must remove consumed handoff docs on task branch after reading. | `handoffs/friend/01-HABIT-AUDIT-AND-FIX.md` | 2026-11-14 |
| Independent mock replay QA handoff | Arjun's friend (optional second task) | Not started. Existing Ashirwad replay implementation remains with its owner; QA/report only. | `handoffs/friend/02-MOCK-REPLAY-QA.md` | 2026-11-14 |
| Claude continuation handoff | Arjun (Codex) | Done and consumed. Claude read it on 2026-11-14 and removed the folder, as its own instructions said. | removed (`handoffs/claude-continuation/`) | 2026-11-14 |
| Continuation handoff (Arjun's remaining model and game work) | Ashirwad | In progress. Handoff read and its context saved outside the repo; folder removed. Tasks: map-geometry review of generated paths, generated-path viewer, generated-route converter (candidates only), adapter diagnosis, CS2 checklist for Tom. | Removed from the repo | 2026-11-14 |
| Offline generated-path review export | Arjun (Codex) | Done. Eight development cases exported on A100 (24 generated paths plus real paths), JSON checked and plots inspected; 12 CPU tests pass. No route promotion. | `clone-model/review.py` | 2026-11-14 |
| Replay page: real player next to clone | Unassigned | In progress (demo version by Ashirwad: 2D map from positions, no video, no generated path) | `match-service/demo/replay.html` | 2026-11-14 |
| Clone profile page | Unassigned | Not started | Not decided | 2026-11-14 |
| Caster voice (Gemini script, ElevenLabs audio) | Unassigned | Not started | Not decided | 2026-11-14 |
| Pro bot voices: donk and broky (ElevenLabs) | Unassigned (research by Codex) | In progress. MVP targets verified voice packs for `donk_v1` and `broky_v1`. Player authorization, verified voices, and playback tests pending. | Section 9.5 | 2026-11-14 |
| Similarity search (MongoDB Atlas) | Unassigned | Not started | Not decided | 2026-11-14 |
| Hosting on Vultr, domain from GoDaddy Registry | Unassigned | Not started | Not decided | 2026-11-14 |
| DEV article | Unassigned | Not started | Not decided | 2026-11-14 |

### 0.3 Things this spec does not know yet

- **The team's "Interface specs doc".** `match-service/` refers to it: section 1 for the clone
  profile format and section 2 for the Server API. It is not in this repository, and the author of
  this spec has not read it. Where this spec touches those two topics, it follows the code in
  `match-service/`. If the doc says something different, the doc's owner decides, and this file must
  be corrected.
- **Who owns each unassigned row above.**

---

## 1. What the project does

The project takes recordings of one person's Counter-Strike 2 (CS2) matches and produces a bot that
plays with that person's habits. The bot runs inside a real CS2 match on a private machine.

A **clone** in this file means: an existing CS2 bot whose routes, purchases, grenade throws, and
reaction numbers are set from one real player's recorded matches.

The project does not build a bot from zero. It combines existing open-source projects and adds the
missing link: recording in, clone out.

**Team rule: every feature and sub-feature starts from the closest existing open-source
implementation.** Find it, judge it, name it in section 4, then build on it. Write new code from zero
only when no usable base exists, and say so here.

## 2. Decisions

### 2.1 Decided by Arjun in the planning interview (2026-11-14)

| Topic | Decision |
|---|---|
| Time | 12 to 24 hours of build time. |
| Team | 4 people. All write code with AI agents, so language skill is not a limit. |
| Machines | CS2 runs on one Windows gaming laptop. Colab Pro is available for training. |
| Proof at judging | First: a side-by-side replay of one round, real player next to clone. Second, if time allows: a match of clone against clone. |
| Approach | Hybrid. A working demo comes first. The core design must support reliable cloning of any person from their recordings. |
| Generating model | **In the build, not a later step.** Section 8 defines it. |
| Demo movement | The clone's movement inside the game is made to work by hand for the demo. The demo must not depend on the model running live. |
| Input | One or more match recording files (`.dem`) per person. |
| Data source | OpenCS2, a public dataset of professional CS2 matches. |
| Who to clone | donk first. Then one FaZe Clan player. |
| Map | Mirage (`de_mirage`) only. |
| Clone strength | Always the real player's true level. No difficulty slider. |
| Voice | A spoken caster on the replay page. |
| Sponsor products | Gemini, MongoDB Atlas, ElevenLabs, Vultr, GoDaddy Registry, DEV article, FaZe prize. Not Tiger Data, Solana, or Chert. |
| Cloning users while they play | Wanted in the design. Low priority, because it cannot be shown at judging. |
| How it earns money | Not decided. |
| Product polish | Low priority. Working clones matter more. |

### 2.2 Decided by the spec's author. Any teammate can overrule.

1. **A clone has three layers:** habits, routes, and skill numbers (section 5).
2. **The second clone is broky.** He is FaZe's sniper. A sniper holds fixed positions, so his clone
   looks clearly different from donk's on a map.
3. **One data path.** Professional recordings and a user's own recordings pass through the same code.
4. **The model's proof is an offline test** (section 8.6), not a live match.

## 3. What is checked and what is not

Checked on 2026-11-14.

**Checked by running a query or request:**
- The match service in CS2 (Tom, Bot Mode on Windows, 2026-11-14): netcon commands reach the game
  (`/health` reachable), game state arrives at `/gsi`, and a wingman donk-vs-broky match loaded
  `de_mirage`, added both bots, set the team names, and went `ready` then `live`. **Failed in the
  same run:** the score stayed 0-0 (game state stuck at round 0, freeze time, while CS2 reset rounds
  about every 30 s), `status` counted both bots as humans, and `record` made no `.dem` file. The
  service went `live` 0.2 s after `ready` because Bot Mode already reported `live`; fixed (below).
- Bot base install and the `record` fault (Tom, same PC, 2026-11-14). CS2-Bot-Improver v1.4.9 was
  copied into `game/csgo` and started from its launcher in Bot Mode (`-insecure`); bots play a
  normal practice match. `start-cs2.ps1` ran on Windows: it found CS2, installed the game state
  config and started the service. **Cause of the 0-0 score found:** every run that sent `record`
  over netcon printed `Prediction time (7.16) is less than sim time (...)? Clamping offset` without
  stopping. The client clock froze about 7 s after the map loaded while the server kept running, so
  game state stayed at round 0 and freeze time, and the bots looked frozen on screen. Sent by hand,
  `record test1` crashed CS2 (`cs2_2026_1114_201951_0_accessviolation.mdmp`). The same command
  sequence after a fresh `map de_mirage`, without `record`, gave no warning, and Tom saw donk and
  broky move and fight. A frozen client stays frozen until the map reloads. The restart fix
  (`mp_warmup_end`, `mp_restartgame 1`) did not change the result while `record` was still sent.
  Also seen once: `bot_add_ct "donk"` straight after `bot_kick` added bots named chelo and SELLTER.
- Clone files against the players' held-back matches (Tom, 2026-11-14; full report in
  `CLONE_AUDIT.md`). Each clone's `stats.json` was compared with every player in its held-back
  match. Among the target and his four teammates, the target scored highest in 5 of 8 tests
  (position and route overlap, per side, both clones) and second in the other 3. Misses: donk T
  (5 rounds) and broky CT routes. T-side position overlap does not separate donk from broky. Real
  broky made 10 of 17 held-back kills with the AWP; `broky_v1`'s full buy is an AK-47 or M4A4.
  Routes average 18.5 s against about 70 s alive per round. One route file matched its recording
  on every tick. No bot was measured: this is a file-level check.
- Playback and scores on Tom's PC (2026-11-14, after Ash's change to stop sending `record`).
  Wingman donk_v1 (CT) vs broky_v1 (T) on `de_mirage` went `ready` then `live`, and
  `GET /matches/<id>` showed CT 1, T 0, round 1. The bot base's chat commands work: `!record test` then
  `!stoprecord` saved 962 ticks and `!replay 1 test` made a bot walk the recorded path. A converted
  file, `!replay <slot> donk_v1_t_2393226_r13`, loads and moves the bot; on a CT bot it walked into a
  wall, as a T-side route played from CT spawn would. The real recording differs from the converter's
  files in `EntityFlags` (65665 vs 1), `Commands[].Fields` (24-59 vs 0), `InputHistory` (about 157k
  characters vs empty), `Subticks` (22 vs none), `MouseDx/Dy` and `MoveType`. The bot base saves its
  recordings in `game/csgo/addons/counterstrikesharp/plugins/BotControllerImpl/recordings/`. When
  the match ended or restarted, the bot base's fill bots (tomiko, swerzieN) replaced donk and broky;
  cause not found.
- Halftime score fix (Ashirwad, 2026-11-14): a test replays Tom's match 09a357d5a255 sequence (7-1,
  then an update with names swapped but not scores, then both swapped). The old code gives 7-7; the
  fixed code keeps 7-1 and ends 9-2 with 11 `round.ended` events. Also with the scores swapping
  first. Against fake game state only; not yet rerun in CS2. 49 match service tests pass.
- In-game similarity scorer (Ashirwad, 2026-11-14), on the two held-back recordings (2393242,
  2393024) downloaded from OpenCS2. The map-area lookup built from broky's match names the area of
  93.3% of the positions in donk's match correctly (92.6% without height), so x and y are enough.
  The references rebuilt from those matches reproduce both profiles' `player_vs_self` numbers
  exactly. A stand-in "bot" replaying each clone's own route files beats one replaying the other
  clone's routes on route overlap on every side for both players, and on position overlap except
  broky's T side (the same blind spot as the audit). This is a perfect-playback check on the files,
  not a bot in CS2. `clone-pipeline/tests/test_ingame.py`; 16 pipeline tests pass.
- In-game score endpoint and proof page (Ashirwad, 2026-11-14). `GET /matches/{id}/score?player=`
  scores a mock match and a saved game-state trace in tests (51 match service and 17 pipeline
  tests pass). In a browser against the mock, the proof page filled the clone column from a mock match (donk CT:
  position 59%, route 38%, against a ceiling of 79% / 57%; marked mock) and showed an error for a
  missing match id. Mock matches walk real routes, so these are not results.
- Live demo on Tom's PC (2026-11-14, match `09a357d5a255`). Restarted CS2 with the updated
  game state config and ran donk (CT) vs broky (T) stand-in bots on Mirage in Wingman with
  recording off. Both live map panels rendered changing bot positions from `/gsi`. The Events
  feed showed `round.ended` from round one. After eight rounds at 7–1, the bots swapped sides
  and the service reported 7–7, emitting six extra `round.ended` events in one update. The
  radar trace still followed the game's round number. CS2 finished automatically with nine
  wins for donk's team after ten traced rounds. The service emitted `match.ended` with reason
  `finished`, reported 9–7 and showed 16 `round.ended` events. Replay played donk's stand-in
  round 1 alongside pro donk's match 2393232 round 5 on a shared clock. The replay used position
  data from CS2 and from the pro recording.
- Demo pages and trace checks on Tom's PC (2026-11-14, match `f1ac03b4bbb5`, donk CT vs broky T,
  stand-in bots, recording off, Tom's PC in spectator, started from the service with
  `start-cs2.ps1 -Record off -Open`). Final score CT 9, T 4. The score went past halftime without
  a jump, and the 13 `round.ended` events equal the 13 rounds played. `GET /matches/<id>/trace` has 13
  rounds with a path for each of the two bots (34 to 239 samples per round), and the trace was saved to
  `data/traces/f1ac03b4bbb5.json` (git-ignored). In a browser, with no console errors: Bot vs bot (two
  live panels, final score, end event), Replay (all three tabs; the real-vs-bot clock advanced from 0 to
  9.9 s), Proof (in-game scores from this match, placed under Default bot) and Play (match went live,
  player put on CT). The older trace of match `09a357d5a255` is gone: the service restarted and
  `GET /matches/09a357d5a255/trace` returns 404.
- Every GitHub repository in section 4 exists. Stars, licenses, and update dates come from GitHub.
- The OpenCS2 counts in section 7 come from queries against its index tables.
- The match service's cs2 backend, against a fake console and hand-written game state updates
  (`match-service/tests/test_cs2.py`, 10 tests, all pass). This checks the service's logic only.
- The RCON and MatchBridge console channels, against fake servers that speak the same protocols
  (`match-service/tests/test_channels.py`, 5 tests, all pass). This checks the Python side only.
- Console safety: every channel refuses commands with a newline or `;` before connecting, and
  profiles with an unsafe `stand_in_bot` are skipped (`match-service/tests/test_safety.py`, 6
  tests). Clone mode against a fake game, CloneDirector and MatchBridge, using the real
  `clones/` profiles (`match-service/tests/test_clones.py`, 7 tests). Replay data: real recorded
  rounds read from `clones/`, traces from game state and from the mock, the closest-round match,
  and the demo pages being served (`match-service/tests/test_replay.py`, 5 tests). All 47 match
  service tests pass. The demo pages ran in a browser against the mock (Ashirwad's Mac): bot vs
  bot panels, play vs a bot, all three replay tabs and the proof page. Tom ran the 26 earlier tests on Windows: they pass with
  `uv run python -m pytest` (Application Control blocks `uv run pytest` there).

- CloneDirector Release build with .NET SDK 10.0.404 and CounterStrikeSharp.API 1.0.378:
  zero warnings/errors. The reference contract was built from CS2-Bot-Controller source revision
  `465fc0e3b0f663f08de935fc1dd069b34aa3f987`; the game machine must use its matching release DLL.
- CloneDirector: 26 C# tests pass (`clone-director/Tests/`). Includes weighted route labels,
  nearest-spawn choice, side/source/buy-type filters, purchases, hand-off state, corrupt file
  rejection, and reading both real profiles plus all 159 generated route files. No CS2 native
  library or bot behavior was run by these tests.
- Re-ran the clone pipeline's 10 synthetic tests; all pass, including purchase priority. Claude's local pipeline and donk clone
  were recovered from a checkout stopped during a rebase. Both teammates' change-log entries
  were retained and the checkout was updated to current main.
- Built broky from four real recordings (79 rounds/routes), reserving match 2393024 (22 rounds).
  Confirmed both profiles load in the match-service catalogue and both holdouts are excluded from
  building matches. Re-ran all 32 match-service tests; all pass (one dependency deprecation warning).
- The character showcase viewer (`frontend/`): `tsc --noEmit` and `next build` clean, plus
  headless-Chromium QA against `next start`. WebGPURenderer initialized the real WebGPU backend,
  all 5 blockout GLBs served and parsed, and manual hot-swaps render through the TSL glitch
  pipeline with zero console errors. Initial model painted in ~20 ms on localhost.

- Re-ran current suites on Windows: 10 pipeline, 26 CloneDirector, and 33 match-service tests pass (69 total). The service has one dependency deprecation warning. This includes reading both clone profiles and all 159 route files.
- Started the CS2 base-game download in the existing Steam client on Arjun's current PC after confirming no running download or CS2 manifest. Observed active transfer at 6%, 3.3 / 57.6 GB downloaded, with Steam estimating about 33 minutes remaining. This is a progress snapshot, not an installation or in-game test. No CS2-Bot-Improver files were installed or run.

- MatchBridge Release compilation ran on Windows with .NET SDK 10.0.404: zero warnings, zero errors. The existing project targets net8.0 and CounterStrikeSharp.API 1.0.367; no C# changes were needed. Re-ran all 42 service tests, including seven clone-mode tests against fakes; all pass. This does not verify loading the plugin or clone playback in CS2.

- CS2 base-game download completed on Arjun's PC: Steam manifest reports all download/staging bytes complete, state 4, update result 0, 74.3 GB installed. No bot-base installer was run by this agent.
- Learned movement: A100-SXM4-80GB optimization completed 600 updates, selected step 400; final held-out identity comparison ran 213 predictions across 71 windows and failed for both players (section 8.6). Twelve CPU integration tests pass. Eight development examples were then exported on the A100 and plotted for review; no model or route was promoted.

**Checked by reading source or documentation, not by running:**
- What each open-source project can do (section 4).
- The calls in the CS2-Bot-Controller programming interface (section 6).
- CS-NET v4's inputs, outputs, and training settings (section 8).
- The match service in this repository (section 9.2).
- CS2-Bot-Improver ships pro bots named `donk` and `broky` (`overrides/Medium/botprofile.db`), and
  its `Commands.txt` adds them with `bot_add_ct "<name>"` / `bot_add_t "<name>"`.
- CS2 Game State Integration field names (`map.phase`, `map.team_ct.score`, `round.win_team`), from
  the CounterStrike2GSI and cs2-gsi library docs.

**Not fully checked:**
- Correct-side full-path fidelity and CloneDirector-driven playback inside CS2. A converted T-side file loaded and moved a CT bot in Tom's manual check, but hit a wall from the wrong spawn.
- Adding a custom entry to the bot personality file.
- Every time estimate in section 11.
- Sending console commands to CS2 through RCON (`-usercon`, `rcon_password`) or the MatchBridge
  plugin. Not needed while netcon works.
- Correct Wingman score and `round.ended` counts across the side swap. The live match ended
  automatically, but the service overcounted rounds (see above).
- Whether a converted route file (`donk_v1_t_2393226_r13`) makes a T-side bot run donk's real path.
  It loads and the bot moves; the path was not checked.
- Whether CS2 sends bot positions to the service when the local player joins a team instead of
  spectating. Positions arrived in the bot-vs-bot spectator run.
- Why `bot_add_ct "donk"` once added other bots straight after `bot_kick`.
- Scoring the bot positions collected in a real CS2 match against the held-back reference.
- CounterStrikeSharp loading MatchBridge, `Server.NextFrame` running
  the commands, and `matchbridge_jointeam` moving the player.
- `tv_record` / `tv_stoprecord` recording a Bot Mode game (`CS2_RECORD=tv`).
- Clone mode in CS2: MatchBridge's `matchbridge_bots`, CloneDirector accepting `clone_add` from
  MatchBridge (it refuses a player's console, so not from netcon), and the clone bots joining.
- What CS2 sends to `/gsi` on a map change. (Game state does arrive; see above.)
- `jointeam` behaving as the service expects. (`mp_teamname_1`/`_2` and `bot_add_ct "<name>"`
  worked in Tom's run.)
- Recording a bot match to a `.dem` file on the laptop and serving it at `demo_url`. In Tom's run
  `record` was accepted but no file appeared.

When you run one of these, move it up and record the result here.

## 4. The parts and their starting points

### 4.1 Open-source projects in use

| Project | What it gives | What was confirmed | License |
|---|---|---|---|
| [CS2-Bot-Improver](https://github.com/ed0ard/CS2-Bot-Improver) | Bots that play full matches: aim, movement, team strategy, purchases. | 1,367 stars. Updated 2026-11-14. Installs on a normal Windows copy of CS2. | AGPL-3.0. Its launcher (`Panel/`) is PolyForm Strict. |
| [CS2-Bot-Controller](https://github.com/XBribo/CS2-Bot-Controller) | Code control of one bot. Records a human's movement and plays it back on a bot. | 29 stars. Updated 2026-11-13. Already included in CS2-Bot-Improver. | AGPL-3.0 |
| [CS2-Bot-NadeSystem](https://github.com/ed0ard/CS2-Bot-NadeSystem) | Grenade throws from recorded throws, one data file per map and grenade type. | Already included in CS2-Bot-Improver. Mirage files exist. | AGPL-3.0 |
| [CS2-Smarter-Bot](https://github.com/ed0ard/CS2-Smarter-Bot) | Fixes for stuck bots. Its C# source is an example of a plugin built on CS2-Bot-Controller. | Already included in CS2-Bot-Improver. | AGPL-3.0 |
| [demoparser2](https://github.com/LaihoE/demoparser) | Reads a match recording into tables. | 746 stars. Updated 2026-11-12. | MIT |
| [CS-NET v4](https://github.com/Gary2005/cs-net) | A trained network that generates player movement. Also a 3D replay viewer that draws a predicted path over the real path. | 113 stars. Trained weights are downloadable (529 MB). Mirage map geometry is included. | MIT |
| [CS2 Clone Lab](https://github.com/hpagni/cs2-clone-lab) | Code for per-player identity in a model (`sim/identity.py`). | 0 stars. No weights and no data, but the identity code is small and self-contained. | MIT |
| [cs2-movesim](https://github.com/370025263/cs2-movesim) | Turns a planned path into key presses. | 0 stars. Tested by its author on the Dust2 map only. | MIT |
| [Next.js](https://github.com/vercel/next.js) | Web framework for the character showcase viewer. | 16.4.6, installed from npm. | MIT |
| [three.js](https://github.com/mrdoob/three.js) | WebGPU renderer (r187: WebGPURenderer, RenderPipeline, TSL) for the viewer. | 0.187.0, installed from npm. | MIT |
| [React Three Fiber](https://github.com/pmndrs/react-three-fiber) | React renderer for the viewer's Three.js scene graph. | 9.8.2, installed from npm. | MIT |

One install of CS2-Bot-Improver gives the first four rows.

### 4.2 Starting point for each feature

| Feature or sub-feature | Starts from |
|---|---|
| Bots that play a match | CS2-Bot-Improver |
| Recording and playing back movement on a bot | CS2-Bot-Controller |
| The playback file format | CS2-Bot-Controller's own recorder source (`csharp/BotControllerImpl/MotionRecording.cs`) |
| Purchase execution order | CS2-Bot-Controller's `src/features/buy/BuyController.cpp` (AGPL-3.0-only), which issues aliases in sequence; the pipeline now orders main weapon, armor, then other items |
| CloneDirector plugin skeleton | CS2-Smarter-Bot's source, and the code samples in CS2-Bot-Controller's `TECH.md` |
| Grenade throws | CS2-Bot-NadeSystem and its Mirage data files |
| Reading recordings | demoparser2 |
| Generating model: network and trained weights | CS-NET v4 |
| Generating model: player identity | CS2 Clone Lab, `sim/identity.py` |
| Generating model: reading recordings into its training format | CS-NET v4's own parser (`demo_parser/`) and data scripts |
| Model test numbers | CS-NET v4's `scripts/evaluate_pretrain.py` |
| Replay page | CS-NET v4's viewer (`visualizer/`) |
| Per-bot voice | Existing match/replay events, [ElevenLabs synthesis API](https://elevenlabs.io/docs/overview/capabilities/text-to-speech) (hosted service), then CS2-Bot-Controller's voice API (AGPL-3.0) for optional game audio. Use [Xiph libopus](https://opus-codec.org/license/) (BSD-3-Clause) to encode game packets offline. |
| Path to key presses (after the hackathon) | cs2-movesim |
| Match control API | This repository's `match-service/` |
| Match service: events from the game | CS2's Game State Integration (Valve). Field names from the [CounterStrike2GSI](https://github.com/antonpup/CounterStrike2GSI) README; read only, no code copied |
| Match service: commands to the game | CS2's network console (`-netconport`). Idea from [csctl](https://github.com/403-Fruit/csctl) (CS:GO); read only. The client is written from zero: about 40 lines, no CS2 client found |
| In-game similarity score | The pipeline's own `similarity.compare()` and `build.stats_block()`; area names are CS2's `last_place_name` from OpenCS2 recordings, looked up by position. Scorer written from zero: no tool found that scores game-state traces |
| Match service: commands to the game, fallback 1 | RCON through the [rcon](https://pypi.org/project/rcon/) Python library (GPL-3.0), used as a dependency |
| Match service: commands to the game, fallback 2 | MatchBridge, a CounterStrikeSharp plugin (`match-service/plugin/MatchBridge/`). Written from zero: no plugin found that runs console commands sent over a local port (LeaderOS Connect, the closest, runs store purchases). Project settings copied from CS2-Bot-Improver's own plugins; calls from the CounterStrikeSharp docs |
| Stand-in bots | CS2-Bot-Improver's pro bot profiles and the `bot_add_ct "<name>"` blocks in its `Commands.txt` |
| Style numbers for every professional | OpenCS2's ready-made index tables |
| Character showcase viewer (5-model WebGPU hot-swap stage) | Written from zero: no template base exists for this design, and the architecture is prescribed by `frontend/AGENTS.md`. Frameworks: Next.js, three.js, React Three Fiber (all MIT, section 4.1) |

### 4.3 Rejected

- **CQ-AVATAR dataset.** 37 GB. Positions are rescaled, so real map positions cannot be read. No key
  presses, no enemy positions, professionals only.
- **Priler/csgobot and nagorixs0/CS2-AI-Bot.** They read the screen to aim. They do not play a match.
- **AtakanDelikan/cs2-imitation-learning.** It reads the game's memory from outside, which is the
  method cheats use. Deathmatch only.

## 5. What a clone is made of

### 5.1 Layer 1: habits

| Habit | Measured from recordings as | Applied to the bot through |
|---|---|---|
| Weapon choice | How often the player buys each weapon | The weapon preference list in the bot personality file (`botprofile.db`) |
| Purchases | What the player buys at each money level | The per-bot purchase call (`SetBuyPlan`) |
| Aggression | How early the player meets an enemy, and how often the player takes the round's first fight | The `Aggression` number in the personality file |
| Teamwork | Average distance to the nearest teammate | The `Teamwork` number in the personality file |
| Grenades | Position, view direction, and type of each throw | The grenade plugin's data files |

The bot personality file is a text file. Each bot entry holds skill, aggression, reaction time,
attack delay, teamwork, and a weapon preference list.

**Caution.** The rule that turns a measured value into a personality number is a design choice.
Nobody has validated it. Section 10 measures whether it works.

Current purchase plans choose item membership by frequency, then order the main weapon and armor
before utility. The controller executes buys sequentially; putting frequent grenades first could
leave no money for the gun. Both built profiles and their `buy_plan.json` files were updated
without changing item membership, measured frequencies, or the profile format.

Weapon preferences currently count shots, which favors automatic weapons. The single full-buy
plan favors AK-47 on T and M4A4 on CT for both clones; broky's AWP use is in the data but its full
purchase mix is not reproduced. This is a limit of the current habit model, not proof that the
players have identical roles. `clones/README.md` records current evidence and limits.

### 5.2 Layer 2: routes

A **route segment** is a stretch of movement from the moment a round goes live until the first of
these: the player meets an enemy, 20 seconds pass, or the player dies.

Each segment stores, for every tick: position, velocity, view direction, and keys held. A **tick** is
one step of the game simulation. CS2 runs 64 ticks per second.

A segment has one of two sources:
- **Recorded.** Cut from the real player's match recording.
- **Generated.** Written by the generating model (section 8) and checked by a person before use.

Each segment has a label: the sequence of named map areas it passes through, for example
`TSpawn > Palace > A Site`. demoparser2 gives the area name for each tick.

### 5.3 Layer 3: skill numbers

The decision is "always true level". So the clone uses:
- `Skill = 100`, the value CS2-Bot-Improver already gives professional bots.
- `ReactionTime` and `AttackDelay` from the player's measured values where the recordings allow a
  measurement, and the CS2-Bot-Improver professional default otherwise.

Measuring reaction time needs the moment an enemy became visible. Recordings give this only roughly.
Treat the measured value as an estimate.

**Current limit:** reaction time is actually `null` in both built profiles, and `aim_skill=1` /
`Skill=100` are maximum base-bot settings, not measured player ratings. The true-level goal in
section 2.1 is unproven. After the opening route, the existing bot AI makes decisions; no
player-specific combat model has been trained or evaluated. A movement identity adapter was trained and tested offline, but both identities failed (section 8.6).

### 5.4 The clone profile file

`match-service/sample_clones/*.json` already defines these fields. This spec keeps them:

| Field | Meaning | Filled from |
|---|---|---|
| `clone_id` | Short unique name | Chosen at build time |
| `display_name` | Name shown in the lobby | The player's name |
| `source` | `"user"` or `"pro"` | Where the recordings came from |
| `reaction_ms` | Reaction time in milliseconds | Layer 3 |
| `aim_skill` | 0 to 1 | Layer 3 |
| `aggression` | 0 to 1 | Layer 1 |
| `weapons` | Preferred weapons, most used first | Layer 1 |
| `positions` | Where the player spends time | Share of time per named map area, per side |
| `model` | The generating model for this clone, or `null` | Section 8: the base model's name and the path to this player's identity vector |

**Proposed new fields.** These are proposals. The owner of the Interface specs doc decides.

| Field | Meaning |
|---|---|
| `buy_plan` | Purchase list per money level |
| `routes` | Route labels per side, each with how often the player took it and its segment files |
| `nades` | Paths to this clone's grenade data files |
| `source_games` | Which recordings the clone was built from |
| `similarity` | The scores from section 10 |
| `stand_in_bot` | Name of a built-in CS2-Bot-Improver bot that plays this clone until CloneDirector works. Removed once `clone_add` is in use. |

Large files (route segments, grenade data, model weights) stay outside the profile. The profile
holds paths to them.

## 6. How a clone drives a bot

### 6.1 What the bot interface allows

Read from the interface source (`IBotControllerApi.cs`):

| Control | Interface call |
|---|---|
| Pause the bot's own decisions | `Lock` |
| Load a movement recording and play it | `LoadReplay`, `StartReplay`, `StopReplay` |
| Record a player's movement | `StartRecord`, `StopRecord`, `GetRecordedMotionExtended` |
| Press keys for the bot | `InjectUsercmd` |
| Steer the bot forward, back, left, right | `StartUsercmdMovement` |
| Set what the bot buys | `SetBuyPlan` |
| Read the bot's personality numbers | `GetBotProfile` |
| Send audio as the bot's voice | `SendVoiceFrame` |

**The limit that shapes the design.** No call sets the bot's view direction on a live tick. Code can
freeze the view or play back a recorded view. So movement reaches a bot as a playback file, whether
a person or a model made it.

### 6.2 The round, step by step

A small C# program inside CS2 (the **CloneDirector** plugin) does this for each clone bot. It is
built on CounterStrikeSharp, the C# plugin framework that CS2-Bot-Improver installs.

1. **Round starts.** The plugin reads the bot's side, money, and spawn point.
2. **Purchase.** The plugin picks the purchase list for that money level and calls `SetBuyPlan`.
3. **Route choice.** The plugin picks a route label at random, weighted by how often the real player
   took each route on that side at that money level. It then picks the segment of that label whose
   start is nearest to the bot's spawn point.
4. **Playback.** When the round goes live, the plugin calls `LoadReplay` and `StartReplay`.
5. **Hand-off.** The plugin calls `StopReplay` when the segment ends, when the bot takes damage, or
   when an enemy fires nearby. CS2-Bot-Improver's own logic then fights and plays the objective,
   using the clone's personality numbers.
6. **Round ends.** The plugin writes a log line: clone, route label, segment source, hand-off reason.

**Implementation as of 2026-11-14:** `clone-director/` builds these steps, but has not run in CS2.
It reads the pipeline's existing `buy_plan[side][type].aliases`, `routes[side]`, and `route_shares`.
Route paths are relative to the clones folder; `route_key`, `file`, `source`, `buy_type`, and
`start` come directly from the pipeline. No match-service endpoint or existing profile field
was changed. Deployment and the manual playback gate are in `clone-director/README.md`.

Pistol rounds use the first round and `mp_maxrounds / 2`; otherwise money below $2,000 means eco,
$2,000-3,999 force, and $4,000 or more full. These are unvalidated approximations of the pipeline's
equipment-value labels. Only routes matching side, source, and buy type are eligible. Route-label
shares are renormalized over eligible labels, then the nearest starting position is selected.
Enemy shots within 1,200 engine distance units stop playback, without a visibility check. Damage
dealt or taken also stops it. Completion, death, pawn replacement, mode change, disconnect, map
change, and unload are handled. The last route and first hand-off reason stay visible until the
next round. A failed stop is reported and prevents starting another route or purchase plan.

`clone_add` preloads files off the game thread, serializes named-bot requests, and attaches only
a new bot with the requested name and side, with a five-second timeout. Personality comes from
`stand_in_bot`, or `display_name` when absent (the pipeline's donk entry is named `donk`). The
plugin does not repack the personality archive or set personality values at runtime. Without a
custom entry installed by a person, it uses the existing named bot's personality, purchases,
and routes. These bot creation and purchase assumptions still need an in-game check.

### 6.3 CloneDirector console commands

| Command | Effect |
|---|---|
| `clone_add <clone_id> <t or ct>` | Adds a bot that uses the clone's personality entry and links the bot to the clone's files |
| `clone_list` | Prints each clone bot, its last route label, and its last hand-off reason |
| `clone_routes <recorded, generated, or off>` | Chooses which segments the clones play |
| `clone_record <on or off>` | Planned, not implemented. Records human players' routes (section 6.4). Low priority. |

The commands are server-console only. The real match service (section 9.2) adds stand-in bots by
default; with `CS2_BOTS=clone` it sends `clone_add` through the MatchBridge plugin instead (not
run in CS2). `clone_routes` stops
current playback and applies the chosen source next round. `clone_record` is not implemented.

### 6.4 Cloning users while they play (low priority)

The same interface records human players. The plugin can call `StartRecord` on each human at round
start and save the segment at round end. These segments are already in the playback format. A user
who plays ten rounds has a route library at the end.

## 7. Data

### 7.1 Source

**OpenCS2** by Julien Blanchon, on Hugging Face. License CC BY 4.0, which requires credit. The match
recordings come from HLTV (the main CS2 results site) and stay under the tournaments' terms.

- [`blanchon/opencs2_dataset_demo`](https://huggingface.co/datasets/blanchon/opencs2_dataset_demo):
  1,988 raw match recordings, 2026-03-23 to 2026-04-20. The index lists player names. On Mirage: 366
  recordings, 7,809 rounds.
- [`blanchon/opencs2_dataset`](https://huggingface.co/datasets/blanchon/opencs2_dataset): ready-made
  per-tick tables and first-person video for 794 map games. On Mirage: 3,054 rounds. Players are
  labeled by slot number 0 to 9, not by name.

Use the raw recordings as the main path, because a user's upload is also a raw recording. Use the
first-person videos on the replay page.

**Do not commit recordings, model weights, or videos to this repository.** `.gitignore` blocks the
common file types.

### 7.2 donk (first clone)

5 Mirage games, 97 rounds, all from IEM Rio 2026. In all of OpenCS2: 12 games, 236 rounds.

| Match ID | Game | Rounds | Date | File in `opencs2_dataset_demo` |
|---|---|---|---|---|
| 2393226 | Spirit vs Falcons | 18 | 2026-04-14 | `demos/shard-europe-17bc5760/2393226/spirit-vs-falcons-m2-mirage.dem` |
| 2393237 | G2 vs Spirit | 20 | 2026-04-15 | `demos/shard-europe-5457b143/2393237/g2-vs-spirit-m1-mirage.dem` |
| 2393232 | RED Canids vs Spirit | 21 | 2026-04-15 | `demos/shard-europe-5457b143/2393232/red-canids-vs-spirit-m1-mirage.dem` |
| 2393240 | Spirit vs MOUZ | 21 | 2026-04-17 | `demos/shard-europe-6ac92abd/2393240/spirit-vs-mouz-m2-mirage.dem` |
| 2393242 | Falcons vs Spirit | 17 | 2026-04-18 | `demos/shard-europe-e407f24a/2393242/falcons-vs-spirit-m2-mirage.dem` |

All five also have per-tick tables and first-person video in `opencs2_dataset`.

**Hold one game back.** Build and train from the first four games (80 rounds). Keep match 2393242
(17 rounds) unseen. Sections 8.6 and 10 use it.

### 7.3 broky (second clone)

5 Mirage games, 101 rounds. Only the first has ready-made tick tables.

| Match ID | Game | Rounds | Date | File in `opencs2_dataset_demo` |
|---|---|---|---|---|
| 2392601 | FaZe vs aimclub | 21 | 2026-03-30 | `demos/shard-europe-185d0746/2392601/faze-vs-aimclub-m1-mirage.dem` |
| 2393037 | FaZe vs BEE | 17 | 2026-04-03 | `demos/shard-europe-3e2bacd0/2393037/faze-vs-bee-m1-mirage.dem` |
| 2393059 | FaZe vs CYBERSHOKE | 22 | 2026-04-05 | `demos/shard-europe-a7396e87/2393059/faze-vs-cybershoke-m1-mirage.dem` |
| 2393063 | FaZe vs illwill | 19 | 2026-04-05 | `demos/shard-europe-b529dd16/2393063/faze-vs-illwill-m2-mirage.dem` |
| 2393024 | Inner Circle vs FaZe | 22 | 2026-04-06 | `demos/shard-europe-db22335d/2393024/inner-circle-vs-faze-m2-mirage.dem` |

Hold back match 2393024 (22 rounds).

**Built 2026-11-14:** `broky_v1`, four building matches, 79 rounds and route files (38 T, 41 CT),
182 extracted throws. The held-back match is excluded from building matches and routes. Both
profiles load in the catalogue reader, and every route file loads in C#. In-game behavior is untested.
The five raw recordings are under `data/demos/broky/` and are ignored by Git.

Player-versus-self comparison on the held-back match (not clone performance): T position overlap
0.705, route overlap 0.579, 38/10 building/held-back rounds; CT position overlap 0.733, route
overlap 0.297, 41/12 rounds. These are small samples. Cross-player overlap sometimes exceeds
self-overlap in these samples, so these measures do not establish player identification or bot
strength. Both players' numbers are in `clones/README.md`.

**Check before the pitch:** FaZe changed players several times in 2026. Nobody has confirmed that
broky is on the November 2026 lineup.

### 7.4 Limits of this data

- 97 rounds supports: route frequencies per side, purchases, weapon choice, grenade throws, rough
  reaction numbers, and one identity vector for the model.
- 97 rounds does not support: training a network on one player alone, or any other map.
- Recording file sizes are not measured. Professional recordings are usually several hundred
  megabytes each. Check free disk space first.

## 8. The generating model

### 8.1 What it is

The generating model is a neural network that writes new movement for a clone. It looks at the last
4 seconds of the game and outputs the next 4 seconds of one player's movement.

It differs from playback. Playback repeats a route the real player took. The model writes a path
that may not exist in any recording, for a situation the player was never recorded in.

### 8.2 The starting point: CS-NET v4

Read from its documentation (`docs/pretrain.md`) and settings file. Not yet run by this team.

- **Size:** 138.7 million parameters. The weights file (`cs-net-v4-pro.pt`) is 529 MB.
- **Input:** 16 steps of game state, one step every 0.25 seconds. Each step holds all 10 players,
  the bomb, and up to 16 grenades. For each player it also holds 64 distance measurements to nearby
  walls, computed from the map's 3D geometry.
- **Output, per player, per step:** a "still alive" flag, a move forward, a move right, a move up, a
  change in up-down view angle, a change in left-right view angle, and a "fires" flag.
- **Precision:** moves in steps of 4 game units. View angles in steps of 5 degrees.
- **How it generates:** one step at a time. After each step it measures the walls again from the new
  position and feeds that back in.

**What this precision means.** 5 degrees is too coarse to aim at an enemy. The model can produce
routes and general view direction. It cannot produce accurate shooting. Fights stay with
CS2-Bot-Improver's own logic.

**What it lacks.** It does not know which player it is generating. Its training code shuffles the
order of the players on purpose, so the network cannot learn any one player's style.

### 8.3 The change: add player identity

1. Add a table with one learned vector per known player. Row 0 means "unknown player" and is all
   zeros. Take this from CS2 Clone Lab's `sim/identity.py`.
2. Attach the vector to the part of the network that generates the movement, using the scale-and-shift
   layer in the same file (`FiLM`). That layer starts at zero. So before training, the changed
   network gives exactly the same output as the original CS-NET v4.
3. Carry each player's Steam ID through the data loader, including through the player shuffle, so
   the right vector meets the right player.
4. Load the original weights. CS-NET's loader accepts a network with extra parts
   (`strict=False`, per its documentation).

### 8.4 Training plan (Colab Pro)

**Stage A, required.** Freeze the whole original network. Train only the identity vectors and the
scale-and-shift layer, on the training games of donk and broky. A small adapter reduces compute but
can still overfit. Reserve whole development rounds from the training matches for checkpoint
selection and early stopping; do not tune on the held-back matches.

**Implementation in progress (Arjun/Codex, 2026-11-14):** `clone-model/` pins CS-NET revision
`268dd2193c8a3d6e330c07dde5a851196c94eeaa` and adapts CS2 Clone Lab's MIT-licensed identity/FiLM
code from `2d3f50eeab9d6883abdb58d83f8c9bd1538b194a`. Nine CPU tests pass, including a real small
CS-NET backbone forward/backward check, exact zero-initial output change, frozen backbone,
unknown identity remaining baseline after bias changes, and shuffled target/identity alignment.

The implementation uses upstream parser/filter/inventory/round-feature/raycast/window modules;
round arrays are cached as NPZ instead of WDS. Each batch trains only the named target player's
last-history-tick decoder prediction, with all ten players as context. Identifiers come from the
parser's Steam-ID metadata. Only the identity table and decoder-conditioning FiLM are optimized.
The original model and output token format remain unchanged. Adapter checkpoints include the
registry, source revision, and base-weight/data-manifest hashes.

Colab notebook setup and raw downloads ran on an L4. At Arjun's request, G4 was selected for
optimization, but Colab reported it unavailable and allocated an **A100-SXM4-80GB** instead.
All ten matches parsed (198 rounds) and transferred to A100. Public preparation archive: GitHub prerelease `clone-training-data-v1`, SHA256 `0e46914cbca514efbb5727b64f9e753116da4afaa98f764be66d15d97cb8ad25`. The training selection in `clone-model/games.json` excludes 2393226 because its donk-named slot has an unverified alternate Steam ID (`76561198018303780`). Canonical donk is `76561198386265483`, consistent across the other four recordings; broky is `76561198201620490`. The learned run uses nine matches / 180 rounds, three donk training matches and four broky training matches plus both unchanged whole-match holdouts. Existing route clones are separate and unchanged.
Match 2393037 contains an eleventh, unassigned person at the first live tick. The upstream parser rejected it. `parse_compat.py` filters roster and metadata together to exactly five unique players on each playing team and rejects ambiguous cases; regression tests cover both first-tick identities and later per-round tick passes. Empty parsed matches are rejected.
Actual CUDA optimization completed 600 updates on the A100 (PyTorch 2.14.1+cu130), batch size 16, learning rate 0.0003, 100,032 trainable parameters, 1,656 training windows and 756 development windows. Training/development took 229.1 seconds. Configured maximum was 1,000; early stopping selected step 400 after four subsequent non-improving checks. Selected dev loss: donk 0.659418 vs base 0.661075; broky 0.652162 vs base 0.654092 (24 dev windows each). This small improvement did not pass the final identity test. Adapter-only checkpoints and full reports are preserved in prerelease `learned-clones-a100-v1`; aggregate provenance is in `clone-model/results/first-a100.json`. `colab_train.ipynb` is a clean reproduction notebook, syntax-checked locally; the original experiment executed in the saved Colab notebook.

**Stage B, only if Stage A works and time remains.** Add small trainable layers
(`LoRA`, also in `sim/identity.py`) to the generating part. Train on about 30 Mirage games, with an
identity vector for every player who has 3 or more games.

**Data preparation.** Use CS-NET's own tools in this order: its parser (`demo_parser/`), then
`scripts/create_training_data.py`. The second step computes the wall distances from
`maps/optimized_obj_files/de_mirage.obj`, which the CS-NET repository includes.

**Hardware.** CS-NET's settings file reports under 25 GB of graphics memory for full training at
batch size 14. Stage A trains far fewer numbers and needs less. Lower the batch size on a smaller
Colab graphics card.

**Cloning a new person later.** Freeze everything and train one new identity vector on that
person's recordings. This is the path that makes "give us your recordings, get a clone" true for the
model, without retraining the network.

### 8.5 How generated movement reaches the demo (made by hand)

The model does not run during the match. `clone-model/review.py` now exports development-only diagnostic examples via the same pinned PredictionEngine: actual, own identity, other identity and base paths, with timing/side/identity/provenance and native early-stop lengths. This new `cs2.clone.review.v1` offline file does not alter the match-service API. It is not a recorded bot match or an approved playback file; failed-validation identities are not promoted. Twelve CPU tests pass, including development/holdout exclusion, dead-anchor fallback and trace timing/channel checks. The exporter ran on the A100 with the step-400 adapter: eight development cases, four per player, 24 generated paths plus eight actual paths. Downloaded JSON was checked for timestamps/channels and held-out exclusion. `plot_review.py` rendered the XY comparisons with Matplotlib; the figure was visually checked. Artifacts and interpretation are attached to prerelease `learned-clones-a100-v1`. Six of eight own paths equal the base exactly; seven equal the other identity exactly. This diagnostic selection is not a validation score. Full test validation now writes an explicit final pass/fail state; dev reviews do not change it. For the demo, a person builds generated segments offline:

1. Pick a real moment from a held-back game, for example the start of a round.
2. Ask the model for the next 4 seconds of the clone's movement, with the clone's identity vector.
   CS-NET's `PredictionEngine.predict_at_tick` does this.
3. To go past 4 seconds, write the generated positions back into the round data for the clone's
   player and ask again. The other nine players keep their real recorded movement.
4. Open the result in the viewer. Reject any path that crosses a wall or stops for no reason.
   Generate again until a path is good.
5. Fill in the steps between the model's 4 outputs per second to reach 64 ticks per second.
6. Convert the path to the bot playback format with the same converter used for recorded segments.
7. Save it under the clone's generated segments. `clone_routes generated` makes the bots play it.

**Say this in the pitch.** The generated routes in the demo were made offline and picked by hand.
The model does not yet run during a match.

### 8.6 The model's proof: the identity swap test

Run `clone-model/validate.py` on each player's held-back game. It uses CS-NET's free-running
`PredictionEngine.predict_at_tick_player_sampled` (one deterministic greedy sample) and the path
error measures used by `scripts/evaluate_pretrain.py`. It additionally extends early-stopped
predictions with their final position so the full true horizon is scored. Future target positions
and angles are not supplied during generation. Report endpoint, speed, and pause-rate errors
alongside average path error. Teacher-forced development loss is not an identity-swap result.

| Rounds from | Identity vector used | Expected |
|---|---|---|
| donk | donk | Lowest error |
| donk | broky | Higher error |
| donk | none (row 0) | Higher error. This is the original CS-NET v4. |
| broky | broky | Lowest error |
| broky | donk | Higher error |

**Pass:** each player's own vector gives the lowest error on that player's rounds.

**First run, measured 2026-11-14:** 71 held-out windows (29 donk, 42 broky), 213 deterministic free-running predictions. Mean path error in Source units (own / other / base): donk **134.15 / 120.33 / 133.74**; broky **99.83 / 105.76 / 92.70**. Both fail. One held-out match per player, correlated windows; not a skill estimate. No model was promoted into the playable clone; both profile model fields remain null. See `clone-model/results/first-a100.md` and the experimental release for all metrics and checkpoint hashes.

**If it fails:** report the numbers as they are. Show the model as "the base model, identity not yet
learned". The in-game demo is unaffected, because it uses recorded segments.

### 8.7 Not attempted in the hackathon

The model running during a match. Reasons:
- Speed is unmeasured. CS-NET's documentation reports 1 to 3 minutes per run on a processor without
  a graphics card.
- The bot interface accepts movement only as playback files (section 6.1), so a live loop would
  have to feed short playback pieces one after another. Nobody has tried that.

### 8.8 Quirks: identity measured as rates, one rule per quirk (added 2026-11-14)

The first learned model failed its identity test (section 8.6 results in
`clone-model/results/first-a100.md`). The diagnosis is in
`clone-model/results/diagnosis-2026-11-14.md`. In short: a 4-second path does not show who the
player is, but rates over a whole match do.

A **quirk** is one number per player per match, such as jumps per minute. `clone_pipeline/quirks.py`
measures 27 quirks at 64 ticks per second for every player in a recording. For the cloned player it
fits one rule per quirk: the player's value, the other players' mean and spread, and whether the
quirk is **distinctive** (at least 1 standard deviation from the others, in the same direction in
every building match).

Each quirk is meant to drive one bot control:

| Quirk | Bot control | State |
|---|---|---|
| Jumps per minute | CloneDirector presses jump at that rate, only while the bot runs, no route is playing, and no fight happened in the last 5 seconds | Code and tests done; not run in CS2 |
| Share of time far from teammates | The personality file's `Teamwork` number | Value written to the profile; installing it is manual |
| Standing-still share, turning speed, shots per burst, grenade mix, time to first fight | None yet | Measured only |

A clone with quirks has `L` after the player's name: `donkL`, `brokyL`. It reuses the `_v1` clone's
routes and purchases, sets `stand_in_bot` to the installed bot name, and adds the fields `learned`,
`quirks`, `quirk_controls`, and `quirk_reference`. Code that reads only the older fields is unaffected.

**The quirk test.** It replaces per-window path error as the identity test. The rule was fixed
before anything was scored with it, and it is looser than the first test, which required the
player's own identity to beat every alternative outright:
- Who is it: the true player is among the 2 nearest of the candidate players.
- Per quirk: the measured value is on the player's side of the others' mean, and covers at least
  half of the distance to the player's value.
- Overall: at least 60% of the distinctive quirks pass.

The same command scores a real match, a recorded bot match, or generated play:
`uv run python -m clone_pipeline.quirks score --profile ../clones/donkL.json --demo <file> --name <name>`.

Results so far, real players on their own held-back matches (the ceiling): donk 1st of 5 with 8 of
10 quirks; broky 1st of 5 with 9 of 10. No bot has been scored.

## 9. Architecture

```
  OFFLINE
  .dem files ──> clone pipeline ──> clone profile + route segments + grenade files
  (OpenCS2 or    (demoparser2)           │
   user upload)                          │
        │                                │
        └──> CS-NET tools ──> generating model (Colab) ──> identity vectors, generated segments
                                                              (checked by hand)
  IN THE GAME (Windows laptop)                                │
  match service ──commands──> CS2 + CS2-Bot-Improver + CloneDirector plugin
  (Server API)                     │ plays the match and records it
        ▲                          ▼
        │                 recording of the clone's match ──> clone pipeline again
  lobby page, match page                                      │
                                                              ▼
  WEB    replay page: real round next to clone round, generated path overlay, caster voice
         profile page: heat map, habits, scouting report, similarity, most similar professionals
```

### 9.1 Clone pipeline (Python)

1. **Parser.** Reads one recording with demoparser2. Writes per-tick rows for the target player and
   event rows for purchases, shots, damage, kills, and grenade throws.
2. **Feature builder.** Cuts route segments (section 5.2). Computes habits (section 5.1). Builds a
   **style vector**: a fixed list of about 30 numbers that summarize a player's habits.
3. **Clone builder.** Writes the clone profile (section 5.4) and the bot personality entry. Converts
   each route segment into the bot playback format.

The same steps run on the clone's own recorded match, to produce the clone's side of the replay page.

### 9.2 Match service (exists as a mock)

`match-service/` is a FastAPI service written by Ashirwad. FastAPI is a Python web framework. Its
`README.md` is the reference for the endpoints and events. In short:

- `GET /clones` lists the clone profiles in a folder.
- `POST /matches` creates a match from a map, a mode, human players, and clones per team.
- Modes: `competitive` (5 per team, first to 13 rounds) and `wingman` (2 per team, first to 9).
- A match moves through `starting`, `ready`, `live`, `ended`. The service can send each change to a
  callback address.
- When a match ends, it gives a `demo_url`: the address of the match recording.

**Today it is a mock.** No CS2 match starts. Round winners are random.

**The real version (not started, proposal):**
1. The service runs on the demo laptop next to CS2.
2. On `POST /matches` it starts the map with the bot base, then sends `clone_add` (section 6.3) for
   each clone.
3. It turns on match recording, and serves the recording file at `demo_url` when the match ends.
4. Its endpoints and messages stay the same, as the mock's README promises.

**Stand-in phase (Ashirwad, in progress).** Until CloneDirector exists, the real version adds each
clone's `stand_in_bot` with CS2's standard add-bot command instead of `clone_add`. The lobby, the
endpoints and the events do not change when `clone_add` replaces it.

**What is written (`MATCH_BACKEND=cs2`, not yet run in CS2).** `match-service/README.md` has the
setup steps.
- Commands go out through one of three channels in `console.py`, set by `CS2_CONSOLE`:
  `netcon` (CS2's network console, the default), `rcon`, or `plugin` (MatchBridge, a small
  CounterStrikeSharp plugin that runs each command inside the game). RCON and the plugin run
  commands on the server side, so `jointeam` becomes `matchbridge_jointeam` (plugin) or is dropped
  (RCON; the person picks a team).
- `match-service/start-cs2.ps1` sets up the Windows PC and starts the service: it installs the game
  state config with a token, builds and installs MatchBridge when asked, and sets the settings. It
  listens on `127.0.0.1` unless `-Listen 0.0.0.0` is given, because the API has no login.
- Values that go into console commands are checked: every channel refuses a command with a newline
  or `;`, and `stand_in_bot` must be a plain name (letters, digits, `_`, `.`, `-`). Found by Tom's
  security check.
- Events come in through CS2's Game State Integration, posted to `/gsi`. Scores come from the team
  scores in game state. Team names `Alpha` (starts CT) and `Bravo` (starts T) keep scores with the
  right team after sides swap. At halftime CS2 can send one update with the names swapped and the
  scores not (Tom's match 09a357d5a255 jumped from 7-1 to 7-7), so the service only accepts a
  reading of the two scores where neither team's score drops, takes the one that adds the fewest
  rounds, and uses the names only to break a tie.
- One match at a time. At most one human: the person at the CS2 PC. Bot against bot puts that
  person in spectator.
- Recording is set by `CS2_RECORD`. `off` (default): nothing is recorded and `demo_url` is `null`
  (the API already allowed `null`). `tv`: GOTV (`tv_enable 1` before the map, `tv_record
  match_<id>`, `tv_stoprecord`), served at `demo_url` from `CS2_DEMO_DIR`; not tried in CS2. The
  player's own `record` is never sent, because over netcon it froze and once crashed CS2 (section 3).
- `GET /health` reports whether the console answers and when game state last arrived.
- `CS2_BOTS` picks who plays a clone. `stand_in` (default) adds its `stand_in_bot`. `clone` sends
  `clone_add <clone_id> <t|ct>` to CloneDirector and reads profiles from `clones/`. CloneDirector
  refuses commands from a player's console, which is what netcon is, so these commands go through
  MatchBridge (server console). The service then polls MatchBridge's `matchbridge_bots` until each
  clone's bot (named after `stand_in_bot`, else `display_name`) is on its team, and fails the match
  after 20 s otherwise. That shows a bot with the right name, not CloneDirector's attachment.
  `de_mirage` only. `start-cs2.ps1 -Bots clone` installs MatchBridge and sets this up.
- `clone_id` and `stand_in_bot` must be plain names; profiles that break this are skipped.

netcon works in CS2 Bot Mode (Tom's run, 2026-11-14); RCON and the plugin stay as fallbacks.
- At match start the service sends `mp_warmup_end` and `mp_restartgame 1`, then ignores
  game state for 2 s. Bot Mode reported `live` before the match started, and CS2-Bot-Improver's own
  team commands end with `mp_restartgame 1` after adding bots.

**The link to the replay page.** `demo_url` is the input to the clone pipeline for the clone's side
of the replay.

### 9.3 Web pages

- **Lobby page and match page.** Owned by teammates, built against the match service.
- **Demo pages (`match-service/demo/`, Ashirwad).** Bare-minimum versions of each feature for the
  judges, served by the match service at `/demo/`. Written from zero (plain HTML and canvas; no
  existing viewer reads these files). They stand in until the teammates' pages exist:
  - *Play vs a bot*: a minimal lobby form (side, mode, map, opponents, teammates), status, score.
  - *Bot vs bot*: starts donk vs broky and shows one live map panel per bot, plus score and events.
  - *Replay*: a bot's round from a match next to the real player's closest recorded round on the
    same side, on one clock; both bots in one round (10.4); and every recorded round.
  - *Proof*: the clone files' ceiling numbers (player vs himself) and habits. The in-game and
    baseline columns score a match picked from the list (or a saved match id) through
    `GET /matches/{id}/score`; a match played with `CS2_BOTS=clone` belongs in the clone column and
    `stand_in` in the baseline. The swap-test card shows Arjun's first run, which failed.
  - Disabled placeholder buttons mark what needs other pieces: first-person video, generated path,
    caster voice, match recording, the clone dashboard, CloneDirector's same-route run, swap test.
- **Replay data behind them (`match_service/replay.py`).** Real rounds: the clone pipeline's route
  files in `clones/` (Brotli JSON, 64 ticks a second), cut to 8 points a second. Bot rounds: the
  cs2 backend records each player's position per round from game state (`allplayers`, only while
  the person at the PC spectates); the mock gives each clone a real recorded route for its side,
  marked `simulated`. "Closest real round": the average distance between the two paths, first 20 s
  of the bot's round. New endpoints (additions; nothing existing changed): `GET /matches`,
  `GET /matches/{id}/trace`, `GET /matches/{id}/compare`, `GET /replay/clones[/{id}[/routes[/{rec}]]]`,
  `GET /replay/outline`. Traces are saved to `TRACE_DIR` when set.
- **Replay page.** Starts from CS-NET v4's viewer, which already draws a generated path over the real
  path. Add: the clone's recorded round next to the real player's round, the real first-person video
  from OpenCS2, and the caster audio.
- **Profile page.** Heat map of positions per side. Weapons, purchases, route frequencies, reaction
  numbers. An AI-written scouting report. Similarity scores. "Most similar professionals".
- **Character showcase viewer (`frontend/`).** Five artist-rigged, KTX2-compressed models
  (built by `scripts/chargen/`) on a WebGPU canvas with a TSL glitch hot-swap transition.
  Rigs integrated and verified (C2).
  Per-character rim-light/HUD accent sync (`rimColor`/`accentColor`); `scripts/verify-models.mjs`
  gates artist GLB drops (size, Idle clip, skins, meshopt).

### 9.4 Sponsor services

- **Gemini, scouting report.** Send the clone profile to a Gemini Flash model. It returns a short
  text on the player's habits.
- **Gemini, caster script.** Send the real round's first-person video clip plus both rounds' event
  lists. It writes about 20 seconds of commentary. This uses Gemini's ability to read video.
- **ElevenLabs, caster voice.** Turn the script into audio with a stock voice. Bot callouts have
  their own approval and playback path in section 9.5.
- **MongoDB Atlas.** One document per clone profile. One style vector per professional in OpenCS2.
  Atlas Vector Search (MongoDB's nearest-neighbor search over lists of numbers) returns the most
  similar professionals for a clone.
- **Vultr.** Hosts the web pages and the services that do not need the game.
- **GoDaddy Registry.** The project's domain. The HackUTA slides give the promo code `MLHUTA76`.

Pick the exact Gemini model name from `https://mlh.link/gemini`. Nobody has checked which Flash
model is current.

### 9.5 Pro bot voices: donk and broky (ElevenLabs)

**MVP scope.** Ship short, scripted CS2 callouts using verified clones of the professional players
donk and broky, mapped to `donk_v1` and `broky_v1`. Both verified player packs must pass the
listening and playback checks below to complete the voice MVP. Self-service voice enrollment and
voices for additional players are outside this MVP. Use clearly labeled fictional voices or
silence as temporary demo fallbacks while a player pack is pending. Label verified output as an
AI-generated bot voice and use a stock voice for the caster.

**Authorization and sourcing, in order.** ElevenLabs requires each speaker to create and verify
their own Professional Voice Clone (PVC), even if the team has permission. Arrange separate
private pilots with donk and broky through the players or their representatives. Define in writing the
approved languages and lines, private match/replay use, any public demo or promotional use,
retention, revocation, and any team or recording rights that apply. The speaker shares the
verified PVC privately with the project, or renders the agreed lines on their own account and
delivers the audio. Prefer a scoped workspace share or speaker-rendered files. Treat external
sharing links as access credentials. Confirm that the project's plan and key can use a shared
voice with the selected model before depending on it.

| Source | How we would use it |
|---|---|
| Fresh player-recorded session | First choice. Ask for an isolated mic track of natural, concise comms. Prefer one setup and the actual language intended for the voice pack. Record quiet tactical speech, with enough delivery variety for callouts such as “one Palace,” “bomb down,” and “save.” |
| Player-owned stream or team practice mic stems | Ask the player or recording owner for clean originals and permission for cloning and output use. Use only the target's isolated channel. Keep any other speakers and private comms out of the dataset. |
| Team or organizer interview masters | Ask for original isolated audio if the player opts in. Team Spirit's [donk profile video](https://www.youtube.com/watch?v=ScuMpQTyaVE) and [BLAST's broky interview](https://blast.tv/cs/news/broky-everyone-thinks-theyre-the-best-team) identify producers to approach. The BLAST page is a written interview. Neither establishes accessible, cleared audio or enough usable minutes. Prefer current recordings in the desired speaking style. |
| YouTube, Twitch, esports VODs and match demos | Use public clips to identify the recording owner or agree on delivery with the speaker. Obtain an authorized original file from its owner if suitable. Public availability or a content license alone does not give permission to clone a speaker. Do not assume OpenCS2 match demos include usable, cleared isolated voice. |

**Recording and generation.** ElevenLabs recommends at least 30 minutes of clean single-speaker
speech and roughly 2–3 hours for the best PVC results. Train in the language intended for the
pack and test English or mixed-language comms separately if needed. Record lossless masters in a
quiet space, with consistent mic position and level. Trim long gaps and omit clipping, music,
other voices, and overprocessed segments. Keep a small separate set of real spoken callouts for
listening comparisons. PVC setup usually takes 3–6 hours according to ElevenLabs and can take
longer. Start with `eleven_v4` where the shared PVC supports it and compare against
`eleven_multilingual_v2`. Start with the provider's default voice settings and vary clone
strength only on persistent accent or resemblance issues. For lines that sound read aloud, compare with Voice Changer
(`eleven_multilingual_sts_v2`) using a consented speaker to perform the intended timing and
emphasis. Verify that the PVC is available for conversion and judge accent and pronunciation by
ear. Instant Voice Cloning is a fast prototype option for a consenting teammate, using about
1–2 minutes of clean audio. Use ElevenLabs Voice Design for an original fictional demo pack.

**Playback.** Pre-render a small pack of short lines and a few variants per event. Start with
round-start and round-end cues with known timestamps. Add tactical cues only when the bot could
know the fact its line states. A spectator's full-map information is unsuitable for team
callouts. Use a separate optional asset pack keyed by clone ID, locale and event plus a version.
Keep ElevenLabs keys, source audio, verification data and private sharing links out of Git and
out of the game and browser. Keep approved audio within its permitted distribution scope. Store
provenance and approved use with the pack so it can be disabled, removed and replaced on
revocation. Restrict generation to reviewed lines. A missing, disabled or invalid pack makes
the bot quiet. No synthesis, network calls or audio encoding on the game path.

1. **Replay first.** Add opt-in playback to the existing replay clock using cached audio. Play
   each cue once when playback crosses its timestamp. Pause cancels playback and seeking clears
   queued cues. Leave the match-service API, the clone profile schema and game startup alone.
   The live spectator test overcounted rounds at halftime (section 3). Use verified cue times
   for the demo and validate the event stream before scheduling automatic round-end lines.
2. **Private CS2 test.** Use the installed CS2-Bot-Controller release's `CanSendVoice`,
   `GetVoiceStatus` and `SendVoiceFrame`. Pre-encode mono audio to the packet format confirmed
   against that release. Start with 48 kHz and 20 ms Opus frames as a test candidate. Send
   individual encoded frames, paced on the game thread, only when the capability is ready.
   Verify frame sizing, slot attribution, recipients and audible output with one fictional pack.
   Use a bounded queue, one active line per bot, a cooldown, and drop stale audio on death,
   disconnect, round/map change, or slot reuse. Disable in-game voice if the release cannot
   deliver it to the intended audience. The replay can still use the same clips.
3. **Promotion.** Compare the same 10–15 unseen lines across candidates, with shuffled model
   labels, and have the speaker or an authorized reviewer listen. Score resemblance,
   intelligibility over game audio, pronunciation of map terms, and whether delivery sounds
   like team comms. Check both clean audio and the actual game channel. Verify missing/corrupt
   packs, offline operation, round transitions and spectators/teammates, and confirm movement,
   purchases, scoring and match completion still behave as before. Only use a speaker's pack
   after approval of the generated lines and delivery context.

**Cost and state.** On 2026-11-14 ElevenLabs listed Creator at US$22/month after the introductory
rate, with PVC creation and one creation slot. Each player can own their own PVC. Confirm sharing, plan entitlements and the
applicable commercial-use terms for the demo and later release. Estimate cost from the chosen
model's character rate or Voice Changer's audio duration, including retakes. For example, 25
cues × 3 variants × 35 characters is 2,625 characters per bot per full TTS pass. Cached playback
does not use ElevenLabs credits per match. The provider docs and repo interfaces were read.
No player authorization, voice training, generation, audio quality comparison, or in-game
voice delivery has been verified.

## 10. Proof and measurement

### 10.1 Side-by-side replay

Pick one donk round with a clear, early, aggressive route. Run the clone on the same side until it
picks the same route label. Show both on the replay page.

### 10.2 Similarity score for the in-game clone

Compare against donk's held-back game (match 2393242):

| Compared with the held-back game | Meaning |
|---|---|
| donk's other four games | The ceiling. How similar donk is to himself. |
| The donk clone, 15 or more recorded rounds | The result. |
| A default CS2-Bot-Improver bot, same number of rounds | The baseline. |

Measures, each per side:
- **Position overlap.** The share of time in each named map area, compared as two distributions.
- **Route overlap.** The share of rounds per route label.
- **Time to first contact.** The median number of seconds until the first fight.

The claim: the clone is closer to donk than the default bot is, on all three.

**How it is measured (written, 2026-11-14).** `clone-pipeline/clone_pipeline/ingame.py` scores a
match trace from the match service (`GET /matches/{id}/trace`, positions per round from game state)
against `clone-pipeline/references/<player>_<held-back match>.json`, the held-back match's stats.
Positions get area names from a lookup built from real Mirage recordings
(`clone_pipeline/maps/de_mirage_places.json`). It prints the ceiling, the clone and a baseline bot
side by side, with round counts. Two limits: a bot's route stops at 20 s or death, while a real
route also stops at first damage; and time to first contact is not measured, since a trace has no
damage events. The match service serves the same score as `GET /matches/{id}/score?player=<bot name
or clone_id>` (`match_service/scoring.py` imports `ingame.py` from the repository; it needs only the
standard library). `start-cs2.ps1` now saves traces to `data/traces/` (`TRACE_DIR`), so a match
can be scored after the service stops; not yet run on Windows. Each trace now records `bots` (`stand_in` or `clone`), so a score says whether
it measured a default bot or the clone.

17 held-back rounds is a small sample. Show round counts next to every number.

### 10.3 Model proof

The identity swap test in section 8.6.

### 10.4 Clone against clone

Use the match service's `wingman` mode. One team has donk's clone and a default bot. The other has
broky's clone and a default bot. Show the two clones' different routes on the replay page afterward.

## 11. Implementation plan

Times are estimates and assume about 16 hours from the start of the build. Four work streams run in
parallel. Owners are in the status board (section 0.2).

| Stream | Covers |
|---|---|
| A. Game | CS2 install, bot base, CloneDirector plugin, real match service |
| B. Data | Download, clone pipeline, route converter, similarity score |
| C. Web | Lobby, match page, replay page, profile page, sponsor services |
| D. Model | CS-NET data preparation, identity change, training, swap test, generated segments |

### Phase 0: prove the risky parts (hours 0 to 2)

- **A.** Install CS2-Bot-Improver on the laptop. Start a bot match on Mirage. Record a short walk
  with the chat command `!record test`, then play it on a bot with `!replay 1 test`. Find the saved
  recording file and give it to stream B. Turn off CS2 automatic updates in Steam (section 14).
- **B.** Download donk's five Mirage recordings. Parse one with demoparser2. Confirm that donk's
  per-tick position, view direction, keys, and area names are present.
- **C.** Run CS-NET's viewer on its bundled example round.
- **D.** On Colab: download the CS-NET weights, run its checkpoint test script
  (`scripts/test_checkpoints.py`), and run one generation on its bundled Mirage example.

**Exit test:** a bot replays a hand-recorded walk. One donk round parses. CS-NET generates one path.

### Phase 1: first clone, habits only (hours 2 to 6)

- **A.** Add donk's entry to the bot personality file. CS2-Bot-Improver ships that file inside a
  packed archive (`botprofile.vpk`), so this includes repacking it. Write the plugin skeleton:
  `clone_add`, and purchases through `SetBuyPlan`.
- **B.** Feature builder and clone builder. Read stream A's recording file and write the route
  converter. Test with `!replay`.
- **C.** Replay page: clone round next to real round, with the video panel.
- **D.** Prepare training data for donk's and broky's games with CS-NET's tools. Add the identity
  table and carry Steam IDs through the loader. Confirm the changed network still gives the original
  output before training.

**Exit test:** `clone_add donk t` adds a bot that buys what donk buys.

### The 6-hour gate (route converter)

Test: a bot replays a route that the converter produced from a donk recording.

- **Pass:** continue as written.
- **Fail:** keep the habit layer. A teammate walks donk's top three routes per side in the game
  while the built-in recorder captures them. Stream B stops work on the converter. Generated
  segments then cannot reach the game either, so the model is shown on the replay page only.

If the fallback is used, the pitch must say the demo routes were hand-recorded from donk's real
routes.

### Phase 2: routes in the game, first proof (hours 6 to 10)

- **A.** Route choice, playback, and hand-off in the plugin. Record a 15-round bot match with the
  donk clone, and a second with a default bot.
- **B.** Run the pipeline on both recorded matches. Compute the similarity score.
- **C.** Profile page. Caster: Gemini script, ElevenLabs audio, playback on the replay page.
- **D.** Stage A training. Run the swap test. Record the numbers in section 8.6.

**Exit test:** the replay page shows a real donk round next to a clone round on the same route, with
spoken commentary. **This is the minimum demo. Record a video of it as a backup.**

### Phase 3: second clone, generated segments, the match (hours 10 to 14)

- **A.** Real match service for `wingman` mode. Clone against clone (section 10.4).
- **B.** Run the pipeline on broky. Compute style vectors for all OpenCS2 players and load them into
  Atlas Vector Search.
- **C.** "Most similar professionals" on the profile page. Hosting on Vultr and the domain. Keep a
  copy that runs on the laptop if the venue network fails.
- **D.** Build generated segments by hand (section 8.5). Show them on the replay page and, if the
  gate passed, in the game.

### Phase 4: finish (hours 14 to 16)

- Whole team: run the full demo three times from a cold start.
- Write the DEV article and the license credits (section 14).
- Only if everything works: grenades from the player's own throws, Stage B training, recording users
  while they play.

### If only 12 hours remain

Cut in this order: grenades, Stage B training, recording users while they play, Vultr hosting,
generated segments in the game, the second clone. Do not cut the replay page, the habit clone in the
game, the similarity score, or the swap test.

## 12. Tech stack

| Layer | Choice |
|---|---|
| Game | CS2 on Windows, started through CS2-Bot-Improver's launcher in bot mode |
| Bot base | CS2-Bot-Improver, latest release, with its bundled Metamod:Source and CounterStrikeSharp |
| Plugin | CloneDirector targets .NET 10 and CounterStrikeSharp.API 1.0.378, following CS2-Smarter-Bot. References the installed release's `BotControllerApi.dll` without bundling it. Actual game loading remains untested. |
| Clone pipeline | Python 3.11 or newer, `uv` for packages, demoparser2, Polars and DuckDB for tables, NumPy |
| Match service | FastAPI, `uv`, pytest. Already in the repository. |
| Generating model | PyTorch, CS-NET v4 code and weights, Colab Pro |
| Replay page | CS-NET v4's viewer (Flask and Three.js) as the base |
| Character showcase frontend | Next.js 16, React 19, Three.js 0.187 (WebGPURenderer + RenderPipeline), Tailwind. In `frontend/` |
| Other web pages | Owners decide |
| Database | MongoDB Atlas with Atlas Vector Search |
| AI text and video | Gemini API, Flash model |
| Voice | ElevenLabs text-to-speech |
| Hosting | Vultr |
| Domain | GoDaddy Registry |

### Proposed folder layout

```
match-service/     exists: the Server API
frontend/          Next.js: WebGPU character showcase (5 blockouts, TSL glitch swaps)
clone-pipeline/    Python: parser, feature builder, clone builder, route converter, similarity
clone-director/    C#: the CloneDirector plugin
clone-model/       changes to CS-NET, training notebook, test results
replay/            the replay page, based on CS-NET's viewer
clones/            built clone profiles (small JSON files only)
SPEC.md  AGENTS.md  CLAUDE.md
```

## 13. Sponsor prizes

| Prize | How the project qualifies | Status |
|---|---|---|
| Main Track | The whole project | Target |
| FaZe Clan, "Be the CTO" | Fans play against a clone of a FaZe player. The prize asks who it is for, why they return, and how it earns. | Target. **The "how it earns" answer is missing and is required.** |
| ElevenLabs | Spoken caster on the replay page | Target |
| Gemini API (MLH) | Scouting report, and a caster script written from video | Target |
| MongoDB Atlas (MLH) | Clone profiles and similarity search | Target |
| Vultr (MLH) | Hosts web pages and services | Target |
| GoDaddy Registry (MLH) | The project's domain | Target |
| DEV writing challenge | One article on what the team built | Target |
| SpaceXSI (MLH) | Requires building with Cursor and Grok Bot | Not targeted, unless a teammate does real work in Cursor with Grok |
| Tiger Data, Solana, Chert | Not selected | Not targeted |
| Hardware Track | No hardware in the project | Not targeted |

## 14. Risks

| Risk | Effect | Response |
|---|---|---|
| The route converter does not produce a playable file | No automatic routes in the game, and no generated routes in the game | The 6-hour gate and the hand-recorded fallback (section 11) |
| The identity vectors learn nothing | The model shows no per-player difference | Report the numbers as they are. The in-game demo does not depend on the model. |
| CS-NET's data tools fail on OpenCS2 recordings | No training | Found in phase 0 or 1. Fall back to CS-NET's bundled example for the viewer, and say the model is untrained on our players. |
| A CS2 update lands during the event | CS2-Bot-Improver depends on exact game internals and can stop working until its authors update it | Turn off automatic updates in phase 0. Keep the backup video. |
| The personality file cannot be repacked, or the game ignores the new entry | No per-clone personality numbers | Use a professional entry that CS2-Bot-Improver already ships, and apply purchases and routes through the plugin only |
| Playback starts away from the bot's spawn point | The bot jumps to the route's start | Pick the segment nearest the spawn point. Accept a small jump. |
| The clone meets an enemy during playback and does not react | The clone dies without fighting | The hand-off rules in section 6.2. Tune them in phase 2. |
| Venue network fails | Hosted pages and AI calls fail | A local copy. Caster audio and reports are generated in advance. |
| Small data | Noisy numbers | Show round counts next to every number |

**Safety rule for the laptop.** CS2-Bot-Improver's bot mode starts CS2 with Valve's anti-cheat
turned off (the launch option `-insecure`). Never join an official or public match in that mode.
Switch back to online mode in the launcher first.

**Licenses.**
- CS2-Bot-Improver and CS2-Bot-Controller are AGPL-3.0. This repository is public. Publish the
  CloneDirector plugin's source under AGPL-3.0. That is the simple, safe choice for code that runs
  against them. The repository has no license file yet. The team must add one.
- CS2-Bot-Improver's launcher (`Panel/`) is PolyForm Strict. Do not change it or share copies of it.
- OpenCS2 is CC BY 4.0. Credit Julien Blanchon and OpenCS2 on the site and in the article.
- CS-NET v4, CS2 Clone Lab, cs2-movesim, and demoparser2 are MIT. Keep their license notices with
  any copied code.
- The match recordings stay under the tournament organizers' terms.

**Real players' names.** The demo uses the names donk and broky. That is normal for a hackathon
demo. A released product would need each player's or team's permission.

## 15. Demo script (3 minutes)

1. **20 seconds.** "Give us your match recordings and we give you a bot that plays like you."
2. **60 seconds.** Replay page. Real donk on the left with his first-person video. The clone on the
   right. Same route, same timing. The caster voice plays.
3. **40 seconds.** Profile page: heat map, habits, similarity against the default bot. Then the
   model: a generated donk path over the real one, and the swap test numbers.
4. **40 seconds.** CS2 on the laptop. donk's clone against broky's clone, live or recorded.
5. **20 seconds.** What is next: the model running during the match, and cloning you while you play.

## 16. Open items

1. **Read the Interface specs doc** and correct sections 5.4 and 9.2 if they differ from it.
2. **Owners** for every unassigned row in section 0.2.
3. **How it earns money.** Required for the FaZe prize.
4. **Is broky on FaZe's November 2026 lineup?**
5. **Project name and domain name.**
6. **A license file for this repository.**
7. **Recordings in CS2.** netcon and game state work. `record` over netcon freezes the client and
   can crash CS2 (section 3); the service no longer sends it, and recording is off by default.
   The spectator run verified automatic match completion and map playback from game state
   positions. The service overcounted rounds at the side swap (section 3). `CS2_RECORD=tv`
   (`tv_record`) has yet to be tried in CS2.

## 17. After the hackathon

1. The model running during a match, feeding the bot short playback pieces. cs2-movesim is the
   starting point for key-press-level control.
2. Cloning users while they play, as a finished feature.
3. An upload page: recordings in, clone out, with one new identity vector trained per person.
4. More maps. Each map needs its own recordings.
5. Expand optional clone voice from pre-rendered callouts to more game situations after the
   private CS2 playback and recipient checks (section 9.5).

## 18. Sources

- [CS2-Bot-Improver](https://github.com/ed0ard/CS2-Bot-Improver)
- [CS2-Bot-Controller](https://github.com/XBribo/CS2-Bot-Controller), with its `TECH.md` and `csharp/BotControllerApi/` source
- Voice research: [ElevenLabs Professional Voice Cloning](https://elevenlabs.io/docs/eleven-creative/voices/voice-cloning/professional-voice-cloning), [private sharing](https://elevenlabs.io/docs/help-center/product/voices/my-voices/how-do-i-share-a-voice), [models](https://elevenlabs.io/docs/overview/models/), [Voice Changer API](https://elevenlabs.io/docs/api-reference/speech-to-speech/convert), [Voice Design](https://elevenlabs.io/docs/eleven-creative/voices/voice-design), [pricing](https://elevenlabs.io/pricing/api), [use policy](https://elevenlabs.io/use-policy), and [voice data privacy](https://elevenlabs.io/privacy-policy).
- Voice delivery and source access: [Bot Controller voice interface](https://github.com/XBribo/CS2-Bot-Controller/blob/main/TECH.md), [Opus RFC](https://www.rfc-editor.org/rfc/rfc6716.html), and [YouTube Terms of Service](https://www.youtube.com/t/terms).
- [CS2-Smarter-Bot](https://github.com/ed0ard/CS2-Smarter-Bot)
- [CS2-Bot-NadeSystem](https://github.com/ed0ard/CS2-Bot-NadeSystem)
- [demoparser2](https://github.com/LaihoE/demoparser)
- [CS-NET v4](https://github.com/Gary2005/cs-net), with its `docs/pretrain.md` and `config/pretrain-a100-pro.yaml`. [Weights](https://huggingface.co/gary2oos/cs-net-v4).
- [CS2 Clone Lab](https://github.com/hpagni/cs2-clone-lab), with its `sim/identity.py` and `train/grl.py`
- [cs2-movesim](https://github.com/370025263/cs2-movesim)
- [OpenCS2 tick tables and video](https://huggingface.co/datasets/blanchon/opencs2_dataset)
- [OpenCS2 raw recordings](https://huggingface.co/datasets/blanchon/opencs2_dataset_demo)
- [CQ-AVATAR dataset](https://huggingface.co/datasets/Unit293/CQ-Avatar-Training) (rejected)
- FaZe lineup reports: [Neityu signing](https://cryptobriefing.com/neityu-faze-clan-permanent-signing/), [summer 2026 roster changes](https://refrag.gg/blog/cs2-2026-rostermania-summer), [team page](https://game-tournaments.com/en/csgo/team/faze)
- HackUTA 2026 tracks and prizes: the organizers' slide deck

## 19. Change log

- 2026-11-14, Ashirwad: read and removed the consumed continuation handoff; its context is kept outside the repo. Started its remaining tasks.

- 2026-11-14, Arjun (Codex): prepared Claude continuation context and prompt, including user-requested broad project tool authorization, failed-run evidence, exact environment/artifact references, ownership limits and consumed-handoff cleanup.

- 2026-11-14, Ashirwad: added `GET /matches/{id}/score` (in-game similarity from a match trace) and filled the proof page's clone and default-bot columns from it; traces record `bots`; `start-cs2.ps1` saves traces to `data/traces/`; the proof page shows the failed first identity test. Tested against the mock only.

- 2026-11-14, Codex: specified verified ElevenLabs voice packs for donk and broky as the voice MVP, with offline audio packs and staged replay and private CS2 validation.

- 2026-11-14, Codex: ran the private Wingman demo with live bot maps and synchronized donk replay; observed automatic completion and six extra halftime round events. Recording stayed off.

- 2026-11-14, Arjun (Codex): verified the offline path exporter on the real A100 checkpoint (eight development examples / 24 predictions), checked its JSON and Matplotlib review figure, and preserved the artifacts in the experimental release. Updated obsolete not-run model/download statements; live clone gameplay and identity likeness remain unproven.

- 2026-11-14, Arjun (Codex): added development-only generated-path review export from the pinned prediction engine and explicit completed validation states. Twelve CPU tests pass; GPU export check pending. No failed identity or generated path is promoted.

- 2026-11-14, Arjun (Codex): preserved and reported the first completed A100 learned-clone experiment (600 updates, selected 400); both held-out identity tests failed, so no promotion. Published experimental adapter/metrics artifacts and a syntax-checked reproduction notebook. Added Arjun's explicit recipient cleanup instructions to the temporary friend handoffs.

- 2026-11-14, Arjun (Codex): prepared complete CPU-only friend handoffs and copy/paste prompts for weapon-role/habit audit and independent mock replay QA, with ownership boundaries, verified data access and acceptance tests. A100 training exceeded 550 real optimizer updates; final identity test pending.

- 2026-11-14, Arjun (Codex): corrected canonical donk identity and excluded one ambiguous-account match before optimization; added empty-match cache rejection. Ten parsed public matches transferred to A100, nine selected for learning. CS2 base download completed successfully on Arjun's PC.

Newest first. One line per change: date, who, what changed.

- 2026-11-14, Arjun (with Claude): diagnosed the failed neural identity model (adapters not usable, not offered as bots). Added per-quirk rules and the looser quirk test to the clone pipeline, the jump-rate quirk to CloneDirector, and the learned-quirk clones `donkL` and `brokyL`. Asked teammates to add both next to the `_v1` clones. Ran: 23 pipeline tests, 28 C# tests, plugin compile, quirk test on both real held-back matches. Not run: anything in CS2. Removed the consumed `handoffs/claude-continuation/`.

- 2026-11-14, Tom (with Claude): recorded the demo-page and trace checks of match `f1ac03b4bbb5`
  in section 3. `-Bots clone` not run: CloneDirector is not installed on Tom's PC.
- 2026-11-14, Tom (with Claude): wired the demo pages to the real CS2 bots. Added `drivers.py` (how each clone
  is played), `driver`/`label`/`playable`/`reason` and `model` on `GET /clones` (additive), the
  `CS2_CLONE_ROUTES` setting (`recorded` or `generated`) as the hook for a trained model, and
  `start-cs2.ps1 -Open`. 57 service tests pass (6 new). Ran on Tom's PC: a donk-vs-broky wingman match
  started from the service on the real game, ran past the halftime side swap with the score and
  `round.ended` count matching every round, and ended by itself at CT 9, T 4. In a browser: Bot vs bot,
  Replay (all three tabs; the real-vs-bot clock advanced), Proof (in-game scores from the real match) and
  the Play page (match went live, player put on CT) worked with no console errors. The Proof page now
  places a stand-in match under Default bot; the overview table no longer says positions and the 9-round
  finish are unseen.
- 2026-11-14, Tom (with Claude): merged Codex's live-demo and voice entries into `SPEC.md` after its
  session ended mid-pull, and added sections 7 to 9 rules to `AGENTS.md` (memory check, demo run, voice
  authorization, handoff folders). No new tests run.
- 2026-11-14, Ashirwad: fixed the halftime score jump Tom found (7-1 to 7-7 in match 09a357d5a255):
  the service now picks the score reading where no team's score drops. Not yet rerun in CS2.
- 2026-11-14, Ashirwad: in-game similarity scorer (`clone_pipeline/ingame.py`): Mirage area lookup and
  donk/broky held-back references from OpenCS2, scores a match trace against them (section 10.2).
  Tested on the clones' route files; no CS2 trace scored yet.
- 2026-11-14, Ashirwad: demo pages at `/demo/` (play vs a bot, bot vs bot side by side, replay,
  proof) with placeholders for Arjun's pieces; match traces from game state positions; replay
  endpoints; 47 tests; pages run against the mock.
- 2026-11-14, Arjun (Codex): kept the verified roster through every upstream tick pass and rejected empty parsed matches after the upstream round-team check skipped the extra-observer match. Nine learned-model tests pass; the A100 is ready while data preparation completes.

- 2026-11-14, Arjun (Codex): compiled MatchBridge Release with SDK 10 (net8.0 target), zero warnings/errors, and re-ran all 42 service tests successfully. Read CLONE_AUDIT.md; its CS2 evidence is for stand-in presets, while data-built clones still await in-game checks. Updated build status; no C# changes.

- 2026-11-14, Arjun (Codex): added a strict CS-NET parser roster wrapper after broky match 2393037 exposed an extra unassigned person; checked its live-tick roster from the real demo and added a passing regression test. Eight learned-model tests pass.

- 2026-11-14, Nikesh: rounded out `frontend/.gitignore` (added `build/`, `coverage/`, `*.pem`,
  npm/yarn debug logs, `.vercel`) and untracked `frontend/AGENTS.md` (git rm --cached + ignored) —
  it's frontend-local design notes, not the shared rules file. Root docs (`AGENTS.md`, `CLAUDE.md`,
  `HANDOFF.md`, `SPEC.md`) are untouched and stay tracked/pushed per section 1/2 above, per the
  user's explicit confirmation.
- 2026-11-14, Arjun (Codex): added the Stage A learned-clone trainer and free-running identity-swap evaluator from pinned CS-NET/CS2 Clone Lab starting points; seven CPU tests pass. Colab pretrained-weight setup and ten match downloads ran; match parsing is underway. Requested G4 was unavailable; A100-SXM4-80GB was allocated for training. No learned-identity success is claimed yet.

- 2026-11-14, Tom (with Claude): ran the playback gate's first half on Tom's PC: `!record`/`!replay`
  work, a converted route file loads and moves a bot (route not confirmed), and scores count through
  the service after Ash's `record` fix. Saved a real recording for the converter. Added
  `TOM_HANDOFF.md`. Updated sections 0.2 and 3.
- 2026-11-14, Tom (with Claude): added `CLONE_AUDIT.md`, a file-level audit of both clones against
  the held-back matches and of the MVP state; recorded its result in section 3.
- 2026-11-14, Ashirwad: match service clone mode (`CS2_BOTS=clone`): `clone_add` to CloneDirector
  through MatchBridge, wait for each clone bot via the new `matchbridge_bots`, `de_mirage` only;
  start script `-Bots clone`. 42 tests pass against fakes; not run in CS2.
- 2026-11-14, Ashirwad: the match service no longer sends `record` (it froze CS2 in Tom's run).
  New `CS2_RECORD` setting: `off` by default (`demo_url` null) or `tv` (GOTV; untried). Start script
  gets `-Record`. 34 tests pass.

- 2026-11-14, Nikesh: showcase COMPLETE & VERIFIED (Nodes A1-A5, B1-B4, C1-C2) — integrated the
  artist's final KTX2+Meshopt rigs (`frontend/public/models/`, built by `scripts/chargen/`) and
  swept all 5 live: mixer Idle path, head-to-toe framing, chromatic rim/HUD, clean KTX transcode,
  0 console errors, 0 GLB refetches. Removed proxy backups and macOS duplicate files.

- 2026-11-14, Nikesh: chromatic sync + gatekeeper in `frontend/` — per-character `rimColor`/
  `accentColor` drive the rim/fill lights, active pill, signal bar and locked dot; added
  `scripts/verify-models.mjs` (`npm run verify:models`). Artist FIFA rig verified live through the
  mixer path; gatekeeper: 5/5 PASS. macOS `* 2.*` duplicates git-ignored.

- 2026-11-14, Nikesh: Node B4 in `frontend/` — dual-mode CharacterModel (AnimationMixer when clips
  exist, procedural bob otherwise), 4 s auto-cycle showcase loop with pause/play and manual
  override, carousel residency (no dispose on swap; explicit evict + LRU-8). Verified live: full
  5-model loop, pause freeze, resume, manual jump, 0 console errors, 0 GLB refetches.
- 2026-11-14, Tom (with Claude): claimed the bot base install and marked it done. Found that
  `record` over netcon freezes the client clock (the cause of the 0-0 score) and crashed CS2 once;
  the stand-in match plays without it. Ran `start-cs2.ps1` on Windows. Updated sections 3 and 16.
- 2026-11-14, Arjun (Codex): confirmed current code is pushed, started the CS2 base-game download in Steam, and re-ran all 69 current automated tests successfully. Game download remains in progress; no in-game clone validation or neural-model training has run.
- 2026-11-14, Ashirwad: recorded Tom's first CS2 run (netcon and game state work; no score, no
  recording); match start now ends warmup, restarts the game, and ignores game state for 2 s.
- 2026-11-14, Arjun (Codex): built the first broky clone from four real Mirage matches (79 routes), held out 22 rounds, corrected purchase order in both clones, added data-built clone documentation and explicit strength limits; 10 pipeline, 26 C#, and 32 service tests pass. All 159 routes load in C#. No in-game bot or replay test was run.
- 2026-11-14, Ashirwad: console safety from Tom's review (refuse newline and `;` in commands; strict
  `stand_in_bot` names); `start-cs2.ps1` listens on 127.0.0.1 by default and points to .NET SDK 10.
- 2026-11-14, Arjun (Codex): recovered the local pipeline and resolved its spec rebase; added CloneDirector from the upstream plugin/controller starting points, purchase and route control, combat hand-offs, strict playback loading, AGPL notices, and deployment notes. Release build and 25 C# tests pass; all 80 donk route files load. Pipeline tests pass. In-game playback and service integration remain untested.

- 2026-11-14, Ashirwad: added RCON and MatchBridge plugin fallbacks for match service console
  commands, and `start-cs2.ps1` to set up the Windows PC. Tested against fake servers only.
- 2026-11-14, Nikesh: implemented the character showcase viewer in `frontend/` (Next.js 16.4.6,
  React 19.3.1, Three.js 0.187.0, WebGPURenderer + TSL glitch pipeline, AssetManager with
  KTX2/Meshopt). Verified B1-B3 in headless-Chromium GPU QA: real WebGPU backend, initial model
  ~20 ms, 5/5 blockout GLBs cached, clean hot-swaps, zero console errors.
- 2026-11-14, Ashirwad: wrote the match service's cs2 backend (console commands out, game state
  in, stand-in bots, recordings, `/health`); added `donk_v1` and `broky_v1` profiles with
  `stand_in_bot`. Tested against a fake console only.
- 2026-11-14, Ashirwad: claimed the real match service; added stand-in bots and a stand-in
  side-by-side page to the status board; proposed the `stand_in_bot` profile field; ignored
  personal agent instruction files in `.gitignore`.
- 2026-11-14, Arjun (with Claude): added the clone pipeline (`clone-pipeline/`), the first donk clone (`clones/donk_v1`), and `HANDOFF.md` for the next agent. Ran on real recordings: parsing, route cutting, habits, playback file writing, 9 tests. Not run: anything in the game.
- 2026-11-14, Arjun (with Claude): first version of this spec. Added the status board, the
  generating model plan, and the agent rules in `AGENTS.md` and `CLAUDE.md`.
- 2026-11-14, Ashirwad: added the mock match service in `match-service/` (commit `6e009f1`).
