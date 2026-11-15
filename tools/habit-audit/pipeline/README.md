# Pipeline correction evidence

This work extends the repository's demoparser2 adapter and habit builder. It does not create a second parser, change the public profile schema, or promote candidate clones.

`demoparser2==0.42.2` ran locally. Its [`inventory` property](https://github.com/LaihoE/demoparser#list-of-fields-the-parser-supports) returns display names, while `inventory_as_ids` returns item-definition IDs. These are different from the CS-NET archive's per-file indices. The [upstream inventory collector](https://github.com/LaihoE/demoparser/blob/main/src/parser/src/second_pass/collect_data.rs) resolves held entities, removes repeated handles, and returns an empty inventory for dead players. Real build-demo inspection confirmed Python lists of names, including AWP while Butterfly Knife was active. The correction reads names directly and deduplicates them again.

The policy was fixed on the seven verified build matches before the separate descriptive holdout audit. Recordings 2393242, 2393024 and ambiguous-account recording 2393226 do not enter build decisions. `data/habit-audit/policy-freeze.json` records the freeze, hashes and training counts. `load_match()` resolves known targets by canonical Steam ID; other callers can provide a Steam ID explicitly, while ambiguous nicknames fail. The builder rejects recordings resolving to different identities.

## Deterministic policy

- Observe inventory on the first live tick, no later than one tick after freeze end. Do not backfill a missing opening from a later pickup. Unknown inventory stays unknown; a known empty list stays empty.
- Rank primary weapon preferences by the count of observed opening rounds carrying each primary. Ties use item name. Other weapons retain shot-based fallback order, also with deterministic ties. Missing evidence emits a warning; the raw evidence report gives observed/missing denominators.
- For each side and existing equipment category, choose one modal carried primary legal to purchase on that side. A gun picked up from the enemy counts as possession but cannot become an illegal buy. Full categories may select an AWP; force primary price is capped at $2,000, eco at $1,000, pistol at zero. When a carried gun is unaffordable, use an affordable purchase observed in the same category if available. Missing inventories use purchase-frequency fallback with an explicit warning. Known no-primary inventories do not invent a gun from teammate-drop purchases.
- Other items keep the existing purchase-frequency threshold of half the rounds. Put primary, then one armor choice, then utility. Preserve existing aliases and all output keys. Purchase frequencies retain their original meaning and are not relabeled as possession.

**Economic limit:** the price table is a static conservative policy assumption, not a current price query against the installed game. Caps constrain the primary only, not an entire complete equipment bundle. The Director's cash categories differ from the pipeline's equipment categories; especially, its full category starts at $4,000 while AWP needs $4,750 before armor. A static profile with one primary cannot encode a runtime cash fallback without changing the owner-controlled interface. This correction does not establish affordable full-AWP buying at every full round, automatic clone sniper play, or accepted `bc_buy` aliases.

## Reproduce

From `clone-pipeline/`, after `uv sync --group dev`, download only `train` rows from the current `clone-model/games.json`. For each tuple `(player, match_id, shard, stem, split)`, download `https://huggingface.co/datasets/blanchon/opencs2_dataset_demo/resolve/main/demos/<shard>/<match_id>/<stem>.dem` to `../data/habit-audit/raw/<player>/<match_id>_<stem>.dem`. Never mix the players' folders. The evidence JSON records checksums.

```sh
uv run python -m pytest -q
uv run python -m clone_pipeline.build --player broky --demos ../data/habit-audit/raw/broky --clone-id broky_v1 --out ../data/habit-audit/candidates
uv run python -m clone_pipeline.build --player donk --demos ../data/habit-audit/raw/donk --clone-id donk_v1 --out ../data/habit-audit/candidates
```

For a baseline on exactly the same verified inputs, use the pipeline source at base revision `a2caf02`, writing to `data/habit-audit/baseline/`. Do not use the committed four-game donk clone as the same-input baseline. Then:

```sh
uv run python ../tools/habit-audit/pipeline/verify_candidates.py --raw-dir ../data/habit-audit/raw --games ../clone-model/games.json --baseline ../data/habit-audit/baseline --candidates ../data/habit-audit/candidates --out ../data/habit-audit/pipeline-evidence.json
```

The verifier parses all seven build demos with the current adapter, records opening inventory/shot counts per match and side with SHA256, checks profile changes are limited to weapons/buy plans/build timestamp, compares every movement payload byte-for-byte, and checks all non-weapon botprofile lines. Reports, raw demos and generated candidates remain ignored. Data credit: Julien Blanchon / OpenCS2, CC BY 4.0; tournament recordings retain their organizers' terms.

An exact download loop (from repository root, uses only the checked-in selection):

```sh
python3 - <<'PY'
import json, pathlib, subprocess
for player, mid, shard, stem, split in json.load(open('clone-model/games.json')):
    if split != 'train':
        continue
    assert mid not in {'2393226', '2393242', '2393024'}
    path = pathlib.Path('data/habit-audit/raw') / player / f'{mid}_{stem}.dem'
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['curl', '-fL', '--retry', '3', '-o', str(path),
        f'https://huggingface.co/datasets/blanchon/opencs2_dataset_demo/resolve/main/demos/{shard}/{mid}/{stem}.dem'], check=True)
PY
```

The verifier above writes every selected input's SHA256 and confirms the canonical target through the actual parser. To extract and run the old pipeline without changing branches or touching current source (also from repository root):

```sh
python3 - <<'PY'
from pathlib import Path
import subprocess
out = Path('data/habit-audit/baseline-src/clone_pipeline')
out.mkdir(parents=True, exist_ok=True)
for source in subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', 'a2caf02', 'clone-pipeline/clone_pipeline'], text=True).splitlines():
    if source.endswith('.py'):
        (out / Path(source).name).write_bytes(subprocess.check_output(['git', 'show', f'a2caf02:{source}']))
PY
clone-pipeline/.venv/bin/python - <<'PY'
from pathlib import Path
import subprocess, sys
root = Path.cwd()
for player in ['broky', 'donk']:
    subprocess.run([sys.executable, '-m', 'clone_pipeline.build', '--player', player,
        '--demos', str(root/'data/habit-audit/raw'/player), '--clone-id', f'{player}_v1',
        '--out', str(root/'data/habit-audit/baseline')],
        cwd=root/'data/habit-audit/baseline-src', check=True)
PY
```

## Local result (2026-11-14)

Baseline suite: 16 passed. Corrected suite: 27 passed; three warnings explicitly identify missing inventory in legacy synthetic fixtures. Candidate CLI ran on four broky matches (79 rounds/routes) and three verified donk matches (62 rounds/routes). Both candidate profiles keep `model=null`; no holdout was passed, so `similarity=null`.

| Candidate | Before primary order | After primary order | Full T / CT |
|---|---|---|---|
| broky | M4A4, AK-47, AWP | AWP, AK-47, M4A4 | AWP / AWP |
| donk, verified 3-match input | AK-47, M4A4, Galil | AK-47, M4A4, M4A1-S | AK-47 / M4A4 |

Same-input baseline comparison: exactly `weapons`, `buy_plan`, `built_at` changed; all 141 route files stayed byte-identical; all non-weapon botprofile lines stayed identical. Broky had two unavailable first-live inventories (one of 33 CT full rounds, one of 27 T full rounds), reported rather than filled from later ticks. Donk had no unavailable opening inventories.

Against the committed bundles, there are additional **input-selection differences**: the committed donk bundle includes the unverified 2393226 account as its first match and profile Steam ID. The verified candidate excludes those 18 rounds: 62 rather than 80, canonical Steam ID, different aggression/positions/routes/grenades/source games. These are not caused by the weapon correction. Broky uses the same four build recordings; removing holdout input for candidate builds leaves its similarity block null. Build timestamps vary intentionally. The source does not replace or edit either committed playable bundle.

Raw `weapon_fire` events cover the full live round, whereas the independent parsed audit's fire-event proxy ends at its final sampled tick. Thus raw gun shots are broky CT345/T281 (AWP47/20), donk CT704/T433; independent sampled proxy counts are CT341/T273 (AWP45/19) and CT697/T431. These are explicitly different horizons, not identical event streams.
