# CloneDirector

Applies the clone pipeline's purchases and opening routes to bots through CS2-Bot-Controller.
After damage, a nearby enemy shot, or the end of the route, playback stops and the installed
bot base resumes play. Only private matches on Mirage are supported.

**Checked here:** Release compilation, automated session/selection tests, and loading the real
both clone profiles plus all 159 donk/broky route files with the C# loader.
**Not checked here:** loading this plugin in CS2, bot creation/name matching, purchase aliases,
or whether generated playback makes a bot follow the real route. Passing the file checks does
not prove movement works in the game. The six-hour gate in `SPEC.md` section 11 is still open.

## Build

Odyssey extension: `clones/ODYSSEY.md` documents four authored/native-AI profiles with distinct
per-entry difficulty and 14 quirks each. `OdysseyMode.cs` adds pawn-scoped pre-damage rules (Poseidon
immune, Odysseus 1.08x enemy-player damage). Both updated DLLs and the native entries are required;
bare `bot_add` does not attach the rules. See `handoffs/tom-odyssey-bots.md` for installation and live
acceptance. No CS2 immunity or difficulty-balance result is claimed by the offline tests.

Needs .NET SDK 10 and `BotControllerApi.dll` from the **same installed controller release** as the
native plugin and provider on the gaming machine. Do not download/run the bot-base installer as
part of this build. A person installs that separately.

From the repository root, in PowerShell:

```powershell
# Copy the installed shared contract to clone-director/libs/BotControllerApi.dll first,
# or provide its absolute path as below. This builds CloneDirector, not the bot base.
$api = 'C:\path\to\game\csgo\addons\counterstrikesharp\shared\BotControllerApi\BotControllerApi.dll'
dotnet build clone-director/CloneDirector.csproj -c Release "-p:BotControllerApiPath=$api"
dotnet test clone-director/Tests/CloneDirector.Tests.csproj -c Release "-p:BotControllerApiPath=$api"
```

Tests need the repository's `clones/donk_v1` and `clones/broky_v1` files. They do not load any CS2 native libraries.
The `Private=false` reference keeps the contract out of the plugin's deployment folder; the
tests copy it only into their own test output folder.

## Install on the private game machine

A person performs these steps. This agent has not installed or started CS2-Bot-Improver.

1. Complete the manual bot-base install and the built-in `!record test` / `!stoprecord` /
   `!replay <slot> test` check from `HANDOFF.md` section 5.1.
2. Create `game/csgo/addons/counterstrikesharp/plugins/CloneDirector/`. Copy these build outputs
   from `clone-director/bin/Release/net10.0/` into it:
   `CloneDirector.dll`, `CloneDirector.Core.dll`, `CloneDirector.deps.json`, and
   `CloneDirector.runtimeconfig.json`. Include this directory's `LICENSE` and `THIRD_PARTY.md`.
   **Do not copy `BotControllerApi.dll` or CounterStrikeSharp's DLLs here.**
3. Copy the repository's `clones/` folder (profile JSON and its matching route directory) into
   that plugin folder. Alternatively set `CLONE_DIRECTOR_CLONES_DIR` to its absolute location
   before starting the game. Route file paths are relative to that clones folder.
4. Use the same controller release for the native plugin, provider, and shared contract.
   Load CloneDirector after the provider. If the provider is reloaded, reload CloneDirector too.
5. Start a **private** Mirage match in the bot base's offline mode (`-insecure`). Use the server
   console commands below. Public/official matches are outside this project's scope.

## Console commands

Commands accept server-console calls only, including commands sent through the match service's
console connection. They cannot be run from player chat or a player's client console.

```text
clone_add donk_v1 t
clone_list
clone_routes off
clone_routes recorded
clone_routes generated
```

`clone_add` loads/validates the profile and route files on a worker, then queues the named bot
command on the game thread. It waits up to five seconds for a **new** bot with that personality
name on the requested team. Requests are serialized; existing bots are never adopted. The
console prints failures (bad files, missing provider, wrong map, missing personality, full team).
Use `clone_list` to confirm the bot actually attached before ending warmup. A successful command
submission alone does not confirm attachment. Keep `bot_quota_mode normal` and avoid a quota
manager that removes added bots.

The personality name is `stand_in_bot` when present, otherwise `display_name`. The pipeline's
`botprofile.txt` currently defines a `donk` entry, and the bot base also documents a built-in
`donk` entry. This plugin does **not** repack `botprofile.vpk` or set aggression, weapon
preferences, reaction time, or teamwork at runtime. Without a manually installed custom entry,
purchases and routes use the existing named bot's personality. See the fallback in `SPEC.md`.

The match service defaults to stand-in bots and now supports `CS2_BOTS=clone`, using MatchBridge to submit CloneDirector commands. That integration is tested against fakes; live attachment/playback still needs verification. The commands above also support manual server-console testing. The service endpoints and profile fields are unchanged.

## Round behavior and current assumptions

- At round start/spawn, clear the previous purchase plan and choose the current side's aliases
  from `buy_plan[side][type].aliases`. Empty aliases explicitly skip purchases. Missing plans
  restore native buying. Pistol rounds are the first round and the configured halftime
  (`mp_maxrounds / 2`). Otherwise: under $2,000 is eco, $2,000–3,999 is force, $4,000+ is full.
  These money thresholds approximate the pipeline's equipment-value labels; tune in the game.
- When freeze time ends, choose only the current side, selected source (`recorded` or
  `generated`), and buy type. Routes without `buy_type` are usable at any money level. Group by
  `route_key`, sample with `route_shares[side][key]` (fallback: one share per label), then take
  that label's nearest spawn. Do not silently use a different side, source, or money type.
- Register the current pawn, load ticks/subticks/commands/history, then start playback.
  Natural completion, damage dealt/taken, death, a pawn change, a mode change, and round/map
  cleanup return control. Enemy shots within **1,200 Source engine units** also stop playback;
  this initial distance uses three dimensions, with no visibility or wall test.
- `clone_routes` stops current playback and takes effect next round. It does not switch paths
  mid-round. `clone_list` retains the route, source, and first hand-off reason until next round.
- Disconnect, map change, and unload stop owned playback and clear owned buy plans. No
  independent bot locks are acquired or removed. Hot reload does not adopt existing bots.
- All game/native API calls run on the game thread. File loading runs on a worker. A map/unload
  generation check discards stale file-load completions.
- `clone_record` and conversion of grenade throws are not implemented.

## Finish the playback gate

First prove a built-in hand recording replays. Find its file under the installed
`BotControllerImpl/recordings/` directory and return a copy for comparison. Then copy
`clones/donk_v1/routes/T/donk_v1_t_2393226_r13.json.br` there and run:

```text
!replay <T bot slot> donk_v1_t_2393226_r13
```

Pass: the bot walks donk's route. If it fails, compare against the real hand recording and
correct `clone-pipeline/clone_pipeline/recording.py`. Its key counters, crouch/ground state,
subtick input, command fields, and mouse deltas are still assumptions. If conversion cannot
be fixed, use hand-recorded versions of donk's routes as specified in section 11.

Then test `clone_add`, check `clone_list`, and start a new round. Confirm the purchase aliases
with `bc_buy <slot> ak47 vesthelm`, then verify natural completion and combat hand-offs. Record
the game evidence and outcomes in `SPEC.md` before calling the in-game clone complete.

Source credits and license: [THIRD_PARTY.md](THIRD_PARTY.md), [LICENSE](LICENSE).
