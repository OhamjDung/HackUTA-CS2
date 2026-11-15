# For Arjun: please check Tom's `donkLF` / `brokyLF` clones

From Tom's Claude session, 2026-11-15. Addressed to Arjun; delete this file when you have answered it.
Branch: `worktree-models-plumbing` (not committed or pushed when this was written).

## What Tom asked for

Add the newest trained models you pushed as clones named `donkLF` and `brokyLF`, played the way `donkL2` / `brokyL2` are.

## What I did (and what it is not)

I did **not** put the neural models into the game. Your release notes and results say the adapters generate
movement/view paths and nothing yet turns those paths into route files, so there was nothing to play. What I
added is the name and the plumbing:

- `clones/donkLF.json`, `clones/brokyLF.json`: copies of `donkL2` / `brokyL2` (recorded routes, quirks, same
  `quirk_controls_disabled`), with `clone_id`, `display_name` and `stand_in_bot` set to the new id and a
  `model` object naming the Round 4 adapter (see "Model check" below) and `routes_generated: false`.
- `clone-director/tools/add_clone_bot_entries.py`: `donkLF` and `brokyLF` added to `COPIES` and
  `HUMAN_AIM_IDS` (human aim like L2). The in-game names only exist after this tool is run on
  `botprofile.vpk` with CS2 closed.
- `match-service/match_service/drivers.py`: a profile whose `model` is an object with
  `routes_generated: false` is listed playable with recorded routes and labelled "(model adapter not converted
  to routes yet)", and as **not playable** when `CS2_CLONE_ROUTES=generated`.
- `match-service/tests/test_lf.py` (2 tests), SPEC.md status row and change-log line.

Behaviour in the game today: `donkLF` plays exactly like `donkL2`, `brokyLF` like `brokyL2`.

## Model check: which model the `model` field names

| Player | Named in the profile | From | Matches your results file? |
|---|---|---|---|
| donk | `round4-development-v1`, selected iteration 4 | `clone-model/results/round4-development.json` (`best_iteration` 4) | yes |
| broky | `round4-development-v1`, selected iteration 1 | same file (`best_iteration` 1, all 4 iterations ran) | yes |

Zip: `Round4-development-v1.zip`, 19,460,680 bytes, sha256 `82f8ad35...169e3a` (from `gh release view`, and
equal to the hash in `round4-development.md`). **I did not download or open the zip**, so I have not seen the
adapter files myself; "contains the adapters" comes from your notes.

Please decide if this is the right model to name. Two candidates exist for donk:
- `round4-development-v1`: newest, but unvalidated and it fails your view gate (turn error worse for both players).
- `donk-imagined-v1`: the only donk model that passed a declared test (test-C), but it was trained before the
  game-sense work, and there is no broky equivalent.
Tom asked for "the newest", so I used Round 4. If you want `donkLF` tied to `donk-imagined-v1` and `brokyLF` to
Round 4 broky, or different names, say so.

## What was run, and what was not

Ran (fakes only, nothing in CS2):
- `uv run python -m pytest tests -q` in `match-service`: 74 passed, 1 failed (`test_path_traversal_is_refused`,
  the known Windows symlink failure).
- `python -m pytest clone-director/tools`: 3 passed.

Not run / not known:
- **C# profile loader with the new `model` object.** `Profiles.cs` deserializes with
  `PropertyNameCaseInsensitive = false`; I found no `model` member in `Core/*.cs` and expect unknown properties
  to be ignored (System.Text.Json default), but I have not run it. C# tests cannot run on Tom's PC.
  **Please run your C# profile-loading tests on `clones/donkLF.json` and `clones/brokyLF.json`.**
- Whether CloneDirector attaches `donkLF` / `brokyLF` in a real match. The first attempt failed earlier:
  `no profile for 'donkLF' exists` came from the bot base, because `botprofile.vpk` had reverted to the original.
  Nothing reached CloneDirector's loader, so the profile was not tested. That also affected `donkL2`.
- Any match with these clones.

## Things I saw on Tom's PC that you may want to know

- CS2 crashed once, 3 s after a match entered warmup: `cs2_2026_1115_042817_0_accessviolation.mdmp`, fault in
  `engine2.dll` offset `0x22523` (read from the dump's exception record). No plugin frame was identified. Cause
  unknown; it did not recur on the next launch. Not clearly related to these clones.
- After that crash both `game/csgo/gameinfo.gi` and `overrides/botprofile.vpk` were back to their original
  content. I do not know what restores them. They were reinstalled by hand. If you know, please say.

## Questions for you

1. Is it right to put a `model` **object** in a clone profile? The profile format is yours and Ash's
   (AGENTS.md section 6). Until now `model` was a string or null. If you prefer a string, I will change it and
   keep the status in another field.
2. Do you want the LF names at all before routes exist, given they behave like L2?
3. When you have generated route files for the Round 4 adapters: the route source is global per match
   (`clone_routes recorded|generated`), so `donkLF` on generated routes cannot share a match with `donkL2` on
   recorded routes. Do you want per-clone route source in CloneDirector, or should the LF routes be installed
   as ordinary routes under the LF profile?
4. Anything in the profile that should differ from L2 for a model-based clone?

## Not part of this review (uncommitted on Tom's main checkout)

Enemy-close hand-off and `DEATH` logging in `CloneDirectorPlugin.cs` / `Core/Combat.cs`, the `_settle_bots`
extra-bot fix, `loop.py` and `donkL2` / `brokyL2` are all uncommitted there. They are separate from this change.
