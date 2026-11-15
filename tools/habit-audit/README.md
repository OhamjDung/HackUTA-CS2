# Source-recording habit audit

This independent CPU audit reads the sparse CS-NET parser format already used by
`clone-model/prepare.py`, separately from the demoparser2 `Match` adapter. It measures
source-player observations, never bot or learned-model performance. Python's standard
library is sufficient. `pipeline/` contains the separate raw-demo correction evidence.

Starting points: the existing pipeline's habits/routes and CS-NET parser schema already
pinned in `clone-model/THIRD_PARTY.md` (MIT). No upstream code is copied here. No existing
tool in the repository summarizes this sparse schema with these denominators, so this
small reader/report adapter is new. Data credit: Julien Blanchon / OpenCS2,
[CC BY 4.0](https://huggingface.co/datasets/blanchon/opencs2_dataset_demo). Original
recordings remain subject to tournament terms.

Run from the repository root:

```bash
python3 tools/habit-audit/fetch_parsed.py --out data/habit-audit
python3 -m unittest discover -s tools/habit-audit -p 'test_audit.py' -v
python3 tools/habit-audit/audit.py --json-dir data/habit-audit/parsed/round_json --games clone-model/games.json --out data/habit-audit/train --split train
```

The download verifies SHA256
`0e46914cbca514efbb5727b64f9e753116da4afaa98f764be66d15d97cb8ad25`
and checks entry paths, types and expanded size before extraction. The ZIP's old
`games.json` is deliberately ignored. Current `clone-model/games.json` selects seven
build matches and two holdouts. Match 2393226 is rejected; its donk-named alternate
account is unverified. Exact canonical Steam IDs, not names, locate targets. Duplicate
IDs, wrong maps, duplicate round IDs, bad time axes and misaligned rosters are rejected.

Each output has `audit.json` (complete per-round, per-match and per-side evidence),
`rounds.csv` (small tabular denominators) and `report.md`. Outputs belong in ignored
`data/`, never in source Git. JSON includes input hashes, selected identities/splits,
source revision, audit code hash, method hash and the full definitions. Round IDs retain
both source zero-based and pipeline one-based names. Windows can use `python` instead
of `python3`; no CS2 or CUDA is used.

The audit has no fit or threshold-search step. After reviewing build evidence and fixing
pipeline policy, record a method lock before opening either holdout. A lock must contain
`method_sha256` and `audit_source_sha256` from the final train report, plus
`pipeline_policy_frozen: true` and a description/hash of the frozen policy. Then:

```bash
python3 tools/habit-audit/audit.py --json-dir data/habit-audit/parsed/round_json --games clone-model/games.json --out data/habit-audit/holdout --split test --method-lock data/habit-audit/method-lock.json
```

The test command rejects missing/stale locks and an already-existing output report.
This is a procedural guard, not cryptographic enforcement against deleting outputs.
Keep the lock and do not use holdout descriptions to choose a policy or threshold.
The seven training matches can be re-audited during implementation; holdouts are one
final descriptive run. No checkpoint or clone is promoted by this tool.

Metric definitions and limits:

- Inventory is deduplicated and decoded with each file's own weapon map. Primary
  possession is reported both as any observed possession per round and alive seconds;
  active-weapon seconds are a distinct quantity, so knife-out AWP carrying is retained.
  Empty inventory is known empty. Missing/unknown entries are missing, never zero.
  First-known alive inventory may be later than the first sample if early data is
  missing; its observation time and first-sample coverage denominator are recorded.
  It is never called freeze-end possession. Source first samples commonly start at
  0.5 s. The tool invents neither those missing seconds nor a final sample's duration.
- Positive elapsed `round_seconds` weights left-sample intervals, capped at a target
  death event. Alive-false samples contribute no time. Speed uses horizontal position
  differences over real elapsed time, avoiding the archive's apparently scaled velocity
  arrays. Endpoints must both be alive/finite. Pause means speed **below 10 Source
  units/s**. Yaw turn uses the shortest wrapped angle and reports degrees/s. These are
  observational proxies, not aim, reaction or decision quality.
- Fire counts come from `events.sound` records with `ty=fire`, correct target index and
  gun weapon ID; they are not sums of sampled `shots` arrays. Knife/grenade fires are
  excluded. Raw full-round fire counts differ slightly from this sampled horizon;
  `RESULTS.md` records the independent build-only comparison without retuning. Kill weapons come from validated attacker/victim indices. Events before
  live or after the last sample are excluded. Missing event lists and invalid indices/
  weapon IDs are counted separately. Do not conflate a valid zero with missing lists.
- Positions/areas use finite left-sample positions and each source's place map. The
  64-unit grid is occupied source positions, not map geometry. Opening coverage is the
  observed interval up to damage dealt/taken, death, 20 s or last sample. It does not
  reproduce an exact 64 Hz route or whole-round decisions.
- Each side retains match/round counts and per-match ranges, not a misleading combined
  accuracy score or tick-based confidence interval. A single holdout match per player
  is weak evidence. Committed profile comparisons describe historical bundles; donk's
  historical bundle includes 2393226 whereas this audit excludes it. Differences are
  not all caused by the weapon-policy fix. Sparse JSON cannot validate the raw-demo
  adapter; use the companion raw-demo pipeline evidence for candidate regeneration.

See `RESULTS.md` for the concise measured outcome. No accepted `bc_buy` alias, in-game
route execution, combat skill, live game-state capture or model identity was tested here.
