# Round4: both training runs completed, neither ready for promotion

2026-11-15, Arjun/Codex. **Development-only experiment; no fresh final test or CS2 deployment.**
Both candidates improve path/tempo measures but regress in turning. This does not fix all tester feedback.

## What actually ran

Executed source `23292e9349e8a5350dd9633b9e340e224e0393b8`, pinned CS-NET
`268dd2193c8a3d6e330c07dde5a851196c94eeaa`. NVIDIA A100-SXM4-40GB, PyTorch2.14.1+cu130,
Python3.13.16. Independent donk and broky rank16 decoder LoRAs, each starting from the same generic
base: four iterations, 80 imagined moments/iteration, eight futures/moment, up to two distinct valid
futures retained, 100 optimizer updates/iteration. 400 updates per player, 800 total; 18.2 and18.0 minutes.
Donk selected iteration4; broky selected iteration1 after completing all four.

The judge adds circular view matching, each player's own movement/fast/still targets, and a historical
speed/proximity noise-exposure proxy. It retains original human-limit filtering and KL anchoring.
This is one combined-objective development experiment, not a complete isolated ablation study.

## Results against each player's generic-base development baseline

32 fixed dev-A moments/player, eight free-running four-second futures/moment. Lower error is better.
These numbers cannot be compared directly with the previous model's consumed test-C results.

| Metric | Donk base → selected | Broky base → selected |
|---|---:|---:|
| Mean path ADE, world units |133.200 →129.413 (2.84% lower)|125.357 →119.798 (4.43% lower)|
| Step-distance distribution W1, units/step |4.288 →3.623|4.657 →4.623|
| Turn distribution W1, degrees/step |4.843 →5.124 **worse**|4.740 →5.351 **worse**|
| Measured human-limit violation share |0.0498% →0%|0.2686% →0.1221%|
| Joint selection score |149.095 →144.402|141.833 →137.129|

The joint score permits tradeoffs; a better score does not mean every objective improved. Neither
candidate passes an all-components-nonregressing gate. Zero measured limit violations is not collision,
fall, grenade or live safety validation. Broky's selected checkpoint contains100 updates; the full
experiment executed400. Donk's selected checkpoint contains400.

The downloaded ZIP hash, executed source hashes, saved adapter player/iteration/rank, 48 finite
tensors/1,179,648 parameters per adapter, and common base/manifest hashes were checked locally.
60 learned-model tests pass; five optional local Open3D map tests skip. Actual Colab optimization and
free-running development selection ran; an offline unit suite is not a game test.

## What is still unproven

No actual sound-audibility improvement, causal response, angle-clearing success, full-round route
diversity, utility strategy, self-kill resolution, live control recovery, jump/AWP fidelity or fresh-match
generalization is established. Keeping two distinct four-second futures is not proof of varied rounds.
Weapon choice/utility strategy are not outputs of this movement model. The original policy still sees
its original full-state inputs; no causal fog-of-war observation adapter was introduced.

1100/2000-unit ranges and150u/s are historical CS1.6/Condition Zero hypotheses, not verified CS2 hearing.
Enemy truth is used by the new offline proxy judge only, with no future enemy trajectory in that judge.
The existing policy's full-state inputs remain a separate limitation. Quirk targets use the specific
player's future, rather than forcing donk to move like an average pro. Full quirk preservation needs
context-conditioned audits, including broky's jumps and AWP role, before promotion.

Existing whole-match tests, dev-B and test-C are consumed; they were not scored again. Fresh matches
and a frozen final rule are required for a new final claim. Base pretraining overlap remains unknown.

## Next work, in order

1. **Tom: diagnose self-kills and control ownership first.** Use the prepared prompt and death/grenade
   timelines; compare modes only in controlled private rounds with Tom. Never interrupt a primed
   grenade merely to test a theory. Retraining does not repair the live route controller.
2. **Fix selection before spending more GPU.** Predeclare separate nonregression gates for view and
   distinctive player habits within safety limits. Compare path-only, path+view, then conditional tempo/
   noise/diversity additions with equal seeds, moments and compute. Increase view priority only on dev;
   report mean and best-of-N, heading/turn errors and diversity separately. Do not select by path alone.
3. **Build one causal observation adapter for training and inference.** Mask hidden positions AND
   relative/derived features; use validated visibility, uncertain sound evidence and timestamped
   last-seen state. Test for future/hidden-state leakage. Compare with the original input contract on
   dev before a full run; replacing one position tensor is insufficient and can shift the distribution.
4. **Measure the remaining behavioral targets.** Use training-only, side/weapon/contact-conditioned
   metrics for sound discipline, reaction, pre-aim, controlled peeks, utility support/variety, route
   entropy, information-triggered changes, spacing/trading and self-damage. Mark missing evidence
   unknown. Calibrate CS2 audibility; do not turn the historical proxy into a runtime enemy detector.
5. **Runtime adaptation and variety.** Once Tom's evidence identifies safe transfer semantics, use
   observable threat information to hand control back, clean up input ownership and sample among
   compatible routes with player-specific shares/history. Test both players and sides, silent/audible
   enemies, friendly/distant noise, damage, sighting and utility-in-progress cases. Preserve spawn,
   side and economy compatibility. This is not learned reasoning or a competing hidden aim loop.
6. **Fresh final test and candidate review.** Freeze additional verified-account matches before
   tuning; keep all overlapping windows within a round/match split. Evaluate once per player with
   uncertainty and quirk/human-limit gates. Reuse `clone-pipeline/clone_pipeline/generated.py`, the
   existing map review and viewer for candidates. Manual geometry/utility approval, private-match
   captures versus native bots, synchronized source replay and blind review remain promotion gates.

Detailed design: [Round4 plan](../ROUND4_GAME_SENSE.md) and
[execution protocol](../ROUND4_RUN_PROTOCOL.md). Research and its source caveats:
[game-sense report](../research/cs2-game-sense.md).
Tom's prompt: [self-kill diagnosis](../../handoffs/tom-self-kill-diagnosis.md).

## Artifacts and reproduction

[Development prerelease](https://github.com/OhamjDung/HackUTA-CS2/releases/tag/round4-development-v1)
contains both adapter directories, iteration records, logs, protocols, runner, manifest and environment.
It is an unvalidated development bundle. Load `imagined_lora.pt` with the exact base and decoder
LoRA wiring from `donk.add_lora`/`imagine.py`; it is not a FiLM `best.pt` or a playable clone profile.
The base weights are not included. Existing playable profiles are unchanged.

ZIP SHA256: `82f8ad3590394492e8f5ae5af42c9bef70523a1178cd32a16d60ba5849169e3a`.
Base checkpoint SHA256: `d961a2d065464da19809d9b6d13e7467fde06a5a93e93c19b12ecd001cce5c20`.
Manifest SHA256: `ebe8bf37c5cbb879e3c845fbf2b9cf9e8ede9f498393bb9d0706ac04cd927c00`.
Exact per-player metrics and adapter hashes are in `round4-development.json`; complete iteration
records are `round4-donk-development.json` and `round4-broky-development.json`.

```bash
# Run each player in a separate process, from pinned source23292e9 and separate output folders.
python clone-model/round4.py --csnet CSNET --cache CACHE --checkpoint BASE \
  --device cuda --player donk --out RUNS/v1-donk --iterations 4 \
  --moments-per-iteration 80 --select-moments 32 --steps-per-iteration 100 --budget-minutes 60
# Repeat with --player broky --out RUNS/v1-broky.
# Use current source for the conservative completion report:
python clone-model/round4_report.py --runs RUNS --out results.json
```
