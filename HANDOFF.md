# Handoff: continue the clone build

Written 2026-11-14 by Claude, for the next coding agent (Codex). Read `AGENTS.md` and `SPEC.md` first.
This file says where the work stopped and what to do next. Delete it when the work below is done.

## 1. The goal

Arjun's instruction: "Frankenstein together the base CS bot, the cloning feature that takes in player
data and creates the working clones."

In plain terms: recordings of a player's CS2 matches go in. A bot that plays with that player's habits
and routes comes out, inside a real CS2 match. `SPEC.md` holds the full design.

## 2. Rules that apply to you

- **Update `SPEC.md` in every commit** (status board in section 0.2, the changed section, the change
  log in section 19). This is in `AGENTS.md`.
- **Start every feature from existing open-source code.** `SPEC.md` section 4.2 lists the starting
  point for each feature.
- **Keep "ran it", "read it", and "assumed it" apart** in everything you write.
- **Arjun's writing rules:** plain words, short paragraphs, define each term on first use, say the
  plain words first and the real name in brackets after. Say what you are about to do before you do
  it. Stop and tell him when something blocks you.
- **Arjun commits and pushes to `main` on this repository.** He chose that explicitly.
- **Never install or run CS2-Bot-Improver's files yourself.** A person does that on the game machine.

## 3. What is done

### 3.1 Clone pipeline: done and tested on real data

Location: `clone-pipeline/`. Python, `uv`, built on demoparser2.

| File | What it does |
|---|---|
| `clone_pipeline/parse.py` | Reads one match recording (`.dem`) into tables for one player |
| `clone_pipeline/routes.py` | Cuts each round's opening route: from "round goes live" until damage, death, or 20 seconds |
| `clone_pipeline/habits.py` | Weapons, aggression, positions, purchases, grenade throws |
| `clone_pipeline/recording.py` | Writes a route as a CS2-Bot-Controller playback file (`<name>.json.br`) |
| `clone_pipeline/similarity.py` | Compares two sets of rounds (positions, routes, timing) |
| `clone_pipeline/build.py` | The command that builds a clone |
| `tests/test_pipeline.py` | 9 tests on a small fake match. All pass. |

Run it from `clone-pipeline/`:

```bash
uv sync
uv run pytest
uv run python -m clone_pipeline.build --player donk --demos ../data/demos --holdout 2393242
```

**Windows note.** If the repository path is long, `uv` can fail to create `.venv`. Set the
environment variable `UV_PROJECT_ENVIRONMENT` to a short folder path. If pytest cannot write to the
temp folder, add `--basetemp <a folder you can write to>`.

### 3.2 The donk clone: built

Location: `clones/donk_v1.json` and `clones/donk_v1/`. Built from 4 of donk's Mirage matches (80
rounds: 32 T-side, 48 CT-side). Match 2393242 was held back for scoring.

| Output | Content |
|---|---|
| `clones/donk_v1.json` | The clone profile. Keeps the fields `match-service` reads, and adds more. |
| `clones/donk_v1/botprofile.txt` | An entry for the bot personality file (`botprofile.db`) |
| `clones/donk_v1/buy_plan.json` | Purchases per side and round type |
| `clones/donk_v1/grenades.json` | 164 grenade throws: position, view direction, type, time |
| `clones/donk_v1/routes/<T or CT>/*.json.br` | 80 playback files, one per round |
| `clones/donk_v1/stats.json` | The numbers used for similarity scoring |

Checked by running: `match-service`'s `load_clones()` reads `clones/donk_v1.json` without changes.

Measured values: aggression 0.52 (donk takes the round's first fight in 22% of rounds, more often
than 52% of the 25 other players in the same matches). Weapons: `ak47`, `m4a1`, `galilar`.

**donk compared with his own held-back match** (the ceiling for any clone):

| Side | Position overlap | Route overlap | Rounds (build, held back) |
|---|---|---|---|
| T | 0.62 | 0.42 | 32, 5 |
| CT | 0.79 | 0.57 | 48, 12 |

The held-back T sample is only 5 rounds. Treat the T numbers as weak.

### 3.3 Match recordings: downloaded, not in git

`data/demos/` holds donk's five Mirage recordings from the OpenCS2 dataset (2.2 GB). `.gitignore`
blocks them. `SPEC.md` section 7.2 lists the file paths. Download command for one file:

```bash
curl -L -o data/demos/2393226_spirit-vs-falcons-m2-mirage.dem https://huggingface.co/datasets/blanchon/opencs2_dataset_demo/resolve/main/demos/shard-europe-17bc5760/2393226/spirit-vs-falcons-m2-mirage.dem
```

The file name must start with the match ID and an underscore. `parse.py` reads the match ID from it.

## 4. What was found along the way

These facts cost time to find. Do not rediscover them.

1. **demoparser2 gives everything needed.** Per tick: position, velocity, view angles, keys, duck
   state, map area name (`last_place_name`), weapon, money. Events: `item_purchase`, `weapon_fire`,
   `player_hurt`, `player_death`, `round_freeze_end`, `round_end`.
2. **demoparser2 does not return the `flags` field,** although it accepts the name. The playback
   file's `EntityFlags` is rebuilt from duck state and vertical speed. This is an assumption.
3. **A gunshot is not a fight.** Professionals fire at nothing while leaving spawn. "Met an enemy"
   means damage dealt or taken.
4. **Exact purchase lists do not repeat,** because players buy items to drop for teammates. The
   purchase plan is "items bought in at least half the rounds of that type". A force or full buy
   always gets a gun and armor, because survivors keep theirs and do not buy again.
5. **The playback file format.** Brotli-compressed JSON:
   `{FormatVersion: 1, Tickrate: 64, Ticks: [...], Subticks: [...], Commands: [...], InputHistory: base64}`.
   Field names are in CS2-Bot-Controller's `csharp/BotControllerApi/Types.cs`. The loader rejects a
   file with any missing field (except fields named `Pad*`). Source:
   `csharp/BotControllerImpl/MotionRecording.cs`.
6. **Playback files can be tested with no new plugin.** CS2-Bot-Controller's own chat command
   `!replay <slot> <name>` loads `<name>.json.br` from its `recordings` folder
   (`game/csgo/addons/counterstrikesharp/plugins/BotControllerImpl/recordings/`, to be confirmed on
   the machine).
7. **This development machine has no CS2.** Codex installed a local .NET 10 SDK and compiled
   CloneDirector. Its 25 C# tests pass, including loading all 80 donk files. Nothing in the game
   was run. See `SPEC.md` section 3 and `clone-director/README.md`.

## 5. What is not done, in order

### 5.1 First: test one playback file in the game (needs a person at the game machine)

This is the highest-risk unknown in the project. `SPEC.md` calls it the 6-hour gate.

1. A person installs CS2-Bot-Improver on the Windows gaming laptop (its README has the steps).
2. Start a bot match on Mirage. In chat: `!record test`, walk a few seconds, `!stoprecord`, then
   `!replay <bot slot> test`. This proves playback works at all.
3. Find the saved `test.json.br`. **Send a copy back.** Compare it with one of our files using
   `clone_pipeline.recording.read_recording()`. Fix `recording.py` wherever our values differ from a
   real recording: `Subticks`, `Buttons1`, `Buttons2`, `EntityFlags`, `MoveType`, `DuckSpeed`,
   `Commands[].Fields`, `MouseDx`, `MouseDy`. All of these are guesses today.
4. Copy `clones/donk_v1/routes/T/donk_v1_t_2393226_r13.json.br` into the `recordings` folder. Run
   `!replay <slot of a T-side bot> donk_v1_t_2393226_r13`.
5. Pass: the bot walks donk's route. Fail: use the fallback in `SPEC.md` section 11 (a person walks
   donk's top routes while `!record` captures them).

### 5.2 Second: the CloneDirector plugin (implemented by Codex; not run in CS2)

Location: `clone-director/`. Release build and 25 C# tests pass. Read `clone-director/README.md`
for deployment, current behavior, and remaining game checks. The notes below preserve the original
starting plan; the implementation is now present. Match-service integration still uses stand-ins.

**Starting points:**
- Project file: copy CS2-Smarter-Bot's `BotState.csproj`. It targets `net10.0`, uses the package
  `CounterStrikeSharp.API` version `1.0.378`, and references `libs\BotControllerApi.dll` with
  `<Private>false</Private>`.
- Getting the interface: CS2-Bot-Controller's `TECH.md`:
  `new PluginCapability<IBotControllerApi>("botcontroller:api")`, fetched in `OnAllPluginsLoaded`.
- Event handling pattern: CS2-Smarter-Bot's `BotState.Lifecycle.cs`.
- Loading a playback file: copy `LoadFromFile` and its `JsonOpts` from CS2-Bot-Controller's
  `MotionRecording.cs`. The types `ReplayTick`, `SubtickMove`, and `ReplayCommandFrame` are in the
  interface library.

**Behavior to build** (`SPEC.md` sections 6.2 and 6.3):

| Step | What the plugin does | Interface call |
|---|---|---|
| `clone_add <clone_id> <t or ct>` | Reads `clones/<clone_id>.json`. Adds a bot. Links the bot's slot to the clone. | Server command `bot_add_t` or `bot_add_ct` |
| Round start | Picks the purchase list for the bot's side and round type, from `buy_plan` in the profile | `SetBuyPlan(slot, "alias alias ...")` |
| Round goes live | Picks a route: weighted by `route_shares[side]`, then the entry in `routes[side]` whose `start` is nearest the bot | `SetReplayPawn`, `LoadReplay`, `StartReplay` |
| The bot is hurt, hurts someone, or an enemy fires nearby | Stops playback so the bot base takes over | `StopReplay` |
| `clone_list` | Prints each clone bot, its last route, and why playback stopped | none |
| `clone_routes <recorded, generated, off>` | Chooses which route files to play | none |

**Unknowns to resolve on the game machine:**
- How to add a bot that uses a named entry of the personality file. CS2-Bot-Improver's
  `Commands.txt` has working examples of adding named professional bots. Read it.
- CS2-Bot-Improver ships the personality file inside a packed archive (`botprofile.vpk`). Adding
  `clones/donk_v1/botprofile.txt` to it means repacking that archive. Fallback: use an existing
  professional entry and apply only purchases and routes.
- Whether the names in `buy_plan.json` (`aliases`) are the names `SetBuyPlan` accepts. Test with the
  console command `bc_buy <slot> ak47 vesthelm`.
- The round-type rule for a bot. The pipeline names a round by the player's equipment value when
  the round goes live (`routes.buy_type`). A bot has not bought yet at round start, so use its money.

### 5.3 Third: everything else in `SPEC.md` section 0.2

Codex built `broky_v1`: four real Mirage matches, 79 routes, and match 2393024 held back (22 rounds).
Both clones' purchase order was corrected; 10 pipeline, 26 C#, and 32 service tests pass. All
159 routes load in C#. See `clones/README.md` for the current evidence and limits.

Remaining priority order: pass the in-game playback gate, record a clone match and score it with
`similarity.compare()`, build the replay page, train the generating model (`SPEC.md` section 8),
and connect CloneDirector to the real match service. None of these is established by file tests.

## 6. Known limits of the current pipeline

- `reaction_ms` is `null` in the profile. Recordings do not say when an enemy became visible.
- `Teamwork` is fixed at 100. Measuring it needs the teammates' positions, which `parse.py` does not read.
- Routes are grouped by where they end (`route_key`). Two different paths to the same area count as
  one route. The full path is kept in each route's `label`.
- The aggression number compares the player only with others in the same matches.
- Grenade throws are extracted but not yet converted to CS2-Bot-NadeSystem's data format. That
  format has not been read.
- The 20-second limit often ends a T-side route while the player is still walking.

## 7. One open question for Arjun

The team's "Interface specs doc" is referenced by `match-service/` but is not in the repository. The
clone profile format in `SPEC.md` section 5.4 follows the code, not that doc. Ask for the doc.
