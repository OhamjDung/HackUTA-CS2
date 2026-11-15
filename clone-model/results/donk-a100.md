# Donk-only model, first run: failed its pass rule

Run on 2026-11-15 on an NVIDIA A100 (40 GB) in Google Colab. Code: `clone-model/donk.py` at commit
`96ff4f0`. Design and pass rule: `clone-model/ROUND3_DESIGN.md` section 8. Numbers: `donk-a100.json`.

## What ran

- CS-NET v4 with small adapters (LoRA, 1.18 million trainable numbers) in its decoder, trained on 754
  donk windows, with a penalty for drifting from CS-NET's move probabilities (KL weight 0.1).
- Checkpoints chosen on dev-A (donk's even development rounds, 148 windows) by teacher-forced loss.
- One evaluation on dev-B (donk's odd development rounds): 168 moments in 7 rounds, 8 sampled
  4-second futures per moment from the donk model and from the unchanged base model.

## Training

The best checkpoint was step 100: loss on dev-A 0.6236 against 0.6264 for the base, **0.44% better**
(round 1 managed 0.25%). After that the model memorised its training rounds: by step 400 it was 1.4%
worse than the base. Training stopped early and kept step 100. About 5% of training windows were
dropped because their real future broke a human per-step limit.

## Result on dev-B: fail

| Rule | Donk model | Base model | Real donk | Result |
|---|---|---|---|---|
| P1: mean path error (lower is better) | 180.4 | 172.7 | | **Fail.** Donk model worse by 7.7 units (95% range 2.8 to 12.6) |
| (best of 8 futures) | 97.0 | 92.6 | | worse |
| P2: step-distance distribution, distance from real donk | 4.65 | 3.34 | | worse |
| P2: view-turn distribution, distance from real donk | 1.36 | 1.45 | | better |
| P2: backwards share of moving steps | 10.5% | 12.4% | 7.2% | better |
| P2 overall | closer on 2 of 3 | | | pass |
| P3: steps breaking a human limit | 0.64% | 0.46% | | **Fail** |

## What it means

1. **The first donk model that generates play does not generate donk's paths better than the
   generic model.** It is slightly worse, and it breaks human limits slightly more often.
2. **Better scores on recorded moves did not carry over to generated play.** Teacher-forced loss
   improved 0.44%, but free-running paths got worse. This is the classic weakness of learning only
   from recorded moves (behaviour cloning): during generation, small errors compound into situations
   the recordings never showed. Methods built for this weakness: DAgger, and training on the model's
   own imagined rollouts (the self-training in design section 8.4).
3. **Some behaviour did move towards donk:** less backwards walking and a turn distribution closer to
   his. The base model itself walks backwards in 12.4% of moving steps against donk's 7.2%, so any
   generated route needs the backwards check.
4. **Data is the limit.** 47 donk rounds were enough to start memorising after 100 steps.

## Not done

Free-running generation from development rounds only; no CS2, no people panel. The merged model
(about 529 MB) stays on the Colab machine and was not saved, because it failed its rule. dev-B is now
used: a further experiment must not be judged on it again.
