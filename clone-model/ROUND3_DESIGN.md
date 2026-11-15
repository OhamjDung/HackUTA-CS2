# Round 3: a donk clone that stays inside human limits and feels like donk

Written 2026-11-15 by Arjun (with Claude). Status: **step 1 (section 6) is built and tested off the game;
it waits for Tom's PC. Steps 2 to 4 are design only.** The measurements in section 3 were run.

Inputs: Arjun watched `donk_v1` against `donkL` in CS2 (Tom's PC). Tom's report on the same run
(`handoffs/arjun-donkL-report.md`, now consumed; its findings are summarised in section 1).

---

## 1. What went wrong, and why

Arjun saw two problems with `donkL`:

1. **It walks backwards a lot.**
2. **It flicks to shoot like an aimbot.** It does not look human.

What Tom measured in the same run: a converted donk route makes a T bot follow the real path within
about 11 game units, against 790 for a bot with no route. CloneDirector attaches `donk_v1` and `donkL`
and plays routes. No clone match has been recorded yet, so no clone has been scored.

**Important: the `donkL` in that match is not the trained model.** Its movement comes from donk's
recorded opening routes (the first 20 seconds or less of a round) and from five quirk rules in
CloneDirector. Everything after that, including all of its aiming and shooting, comes from the bot base
(CS2-Bot-Improver). The trained model (`v2.py`) does not drive any bot yet.

### 1.1 The flicks: cause found (read in the source, not yet tested in the game)

`donk_v1` and `donkL` both use a copy of the bot base's `donk` personality entry
(`clone-director/tools/add_clone_bot_entries.py`). That entry is:

| Setting | Value in the `donk` entry | Bot base default | What it means |
|---|---|---|---|
| `LookAngleMaxAccelAttacking` | a 117-digit number | 5,000 | No limit on how fast the view can speed up while fighting |
| `LookAngleStiffnessAttacking` | 3,000 | 500 | How hard the view is pulled onto the target |
| `ReactionTime` (template `ProTop`) | 0 | 0 | Seconds before reacting to a seen enemy |
| `AttackDelay` | 0 | 0 | Seconds before the first shot |
| `AimFocusOffsetScale` | 0 | 0 | Aim error while tracking (0 is perfect) |

A bot with these settings can turn onto a head in one game tick (1/64 s) and shoot at once. Section 3
shows this is far outside what any of the 50 measured pros do. The same settings are on 23 of the bot
base's professional entries, so `donk_v1` flicks the same way; it is not specific to `donkL`.

Two of my quirk rules can make shooting look more mechanical (not tested): `donkL` holds crouch for
0.6 s at the start of 30% of bursts, and cuts bursts short by blocking the trigger for 0.3 s.

### 1.2 The backwards walking: not the routes; most likely a quirk rule (not yet tested)

Measured (section 3): real donk walks backwards for 9.2% of the time he moves. Across 50 pros the range
is 4.9% to 10.8%. The route files `donkL` replays contain **5.3%**. So the replayed routes are not the
source.

The leading suspect is my **restlessness** rule. When the bot has been still for more than 11% of its
alive time, and for 2 seconds in a row, CloneDirector pushes it sideways for 0.35 s. A bot base bot
holds angles almost all the time, so this fires about every 2 seconds. The bot then walks back to its
spot while keeping its aim on the angle it holds, which is walking backwards. Only `donkL` has this rule,
which fits what Arjun saw.

**How to confirm:** record one match with `-Record tv` and run
`uv run python -m clone_pipeline.limits measure --out bots.csv <match.dem>` on it. The tool reports each
bot's backwards share. Then turn the rule off and record again.

---

## 2. Principles

1. **Human first.** A clone that does one inhuman thing looks like a bot, whatever its similarity
   score. Staying inside human limits is a gate, not a score.
2. **Perception over statistics.** The product is that a viewer or player believes they are watching
   or playing donk. The evaluation must measure that directly (section 5). The similarity score is a
   secondary check.
3. **Limits come from data.** Every limit in section 4 is a measured number from elite pros, not a guess.
4. **Enforce limits in every layer that moves the bot.** The bot base's aim, CloneDirector's rules, the
   model's training, the model's decoding, and playback. A limit enforced in only one place leaks.
5. **Decide the tests before running them.** As before: pass rules are written down first, and
   held-back data is used once.

---

## 3. Measured human limits (ran)

Tool: `clone-pipeline/clone_pipeline/limits.py` (new; definitions in its header). Data: the 8 Mirage
matches that are **not** held back (2392601, 2393037, 2393059, 2393063, 2393226, 2393232, 2393237,
2393240), all 10 players each: 80 player-matches, 50 different pros, about 30 hours of alive time.
Per-player numbers: `clone-model/results/human-limits.csv`.

### 3.1 At the game's 64 ticks per second

| Measure | p50 | p95 | p99 | p99.9 | Highest |
|---|---|---|---|---|---|
| Turn speed of the view (°/s) | 2 | 195 | 632 | **1,107** | 3,845 (likely spectator or death artefacts) |
| Turn acceleration (°/s²) | 45 | 3,390 | 10,476 | **22,556** | |
| Peak turn speed in the 0.25 s before a burst (°/s) | 32 | 257 | 729 | 1,839 | 2,154 |
| View change in the 0.25 s before a burst (°) | 2.2 | 18.7 | 43.9 | 127 | 171 |
| Flick time, flicks of 15° or more (s) | **0.36** | 0.47 | | | p5 = **0.11**, p1 = 0.08 |
| Response time after being hit (s) | 0.20 | 1.53 | | | p5 contaminated by shots already in flight |
| Speed at the first rifle shot (units/s) | 59 | 173 | 215 | 225 | |
| Unbroken backwards walking (s) | 0.23 | 1.5 | **3.0** | 6.3 | 10.5 |

| Per player-match | Lowest | Median | Highest | donk (4 matches) |
|---|---|---|---|---|
| Backwards share of moving time | 4.9% | 7.5% | **10.8%** | 9.2% |
| Backwards seconds per alive minute | 1.8 | 3.1 | 4.8 | 4.2 |
| Turn speed p99.9 (°/s) | 729 | about 1,050 | 1,565 | 1,171 |

donk is among the most backwards-walking players and among the fastest turners, but inside the range.

### 3.2 At 4 steps per second (the model's resolution)

| Per 0.25 s step | p50 | p95 | p99 | p99.9 | Highest |
|---|---|---|---|---|---|
| Yaw change (°) | 1.1 | 44.7 | 105.9 | **160.5** | 179.9 |
| Pitch change (°) | 0.2 | 6.3 | 15.9 | **42.6** | 116.2 |
| Distance moved (units) | 27.6 | 62.5 | 62.9 | **67.9** | 78.9 |
| Change of step movement (units) | 7.7 | 37.4 | 53.4 | **67.4** | 99.7 |

---

## 4. The constraints

Two kinds:
- **Hard limits:** never exceeded, anywhere. Set at the elite p99.9, or the highest single-player value
  where that is more permissive, so a real pro never breaks them.
- **The donk envelope:** the shape of donk's own distribution. A clone should sit inside it, not just
  under the hard limit. Measured on donk's 4 building matches.

### 4.1 Hard limits

| ID | Limit | Value | Source |
|---|---|---|---|
| H1 | View turn speed, sustained over 4 ticks | ≤ 1,600 °/s | highest player p99.9: 1,565 |
| H2 | View turn speed, any single tick | ≤ 2,200 °/s | flick peak max: 2,154 |
| H3 | View turn acceleration | ≤ 36,100 °/s² at a player-match's p99.9 | highest player-match p99.9: 34,411 (corrected; 25,000 failed real pros) |
| H4 | Flick time, flicks of 15° or more | ≥ 0.08 s | p1 |
| H5 | First shot at a newly seen enemy | ≥ 0.15 s after it becomes visible | below the 0.20 s median response; to be checked in game |
| H6 | Unbroken backwards walking | ≤ 6.3 s | p99.9 |
| H7 | Backwards share of moving time, per match | ≤ 11% | highest player-match: 10.8% |
| H8 | Yaw change per 0.25 s step | ≤ 165° | p99.9: 160.5 |
| H9 | Pitch change per 0.25 s step | ≤ 45° | p99.9: 42.6 |
| H10 | Distance per 0.25 s step | ≤ 68 units, except jumps and boosts | p99.9: 67.9 |
| H11 | Change of step movement (acceleration) | ≤ 68 units per step | p99.9: 67.4 |
| H12 | Paths through walls or out of the map | never | `clone-model/map_review.py` |

### 4.2 The donk envelope (soft; scored, not a gate on its own)

Each is compared with donk's own value; the tolerance is how much donk varies between his own matches.

| Feature | donk | Why a viewer notices it |
|---|---|---|
| Backwards share of moving time | 9.2% | Backpedalling looks robotic when overdone |
| Sideways share of moving time | 47.7% | Strafing style |
| Turn speed p50 / p99 / p99.9 | measured per match | Calm or twitchy aim |
| Flick time distribution | p50 0.34 s | Snappy aim reads as aimbot when too fast |
| Speed at first rifle shot | p50 60 | Counter-strafing before shooting |
| Jumps per minute | 4.1 | donk's quirk |
| Standing-still share | 11% | donk's quirk |
| Distance from teammates | 694 units | donk plays apart from the team |

### 4.2a How the limits are checked in practice (built, 2026-11-15)

`uv run python -m clone_pipeline.limits check --name <bot> [--like donk] <match.dem>` measures one player
in a recording and checks 9 limits per player-match. The thresholds are in
`clone-pipeline/references/human_limits.json`, made by `limits calibrate` from the 80 real pro
player-matches: each sits 5% beyond the most extreme real player-match, so **every measured pro passes**,
and a bot fails only by doing what no measured elite pro did.

| Check | Limit | Most extreme real player-match |
|---|---|---|
| Sustained turn speed, p99.9 | ≤ 1,524 °/s | 1,452 |
| Turn speed, p99.9 | ≤ 1,643 °/s | 1,565 |
| Turn acceleration, p99.9 | ≤ 36,131 °/s² | 34,411 |
| Backwards share of moving time | ≤ 11.4% | 10.8% |
| Unbroken backwards walking, p99 | ≤ 5.1 s | 4.8 s |
| Flick time (flicks of 15° or more), p5 | ≥ 0.090 s, needs 5 flicks | 0.095 s |
| Pitch change per 0.25 s step, p99.9 | ≤ 67.4° | 64.2° |
| Distance per 0.25 s step, p99.9 | ≤ 77.3 units | 73.6 |
| Change of step movement, p99.9 | ≤ 81.1 units | 77.3 |

Known weakness: the flick check. Real donk on his held-back match 2393242 made a 15° flick in 0.059 s,
below the limit; the check skipped it because he made fewer than 5 such flicks. The threshold was not
changed after seeing this, because that match is held back. Decide on more data.

### 4.3 Where each limit is enforced

| Layer | What controls the bot there | How limits are enforced | Covers |
|---|---|---|---|
| L0. Bot base personality | Aiming and fighting, all of the round after the route | Replace the copied `donk` aim settings with finite, measured ones (section 6, step 1) | H1 to H5 |
| L1. CloneDirector rules | Quirks during and after routes | Remove or fix rules that break limits (restlessness first); check every rule with `limits.py` on a recorded match | H6, H7 |
| L2. Model training | What the model learns | Penalty in the loss for predicted steps beyond H8 to H11; training data cleaned of spectator and death artefacts | H8 to H11 |
| L3. Model decoding | What the model produces | Forbid the tokens that would break H8 to H11 given the previous step, before sampling | H8 to H11 |
| L4. Smoothing to 64 Hz | The playable route file | Minimum-jerk smoothing with turn-speed and acceleration caps, not straight lines | H1 to H3 |
| L5. Rejection | Which generated routes are kept | Run `limits.py` and `map_review.py` on every candidate; drop any with a hard violation | H1 to H12 |

---

## 5. Evaluation: does it look and feel like donk?

Ordered by importance. A clone ships only if it passes tiers 1 and 2. Tier 3 informs, it does not gate.

### Tier 1. Hard-limit check (automatic, every checkpoint and every recorded match)

- **Zero violations** of H1 to H12 per 10 minutes of the clone's play.
- For generated routes: run on the 64 Hz playable file. For the game: run `limits.py` on a GOTV recording.

### Tier 2. People judge it (the real test)

A blind, written-in-advance panel. This is the core of the product, so it is the main test.

**Clips.** Pick 12 opening routes with the same route label. For each, record 4 versions in CS2 with
GOTV, from the same spectator camera: real donk (the original demo), `donkL` (current), the round 3
clone, and a default bot. Cut each to 15 seconds. Use both a third-person and a first-person camera.

**People.** At least 10, split into two groups: people who play CS2 regularly, and people who do not.
Teammates may not rate clips they helped produce.

**Questions per clip, in random order, without names:**
1. Human or bot? (two choices)
2. If human: which of these three players is it? (donk, a teammate of donk, a player from another team)
3. "This looks like donk," 1 to 7.
4. Mark any moment that looks robotic, with a reason: snapping aim, backpedalling, jitter, walking into
   walls, perfect spray, too-fast reaction, other.

**Measures and pass rule (fixed now):**

| Measure | Pass |
|---|---|
| Rated "human" | at least 60% of the rate real donk clips get |
| Robotic marks per minute | no more than 2 times the rate real donk clips get |
| Identified as donk, when rated human | above chance (1 in 3), and at least half the rate real donk gets |
| "Looks like donk" rating | at least 1 point above the default bot |

Real donk clips are the control: they set the baseline for every measure, because people mark
real players as robotic too.

### Tier 3. Automatic proxies (cheap, used to choose checkpoints)

1. **Envelope score:** for each feature in 4.2, how close the clone is to donk, relative to how much
   donk varies between his own matches. Weighted by how often that feature is marked in tier 2.
2. **Bot detector:** a small classifier trained to tell real pros from bot base bots on 2-second windows
   of view and movement (training data: the pro recordings, and recorded bot base matches). Score: how
   often it mistakes the clone for a human. Never train it on the clone itself.
3. **Who is it:** the existing quirk test (`clone_pipeline/quirks.py`) and the v2 likelihood test.

The similarity score from earlier rounds is tier 3, item 3. It no longer decides anything alone.

---

## 6. Next round, step by step

### Step 1. Fix the live bot now (no training; needs Tom's PC). Built 2026-11-15; waiting for Tom.

Done off the game: `clone-director/tools/add_clone_bot_entries.py` writes `HUMAN_AIM` into the four clone
entries (simulated: a 45° flick settles in 0.34 s, peak under 1,200 °/s, acceleration at most 20,000 °/s²;
the current settings give 0.09 s, 2,109 °/s and 135,000 °/s²). `donkL` and `brokyL` no longer apply the
restlessness or crouch-at-burst rules (`quirk_controls_disabled` in each profile says why). The test steps
for Tom are in `handoffs/tom-human-aim-test.md`. The simulation assumes the bot aim model of the earlier
Counter-Strike bot code; whether CS2 behaves the same is what Tom's recording shows.

1. **Aim:** give the clone entries finite aim settings. Starting values, to be tuned by measurement:
   `LookAngleMaxAccelAttacking` 20,000, `LookAngleStiffnessAttacking` 1,150 (the bot base's `ProSteady`
   value), `LookAngleDampingAttacking` 50, `ReactionTime` 0.15, `AttackDelay` 0.05, a small non-zero
   `AimFocusOffsetScale`. The bot base's units for these are not documented; the values are a start.
2. **Rules:** turn off the restlessness rule and the crouch-at-burst rule until each passes tier 1 in a
   recorded match. Keep jump rate and burst length only if they pass.
3. **Measure:** record 3 matches with `-Record tv`, run `limits.py` on the bots, and adjust the step 1
   values until tier 1 passes and the turn and flick distributions sit inside donk's envelope.

This step alone should remove the aimbot look, because the fighting is the bot base's. It does not need
the model.

### Step 2. Let the model generate routes (code; `handoffs/remaining-work.md`, task 7)

v2 identities change the inputs of every generation step, but CS-NET's prediction engine builds those
inputs itself. Wrap the engine so v2 identities reach generation. Use random sampling with a guidance
scale above 1, not always the most likely step.

### Step 3. Train round 3 (`v3.py`, based on `v2.py`)

| Change | Why |
|---|---|
| Train on many more players: all Mirage matches in OpenCS2 with players seen in 2 or more matches | 10 identities is too few to learn what makes a player distinct |
| Clean the training data: drop windows with spectator jumps, deaths and respawns, and any step beyond H8 to H11 | The model must not learn artefacts as moves |
| Loss: next-step likelihood + the v2 teammate margin + a limit penalty | The penalty is the expected amount by which predicted steps exceed H8 to H11 |
| Second loss term on rollouts: generate 2-second rollouts during training and penalise backwards share and turn distribution outside donk's envelope | Fixes the problems at the level people see, not one step at a time |
| Decoding: forbid tokens that break H8 to H11 (layer L3) | A hard guarantee no penalty can give |
| Smoothing: minimum-jerk, capped (layer L4) | Removes the straight-line jumps between 4 Hz points |
| Rejection: `limits.py` + `map_review.py` on every candidate (layer L5) | Last line of defence |
| Choose the checkpoint on development rounds by tier 3, not by likelihood | Optimise what people see |
| Re-check the top 3 checkpoints in float32 | Rounding error was as large as the gain in round 2 (Ashirwad) |

### Step 4. Test it

1. Tier 1 on 10 minutes of generated play from development rounds. Zero violations required.
2. Tier 3 on the same. Record the numbers.
3. Convert the best routes to playable files, play them in CS2 with the step 1 aim settings, record
   with GOTV, run tier 1 again on the recording.
4. Tier 2 panel, once, as written in section 5.

### A problem to solve before step 4

**There is no unused donk Mirage match left.** OpenCS2 has 5 donk Mirage matches; 2393242 is used up as
a final test (`SPEC.md` 8.9). Options: (a) use the tier 2 panel as the final test, since it judges new
generated play rather than held-back data; (b) download newer donk matches if OpenCS2 adds them; (c) hold
out a donk match on another map and train on more than Mirage. Recommended: (a), with (b) if available.

---

## 8. Donk only: a model that generates donk's play (added 2026-11-15)

Arjun's decision: train a donk model only, for now.

### 8.1 Why the earlier models could not show "plays like donk"

- Round 1 (`model.py`): identity changed nothing in 64% to 72% of test cases.
- Round 2 (`v2.py`): picks out the right player among teammates for 8 of 10 players, but it only scores
  recorded moves. CS-NET's prediction engine builds its own per-step inputs, so v2 identities cannot
  generate play. No round 2 model has produced a single donk path.

### 8.2 The design (`clone-model/donk.py`)

| Choice | Source of the idea | Why here |
|---|---|---|
| Start from CS-NET, trained on many pros, then specialise to donk | AlphaStar: supervised learning on human replays first | donk has about 47 training rounds; the base supplies everything else |
| Penalise drift from CS-NET's move probabilities (KL to the base, weight 0.1) | AlphaStar: KL penalty to the supervised human policy | Keeps the model human and stops it memorising 47 rounds |
| Train only small adapters (LoRA, rank 16, about 1.2 million numbers) in the decoder | LoRA (Hu et al., 2021) | Little data; and the adapters fold back into a normal CS-NET file |
| Fold the adapters into an ordinary CS-NET checkpoint | | CS-NET's own engine then generates donk play: no new generation code, which removes round 2's blocker |
| Drop training windows whose real future breaks H8 to H10 | Section 4 of this design | Do not learn spectator or death artefacts as moves |
| Sample 8 futures per moment and reject those breaking human limits | Imagination: planning by sampling a learned model's futures | Layer L5; also the basis of self-training (8.4) |

### 8.3 How it is judged, fixed before the run

Rounds: donk's development rounds, split by round number. Even rounds (dev-A) choose the checkpoint by
teacher-forced loss. Odd rounds (dev-B) are used once, for the result. Matches 2393242 and 2393024 are
not used: they were spent as final tests in round 2.

For each dev-B moment, CS-NET's engine samples 8 free-running 4-second futures from the donk model and
8 from the unchanged base model. Pass rule (constants at the top of `donk.py`):

- **P1, path:** the donk model's mean path error is lower than the base's, and the 95% paired bootstrap
  interval of the difference lies entirely below zero.
- **P2, behaviour:** the donk model is closer than the base to real donk on at least 2 of 3: the
  distribution of distance per step, the distribution of view turn per step, and backwards share.
- **P3, human limits:** the donk model breaks H8 to H10 on no larger a share of steps than the base.

A pass means donk's generated movement is measurably closer to donk than the generic model's. It is not
the people panel (section 5, tier 2), it is not combat, and it is not in CS2.

### 8.4 Next, if it passes: self-training by imagination (design only)

Expert iteration, the loop behind AlphaZero, adapted to imitation:
1. From training-round moments, sample 8 futures with the donk model.
2. Keep only futures that pass the human limits and that a judge rates most donk-like. The judge: the
   round 2 identity model's preference for donk over his teammates (`v2.py`), plus the donk envelope.
3. Fine-tune on the kept futures together with the real data, with the same KL anchor.
4. Repeat while dev-A improves.

This lets the model learn from situations donk was never recorded in, which recorded data alone cannot
give. It is also how a discriminator-style reward (as in GAIL) enters without full reinforcement
learning, which would be too slow for the time left.

## 7. What is not known yet

- Whether the bot base's aim settings behave like the numbers suggest. Only measuring a recording shows it.
- Whether the restlessness rule is the cause of the backwards walking. The recording in section 1.2 decides.
- Whether GOTV recording (`-Record tv`) works on Tom's PC. Never tried. Every in-game measurement here needs it.
- Response time is a stand-in for reaction time. True reaction time needs to know when an enemy became
  visible, which the recordings only show roughly.
- Turn speeds above 1,800 °/s in the data are probably artefacts (spectator switches, deaths), not players.
