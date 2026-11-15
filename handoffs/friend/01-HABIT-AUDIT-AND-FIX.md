# Task 1: audit quirks and correct weapon-role extraction

## Outcome

Produce a reproducible, CPU-only habit audit for donk and broky, then correct the pipeline so carrying an AWP across rounds is not mistaken for preferring rifles. Preserve the current public clone-profile schema. This is the primary assignment; it can start immediately without Arjun's GPU or CS2.

## Ownership and boundaries

Own new tools under tools/habit-audit/ (including its README/tests). You may change clone-pipeline/clone_pipeline/parse.py, habits.py and build.py, their existing tests, and your own SPEC row/section when evidence supports the correction. Do not edit clone-model/, clone-director/, match-service/, frontend/, the bot installer, or committed clones/ bundles. Write candidate rebuilt profiles under ignored data/habit-audit/candidates/; Arjun will review/promote them. Any required profile/API schema change needs owner agreement first; retain function signatures and existing keys where possible.

Read first:
- AGENTS.md; SPEC.md sections 0, 3, 5, 7, 8 and 10.
- CLONE_AUDIT.md, especially 2.4-2.6 and its limits.
- clone-pipeline/clone_pipeline/{parse,habits,build,routes,similarity}.py and tests/test_pipeline.py.
- clones/broky_v1.json; clones/broky_v1/buy_plan.json; clones/broky_v1/botprofile.txt; corresponding donk files.

## Evidence already available

weapon_preferences() ranks weapons by shots fired. buy_plan() counts new purchases, then fills missing guns from purchase frequency. A saved sniper rifle can be held/used for several rounds without a new purchase; its low firing rate also loses against automatic rifles. Do not just hardcode `broky -> AWP` or rank by held-out kills. The correction must work for arbitrary players and use build data.

The historical audit reported 10 of 17 broky holdout kills used an AWP while his full-buy plan selected AK/M4. Treat that as a bug hypothesis to reproduce; it is not a tuning target. That audit's raw script/results were on Tom's PC, so your work must stand on its own.

## Data and identities

Use the archive and checksum in 00-START-HERE.md for a quick audit. It is CS-NET parser output, **not** clone_pipeline.parse.Match tables. Build a separate reader; do not feed it into load_match() or assume .json.gz is .dem.

Format inspected in this handoff:
- Top-level players: [{steamid, name}, ...], weapons: {display_name: integer_id}, rounds: list.
- Each round has id (zero-based here), teams aligned to top-level players, ticks, round_seconds, players aligned to that same roster, events.
- Each round-player has parallel arrays x/y/z, yaw/pitch, vx/vy/vz, alive, weapon, inventory, shots, place, etc.
- weapon and inventory contain IDs into the **per-file weapons map**. Invert it separately for every file. Do not use one global weapon-index table. The active weapon can be a knife while inventory contains the AWP.
- events.kills records have a/v/w (attacker index, victim index, weapon ID) and t (game tick), plus other fields. Never confuse those indices with Steam IDs. Validate fields before relying on them.
- Sampling is approximately 0.25 s; round_seconds often starts at 0.5, not exactly zero. Weight durations by actual elapsed times. Report missing start coverage rather than inventing freeze-end inventories.
- This format's zero-based round IDs differ from clone-pipeline's one-based rounds; preserve both names explicitly when joining.

Canonical targets: donk 76561198386265483; broky 76561198201620490. Resolve target indices from IDs, never names alone. Reject duplicates/missing targets. Exclude unverified donk event-account match 2393226. The verified selection and dataset shards/stems are in clone-model/games.json.

Build/development source matches:
- donk: 2393237, 2393232, 2393240.
- broky: 2392601, 2393037, 2393059, 2393063.
Holdouts: donk 2393242, broky 2393024. Freeze methodology using build matches first; then run holdout audit exactly once and report separately. Do not choose thresholds, policies or checkpoints using holdouts.

## Milestone A: independent audit (ship this even if time is short)

Provide a documented CLI taking --json-dir, --games and --out. Save structured JSON/CSV plus a short Markdown interpretation under ignored data/habit-audit/. Separate player, side, source match and split; show counts and missing data.

Measure at least:
1. Primary weapon possession per round and alive time, active-weapon time, shots and kill weapon mix. Report those as different quantities. Include inventory-held AWP even with a knife active; avoid double-counting inventory entries or dead ticks.
2. Alive-time speed distribution, pause share with a declared threshold, view-turn rate with yaw wraparound, position/area usage, opening-route duration and fraction of alive time covered. Use finite values and actual time deltas. Name these observational proxies; they do not measure human aim or decision-making.
3. Side-specific comparisons with committed profile/buy-plan choices. Identify supported mismatches and insufficient evidence. No fake all-in-one similarity percentage; include denominators and uncertainty from few matches.

Do not label these source paths as bot-generated or live match traces. Do not combine this with a neural-model identity score.

## Milestone B: pipeline correction

For a faithful fix and candidate regeneration you need raw .dem recordings; the parsed archive alone cannot prove what the existing demoparser2 adapter returned. Download just the needed build recordings using each tuple in clone-model/games.json:
`https://huggingface.co/datasets/blanchon/opencs2_dataset_demo/resolve/main/demos/<shard>/<match_id>/<stem>.dem`
Save as `<match_id>_<stem>.dem` under ignored per-player folders, because load_match() derives the match ID from the filename. Several GB and a few minutes of parsing may be needed; no CS2 installation is needed. Start with broky, then the verified donk build data. Do not place both players' unrelated demos in one build folder.

In clone-pipeline/ (PowerShell):
```powershell
uv sync --group dev
uv run python -m pytest
uv run python -m clone_pipeline.build --help
```

Inspect the pinned/current demoparser2 API and existing item_def_idx/inventory fields before choosing extraction properties. Build on the existing parser, not a second independent demo parser. Make raw weapon possession available with clear meaning and account for retained weapons, side legality, missing fields, drops and empty inventories. Do not silently convert unknown/missing evidence into zero possession.

Choose and document a deterministic training-data policy that retains player weapon role while respecting economic categories. Inspect training evidence before setting its thresholds. Do not assume an AWP is affordable for every force buy, or drop purchase order (primary, armor, utility). Avoid buying two competing primaries. Keep existing buy-plan keys and alias conventions; direct changes to accepted bot buy aliases are outside this assignment.

Meaningful regression tests must include:
- A sniper keeps an AWP for multiple rounds with no new AWP purchases, and fires fewer shots than a rifle user.
- Knife active while an AWP is carried; per-file weapon indices reordered; duplicate inventory items.
- Empty/missing inventories and no combat events produce explicit fallback/missing-data behavior.
- T/CT and pistol/force/full distinctions; affordable fallback and primary-before-utility order remain intact.
- A rifle-heavy player does not become an AWPer; holdout inputs never enter build decisions.
- Ambiguous Steam IDs are rejected, not joined by nickname.

Run existing pipeline tests plus your added tests. Regenerate candidate broky and verified donk bundles to ignored output folders using the actual CLI; compare JSON and botprofile text before/after. Do not commit hundreds of regenerated routes for a buy-policy change. Report any non-weapon differences or nondeterministic fields. Do not claim bc_buy aliases or gameplay worked without CS2.

## Acceptance and return

A fresh checkout + documented commands must reproduce the report. Include inputs/checksums/selected IDs, data source/license, metric definitions, split boundaries, source revision and test output. Return candidate buy plans and concise evidence tables separately from source Git commits. Arjun owns integration and CS2 verification. Estimate: audit 2-4 hours; correction 2-4 more; send Milestone A early.

## Paste this prompt into your coding assistant

You are helping Arjun with https://github.com/OhamjDung/HackUTA-CS2.git on a separate CPU computer without CS2. Execute Task 1 in this handoff, starting with the independent habit audit, then the weapon-role extraction correction. Read 00-START-HERE.md and this document in full, plus current AGENTS.md and SPEC.md. Pull current main and create branch friend/habit-audit. Use the existing open-source parser/pipeline. The current Colab learned-model run belongs to Arjun; do not touch clone-model/ or use either adaptation holdout for fitting, thresholds or policy selection. Resolve targets by canonical Steam ID; exclude ambiguous match 2393226. Start with the 26.6 MB public parsed archive for CPU analysis; raw .dem files are needed to verify/regenerate the pipeline correction, and can be parsed without installing CS2. Own tools/habit-audit/ and the narrow clone-pipeline files listed above. Preserve the public clone-profile format and teammate-owned directories. Produce runnable source, meaningful regression tests, training-only candidate buy plans and a transparent evidence report, with exact commands and missing-data limits. Never hardcode broky's AWP role or claim identical quirks/pro skill. Update your SPEC row, relevant section and changelog with each project commit, after pulling latest main. Keep commits concise. Push your branch and return its URL plus ignored report/candidate artifacts; do not merge to main or promote playable clones. Continue autonomously through both milestones where inputs allow, and return Milestone A promptly if a concrete blocker prevents B.
