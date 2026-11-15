# Plan: v2 clones — v1's strength, L2's quirks, rule-based game sense

Written 2026-11-15 for Tom (Claude). A plan only: nothing here is built or run yet.
Owners to agree with: Arjun (CloneDirector, clone pipeline), Ash (match service, profile format).

## 1. Goal and priority order

Make `donk_v2` and `broky_v2`: built on `donk_v1` / `broky_v1`, carrying the quirks that `donkL2` / `brokyL2`
carry, and adding objective game-sense rules, while fighting as well as v1.

When two behaviours conflict, this order decides:

1. **Safety.** No self-kills, no wallhacks, private matches only.
2. **Quirks and fighting strength, equal top priority.** A game-sense rule never removes a quirk and never
   weakens the bot's aim below v1.
3. **Game sense.** Rules add awareness only where they don't break 1 or 2.

New version, new ids (AGENTS.md section 7): `donk_v2`, `broky_v2`. v1, L, L2 and LF stay unchanged as baselines.

## 2. What went wrong with the quirk versions (L / L2), from the code

| Problem testers saw | Cause (read in `CloneDirectorPlugin.cs`, not run) |
|---|---|
| **Ignored sound** | While a recorded route plays, the bot base's own AI has no control, and that AI is the only part that hears. The route stops only on damage taken or dealt, death, or an enemy **shot** within 1,200 units. Footsteps, reloads and an enemy in plain view do not stop it. |
| **No game sense** | The plan is fixed at freeze end: the same spawn + buy type + destination always gives the same route. The view angles come from the pro's other round, so nothing checks angles where enemies could be now. Run/walk buttons also come from that round, so nothing decides to walk quietly. |
| **Weaker than v1** | L2's bot entry has human aim settings (0.18 s reaction time, capped turn acceleration, softer stiffness, a fire delay). v1 and L use the bot base's original donk/broky entry, which reacts instantly. These were untuned starting values and are the most likely reason L2 felt worse. |
| **Walked backwards** | The restless quirk's sidestep made the bot base walk back to its spot. Already disabled in L2 (`quirk_controls_disabled.still_share`). |
| **Self-kills** | Cause unknown. Leading suspect: a route stopped while a grenade was pulled. My `DEATH` log line (uncommitted, on Tom's main checkout) is built to find out. |

## 3. Why not the neural model for this (measured today)

- **Speed:** one 4-second prediction took 6.5 s on Tom's RTX 3050 with the adapter merged, and about 2.1 s on Arjun's A100 (from his run log). The bottleneck is token-by-token decoding, not raw compute.
- **Map check:** of 18 paths generated with the Round 4 adapters and the base model, 0 passed Arjun's map check. They left the walkable map within 0.25–3 s, even with height snapped to the floor.
- **My reproduction was cut short:** my path error (295 units) was more than double Arjun's (129–133), from a harder moment. The run that would settle whether that comes from my setup was stopped before it finished.
- **Conclusion:** keep the neural model in the offline replay and proof pages. Game sense goes in as rules in CloneDirector, as asked.

## 4. Design: three layers in CloneDirector, on top of v1

```
freeze end ──> [A] route choice (varied)  ──> recorded route plays (v1)
                     │                              │  stop on information (R1, R2), never mid-grenade (R8)
                     │                              ▼
                     │                       [B] game-sense rules (R3 to R7) while walking
                     ▼                              │
               native bot AI fights with v1's full-strength aim
               [C] quirks stylise everything above (jump, burst, single shots, crouch shots)
```

Inputs are only what a human in that seat could know:
- the bot's own sight (a line-of-sight ray inside its field of view)
- sounds the game reports
- map knowledge measured from pro demos

Hidden enemy positions are never used to trigger anything. That rule is Arjun's, and it is right.

### Layer A — varied plans (fixes "same tactic every round")

- **R5 Route choice.** Draw among all routes to the chosen destination that start near the bot's spawn and match side and buy type, not only the nearest one. Lower the weight of a destination used in the last two rounds. Target: route variety (G7) inside the player's own range.

### Hand-off on information (fixes "ignored sound")

- **R1 Sound.** Listen to CS2's sound events (`EventPlayerSound`, `weapon_fire`, footstep/reload events) from enemies. If one is within the hearing range, stop the route and give control to the bot base's AI. Also remember a blurred "last heard" position. Starting ranges come from the old bot code (footstep 1,100, gunfire 2,000), as hypotheses. Step 0 checks what CS2 actually reports.
- **R2 Sight.** Each tick, test whether a living enemy is visible to the bot: inside a 90° view cone, within range, and with a clear line of sight from eye to head on the map mesh. If so, hand off. This replaces my temporary "enemy within 900 units" rule, which ignores walls.
- **R8 Grenade safety.** Never stop a route while a grenade is pulled. If the active weapon is a grenade and attack is held, wait until it is thrown or 1 s has passed. Confirm against the `DEATH` logs first.

### Layer B — game-sense rules while walking (fixes "no game sense")

- **R3 Check angles.** From pro demos, compute Mirage's common first-sighting spots: clusters of where enemies were first seen or killed. When the route approaches one that isn't visible yet, aim at it with the bot API's `LockTarget`. Target: pre-aim share (G3) inside the pro range.
- **R4 Sound discipline.** Before first contact, when there is a "last heard" enemy within about 1,500 units, or the route enters a contested area at a contested time (from pro-demo timing priors), switch to walking with `StartUsercmdMovement` (walk held). The player's own data sets how often this is allowed: donk runs more than most pros (`full_speed_share` z +1.1, `still_share` z -1.9), so his v2 walks less than broky's. Target: audible share near enemies (G1) inside the player's range.
- **R6 After a fight.** Keep the existing quiet window (`QuietUntil`) so quirks don't fire mid-fight. Do not re-peek the same angle within 3 s of taking damage from it: let the native AI reposition. A small rule, only if measurement shows repeat-peek deaths.
- **R7 React to the last-heard position.** If a sound was heard but no enemy is seen, turn toward the blurred position for 1–2 s. This is the old bot's documented behaviour, which the route replay currently blocks.

### Layer C — quirks keep priority

- **Source of the quirks (Tom, 2026-11-15): the two latest versions, `donkLF`/`brokyLF` and `donkL2`/`brokyL2`.** There is no L3 or L4. LF's quirk settings are identical to L2's: LF was made as a copy of L2 plus model metadata. On top of those, v2 takes the per-player movement-tempo targets from Arjun's Round 4 run: own pace, fast share and still share, measured from each player's training data in `clone-model/round4.py`. Those exist only inside the neural judge today, so step 0 exports them as numbers.
- **Applied in v2:**
  - **from L2:** jump rate, burst length, single-shot share
  - **re-enabled after a fix:** crouch at burst start (shorter hold), restless sidestep (send it as a movement nudge that doesn't move the bot's "home" spot)
- **Arbitration rule:** a game-sense rule may suppress a quirk only if the player's own demos show he also suppresses it in that context.
  - **Example:** broky's jumps (z +3.1) stay on during quiet walking unless his demos show he stops jumping when walking near enemies. Measure "jumps per minute while walking within 1,500 units of a heard enemy" before deciding.
  - **This needs context-split quirk rates.** `quirks.py` gets a context column (contact phase, walking or running, heard enemy or not).
- **Fighting strength:** v2 uses the original donk/broky bot entry, as v1 does, with no human-aim limits. Optional A/B: a mild variant (reaction 0.10 s, high acceleration) only if testers say v1 aim looks robotic. Strength is never traded for realism without a test.

## 5. Steps, in order

### Step 0 — measure first (laptop, no game)
1. `clone-pipeline/clone_pipeline/gamesense.py`: G1–G9 from Arjun's `ROUND4_GAME_SENSE.md` section 2, starting from `quirks.py` / `limits.py`, using demos already held. Output: `references/game_sense.json` with the population range and the donk and broky values.
2. First-sighting clusters for R3, and contested-area timing priors for R4, from the same demos.
3. Context-split quirk rates (section 4, Layer C) for the arbitration rule.
4. Check whether CS2 demos record `player_sound` and with which fields. If yes, they set R1's real ranges.

### Step 1 — safety and diagnosis (Tom's PC, one private match)
1. Commit my `DEATH` logging, then play v1 and L2 for a few rounds and read the `DEATH` lines. That confirms or rules out the grenade cause.
2. Get match recording working (`-Record tv`, never `record` over netcon). Every later step is scored from a recording.

### Step 2 — build v2 in CloneDirector (C#, Arjun's code)
In order, each with unit tests (now runnable on Tom's PC with `-p:BotControllerApiPath=...`):
1. R8 grenade safety
2. R2 sight hand-off, replacing the 900-unit rule
3. R1 sound hand-off
4. R5 route variety
5. R3 angle checks with `LockTarget`
6. R4 quiet walking
7. R7 turn toward a sound
8. the quirk fixes and the arbitration rule

New profiles `donk_v2.json` / `broky_v2.json`: copies of v1 plus quirk controls and a `game_sense` section holding the thresholds. Bot entries are plain copies of donk/broky, with no human aim.

Each rule gets its own on/off switch in the profile, so one rule can be tested at a time.

### Step 3 — test against the baselines (Tom's PC, recorded)
Run v1, L2 and v2 against the same opponents, each in an equal number of rounds, and score each recording on three tables:
- **Strength:** kills/deaths and round win rate. v2 must not be worse than v1 beyond noise.
- **Quirks:** the existing quirk test. v2 must keep L2's quirk scores.
- **Game sense:** G1, G2, G3, G7 and G8 inside the player's range; self-damage zero.
Then a short blind test: testers play v1 and v2 without knowing which, and say which feels more like the player.

## 6. Unknowns to settle early

| Unknown | How to settle | Blocks |
|---|---|---|
| What `LockTarget` does (aim lock? for how long?) | Read the bot base docs; one console test | R3, R7 |
| Whether CS2 fires `EventPlayerSound` for footsteps, and its fields | Log events for 2 minutes of a private match | R1 |
| Whether stopping a route cleanly hands control back with no stuck buttons | A `DEATH`/hand-off log in one match | R1, R2, R8 |
| Whether GOTV recording (`-Record tv`) works | One match | Step 3 |
| The self-kill cause | `DEATH` lines | R8 |

## 7. What this does not do

- No learned reasoning, and no reacting to things the bot couldn't perceive.
- Utility stays whatever the recorded route carries. Varied utility comes only from R5's route variety. A smarter grenade choice is later work.
- Teamwork and trading are left to the bot base AI.
