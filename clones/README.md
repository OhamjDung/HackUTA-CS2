# First data-built clones

Built for Mirage (`de_mirage`). These are profiles and movement files made from real match
recordings. They have not been proven inside CS2. The built-in professional presets under
`match-service/sample_clones/` are separate stand-ins.

| Clone | Building matches | Building rounds and routes | Held-back match | Held-back rounds | Extracted throws |
|---|---:|---|---|---:|---:|
| `donk_v1` | 4 | 80: 32 T, 48 CT | 2393242 | 17: 5 T, 12 CT | 164 |
| `broky_v1` | 4 | 79: 38 T, 41 CT | 2393024 | 22: 10 T, 12 CT | 182 |

Each profile has weapon preferences, positions, purchases, route shares, source-match IDs, and
comparison numbers. Each corresponding folder contains `botprofile.txt`, `buy_plan.json`,
`grenades.json`, `stats.json`, and one `.json.br` movement file per route. Both held-back matches
are excluded from the building matches and routes.

## What was checked

- Built broky from all five downloaded recordings, reserving one for comparison.
- Both profiles and all **159** route files load in CloneDirector's C# loader.
- Both profiles load through the match service's `load_clones()` catalogue reader.
- 10 pipeline tests, 26 CloneDirector tests, and 32 match-service tests pass.
- Corrected purchase execution order: main weapon, armor, then remaining items. The controller
  issues buy commands sequentially, so frequent grenade purchases must not consume the weapon
  budget first. Item membership and measured frequencies were retained in both bundles.

This does not prove the game accepts every alias, follows the converted movement, or plays at
the real player's strength. In-game playback, custom personality installation, and full match
recording still need the private-machine test in `clone-director/README.md`.

## How faithful are they?

Opening movement is cut from the player's own matches, up to 20 seconds or first contact/death.
After that, CloneDirector gives control back to the existing bot AI. No player-specific combat
or movement-generating model has been trained. Reaction time is unmeasured. Teamwork is fixed.
Extracted grenade throws are not yet installed into the grenade system.

The current weapon preference list counts shots, which favors automatic weapons over a sniper
rifle that fires fewer bullets. The single full-buy plan for both clones currently favors an
AK-47 on T and an M4A4 on CT. Broky's data includes AWP use, but this version does not reproduce
his full sniper purchase mix. The name alone does not make a bot a faithful sniper clone.

The profile's `aim_skill=1` and personality's `Skill=100` are settings, not proof of pro-level aim.
Until a bot match is recorded, there is no measured clone rank, win rate, or player-similarity
score. A useful expectation is a practice bot with player-specific opening tendencies; copying
the player's whole-round decisions and combat skill remains unproven.

The existing `similarity.player_vs_self` numbers compare each player's building matches with
their held-back match. **They are not clone performance or clone accuracy percentages.**

| Player / side | Position overlap | Route overlap | Building / held-back rounds |
|---|---:|---:|---|
| donk T | 0.621 | 0.421 | 32 / 5 |
| donk CT | 0.787 | 0.571 | 48 / 12 |
| broky T | 0.705 | 0.579 | 38 / 10 |
| broky CT | 0.733 | 0.297 | 41 / 12 |

These small samples show that even a real player varies between matches. In these samples,
cross-player position/route overlap sometimes exceeds a player's own held-back overlap, so
the scores do not yet establish reliable player identification.

## Use on the private game machine

Follow `clone-director/README.md`. Copy this whole `clones/` folder into the installed
CloneDirector folder, or set `CLONE_DIRECTOR_CLONES_DIR` to its absolute location. Once the
built-in recorder and one converted route have passed playback testing, use the server console:

```text
clone_add donk_v1 t
clone_add broky_v1 ct
clone_list
```

Confirm both bots attached before starting a new round. The live match service still adds
stand-ins; pointing its catalogue at these profiles alone does not activate CloneDirector.
Replay of movement through the bot controller is also separate from the proposed side-by-side
web replay page, which has not been built.

Data credit: Julien Blanchon / [OpenCS2](https://huggingface.co/datasets/blanchon/opencs2_dataset_demo),
CC BY 4.0. Original match recordings remain subject to their organizers' terms and are not included.

## Learned-quirk clones: `donkL` and `brokyL`

**Request to teammates: please add `donkL` and `brokyL` wherever `donk_v1` and `broky_v1` are
offered** (the lobby, the clone list, the demo pages). The "L" stands for "learned". Having both
lets us compare the learned version with what we have now.

What an L clone is: the same routes and purchases as the `_v1` clone, plus per-player quirk rules
fitted from the recordings by `clone-pipeline/clone_pipeline/quirks.py`. It is **not** the neural
model. The neural identity adapters failed their test and are not used
(`clone-model/results/diagnosis-2026-11-14.md`).

| Clone | Built on | Distinctive quirks | Applied in the game today | Measured only |
|---|---|---:|---|---|
| `donkL` | `donk_v1` | 10 | jumps 4.1 per minute; bursts of 4.2 shots on average, 26% single shots; crouches for 30% of bursts; sidesteps when still more than 11% of the time; Teamwork 100 | turning speed, flashbang share, first-kill share |
| `brokyL` | `broky_v1` | 10 | jumps 6.2 per minute; bursts of 2.6 shots on average, 64% single shots; crouches for 25% of bursts; sidesteps when still more than 19% of the time; Teamwork 90 | flashbang share, sniper rifle share |

Checked by running: 23 pipeline tests and 30 CloneDirector tests pass; both L profiles load in the
C# loader; the plugin compiles. **Not run in CS2.** The Teamwork number only takes effect if the
personality file is edited by hand.

Three things to know before a comparison:
1. An L clone uses the same installed bot name as its `_v1` clone (`stand_in_bot`). Two bots with the
   same name cannot join one match, so compare them in separate matches.
2. The L clone needs the CloneDirector build from this commit or later. An older build ignores the
   quirks and behaves exactly like `_v1`.
3. To score a recorded bot match against the real player:

```
cd clone-pipeline
uv run python -m clone_pipeline.quirks score --profile ../clones/donkL.json --demo <recording.dem> --name donk
```

The real players pass this test on their own held-back matches: donk 1st of 5 with 8 of 10 quirks,
broky 1st of 5 with 9 of 10. That is the ceiling for any clone.
