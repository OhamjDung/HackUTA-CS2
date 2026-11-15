# Why the first identity adapter failed, and the predeclared plan for experiment 2

> **Superseded where it conflicts (decided 2026-11-14).** Experiment 2 is Arjun's `clone-model/v2.py`
> (SPEC section 8.9). Where section 5 below and v2 differ, v2 is followed as written. Sections 1-4
> (the diagnosis of the first run) still stand.

Date: 2026-11-14. Machine: a Mac, CPU only (PyTorch 2.15.0, Python 3.12). No model was trained,
selected or promoted. Inputs: the first A100 run (prerelease `learned-clones-a100-v1`), its
development review file, and the development rounds of the seven training matches.

**Held-out data.** No held-out match (donk 2393242, broky 2393024) was opened. Their parsed JSON
files were not even extracted from the archive. The per-window held-out records in
`run/validation.json` were not read. The only held-out numbers used here are the published
aggregates in `first-a100.md`.

Each statement below is marked **ran** (measured here), **read** (from code or files, not run) or
**assumed**.

## 1. What was run

| Step | Command | Result |
|---|---|---|
| Adapter-only analysis | `diagnose_adapter.py adapter --best run/best.pt --last run/last.pt --training run/training.json --review Generated-path-review-dev.json --manifest manifest.json --lr 3e-4 --csnet <csnet>` | 4 s on CPU |
| Base checkpoint | CS-NET `scripts/download_checkpoints.py --pretrain-only` | 529 MB; SHA256 `d961a2d0…cce5c20`, the same as the run's |
| Training data archive | `cs2-rounds-transfer.zip` from `clone-training-data-v1` | SHA256 `0e46914c…8ad25`, matches; only the 7 training matches extracted |
| Development cache | `prepare.build_cache` on the 7 training matches, with a wrapper that keeps only development rounds after the upstream filter (script kept outside the repo) | 42 rounds, 18 s; every file's tick count and target index match the released manifest |
| Decoder measurement | `diagnose_adapter.py decoder ... --adapter best.pt --scales 2 5 10`, then `--adapter last.pt` | all 756 development windows (316 donk in 15 rounds, 440 broky in 27 rounds), float32; 14 min and 9 min wall time on 10 threads |
| Check | `... decoder --max-per-player 24` (the trainer's own development subset) | see 3.1 |

Tests: `CSNET_ROOT=<csnet> python -m pytest tests` gives 25 passed (12 old, 13 new).
All measured numbers are in `adapter-diagnosis.json`. The 24-window subset report there came from
an earlier version of the tool, without the shared-only control or round errors.

## 2. Findings from the adapter alone (ran)

Registry row 1 is broky (76561198201620490), row 2 is donk (76561198386265483).

**The identity vectors are still their random starting values.** The trainer's seeded start was
rebuilt (seed 42, model built on CPU, then the adapter). The rebuild is right: each trained row has
cosine 0.9996 with its rebuilt start (at step 400). Training moved each 64-number vector by a norm
of about 0.23 out of 6.9 (3%); no number moved more than 0.048. The two vectors had cosine 0.034 at
the start and 0.080 at step 400. They are two random codes, close to orthogonal, not two learned
descriptions of players. The zero-initialized FiLM layer means the vectors get no gradient until the
FiLM weights have grown, so this is expected (read: `identity.py`).

**So the adapter is two constant shifts.** With two identities, `W e_i + b` is just one fixed
1,536-number vector per player: a scale (gamma) and shift (beta) for the 768 numbers of the
decoder's condition. The 100,032 trainable numbers give two such vectors, nothing that depends on
the situation.

| Step 400 (selected) | broky | donk |
|---|---:|---:|
| gamma: norm / RMS / largest | 2.51 / 0.091 / 0.37 | 3.01 / 0.109 / 0.38 |
| gamma: dimensions above 0.1 | 204 of 768 | 273 of 768 |
| beta: norm / RMS / largest | 13.7 / 0.50 / 1.80 | 13.1 / 0.47 / 1.45 |
| beta: dimensions above 0.5 / 1.0 | 225 / 34 | 230 / 26 |

The change is spread out: the top 10% of dimensions hold about 45% of each vector's energy.

**Most of it is shared by both players.** The two betas have cosine 0.54. Split into the part both
players share and the part that differs: beta shared 11.8, beta half-difference 6.4; gamma 2.0 and
1.9. Only the half-difference can make own identity beat the other identity.

**Adam's step size, not the regularizer, limited the size.** With learning rate 3e-4, Adam moves a
number by at most about 3e-4 per update, so at most 0.12 after 400 updates. The largest FiLM weight
is 0.062, 51% of that bound. Weight decay shrank values by only 0.12%. The regularizer
(`0.001 × mean squared change of the condition`) was 0.99 at step 400 and 1.13 at step 600, still
rising, and only 0.2% of the objective. It did not hold the adapter back.

**Steps 400 to 600.** The FiLM weights changed by 38% of their norm (cosine 0.967), beta grew from
13.7 to 17.4 (broky) and 13.1 to 16.5 (donk), and gamma turned noticeably (cosine 0.64 and 0.71
with its step-400 value). Development loss did not move: mean 0.65579 at step 400, 0.65580 at 600.
The parameters kept drifting in directions the development loss did not reward.

**Training log.** The trainer recorded only the own-identity batch loss, never the base loss on the
same batch, so training gain cannot be read from the log. Batch loss: mean 0.609, standard deviation
0.065 (16 windows per batch). Logged development gain at the end: donk 0.6611 to 0.6594 (0.0017,
0.25%), broky 0.6541 to 0.6522 (0.0019, 0.29%), measured on 24 windows per player. The early-stop
threshold was 0.0001.

**Development review file (8 cases, 4 per player).** All three paths are exactly equal in 6 of 8.
Own equals base in 6, own equals other in 7, other equals base in 7. Where they differ, the largest
gap is 4.0 Source units (one movement token, donk round 10) and 0.98 units (broky round 4). These
change average path error by 0.006 and 0.15 units.

**An estimate, checked later.** If the condition is independent of gamma and beta, the logged
regularizer implies a condition RMS of about 8.7 per number (assumed). Measured on development
windows: 10.0 (3.2).

## 3. Findings from the decoder on development windows (ran)

### 3.1 The measurement reproduces the trainer

On the trainer's own 24-window subsets, the float32 CPU base loss is 0.66178 (donk) and 0.65175
(broky). The trainer logged 0.66108 and 0.65409 in bfloat16 on the GPU. The precision gap (0.0007
and 0.0023) is as large as the adapter's whole gain. Own minus base: CPU -0.0017 / -0.0014, logged
-0.0017 / -0.0019.

### 3.2 All 756 development windows, step-400 adapter

Teacher-forced loss per predicted token (lower is better). Uncertainty is the standard error over
rounds, because windows from one round are correlated.

| | donk (316 windows, 15 rounds) | broky (440 windows, 27 rounds) |
|---|---:|---:|
| own / other / base loss | 0.62064 / 0.62109 / 0.62161 | 0.61300 / 0.61382 / 0.61417 |
| own minus base | -0.00109 ± 0.00037 | -0.00114 ± 0.00022 |
| own minus other | -0.00036 ± 0.00022 | -0.00090 ± 0.00026 |
| shared part only, minus base | -0.00102 ± 0.00030 | -0.00078 ± 0.00026 |
| rounds where own beats other | 10 of 15 | 22 of 27 |
| top token same as base: own / other | 98.98% / 99.20% | 99.26% / 99.17% |
| top token same, own vs other | 98.99% | 99.20% |
| mean KL from base: own | 0.00047 | 0.00035 |
| another window's condition instead (control) | 90.7% same, KL 0.108, loss +0.105 | 91.5% same, KL 0.112, loss +0.116 |
| median gap between top two logits (base) | 3.78 | 3.93 |
| mean largest logit change, own vs base | 0.25 | 0.24 |
| condition RMS / FiLM change RMS | 10.0 / 1.02 | 10.0 / 0.93 |
| after `cond_proj`: RMS / change RMS | 64.1 / 3.8 | 63.7 / 3.6 |

What this shows:

- **The identity barely touches the predictions.** About 1% of predicted tokens change. A different
  window's condition changes 8 to 9% and moves the distribution 230 to 320 times as much (KL). The
  decoder clearly uses its condition slot. The adapter only nudges it by 6% of its size.
- **Most of the gain is not about identity.** The shared part alone gives 94% (donk) and 68% (broky)
  of the own-vs-base gain. The trainer's selection rule compared own with base only, so it rewarded
  this shared shift.
- **An identity signal exists but is small.** Own beats other by 0.0009 ± 0.0003 per token for
  broky (22 of 27 rounds) and by 0.0004 ± 0.0002 for donk (10 of 15 rounds, within noise).
- **Greedy decoding hides it.** A typical logit changes by much less than 0.25, while the top two
  tokens are usually 3.8 apart. Free-running greedy generation then gives the same token sequence,
  so the same path. This explains the 6 of 8 identical review paths (inferred from the numbers, not
  a separate experiment).

### 3.3 Scaling the trained change (probe, not a trained model)

The FiLM change was multiplied by K for both identities.

| K | donk own loss | donk own minus other | broky own loss | broky own minus other | own vs other same top token (donk / broky) |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.62064 | -0.00036 ± 0.00022 | 0.61300 | -0.00090 ± 0.00026 | 99.0% / 99.2% |
| 2 | 0.62059 | -0.00058 ± 0.00043 | 0.61255 | -0.00193 ± 0.00054 | 98.1% / 98.5% |
| 5 | 0.62620 (worse than base) | -0.00100 ± 0.00097 | 0.61626 (worse than base) | -0.00610 ± 0.00124 | 95.4% / 96.0% |
| 10 | 0.65199 | -0.00579 ± 0.00220 | 0.64041 | -0.02297 ± 0.00425 | 91.9% / 91.6% |

Doubling helps a little: own loss is slightly lower and the gap to the other identity doubles. So the
adapter stopped a bit short. But by K = 5 own identity is worse than no identity for both players.
Along this direction the best gain over base is about 0.0010 (donk) to 0.0016 (broky) nats per
token, at K = 2. A bigger push alone will not make own identity both better than base and clearly
different from other. At K = 5 the own-vs-other gap grows mainly because the other identity's loss
rises faster (broky: own +0.0021 over base, other +0.0080), not because own gets better.

### 3.4 Step 600 (last.pt)

| All 756 development windows | donk step 400 | donk step 600 | broky step 400 | broky step 600 |
|---|---:|---:|---:|---:|
| own minus base | -0.00109 ± 0.00037 | -0.00129 ± 0.00041 | -0.00114 ± 0.00022 | -0.00102 ± 0.00029 |
| own minus other | -0.00036 ± 0.00022 | -0.00063 ± 0.00024 | -0.00090 ± 0.00026 | -0.00057 ± 0.00025 |
| rounds where own beats other | 10 of 15 | 12 of 15 | 22 of 27 | 21 of 27 |
| top token same, own vs other | 98.99% | 98.90% | 99.20% | 99.21% |

Two hundred more updates moved the identity gap toward donk and away from broky. Neither checkpoint
reaches 2% changed tokens. The 24-window development check could not see this difference (both
steps scored 0.6558).

## 4. Likely causes, most likely first

1. **The adapter can only express a tiny, mostly shared change (strongest evidence).** It is one
   constant scale-and-shift per player on a single decoder input (position 0 of 160). It changes
   about 1% of teacher-forced tokens and KL by about 0.0004 nats. 68 to 94% of its gain is shared by
   both players. Scaling shows that making it larger stops helping by K = 2 to 5. Placement and form
   cap what Stage A in its current shape can learn.
2. **The objective and selection never asked for identity.** Training minimized own-identity loss
   only. Checkpoints were chosen by own-vs-base development loss on 24 windows per player. Nothing
   rewarded own over other, and the shared FiLM bias plus alternating batches let both identities
   learn the same "pro player on Mirage" shift. The test, by contrast, requires own to beat other.
3. **Greedy free-running decoding turns small logit changes into nothing.** The median top-two logit
   gap is about 3.8 and typical changes are well under 0.25, so the greedy path rarely changes (6 of
   8 review paths identical). When a token does flip, the path changes by about one 4-unit token
   step. Held-out differences of this kind on 29 and 42 correlated windows from one match per player
   are as likely to be noise as signal (the held-out test failed both ways: own was worse than
   other for donk, worse than base for broky).
4. **Training was short and slow for the identity vectors.** Learning rate 3e-4, 400 updates, Adam
   bound 0.12 per number. The identity vectors stayed at their random start (cosine 0.9996). With
   only two identities this costs nothing in expressiveness, since `W e_i` can be any vector. It does
   mean the vectors are not learned descriptions, and that adding players later would not reuse
   anything.
5. **Selection noise.** 24 windows per player, a 0.0001 threshold, and bfloat16 losses whose precision
   error (0.0007 to 0.0023) is as large as the gain being measured. Step 400 against step 600 was
   decided by 0.00001. The training windows were also few: stride 16 gives one supervised anchor per
   4 seconds of play (1,656 windows, about 9,600 samples drawn over 600 updates).
6. **The players are close in what the decoder sees (weaker evidence).** The identity-specific
   teacher-forced gap is 0.0004 to 0.0009 nats per token. It is not clear whether the data (15 donk
   and 27 broky development rounds) can separate the two players any better in this form. Not tested
   further.

**Ruled out (read, not run):** a train/inference mismatch. Training modulates the target player's
last-tick condition before the decoder (`model.py`). Inference hooks the same FiLM onto the temporal
transformer's output, and `predict_at_tick_player_sampled` takes the same last-tick, target-player
vector as the condition (`validate.py`, CS-NET `prediction_engine.py`). `temperature=0` is greedy
there (the logits are divided by 1e-6 before top-p). The unknown row stays the exact base.
Regularization too strong: also ruled out (section 2).

## 5. Predeclared plan for experiment 2

**Status: superseded where it conflicts with `v2.py`.** The two plans agree on the main fixes:
identity at every decoder step and a loss that rewards own identity over another. Where they
differ, v2 decides:

| Point | This plan | Followed (v2) |
|---|---|---|
| Identities | 2 (donk, broky) | Every player in 2 or more non-held-back matches, about 10 |
| Pull-back penalty | Kept at 0.001 | Removed |
| Identity hidden at random | No | 15% of targets, with `guided_logits` for later generation |
| Training length | Up to 3,000 updates, 4 runs (arms S and M, two learning rates) | Up to 2,000 steps, one run, patience 5 |
| Checkpoint selection | Float32, all 756 development windows, worse of two players | "Who is it?" on 120 development windows (bfloat16 on GPU) |
| Development gates G1-G3 | Required before the held-out test | Not used |
| Held-out test and pass rule | SPEC 8.6 free-running path error, own below other and base | Likelihood "who is it?": true identity in the top 2 of 5 teammates for at least 60% of players |

What this means for the result: a v2 pass shows the model tells players apart from their recorded
moves. It is not the SPEC 8.6 path test and produces no playable paths. The held-out matches are
still used once, after training, by v2. The text below is kept as a record of the alternative.

Everything below is fixed before any run. Decisions use training and development data only. The
held-out matches are evaluated once, at the end, on one configuration.

### 5.1 Stays the same

The pinned base checkpoint (SHA256 `d961a2d0…`) and CS-NET revision `268dd219…`. The nine-match
selection in `games.json` (2393226 excluded). The round split hash, so the same 99 training, 42
development and 39 held-out rounds. Canonical IDs donk 76561198386265483 and broky
76561198201620490. A frozen backbone. The SPEC 8.6 held-out test and its pass rule. The clone
profiles' `model` field stays null.

### 5.2 Changes (all inside Stage A)

Only identity vectors and FiLM layers train. The backbone stays frozen. No LoRA.

1. **Identity reaches every decoder step (arm M).** Arm M adds zero-initialized FiLM layers, driven
   by the same identity vector, to the per-tick context slots the decoder reads: the outputs of
   `decoder.depth_dec_adapter`, `xyz_dec_adapter` and `angle_dec_adapter` (48 positions instead of
   1). Hooks on those three modules apply in training and in `PredictionEngine` (which calls them
   each tick, read), so inference needs no new code path. Arm S keeps the current single point.
   The unknown identity remains the exact base. A test must show a zero first-step change and an
   unchanged unknown identity.
2. **An identity-contrastive term.** The objective becomes `CE_own + 1.0 × relu(CE_own − CE_other +
   0.005) + 0.001 × regularizer`. `CE_other` is the same batch with the other identity (decoder only;
   cheap). This rewards own over other, not only over base.
3. **Stronger optimization.** AdamW learning rate 1e-3 and 3e-3 (both tried, see 5.3). At most 3,000
   updates, batch 16. A development check every 100 updates; stop after 8 checks without
   improvement. Training windows with stride 4 instead of 16 (4 times more anchors; development and
   held-out windows stay at stride 16).
4. **Better selection.** Development metrics in float32 on all 756 development windows, not 24 per
   player. Development score per player: `CE_own − min(CE_other, CE_base)`. A checkpoint's score is
   the worse of the two players' scores. Keep the checkpoint with the lowest score. Log the base and
   other-identity loss for each logged training batch.

Four runs in total: arms S and M, each at learning rate 1e-3 and 3e-3, seed 42. No other settings
get tried. That keeps the development rounds (15 donk, 27 broky) from being over-used.

### 5.3 Development gate (decided on development data only)

For each run's selected checkpoint, both players must meet all three:

- **G1 (teacher-forced, `diagnose_adapter.py decoder`):** own minus other and own minus base are both
  negative, each by more than 2 standard errors over rounds.
- **G2 (the identity changes predictions):** own and other differ in at least 3% of teacher-forced top
  tokens (now 0.8 to 1.0%).
- **G3 (free-running, `validate.py --split dev`, written to its own folder):** own development path
  error is lower than both other and base.

If several runs pass, take the lowest mean development own path error over the two players. If none
passes, experiment 2 is reported as failed on development data. The held-out matches are then not
evaluated, stay unused for a later predeclared test, and Stage B does not start.

### 5.4 Final held-out test (once)

Run only the chosen checkpoint: `validate.py --split test`. **Pass rule, unchanged from SPEC 8.6:**
for donk on 2393242 and for broky on 2393024 separately, own-identity mean path error (ADE, greedy
free-running, early stops extended) is lower than both the other identity and no identity. Report
endpoint, speed and pause-rate errors and a round bootstrap next to it, but they do not change the
result. No re-run, re-selection or tuning after seeing it. A pass does not promote anything into the
playable clones. It would still need path checks on the map and in the game. A fail is reported as
it is.

### 5.5 Stage B

SPEC 8.4 allows LoRA only if Stage A works. This plan uses no LoRA and keeps the backbone frozen.
Arm M adds FiLM layers at more points, which is still Stage A: identity vectors plus scale-and-shift
layers. It does change SPEC 8.3 step 2 (one FiLM point), so the lead must agree, and SPEC 8.3/8.4
must be updated when it is built. Stage B is considered only if the 5.4 test passes.

## 6. Limits

Development windows were measured teacher-forced; free-running development paths were not
regenerated here (only the 8 existing review cases). The development windows include the 24 per
player that chose the step-400 checkpoint, so the step-400 numbers are slightly flattering. The
scaling probe is a probe of one direction, not a trained model. No GPU run, game run or held-out
analysis was done. Nothing here shows that any model learned a player's quirks.
