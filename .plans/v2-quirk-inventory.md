# Quirk inventory across all versions, and the v2 quirk list for donk and broky

Checked 2026-11-15 against GitHub `main` at `02e13af`: clone profiles, `CloneDirectorPlugin.cs`, `quirks.py`,
`gamesense_audit.py`, `results/round4-training-proxies.json`. Read from files; nothing here was run in CS2.

## 1. What each version actually has

| Version | Routes | Quirks applied in the game | Aim | Game sense / sound |
|---|---|---|---|---|
| `donk_v1`, `broky_v1` | recorded pro routes | none; profile habits only (weapons, buy plan, aggression 0.52 / 0.333) | bot base's original entry (instant reaction) | none |
| `donkL`, `brokyL` | same as v1 | jump rate, burst length, single-shot share, crouch at burst start, restless sidestep | original entry | none |
| `donkL2`, `brokyL2` | same | jump rate, burst length, single-shot share (crouch and restless switched off) | **human aim limits** (0.18 s reaction, capped turning) | none |
| `donkLF`, `brokyLF` | same | identical to L2 | identical to L2 | none |
| Round 4 neural model | not in the game | per-player tempo targets inside its training judge only | n/a | offline noise proxy in its judge only |
| main's CloneDirector (all clones) | — | — | — | hand-off when an enemy **fires** within 1,200 units, or (my addition) is within 900 units with no wall check |

**Answer to "do we have sound/game-sense quirks implemented?": no.** No version has sound or game-sense
behaviour in the bot. Arjun **measured** them offline in `gamesense_audit.py`. That is useful as targets,
but no bot uses it.

## 2. All 27 measured quirks, per player

z = how far the player is from the pro population (|z| at least 1 = distinctive). "Applied" = CloneDirector drives it in L/L2/LF.

### donk (distinctive ones in bold)

| Quirk | donk | Pros' mean | z | Status today |
|---|---:|---:|---:|---|
| **Jumps per minute** | 4.1 | 1.7 | +1.22 | applied (L, L2, LF) |
| **Still share** (time standing still) | 0.109 | 0.196 | -1.91 | sidestep built, switched off in L2/LF (walked backwards) |
| **Full-speed share** | 0.296 | 0.246 | +1.11 | not applied |
| **Mean speed** (u/s) | 128.9 | 112.8 | +1.46 | not applied |
| **Look speed** (deg/s) | 4.4 | 2.4 | +1.37 | not applied ("bot interface has no view control" — see 4) |
| **Peek-left share** | 0.44 | 0.52 | -1.08 | not applied |
| **Flash share** of grenades | 0.18 | 0.27 | -1.03 | not applied (grenades come from routes and buy plan) |
| **Opening-duel rate** | 0.31 | 0.19 | +1.30 | not applied (bot entry Aggression could) |
| **Team distance** (units) | 694 | 1,047 | -1.39 | not applied |
| **Alone share** | 0.169 | 0.407 | -1.86 | not applied |
| Single-shot burst share / shots per burst | — | — | -0.66 / +0.26 | applied (not distinctive) |
| Crouched-shot share | — | — | +0.13 | built, switched off |
| 15 others (pitch spread, crouch time, knife out, first-shot speed, …) | | | under 1 | ordinary: keep inside the pro range |

### broky

| Quirk | broky | Pros' mean | z | Status today |
|---|---:|---:|---:|---|
| **Jumps per minute** | 6.2 | 1.1 | +3.08 | applied (L, L2, LF) |
| **Slow share** (walking or crouching) | 0.434 | 0.514 | -1.35 | not applied |
| **Knife-out share** | 0.234 | 0.182 | +1.08 | not applied |
| **Single-shot burst share** | 0.637 | 0.388 | +1.86 | applied |
| **Shots per burst** | 2.6 | 3.8 | -1.46 | applied |
| **Turn before shot** (deg) | 1.09 | 1.80 | -1.11 | not applied (he pre-aims) |
| **AWP shot share** | 0.108 | 0.012 | +2.70 | not applied (buy plan favours M4; README says AWP not reproduced) |
| **Flash share** of grenades | 0.43 | 0.26 | +1.84 | not applied |
| **Fire (molotov) share** | 0.171 | 0.248 | -1.20 | not applied |
| **Alone share** | 0.222 | 0.372 | -1.03 | not applied |
| Crouched-shot share, still share | — | — | -0.37 / +0.43 | built, switched off |
| 15 others | | | under 1 | ordinary |

### Game-sense and sound measures (Arjun's `round4-training-proxies.json`, training rounds only)

| Measure | donk | broky | Meaning |
|---|---:|---:|---|
| Fast (>150 u/s) share | 0.359 | 0.328 | time running |
| Still (<4 u/s) share | 0.081 | 0.189 | time standing |
| Noise proxy | 0.078 | 0.083 | share of time running within hearing range of an enemy |
| Sound response share | 0.385 | 0.363 | turns toward / reacts to an enemy sound within 1 s |
| Sound response median | 0.5 s | 0.5 s | delay (4 Hz data: not finer than 0.25 s) |
| Active AWP share | 0.0 | 0.266 | time holding an AWP |

Hearing radii (1,100 footsteps, 2,000 gunfire) and the 150 u/s cut are historical CS1.6 values, not verified CS2. Arjun says so too.

## 3. The v2 list: what makes each better than v1

v2 = v1's routes and full-strength aim + every distinctive quirk we can drive + game-sense rules held to each player's measured targets. Quirks and strength are top priority (plan: `v2-quirks-gamesense-plan.md`).

### Shared by both (game sense and sound, new code in CloneDirector)

| # | Rule | Target from the player's data | Exists? |
|---|---|---|---|
| G-1 | Stop the route and fight when an enemy is **heard** (CS2 sound events) | react within about 0.5 s, about 36–39% of sounds (response share) | new |
| G-2 | Stop the route when an enemy is **seen** (own view cone + line of sight), replacing the 900-unit rule | — | new (the 900-unit rule exists) |
| G-3 | **Check angles**: aim at common first-sighting spots before reaching them (`LockTarget`) | pre-aim share inside pro range; for broky also his low turn-before-shot | new |
| G-4 | **Quiet movement** near a heard enemy | keep each player's noise proxy (donk 0.078, broky 0.083), not lower | new |
| G-5 | **Turn toward a heard sound** when nothing is seen | 1–2 s, as the old bot does | new |
| G-6 | **Varied routes**: all fitting routes, avoid repeats | route variety inside the player's range | new |
| G-7 | **Never stop a route mid-grenade** (self-kill safety) | zero self-damage | new |
| — | Full-strength aim: original bot entry, **no human-aim limits** | v1's kill/death rate or better | exists (v1 entry) |

### donk_v2 quirks

| Quirk | How it is driven | Exists? |
|---|---|---|
| Jumps 4.1/min while running | CloneDirector jump injection | **exists** |
| Burst length, single shots (his values) | trigger release | **exists** |
| Rarely still (0.109) | sidestep re-enabled with a fix: a movement nudge that doesn't move the bot's home spot | fix needed |
| Runs more (full-speed 0.296, speed 129) | G-4 allows running up to his noise proxy; quiet walking only near a heard enemy | new, part of G-4 |
| Fast look (4.4 deg/s, z +1.37) | keep the original entry's fast turning (no limits); optional higher look stiffness | exists via v1 entry |
| Takes opening duels (0.31) | bot entry Aggression raised from his measured rate | new: bot-entry field |
| Plays close to team (alone share 0.169, distance 694) | bot entry Teamwork high | new: bot-entry field |
| Fewer flashes (0.18) | buy plan: fewer flashbangs | new: buy-plan data |

### broky_v2 quirks

| Quirk | How it is driven | Exists? |
|---|---|---|
| Jumps 6.2/min (z +3.08) | CloneDirector jump injection; stays on during G-4 unless his data shows he stops | **exists** |
| Tap-fires (single shots 0.637, bursts 2.6) | trigger release | **exists** |
| AWP player (AWP shots 0.108, holds AWP 27%) | buy plan: AWP on full buys when affordable | new: buy-plan data |
| More flashes (0.43), fewer molotovs (0.171) | buy plan | new: buy-plan data |
| Pre-aims (turn before shot 1.09) | G-3 angle checks | new, part of G-3 |
| Knife out while running (0.234) | switch to knife when running before contact (`SwitchBotWeapon`) | new: plugin |
| Rarely slow (slow share 0.434) | G-4 quiet walking rarer for broky than for donk | new, part of G-4 |
| Stays with team (alone share 0.222) | bot entry Teamwork | new: bot-entry field |

### Not drivable yet (stay measured only)

donk's peek-left share and team distance as a direct control; any grenade choice beyond the buy plan and the routes' own throws.

## 4. Corrections to older notes

- The profile says look speed has "no control over view direction". The bot API does have `LockTarget`, and look acceleration/stiffness fields (`LookAccelAtk`, `LookStiffAtk`) in `GetBotProfile`. View control is possible; how far it goes is untested.
- L2/LF feel weaker than v1 mainly because of the human-aim limits, not the quirks (section 1).
