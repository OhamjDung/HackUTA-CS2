> Recovery/review note (Codex, 2026-11-15): this is Claude's recovered uncommitted DESIGN, not implemented training. Read handoffs/mvp-round4-continuation.md before implementation. Corrections: generated.py and map review/viewer tools already exist; adapt them. ReGameDLL hearing rules are historical proxies, not verified CS2 values. Never use true hidden enemy positions for runtime triggers/quiet movement. Preserve quirks within safe/human bounds, not above them. Condition broky/donk targets on context; do not infer a universal walking order. A 4 Hz, four-second model cannot establish sub-tick reactions or full-round tactics. New final tests must use fresh matches. The continuation handoff specifies actionable stages and acceptance.

# Round 4 plan: game sense for the donk and broky clones

Written 2026-11-15 for Arjun, after a tester's feedback on the clone bots. Nothing in this plan has been
built or run yet. The research behind it, with sources, is `clone-model/research/cs2-game-sense.md`.

## 1. The feedback, and what causes each problem

The tester said, in short:

1. The bot plays one tactic every round, for example mid to A with the pro's smoke and flash.
2. It does not change its plan when the tester is there, makes noise, or shoots at it.
3. It does not check angles.
4. It does not use utility to trick the opponent (varied smokes and flashes).
5. It makes noise and gives away its position; a pro would not.
6. It kills itself (cause unknown: Tom's agent diagnoses it, `handoffs/tom-self-kill-diagnosis.md`).
7. It has no game sense overall.

The bots testers play today are the **rule-based clones** (`donk_v1`, `broky_v1`, `donkL`, `brokyL`). They
replay a recorded pro route, then hand over to the game's own bot. The learned model is not in the game
yet: nothing converts its generated paths into bot routes (SPEC 8.12). So the causes are in the clone
plugin, read from `clone-director/CloneDirectorPlugin.cs` and `clone-director/Core/Profiles.cs`:

| Problem | Cause in the code (read, not run) |
|---|---|
| 1. Same tactic every round | At freeze end, `Choices.Pick` draws a destination by the pro's share, then always takes the route whose start is **nearest the spawn**. Same spawn + buy type + destination = the identical route. donkL T side: 32 routes, 11 destinations, but 12 routes (38% of rounds) go to Top of Mid. |
| 2. Ignores noise and the opponent | A replay stops only when the bot is hurt, deals damage, dies, or an enemy **fires** within 1200 units. Seeing an enemy, or hearing footsteps, does not stop it. While a replay plays, the game's bot (which does hear, see below) has no control. |
| 3. Does not check angles | The replay plays the pro's view angles from a different round: the pro looked where *his* enemies were. Nothing aims at where enemies could be now. |
| 4. Same utility | Utility comes only with the replayed route, so it repeats with the route. |
| 5. Loud | The replay copies the pro's walk/run buttons from another round; after hand-over, the game's bot runs. Nothing decides to walk because an enemy may hear. |
| 7. No game sense | All of the above: plans are fixed before the round and never change on information. |

## 2. What "game sense" means here, in objective terms

Game sense is not measured directly. We measure **behaviour that a player with game sense shows**, from
demo data (positions, speed, view angles, buttons, shots, grenades, damage, deaths). Nine measures, G1 to
G9. Each is computed the same way for real pro demos, for the bots' GOTV recordings, and for the learned
model's generated play.

Notation: "audible" uses the game's own bot hearing rules (ReGameDLL_CS `bot_util.cpp`, read by the
research): running footsteps are heard within **1100 units** and only above **150 units/s** horizontal
speed (crouching never makes a footstep event); normal gunfire within **2000 units**; AWP shots and HE
explosions everywhere. Valve has not published CS2's own values; community guides quote about 1100. We use
these as the starting definition and check them against CS2 in step 0.

| # | Behaviour | Measure from demo data | Starting threshold (a proposal; calibrate on pro demos in step 0) |
|---|---|---|---|
| G1 | **Sound discipline** | Share of alive time that is *audible to an enemy who has not yet seen you*: speed > 150 u/s, not crouched, within 1100 units of an enemy, before first contact in the round | Within the player's own range (see section 3) |
| G2 | **Reacts to sound and gunfire** | After an enemy becomes audible to the player, or fires within 2000 units, or hits the player: does the player, within 1 s, turn the view to within 30 degrees of the source, or change movement (stop, go silent, or move more than 100 units away within 2 s)? Share of events and median delay | Within the pro range for share and delay |
| G3 | **Checks angles (pre-aim)** | Spots where enemies are often first seen on Mirage (clusters of first-sighting and kill positions from all pro demos). Share of time, while moving towards such a spot before it is visible, that the crosshair is within 5 degrees of it | Within the pro range |
| G4 | **Peeks with control** | Speed at the first shot of a burst below 34% of the weapon's top speed (Leetify's definition); exposure time of jiggle peeks | Already partly a quirk (`rifle_speed_at_first_shot`) |
| G5 | **Utility before a fight** | Share of first fights preceded within 2 s by the player's own or a teammate's flash or smoke on that area | Within the pro range |
| G6 | **Varied utility** | Group throws by (thrown-from area, landing area). Entropy of the groups per side and half | At least the player's own entropy |
| G7 | **Varied plans across rounds** | Group rounds by route (sequence of map areas). Entropy per side; longest run of identical routes | At least the player's own entropy; no 3 identical rounds in a row unless the player does it |
| G8 | **Changes plan on information** | After contact or hearing an enemy in the first 40 s, share of rounds where the player leaves the planned route (moves away from the route's next area within 5 s) | Within the pro range |
| G9 | **Stays alive sensibly** | Self-damage (own HE or fire, fall damage); deaths without a trade by a teammate within 5 s (HLTV's trade window); distance to nearest teammate | Self-damage: zero; the others within the player's range |

The research found **no published pro numbers** for G1, G2, G3, G5, G7 or G8. Step 0 therefore measures
them on our own demos: all pros in the CS-NET training data (the "population") and donk and broky.

## 3. Quirks first

The user's rule: **quirks hold priority over shared pro technique.** This rule makes it exact:

- Every measure, quirk or game sense, gets its target from **the player himself**, never from an average
  pro.
- A measure on which the player is **distinctive** (|z| at least 1 against the population, as in
  `quirks.py`) is held tightly to the player's value.
- A measure on which he is ordinary only has to stay **inside the pro population's range**.
- When a game-sense habit and a quirk disagree, the quirk wins.

Why this matters: donk's measured quirks include running more and standing still less than other pros
(`full_speed_share` z +1.1, `mean_speed` z +1.5, `still_share` z -1.9). So "quieter" must not mean "walk
like an average pro". The target for G1 is donk's own audible share near enemies, which may be higher than
other pros', but must be lower than the bot's now. broky's quirks (jumps z +3.1, AWP shot share z +2.7,
fewer slow-walking moments z -1.35) stay as they are, while G1 to G9 are added.

## 4. The plan, in order

The rule-based clones are what testers play now, so they come first. The learned model gets the same
measures in its training and judge, so it is ready when the converter exists.

### Step 0: measure (laptop, no GPU)

1. `clone-pipeline/clone_pipeline/gamesense.py`: compute G1 to G9 from a demo, for one player or all.
   Start from `quirks.py` and `limits.py` (same data and the same table output). For G3, cluster
   first-sighting positions; visibility uses the Mirage mesh ray cast already in `clone-model/map_review.py`
   (from CS-NET).
2. Run it on the pro population (the CS-NET demos we hold) and on donk and broky. Write
   `clone-pipeline/references/game_sense.json`: the population range for each measure, and each player's
   value and z.
3. Check the hearing values against CS2: does the CS2 demo record the `player_sound` event (fields `Radius`,
   `Duration`, `Step`)? If yes, use it to find CS2's real footstep range and silent speed and replace 1100
   and 150.
4. Add G1 to G9 to the quirk test report, so a bot's GOTV recording gets one table: quirks, game sense,
   human limits.

Done when: the table exists for donk, broky and the population; the thresholds in section 2 are replaced
by measured ranges.

### Step 1: rule-based clones react and vary (C#, `clone-director`)

1. **Stop the replay on information** (problem 2). Besides damage and nearby fire, stop when an enemy
   becomes **visible** to the bot, or **audible** by the hearing rules above (enemy running within 1100
   units, firing within 2000, any AWP shot or HE). After the stop, the game's own bot has control, and it
   already investigates noise (it remembers one noise for 3 s and goes to look with a chance of
   1 - distance/2000; research section on bot hearing). Keep `QuietUntil` so quirks do not fire during it.
2. **Vary the plan** (problems 1 and 4). In `Choices.Pick`: draw among *all* routes of the chosen
   destination that start from the bot's spawn area, not only the nearest one; and lower the weight of a
   destination used in the last two rounds, so that the bot's route entropy (G7) matches the player's.
   Utility varies with it, because it comes with the route.
3. **Walk when an enemy could hear** (problem 5). After hand-over, while no enemy has been seen and the
   bot is within 1100 units of a likely enemy area, hold walk, at the rate the player himself walks there
   (G1, from step 0). donk will walk less than broky, as the quirks say.
4. **Look at the angles** (problem 3). After hand-over, when moving towards a common enemy spot (G3
   clusters) that is not visible, aim at it. This uses the bot controller's existing aim injection.
5. **Fix the self-kills**, once Tom's diagnosis names the cause. The leading suspect from the code: a replay
   stopped while the bot holds a pulled grenade.

Done when: on Tom's PC, a GOTV recording of clone bots scores inside the player's range on G1, G2, G7
and G8, has no self-damage, and still passes the quirk test. Then a short blind people test (tier 2).

### Step 2: learned model training changes (Colab)

Starting point: `clone-model/imagine.py` (passed on test-C). Changes:

1. **Judge.** The kept imagined future is chosen by a score, not by path distance alone:
   path distance to the real future + view distance to the real future (fixes the view drift seen in
   round 4 of `imagine.py`) + penalties for breaking G1 or G2 against the player's own range + the
   human-limit filter. Quirk measures weigh more than game-sense measures (section 3).
2. **Fog of war.** CS-NET sees all ten players' positions, so it can "know" where enemies are without
   hearing or seeing them. In training, replace an enemy's state with the last state the cloned player
   could have known (seen, or heard by the rules above). Then reacting to sound has to be learned from
   sound. This is the change with the most risk: test it on dev rounds against the plain model first.
3. **Keep variety.** Keep up to the best 2 distinct futures per moment, not 1, and check that the spread
   of generated routes (G7) does not shrink from round to round. Round 4 of `imagine.py` became more
   predictable (its best-of-8 got worse).
4. **Plan conditioning (stretch).** As AlphaStar did with its strategy statistic, give the model the round's
   planned route (destination area) as an extra input, drawn at play time from the player's own shares,
   and hidden 10% of the time in training. This gives variety on demand.
5. **broky.** `donk.py` and `imagine.py` hard-code `PLAYER = "donk"`. Add `--player`, then run everything
   for broky too.

### Step 3: data, and a fair final test

All of donk's held-back data is used: the two final-test matches (round 2), dev-B and test-C. A new final
test needs **new matches**: download further Mirage demos of donk and of broky (OpenCS2 or HLTV), keep
them out of everything, and fix the pass rule before the run. The chess research (Maia) warns that a model
per player gained little until thousands of games per player; we have about 47 rounds each, so more data
is the most likely single gain. broky was benched by FaZe in June 2026; his 2026 matches may show weak form.

### Step 4: pass rules, fixed before the run

For the rule-based clones (on GOTV recordings of private matches) and for the learned model (on generated
play, until the converter exists), on the new matches:

- **Quirks:** the quirk test passes, as now.
- **Game sense:** G1, G2, G7 and G8 inside the player's own range (section 3); G9 self-damage zero.
- **Human limits:** `limits.py` passes.
- **People:** in a blind panel, players do not pick the clone as "a bot" more often than chance; this is
  the final judge, as in `ROUND3_DESIGN.md` section 5.

## 5. Not known yet

- How the bots kill themselves (Tom's diagnosis).
- CS2's real footstep range and silent speed (step 0, point 3).
- Pro values for G1, G2, G3, G5, G7, G8 (step 0).
- Whether fog of war helps or hurts the learned model (step 2, point 2).
- How the learned model gets into the game: the converter from generated paths to bot routes is still not
  built.
