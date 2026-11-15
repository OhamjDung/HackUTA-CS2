# Second learned-identity experiment: the held-back test passed

Run on 2026-11-14 on an NVIDIA A100 (40 GB) in Google Colab. Code: `clone-model/v2.py` at commit
`94a6fdb`. Full numbers: `second-a100.json`. Design: `SPEC.md` section 8.9.

## What ran

- The frozen CS-NET v4 base, plus a new identity adapter with 248,000 trainable numbers.
- 10 identities: the 5 Spirit players and the 5 FaZe players in the nine cached matches.
- 2,000 training steps, about 7 minutes. Every 100 steps, a check on development rounds (rounds from
  the building matches that training does not use).
- The checkpoint with the best development check was step 1,800.
- The held-back test ran **once**, automatically, on that checkpoint. Held-back matches: donk's
  2393242 and broky's 2393024. Nothing was re-run or re-tuned afterwards.

## The test and the result

For each player, all of the player's windows in the held-back match are scored under each of the
5 identities of the player's team: how likely are the player's real moves under that identity?
The true identity is then ranked. The rule, fixed in the code before the run: a player passes when
the true identity is in the top 2; the experiment passes when at least 60% of players pass.

**Result: pass. 8 of 10 players in the top 2 (rule: 6). 6 of 10 ranked first.** Guessing would put
4 of 10 in the top 2.

| Team | Player | Windows | Rank of true identity (of 5) |
|---|---|---:|---|
| Spirit | donk | 276 | 1 |
| Spirit | magixx | 331 | 1 |
| Spirit | zont1x | 302 | 1 |
| Spirit | SH1R0 | 328 | 2 |
| Spirit | tN1R | 290 | 2 |
| FaZe | jcobbb | 272 | 1 |
| FaZe | Twistzz | 345 | 1 |
| FaZe | karrigan | 338 | 1 |
| FaZe | broky | 396 | 3 (fails) |
| FaZe | frozen | 332 | 4 (fails) |

## What the result does not show

1. **The identity does not beat "no identity" for most players.** For 6 of the 10 players (donk,
   tN1R, broky, frozen, Twistzz, karrigan), the real moves are slightly *more* likely with no
   identity than with the player's own. The true identity wins among teammates by being the least
   wrong of the five. Only magixx, zont1x, SH1R0 and jcobbb are better described by their own
   identity than by the plain model.
2. **The differences are small.** The gap between the true identity and the average teammate is
   about 0.005 units of loss on a loss of about 0.6, under 1%. The checkpoint was picked in bfloat16
   on 120 development windows, where rounding error is of a similar size. A float32 re-check of the
   top checkpoints was not done.
3. **broky, one of the two cloned players, fails individually** (3rd of 5).
4. **It does not generate play.** It scores real recorded moves. It is not the path test in
   `SPEC.md` section 8.6, and it produces no routes a bot can play. That needs the prediction-engine
   change in `SPEC.md` section 8.9.
5. **Small and narrow.** Two teams, one map, one held-back match per team.

## Pitch wording

Agreed with Ashirwad: "Given a player's real moves from a match it has never seen, the model picks
out who the player is among their teammates for 8 of 10 players." Do not say that the model plays
like the player, generates the player's paths, or beats a model without identity.

## Artifacts

Saved on 2026-11-14 to Arjun's PC: `Documents/Codex/2026-11-14/files-pasted-by-the-user-handoff/work/learned-results-v2/learned-clones-v2.zip` (1,854,456 bytes, SHA256 `3f278e33956ff46660baf1350055242ddc46407550f260c68c1dd941f61abcdd`, the same checksum Colab printed). It holds `best.pt` (step 1,800), `last.pt`, `registry.json`, `training.json`, `test.json` and `progress.json`. `best.pt` was loaded on the PC: 10 identities, all values finite. Not committed (`AGENTS.md` section 4); ask Arjun for a copy.

Data credit: Julien Blanchon / OpenCS2, CC BY 4.0.
