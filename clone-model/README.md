# Learned clones: Stage A

Builds on the pretrained CS-NET v4 movement model and CS2 Clone Lab's player identities.
This trains movement tendencies, not a replacement for the bot's combat AI.

Player IDs are exact Steam IDs. The base network stays frozen. Only two identity vectors and
a zero-initialized scale-and-shift layer (FiLM) are trained. Unknown identity always uses the
unaltered base, even after training. Player shuffling also shuffles the identities and target
index. The first forward pass is tested against the unadapted output.

Source pins and retained notices are in `THIRD_PARTY.md`.

## Data and validation

- Build from the verified selection in this directory's `games.json`: three donk and four broky training matches, with one separate holdout per player.
- Reserve whole rounds from those matches for development using a stable hash (about 20%).
  These select checkpoints and early stopping. Overlapping windows stay in the same split.
- Never train or select a checkpoint on donk match **2393242** or broky match **2393024**.
- Use all 10 players, bomb, projectiles, positions, view, inventory, sounds, and real map-wall
  rays as context. Supervision comes only from the target player's movement/fire tokens.
- Train teacher-forced tokens. Final validation runs freely through CS-NET's prediction engine,
  recomputing wall distances, positions, and angles from generated movement. Future target
  positions and view angles are not supplied to free-running generation.
- Compare own identity, the other player's identity, and no identity on the same held-back
  contexts. Report mean path error (ADE), endpoint error (FDE), speed error, and pause-rate error.
  Early-stop paths are extended with their last point to score the whole true horizon.
- Call the identity test a pass only if own identity has lower held-out mean path error than
  both alternatives, separately for both players. Failure is a result, not permission to tune
  on the held-out matches. Few matches mean uncertain estimates. The original checkpoint's
  training-set overlap with these matches is unknown; held-out means excluded from our adaptation.

## Commands

Use Python 3.11+ with PyTorch, NumPy, PyYAML, pytest, WebDataset, zstandard, Open3D, demoparser2,
pandas, tqdm, and huggingface_hub. Colab already supplies PyTorch. Clone CS-NET to a separate
folder and check out `268dd2193c8a3d6e330c07dde5a851196c94eeaa`. Download its path checkpoint with
`scripts/download_checkpoints.py --pretrain-only`.

The Colab notebook downloads and parses the ten recordings with CS-NET's `demo_parser` at
0.25-second intervals. `parse_compat.py` wraps that parser to filter its roster and metadata
consistently to exactly five players on each playing team. Match 2393037 contains an extra
unassigned person; a roster that remains ambiguous is rejected, never guessed.
`games.json` records tuples of player, match ID, dataset shard, demo stem,
and train/test source split. Parsed files are named `<match_id>.json.gz`.

From this directory, with the paths set for your machine:

```bash
python prepare.py --csnet /content/csnet --json-dir /content/round_json --games /content/games.json --out /content/cache
python train.py --csnet /content/csnet --cache /content/cache --checkpoint /content/checkpoints/cs-net-v4-pro.pt --out /content/run --steps 500
python validate.py --csnet /content/csnet --cache /content/cache --checkpoint /content/checkpoints/cs-net-v4-pro.pt --adapter /content/run/best.pt --out /content/run
CSNET_ROOT=/content/csnet python -m pytest tests
```

Checkpoints are adapter-only: keep the pinned base checkpoint separately. `best.pt` is chosen by
development loss; it may remain at step 0 if training never improves it. `progress.json` and
`training.json` distinguish setup, optimizer progress, and trained-but-not-yet-validated state.
`validation.json` contains the identity-swap results and individual evaluation records.

## What “same quirks” can mean here

Movement/view habits can be learned statistically from these samples. Purchase plans and
recorded openings remain in the existing clone profiles. The movement model does not learn
buying, personality values, grenade lineups, teamwork calls, or precise human aim. It has not
been wired into live CS2. A training-loss decrease alone does not establish player likeness.
No route or identity is promoted to the playable clone just because training completed.

The current learned run excludes match 2393226: its donk-named slot has Steam ID 76561198018303780, which differs from canonical donk 76561198386265483 in the other four recordings. Ownership of that event account is unverified. The run uses three donk training matches plus one holdout, and four broky training matches plus one holdout (180 parsed rounds total). The public preparation archive retains all ten source recordings; use this directory's games.json to select the verified nine.

## Inspect generated paths without promoting them

`review.py` uses the same pinned PredictionEngine and checkpoint/manifest hashes. It exports up to four deterministic **development** round examples per player, using an alive midpoint (early anchor if already dead), with real, own-identity, other-identity and generic-base paths. It does not select the best-looking paths or change a clone profile.

```bash
python review.py --csnet /content/csnet --cache /content/cache --checkpoint /content/checkpoints/cs-net-v4-pro.pt --adapter /content/run/best.pt --out /content/review.json --per-player 4
```

The new offline artifact format is `cs2.clone.review.v1`, not a match-service API change. Each case identifies player/Steam ID, match/zero-based round, side, context tick and round time, start position, actual trace and three prediction traces. Paths are `[seconds after context, x, y, z]` in Source units; the first predicted point is at 0.25 s. Separate yaw/pitch, alive and firing values keep upstream meanings; the angle is the heading used for that step. Native early-stop lengths are retained, not filled with invented movement. A consumer can use start_position at t=0. No map collision approval, 64 Hz playback conversion, recorded-game provenance or in-game deployment is implied. Keep exports under ignored data/, outside playable clones.

After a complete test-split validation, progress.json now records `validation_failed` or `validated_pass` and deployed=false; a dev-only review cannot overwrite the held-out result. The first experimental adapter failed both held-out identity tests; see results/first-a100.md and GitHub prerelease learned-clones-a100-v1. Passing an offline test would still require manual path and game checks before promotion.

To check a review file against the de_mirage mesh (wall crossing, floor support, speed; long
stops and native early stops are reported, not failed), install Open3D, NumPy and Matplotlib from
PyPI and run `python map_review.py /content/review.json --csnet /content/csnet --out-dir data/map-review`.
It writes `<stem>.check.json` (`cs2.clone.review-check.v1`), `<stem>.check-details.json` (notes,
measurements and calibration on the real paths) and one top-down figure per case. Thresholds are
set so all real development paths pass. An automated pass is not an approval: a person must still
review each path. Results: `results/generated-path-map-review.md`.

For a static XY review figure, install Matplotlib from PyPI if absent, then run `python plot_review.py /content/review.json --out /content/review.png`. This plot has no map/collision geometry. The first A100 export completed all eight development cases; the resulting figure and JSON are attached to the experimental release.
