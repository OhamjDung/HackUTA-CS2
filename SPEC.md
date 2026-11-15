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
| Research: which bots, dataset, and model to build on | Arjun | Done | Sections 4, 7, 8 | 2026-11-14 |
| This spec and the agent rules | Arjun | Done | `SPEC.md`, `AGENTS.md`, `CLAUDE.md` | 2026-11-14 |
| Match service, mock version (Server API with a fake CS2 server) | Ashirwad | Done | `match-service/` | 2026-11-14 |
| Match service, real version (starts and controls a real CS2 match) | Ashirwad | In progress. Written (`MATCH_BACKEND=cs2`) with three console channels (netcon, RCON, MatchBridge plugin) and a Windows start script; tested only against fake servers, not in CS2 | `match-service/match_service/backends/cs2.py` | 2026-11-14 |
| Stand-in bots: built-in CS2-Bot-Improver pro bots used in place of clones until CloneDirector works | Ashirwad | In progress. `donk_v1` and `broky_v1` profiles use the `donk` and `broky` bots; not run in CS2 | `match-service/sample_clones/` | 2026-11-14 |
| Side-by-side page, stand-in version (two synced panels; replay page content replaces it) | Ashirwad | Not started | Not decided | 2026-11-14 |
| Lobby page | Tom (named in `match-service/README.md`) | Unknown. Owner: please update. | Not in the repo yet | 2026-11-14 |
| Match page | Nikesh (named in `match-service/README.md`) | Unknown. Owner: please update. | Not in the repo yet | 2026-11-14 |
| CS2 with the bot base installed on the demo laptop | Unassigned | Not started | Demo laptop | 2026-11-14 |
| Clone pipeline: recording in, clone profile out | Arjun (Codex) | Done. 10 tests pass; purchase order corrected in both clones. | `clone-pipeline/`, `HANDOFF.md` | 2026-11-14 |
| donk clone (`donk_v1`): profile, purchases, grenades, 80 route files | Arjun | Done. Built from 4 matches, 80 rounds. | `clones/` | 2026-11-14 |
| broky clone (`broky_v1`): data-built profile and routes | Arjun (Codex) | Done. Built from 4 matches, 79 rounds/routes; held back 22 rounds. Files load in C#; not run in game. | `clones/broky_v1.json`, `clones/README.md` | 2026-11-14 |
| Route converter: recording data to the bot playback format | Arjun | In progress. Files are written. **Not tested in the game.** Several field values are guesses (`HANDOFF.md` section 5.1). | `clone-pipeline/clone_pipeline/recording.py` | 2026-11-14 |
| CloneDirector plugin: applies a clone to a bot inside CS2 | Arjun (Codex) | In progress. Compiles; 26 C# tests pass, including all 159 donk/broky files. Not run in CS2. | `clone-director/` | 2026-11-14 |
| Generating model: CS-NET v4 plus player identity | Unassigned | Not started | `clone-model/` (proposed) | 2026-11-14 |
| Replay page: real player next to clone | Unassigned | Not started | `replay/` (proposed) | 2026-11-14 |
| Clone profile page | Unassigned | Not started | Not decided | 2026-11-14 |
| Caster voice (Gemini script, ElevenLabs audio) | Unassigned | Not started | Not decided | 2026-11-14 |
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
- Every GitHub repository in section 4 exists. Stars, licenses, and update dates come from GitHub.
- The OpenCS2 counts in section 7 come from queries against its index tables.
- The match service's cs2 backend, against a fake console and hand-written game state updates
  (`match-service/tests/test_cs2.py`, 10 tests, all pass). This checks the service's logic only.
- The RCON and MatchBridge console channels, against fake servers that speak the same protocols
  (`match-service/tests/test_channels.py`, 5 tests, all pass). This checks the Python side only.
- Console safety: every channel refuses commands with a newline or `;` before connecting, and
  profiles with an unsafe `stand_in_bot` are skipped (`match-service/tests/test_safety.py`, 6
  tests). All 32 match service tests pass. Tom ran the 26 earlier tests on Windows: they pass with
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

**Checked by reading source or documentation, not by running:**
- What each open-source project can do (section 4).
- The calls in the CS2-Bot-Controller programming interface (section 6).
- CS-NET v4's inputs, outputs, and training settings (section 8).
- The match service in this repository (section 9.2).
- CS2-Bot-Improver ships pro bots named `donk` and `broky` (`overrides/Medium/botprofile.db`), and
  its `Commands.txt` adds them with `bot_add_ct "<name>"` / `bot_add_t "<name>"`.
- CS2 Game State Integration field names (`map.phase`, `map.team_ct.score`, `round.win_team`), from
  the CounterStrike2GSI and cs2-gsi library docs.

**Not checked. Nobody has run any of this yet:**
- Installing the bot base on the demo laptop.
- Playing a pipeline-produced route inside CS2 (the format loads in C#; movement is still untested).
- Adding a custom entry to the bot personality file.
- Running or training CS-NET v4 on this project's data.
- Every time estimate in section 11.
- Sending console commands to CS2 from the match service, through any of the three channels:
  CS2's network console (`-netconport`; no source confirms CS2 still supports it), RCON on a Bot
  Mode game (`-usercon`, `rcon_password`), or the MatchBridge plugin.
- Building MatchBridge (never compiled), CounterStrikeSharp loading it, `Server.NextFrame` running
  the commands, and `matchbridge_jointeam` moving the player.
- `tv_record` / `tv_stoprecord` recording a Bot Mode game (used by the RCON and plugin channels).
- Running `match-service/start-cs2.ps1` on Windows. It was written on a Mac without PowerShell.
- CS2 sending game state to the match service's `/gsi` endpoint, and what it sends on a map change.
- `jointeam`, `mp_teamname_1`/`_2`, and `bot_add_ct "<name>"` behaving as the service expects.
- Recording a bot match to a `.dem` file on the laptop and serving it at `demo_url`.

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
| Path to key presses (after the hackathon) | cs2-movesim |
| Match control API | This repository's `match-service/` |
| Match service: events from the game | CS2's Game State Integration (Valve). Field names from the [CounterStrike2GSI](https://github.com/antonpup/CounterStrike2GSI) README; read only, no code copied |
| Match service: commands to the game | CS2's network console (`-netconport`). Idea from [csctl](https://github.com/403-Fruit/csctl) (CS:GO); read only. The client is written from zero: about 40 lines, no CS2 client found |
| Match service: commands to the game, fallback 1 | RCON through the [rcon](https://pypi.org/project/rcon/) Python library (GPL-3.0), used as a dependency |
| Match service: commands to the game, fallback 2 | MatchBridge, a CounterStrikeSharp plugin (`match-service/plugin/MatchBridge/`). Written from zero: no plugin found that runs console commands sent over a local port (LeaderOS Connect, the closest, runs store purchases). Project settings copied from CS2-Bot-Improver's own plugins; calls from the CounterStrikeSharp docs |
| Stand-in bots | CS2-Bot-Improver's pro bot profiles and the `bot_add_ct "<name>"` blocks in its `Commands.txt` |
| Style numbers for every professional | OpenCS2's ready-made index tables |

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
player-specific combat or generating model has been trained or evaluated.

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

The commands are server-console only. The real match service (section 9.2) still adds stand-in
bots; switching it to `clone_add` remains its owner's integration task. `clone_routes` stops
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
scale-and-shift layer, on the training games of donk and broky. Few numbers are trained, so the run
is short and cannot badly overfit.

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

The model does not run during the match. For the demo, a person builds generated segments offline:

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

Run on each player's held-back game, with CS-NET's `scripts/evaluate_pretrain.py`. It reports the
average distance between the generated path and the real path.

| Rounds from | Identity vector used | Expected |
|---|---|---|
| donk | donk | Lowest error |
| donk | broky | Higher error |
| donk | none (row 0) | Higher error. This is the original CS-NET v4. |
| broky | broky | Lowest error |
| broky | donk | Higher error |

**Pass:** each player's own vector gives the lowest error on that player's rounds.

**If it fails:** report the numbers as they are. Show the model as "the base model, identity not yet
learned". The in-game demo is unaffected, because it uses recorded segments.

### 8.7 Not attempted in the hackathon

The model running during a match. Reasons:
- Speed is unmeasured. CS-NET's documentation reports 1 to 3 minutes per run on a processor without
  a graphics card.
- The bot interface accepts movement only as playback files (section 6.1), so a live loop would
  have to feed short playback pieces one after another. Nobody has tried that.

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
  commands on the server side, so the service translates the client-only ones: `record` and `stop`
  become `tv_record` and `tv_stoprecord` (with `tv_enable 1` before the map loads), and `jointeam`
  becomes `matchbridge_jointeam` (plugin) or is dropped (RCON; the person picks a team).
- `match-service/start-cs2.ps1` sets up the Windows PC and starts the service: it installs the game
  state config with a token, builds and installs MatchBridge when asked, and sets the settings. It
  listens on `127.0.0.1` unless `-Listen 0.0.0.0` is given, because the API has no login.
- Values that go into console commands are checked: every channel refuses a command with a newline
  or `;`, and `stand_in_bot` must be a plain name (letters, digits, `_`, `.`, `-`). Found by Tom's
  security check.
- Events come in through CS2's Game State Integration, posted to `/gsi`. Scores come from the team
  scores in game state. Team names `Alpha` (starts CT) and `Bravo` (starts T) keep scores with the
  right team after sides swap.
- One match at a time. At most one human: the person at the CS2 PC. Bot against bot puts that
  person in spectator.
- The recording is `match_<id>.dem`, served at `demo_url` from `CS2_DEMO_DIR`.
- `GET /health` reports whether the console answers and when game state last arrived.

Which channel works in CS2 is not tested. Try netcon first, then RCON, then the plugin.

**The link to the replay page.** `demo_url` is the input to the clone pipeline for the clone's side
of the replay.

### 9.3 Web pages

- **Lobby page and match page.** Owned by teammates, built against the match service.
- **Replay page.** Starts from CS-NET v4's viewer, which already draws a generated path over the real
  path. Add: the clone's recorded round next to the real player's round, the real first-person video
  from OpenCS2, and the caster audio.
- **Profile page.** Heat map of positions per side. Weapons, purchases, route frequencies, reaction
  numbers. An AI-written scouting report. Similarity scores. "Most similar professionals".

### 9.4 Sponsor services

- **Gemini, scouting report.** Send the clone profile to a Gemini Flash model. It returns a short
  text on the player's habits.
- **Gemini, caster script.** Send the real round's first-person video clip plus both rounds' event
  lists. It writes about 20 seconds of commentary. This uses Gemini's ability to read video.
- **ElevenLabs, caster voice.** Turn the script into audio with a stock voice. Do not copy a real
  caster's or player's voice.
- **MongoDB Atlas.** One document per clone profile. One style vector per professional in OpenCS2.
  Atlas Vector Search (MongoDB's nearest-neighbor search over lists of numbers) returns the most
  similar professionals for a clone.
- **Vultr.** Hosts the web pages and the services that do not need the game.
- **GoDaddy Registry.** The project's domain. The HackUTA slides give the promo code `MLHUTA76`.

Pick the exact Gemini model name from `https://mlh.link/gemini`. Nobody has checked which Flash
model is current.

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
| Other web pages | Owners decide |
| Database | MongoDB Atlas with Atlas Vector Search |
| AI text and video | Gemini API, Flash model |
| Voice | ElevenLabs text-to-speech |
| Hosting | Vultr |
| Domain | GoDaddy Registry |

### Proposed folder layout

```
match-service/     exists: the Server API
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
7. **Which console channel works in CS2.** All three are written (netcon, RCON, MatchBridge
   plugin); none is tested in CS2. Tom's laptop test with `GET /health` decides.

## 17. After the hackathon

1. The model running during a match, feeding the bot short playback pieces. cs2-movesim is the
   starting point for key-press-level control.
2. Cloning users while they play, as a finished feature.
3. An upload page: recordings in, clone out, with one new identity vector trained per person.
4. More maps. Each map needs its own recordings.
5. The clone speaking in the game's voice chat. The bot interface supports it (`SendVoiceFrame`).

## 18. Sources

- [CS2-Bot-Improver](https://github.com/ed0ard/CS2-Bot-Improver)
- [CS2-Bot-Controller](https://github.com/XBribo/CS2-Bot-Controller), with its `TECH.md` and `csharp/BotControllerApi/` source
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

Newest first. One line per change: date, who, what changed.

- 2026-11-14, Arjun (Codex): built the first broky clone from four real Mirage matches (79 routes), held out 22 rounds, corrected purchase order in both clones, added data-built clone documentation and explicit strength limits; 10 pipeline, 26 C#, and 32 service tests pass. All 159 routes load in C#. No in-game bot or replay test was run.

- 2026-11-14, Ashirwad: console safety from Tom's review (refuse newline and `;` in commands; strict
  `stand_in_bot` names); `start-cs2.ps1` listens on 127.0.0.1 by default and points to .NET SDK 10.
- 2026-11-14, Arjun (Codex): recovered the local pipeline and resolved its spec rebase; added CloneDirector from the upstream plugin/controller starting points, purchase and route control, combat hand-offs, strict playback loading, AGPL notices, and deployment notes. Release build and 25 C# tests pass; all 80 donk route files load. Pipeline tests pass. In-game playback and service integration remain untested.

- 2026-11-14, Ashirwad: added RCON and MatchBridge plugin fallbacks for match service console
  commands, and `start-cs2.ps1` to set up the Windows PC. Tested against fake servers only.
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
