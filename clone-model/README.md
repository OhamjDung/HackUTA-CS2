# Learned clones: Stage A

Builds on the pretrained CS-NET v4 movement model and CS2 Clone Lab's player identities.
This trains movement tendencies, not a replacement for the bot's combat AI.

Player IDs are exact Steam IDs. The base network stays frozen. Only two identity vectors and
a zero-initialized scale-and-shift layer (FiLM) are trained. Unknown identity always uses the
unaltered base, even after training. Player shuffling also shuffles the identities and target
index. The first forward pass is tested against the unadapted output.

Source pins and retained notices are in `THIRD_PARTY.md`.

## Data and validation

- Build from the four matches per player in `SPEC.md` sections 7.2 and 7.3.
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
0.25-second intervals. `games.json` records tuples of player, match ID, dataset shard, demo stem,
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
