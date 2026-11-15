# First learned-clone experiment: identity test failed

Ran on 2026-11-14 using NVIDIA A100-SXM4-80GB (PyTorch 2.14.1+cu130). Training stopped after 600 updates (229.1 seconds of optimizer/development work); development loss selected step 400. The pretrained 138.7M-parameter base stayed frozen; the identity/FiLM adapter has 100,032 trainable parameters.

| Player | Held-out windows | Own path error | Other identity | Generic base | Pass |
|---|---:|---:|---:|---:|---|
| donk | 29 | 134.15 | 120.33 | 133.74 | No |
| broky | 42 | 99.83 | 105.76 | 92.70 | No |

Errors are mean average displacement in Source game units, lower is better. A pass requires each player's own identity to beat both alternatives. donk's own adapter was worse than broky's and slightly worse than the base. broky's own adapter beat donk's but was worse than the base. **Both fail. These checkpoints are experimental and have not been promoted or deployed.**

Data: nine verified Mirage recordings, 180 rounds; 99 train, 42 dev, 39 held out. Training used 1,656 windows, development contained 756; 24 windows per player were used at each development check. Final evaluation used 29 donk and 42 broky windows, with one deterministic greedy prediction for own/other/base (213 inferences). Holds: 2393242 and 2393024. The ambiguous donk event-account recording 2393226 was excluded.

The small development-loss improvement did not establish held-out likeness. No identical quirks, professional combat skill, purchase behavior, grenade lineups or human aim has been demonstrated. Original CS-NET pretraining overlap is unknown. Existing recorded-opening clones remain separate; their model fields stay null.

The ZIP contains adapter-only best.pt and last.pt, environment, registry/data manifest, per-window metrics and final progress. Keep the separately downloaded pinned CS-NET base checkpoint; its SHA256 and source revision are in the results JSON/checkpoints. training-progress.json preserves the original trainer state; progress.json records the completed failed validation. No raw demos or base weights are included.

Reproduction: open Reproduce-first-learned-clones.ipynb in Colab and select A100 before execution. Its cells compile locally, but that clean reproduction notebook itself has not been executed end to end; the equivalent experiment ran in the linked saved Colab notebook. Results may vary by software/hardware. Do not use this held-out failure to tune another model on those matches.
