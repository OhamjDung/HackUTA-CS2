# Why the first learned model failed, and what replaced it

Written 2026-11-14 by Arjun (with Claude). The numbers come from the saved per-window results of the
first A100 run (`first-a100.json`) and from a new measurement on match recordings. No model was
trained for this note.

## 1. The neural identity adapters are not usable

| Check on the saved held-out results | donk | broky |
|---|---|---|
| Test windows | 29 | 42 |
| Windows where the path with the player's identity is identical to the path with no identity | 72% | 64% |
| Path error, own identity minus no identity (game units), with its 95% range | +0.4 (−1.6 to +2.5) | +7.1 (−0.9 to +21.1) |
| Path error, own identity minus the other player's identity, with its 95% range | +13.8 (−1.1 to +41.4) | −5.9 (−17.1 to −0.0) |
| Spread of path error across windows (standard deviation) | 137 | 93 |
| Training score with identity against without (lower is better) | 0.6594 against 0.6611 | 0.6522 against 0.6541 |

Reading:
- The adapter changes nothing in about two thirds of cases.
- Every range includes zero or touches it. The test could not have detected a real effect of this size.
- Identity improves the training score by 0.25%. The game situation already explains a 4-second move.

**Decision: the adapters are not offered to the team as playable bots.** They have no measurable
effect, they cannot drive a bot during a match, and weights may not be committed to this repository
(`AGENTS.md` section 4). They stay downloadable from the release `learned-clones-a100-v1` for anyone
who wants to inspect them.

## 2. Where identity is in the data

Measured: 27 quirks per player per match, at 64 ticks per second, for all ten players in each
building match. Code: `clone-pipeline/clone_pipeline/quirks.py`. Held-back matches were not used to
fit anything.

Each real player was then tested on his own held-back match, which the rules had never seen:

| Player | Held-back match | "Who is it?" among 5 teammates | Distinctive quirks reproduced |
|---|---|---|---|
| donk | 2393242 (17 rounds) | 1st of 5 | 8 of 10 |
| broky | 2393024 (22 rounds) | 1st of 5 | 9 of 10 |

So identity is easy to find in rates over a whole match. It is not in a single 4-second path.

donk's strongest quirks: stands still 11% of the time (others 20%), is far from teammates 17% of the
time (others 41%), turns at 4.4 degrees per second while moving (others 2.4), jumps 4.1 times per
minute (others 1.7), is in the first kill of 31% of rounds (others 19%).

broky's strongest quirks: jumps 6.2 times per minute (others 1.1), fires 11% of his shots with the
sniper rifle (others 1%), fires single shots in 64% of bursts (others 39%), throws flashbangs as 43%
of his grenades (others 26%).

Limits: one team per player, four building matches, and a small candidate list (5 teammates). Role
is mixed in: a sniper is easy to tell from a rifler.

## 3. The test rule, and how it was loosened

The first rule: the player's own identity must beat every alternative outright on path error.

The new rule, fixed before any scoring (constants at the top of `quirks.py`):
- **Who is it:** the true player must be among the 2 nearest of the candidates.
- **Per quirk:** the measured value must be on the player's side of the population mean and cover at
  least half of the distance to the player's value.
- **Overall:** at least 60% of the player's distinctive quirks must pass.

Do not change these after seeing a bot's or a model's score.

## 4. What a retrained neural model should change

Untested recommendations, from the failure above and from published work on individual player models:
1. Train across many players, not two. OpenCS2 has 3,054 Mirage rounds with ten players each.
2. Feed identity into every generation step, not into one vector.
3. Remove the penalty that pulls the identity-adjusted vector back toward the unadjusted one.
4. Hide the identity at random during training, and amplify the with-identity difference when generating.
5. Sample moves at random from the model's probabilities. Always taking the most likely move erases tendencies.
6. Judge it with the quirk test above on many seconds of generated play, not with per-window path error.
