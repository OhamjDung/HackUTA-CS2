# Start here: work that can move to your computer

Prepared for Arjun's friend on 2026-11-14. Repository: https://github.com/OhamjDung/HackUTA-CS2.git . Pull current main before starting: teammates are actively pushing.

## Recommended assignment

Start with **Task 1: clone habit audit and weapon-role correction**. This directly addresses the request for clones with the real players' quirks. An ordinary CPU laptop is enough. No CS2, Steam, GPU, Colab subscription, or game credentials are needed. Budget roughly 2-4 focused hours for the audit and another 2-4 for a tested pipeline correction; estimates depend on familiarity and downloads.

After Task 1, or while waiting for raw-demo downloads, take **Task 2: independent mock replay QA** (about 1-2 hours). It runs in a browser against a local Python service without CS2. The replay implementation already belongs to Ashirwad: test and report it; do not build a second viewer or modify his implementation without coordinating.

Each task document ends with a complete prompt to paste into your coding assistant. Use a separate branch for each task. Send Arjun the branch/PR URL, exact verification commands, results, and any files excluded from Git. Do not assume this package means the task has already been completed.

## What stays on Arjun's computer / Colab

- The current learned-model workflow: CS-NET v4 frozen backbone plus two identity/FiLM adapters, on Colab's allocated NVIDIA A100-SXM4-80GB. It has prepared-data checks, training, and held-out identity-swap validation. Do not start a competing training run or edit clone-model/ while this run is in progress.
- The two whole-match adaptation holdouts: donk 2393242 and broky 2393024. They must never enter training or policy selection. Your final audit may describe them after your method is fixed, but cannot use them to select a fix.
- CS2 base installation is complete on Arjun's PC. Installing the bot base, testing route playback, measuring real gameplay, GSI capture and recording need a CS2 machine and remain with the game-machine owners.
- CloneDirector, MatchBridge, match-service implementation and frontend showcase stay with their current owners. Do not restart or control anyone else's game or service.

## Current facts and limits

- Data-built donk_v1 and broky_v1 exist: 80 and 79 recorded opening routes respectively, plus counted habits and buy plans. Their model fields remain null until a validated learned model is integrated.
- The existing route bundles have compiled/load tests. Latest SPEC reports a converted donk T-side file manually loaded and moved a bot on Tom's PC; it was tried from CT spawn and hit a wall. Correct-side playback and full CloneDirector operation still need verification. Stand-in presets playing on Tom's PC are not proof that the full data-built clone works.
- CLONE_AUDIT.md identified broky's full-buy rifle policy and shots-based weapon ranking as a role mismatch. Audit text about the learned model/replay being absent is stale: clone-model/ and match-service/demo/replay.html now exist. Prefer current SPEC and code for status.
- Existing routes average about 18 seconds. They are recorded openings, not generated full-round behavior. Neither a mock trace nor a copied real route demonstrates learned movement or professional combat skill.
- donk's canonical ID is 76561198386265483; broky's is 76561198201620490. One donk-named event recording (2393226) uses 76561198018303780, an unverified alternate account. The current learned selection excludes it. Do not silently equate the two IDs or rebuild the donk bundle from that account.

## Shared setup and data

1. Clone the repository locally and read AGENTS.md, SPEC.md sections 0, 3, 5, 7, 8 and the section for your task. Read CLONE_AUDIT.md as historical evidence, not a current status board.
2. Install Python 3.11+ and uv from their official sources if needed. Node/CS2 are not required for either assignment.
3. For code, use the existing implementations: demoparser2/pipeline for habit extraction; existing match-service replay and tests for QA. Follow repository source/license rules.
4. Keep datasets, recordings, weights, videos, credentials and local report artifacts out of Git. Put intermediate data under ignored data/. Commit source, small synthetic fixtures/tests, documentation and concise summaries only.
5. Before editing SPEC, pull latest main. Every project commit updates only your status row/section plus one changelog line. Keep commits short, e.g. `Audit clone habits`, `Preserve sniper roles`, `Test replay edge cases`.
6. Push your own branch and open a draft PR or give Arjun its URL; do not force-push or overwrite main. Preserve teammates' changes when merging.

A 26.6 MB archive contains the ten public demo recordings already parsed at 0.25-second intervals:
https://github.com/OhamjDung/HackUTA-CS2/releases/download/clone-training-data-v1/cs2-rounds-transfer.zip
SHA256: 0e46914cbca514efbb5727b64f9e753116da4afaa98f764be66d15d97cb8ad25

Download with a browser or curl to ignored data/, verify SHA256, inspect archive paths before extraction. It includes games.json and round_json/<match_id>.json.gz. Use **the latest clone-model/games.json from Git** for the verified nine-match selection; the archive's historical games.json still lists the excluded tenth match. Do not run the archive selection blindly.

Data attribution: Julien Blanchon / OpenCS2, https://huggingface.co/datasets/blanchon/opencs2_dataset_demo (CC BY 4.0, as recorded in the repo). The archive has parsed data, not .dem files and not trained weights. Task 1 explains when raw demos are needed.

## Return format

- Task and branch/PR URL; base commit and final commit.
- Files changed and what behavior changed.
- Exact commands run, test counts, and what remains untested.
- Evidence report with denominators, train versus holdout labels and reproducible inputs.
- Link or attach ignored report outputs separately; do not commit recordings/datasets.
- Specific questions/blockers for Arjun. Never call a clone human-identical or pro-level based on offline files.
