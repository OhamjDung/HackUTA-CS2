# Continue the CS2 clone MVP and Round 4 work

Prepared 2026-11-15 from GitHub main fd4188084be0f9b1d95b3e287a521be80c8fff55 plus Claude's recovered local drafts. Pull latest main before starting. Repository: https://github.com/OhamjDung/HackUTA-CS2 . This handoff supersedes stale status statements in handoffs/remaining-work.md; do not delete another recipient's handoff.

## Quick state and readiness

We have a working prototype, not an acceptance-tested MVP. Recorded donk and broky clones and fitted-rule variants donkL/brokyL exist. These L variants are measured habit rules, not the neural movement model. CloneDirector loaded on Tom's PC, attached clones and played a donk route. A correct-side converted T route reportedly stayed within about 11 units in one test. That does not establish every route or utility throw is safe.

The later donk neural model (imagine.py) passed its declared offline test once: mean path error 147.6 vs generic 166.4 (11.3% lower); limit violations 0.05% vs 0.55%. This replaces the earlier blanket statement that every learned experiment failed. But test-C was only 7 rounds /119 moments from existing training matches, base pretraining overlap is unknown, view-turn likeness worsened, and sample diversity narrowed. It is not deployed in CS2. Broky has no equivalent passing generative model; the earlier identity-ranking experiment placed him third among teammates. Never transfer donk's success claim to broky.

Current authoritative evidence: SPEC sections 0,3,8.8-8.12; clone-model/results/imagine-a100.md; release https://github.com/OhamjDung/HackUTA-CS2/releases/tag/donk-imagined-v1 . Existing generated converter and map-review/viewer tools already exist; adapt them, do not rebuild them. Candidate conversion is not approval or deployment.

Testers report fixed tactics, ignoring new information, weak angle clearing, repetitive utility, noisy movement and self-kills. Separate runtime replay/controller defects from learned-policy defects: today testers mostly encounter rule-driven recorded routes plus native AI. A better offline model cannot fix an input held by the replay controller or a stuck grenade.

## Read/recover first

Read AGENTS.md, SPEC.md, clone-model/ROUND3_DESIGN.md, clone-model/ROUND4_GAME_SENSE.md, clone-model/research/cs2-game-sense.md and its four source notes. The Round 4 plan and Tom prompt were untracked when Claude hit its limit; they are recovered with this handoff. Original combined research and notes are preserved with a review warning: source citations and proposed thresholds need checking; recovery is not independent verification. Do not claim research completion equals implementation.

Important correction: ReGameDLL_CS targets CS1.6/Condition Zero, not CS2. Its 1100-unit steps, 2000-unit normal fire and <=150u/s silent-speed rules, single-noise memory and investigation heuristic are hypotheses for an optional configurable baseline. They are NOT established CS2 mechanics. Verify the precise source revision/functions and exceptions, and instrument CS2 sound events. EventPlayerSound Radius/Duration/Step fields alone do not prove what each listener actually hears. Sources: https://github.com/rehlds/rehlds.github.io/blob/master/docs/core-projects/ReGameDLL_CS/index.md ; https://docs.cssharp.dev/api/CounterStrikeSharp.API.Core.EventPlayerSound.html .

## Priority and ownership

| Priority | Work | Owner/machine | Acceptance |
|---|---|---|---|
| P0 | Diagnose self-kills, capture evidence | Tom, existing CS2 machine | Categorized deaths and 5-second timelines; confirmed causes vs hypotheses |
| P0 | Safe information-triggered replay handoff | Runtime agent, clone-director | Visible/audible/threat events interrupt appropriately; no held grenade/button/aim state left behind; human/private-match check |
| P0 | Real clone recording, scoring and synchronized replay | Tom + Ashirwad | A real clone round compared on same clock with source; default-bot baseline; provenance and scores verified |
| P0 | Verify purchases, identity names, both sides, score transitions and handoff | Tom + service owner | Cold-start test, full match, no double counting/phantom rounds, no duplicate names |
| P1 | Measure game-sense proxies and player targets | CPU/data agent | Missingness-aware per-player/per-situation report and tests, using build data only |
| P1 | Round4 training, including broky | Model agent + Colab | Parameterized players, dev-selected model, fresh frozen final tests, complete ablations |
| P1 | Learned movement into candidate playback | Model + existing generated converter owner | Collision/human review, aligned spawn/side/timing, no promotion until private-game proof |
| P1 | Finish demo polish and backup | Frontend/replay owner | Real-vs-clone replay plus offline stock-voice commentary and backup video; three cold-start rehearsals |
| P2 | Full spec extras | Assigned teammates | Profile/scouting page, Atlas style search, hosting/domain, DEV article, licensing/credits and pitch claims checked |

Strict minimum demo per SPEC phase2: real round next to clone round on the same route, spoken commentary, backup recording. Do not cut habit clone in game, replay, similarity/default baseline or the model proof. Full spec includes more than this minimum. Verified real-player voice packs remain blocked on speaker permission/verification; use explicitly fictional stock voices for fallback, not an unauthorized imitation. Review actual upstream licenses before adding a root license; do not guess compatibility from an old handoff.

## Objective game-sense specification

We train observable conditional behavior, not reasoning ability or a hidden intelligence score. Treat each metric as a proxy with confounders. Targets come from the specific player's training data, split by side, weapon/economy and situation where supported. Show counts, match-level uncertainty, missing fields and measurement resolution.

1. Noise exposure: time running/audibly stepping in plausible enemy hearing range before contact; conditional run-to-walk transitions. Own noise level plus enemy-awareness state, not a global silence target.
2. Information response: latency and action after a perceptible sound, sighting or damage: turn, cover, stop, retreat or replan. A purposeful hold need not turn toward every bait sound. Separate those choices and survival outcomes.
3. Angle clearing: angular error/coverage at plausible danger angles and first visibility, using training-only danger maps and defensible visibility estimates. Mesh raycasts alone omit smoke/FOV/occlusion nuances; mark limitations.
4. Controlled peeking/fire: weapon-specific movement at first burst, cover exposure and repeat-peek patterns. Four-Hz data cannot establish sub-tick counter-strafing or precise reaction time; use event/native-tick data where available.
5. Utility support and variety: pre-contact flash/smoke support, route-conditioned throw diversity and self-damage; observed throws are not proof a lineup works from another spawn.
6. Plan diversity/adaptation: route entropy and repetition conditional on side/buy/spawn, and observable post-information movement changes. Do not infer a player's intended plan from the future path being scored.
7. Team/round context: teammate support/trade opportunity, bomb/time/economy-aware movement where inputs and coverage permit. Do not conflate untraded death with bad play.
8. Safe execution: own grenade/fire/fall damage and controller-related deaths; distinguish bomb deaths, teamkills and console/world deaths. Aim for zero avoidable controller-induced harm, not a promise of no self-damage in all human play.

Quirks take priority over generic pro averages WITHIN feasibility and human/safety bounds. Preserve donk's more running/less stillness in appropriate contexts; do not enforce universal walk. Preserve broky's jump/AWP/low slow-walk signature without jumping off ledges or forcing an unaffordable AWP. Recompute supplied z-scores from build data; don't hardcode identities or unverified thresholds. The draft incorrectly infers that broky should always walk more than donk despite broky's low slow-walk signature; use conditional measured targets.

## Detailed next-run implementation plan

Stage A — freeze protocol before GPU work:
- Manifest every source recording, exact Steam ID, source revision/hash and split. Quarantine ambiguous account IDs. All earlier final sets, including test-C, are consumed; acquire independent new matches for donk AND broky. Prefer whole-match test separation over windows/rounds from the same match. Check whether base pretraining overlap can be identified and disclose what cannot.
- Calibrate game-sense targets and uncertainty using training matches only. Freeze dev selection, pass rules and ablations before scoring final data. Bootstrap by match/round, not independent overlapping windows. Few held-out matches cannot establish broad professional skill.
- Distinguish offline evaluator privilege from policy information. Evaluators may use true enemy positions to label outcomes; neither live policy nor its inputs may use hidden enemy truth.

Stage B — CPU implementation:
- Reuse quirks.py, limits.py, demo parser and map_review.py to implement a gamesense module with explicit missing-data flags and metric definitions. Build synthetic tests for yaw wrap, same-team noises, sound expiry/priority, out-of-range events, dead players, missing inventory/visibility, smoke uncertainty and future leakage.
- Keep a causal observation/belief state: last-seen location and time, source/uncertainty of heard position, decaying evidence, teammate information only when actually available. Update only from past/current observations. Apply consistent masking to positions, relationships, relative angles, sound features and other derived channels—not just one position tensor. Do not substitute a precise enemy location for a noisy sound estimate.
- Preserve the base model's tensor/vocabulary contract. First introduce a versioned observation adapter and compare with the original on dev; blind replacement of all enemy positions is an out-of-distribution change. Unknowns need explicit masks. Train and inference must share the same observation builder.
- Parameterize donk.py/imagine.py and companion loaders/evaluators/paths via --player and Steam-ID registry, with separate player-specific initialization/artifacts. Keep a regression path reproducing the frozen donk experiment. Both players must flow through identical code, no name-dependent gameplay rules.

Stage C — candidate selection/objective:
- Keep imitation plus KL-to-base and human-limit filters. Normalize score components with TRAINING scales. Prefer lexicographic gates: valid/safe/human-limit compliant, preserve distinctive player-conditioned behavior, then game-sense proximity and path/view match. Document tradeoffs; arbitrary loss weights can erase quirks.
- Add circular view-angle/turn-rate loss to address the observed turn drift, plus conditional noise/reaction proxies that can actually be evaluated for the generated horizon. Do not claim a 4-second generator learns whole-round route entropy, buying or utility strategy without appropriate outputs and longer-horizon controller evaluation.
- Keep multiple genuinely distinct valid futures with a declared diversity distance; normalize/deduplicate and train on their rollout contexts. Compare against original best-of-8; do not reward entropy at the expense of valid movement or player consistency.
- Use sampled per-round tactical/route context only if supported by both training and inference. Treat new plan conditioning as an ablation/stretch, not MVP prerequisite. Route selection must use available observations, not future ground truth.

Stage D — staged GPU experiments on available premium A100:
1. Reproduce original baseline and inspect labels. No expensive run before schema/tests pass.
2. Dev ablation: baseline; path+view; +causal observations; +conditional game-sense judge; +diverse futures. Keep compute/seed/sample budgets comparable. Run both players; do not assume donk improvements transfer.
3. Evaluate free-running rollouts, not just teacher-forced loss or best-of-N. Report mean and best-of-N separately, path/view distributions, player-specific quirks, human limits, conditional responses and diversity. Preserve failed runs.
4. Select with dev only, then evaluate ONCE on newly frozen test matches; report per-player results and uncertainty. Predeclare that neither a path-only gain nor likelihood identification proves game sense. Any following iteration needs independent final evidence.
5. Produce candidate artifacts with provenance, model and observation version, spawn/side/time alignment, manual geometry/utility approval and no automatic playable-profile promotion.

Stage E — live runtime and acceptance:
- During replay the native bot cannot adapt; add evidence-driven interruption and explicit cleanup/ownership transfer, not a competing hidden movement/aim loop. Threats must be observable to the bot. Test sound/visibility triggers separately from damage/fire.
- Randomize among compatible routes within measured spawn tolerance, side/source/buy type; add history-aware selection without forcing uniform play or impossible spawn transitions. Preserve learned shares over a declared measurement window. No teleports or stale utility.
- Avoid omniscient 'nearest enemy' walk/aim rules. Use causal likely-danger areas, heard/seen evidence and native bot visibility. Do not force a delayed grenade release or clear its attack state until controller semantics and Tom's evidence identify safe behavior.
- Compare v1/L/native baselines and new candidate on controlled private scenarios: silent enemy, audible running, distant/same-team sound, damage, enemy seen, bait noise, utility in progress, map/round/death disconnect. Log why control changed. Record both sides and both players, then quirk/game-sense/limits and blind reviewer checks.

## Prompt 1 — model/data agent (CPU first, then Colab)

Read this handoff and recovered Round4 plan/report, current AGENTS/SPEC and imagine-a100 results. Implement the CPU observation/measurement and player-parameterization work in Stages A/B first, using existing open-source bases and tests. Define the next experiment protocol and targets from training data before any GPU run. Include broky throughout. Preserve donk's passing checkpoint and do not reuse consumed final tests for tuning. Do not replace causal observations with omniscient enemy state. Then run the staged dev ablations on the best available authorized Colab GPU, choose using dev only and evaluate on fresh final matches. No claim of broad game sense from a four-second movement score. Own clone-model and agreed pipeline metric modules, coordinate shared parser changes. Update SPEC per commit, concise messages, push your branch and return runnable commands, hashes, per-player metrics and failures. Do not duplicate runtime/Tom tasks. You may use shell, filesystem, Git/gh, official packages, Python/.NET, browser automation and existing Colab tools for this project subject to actual tool permissions; no credentials or safety bypasses.

## Prompt 2 — runtime agent

Read this handoff's Stage E, current CloneDirector code and Tom's findings before fixing self-kills. First instrument current control ownership, route choice, active weapon, attack/throw state and stop reason. Implement observable sound/visibility-triggered interruption with native-AI handoff and cleanup tests; add compatible history-aware route sampling. Quirk fidelity must stay conditional and measured; no omniscient enemy positions or generic walking/aim overrides. Keep interface formats stable and work with Tom for live tests. Do not start/restart his game without permission or run the bot-base installer. Produce isolated changes, regression tests and a candidate build; report compile/fake tests separately from live behavior. Never apply speculative grenade handling as a 'fix' without reproducing the cause.

## Prompt 3 — Tom's self-kill diagnosis

Read AGENTS section7 and the recovered handoffs/tom-self-kill-diagnosis.md. Diagnose before modifying plugin/profile behavior. Use an existing recording if possible; otherwise have Tom authorize a controlled private run with reliable demo capture. Do not send record over netcon. Collect clone ID/actual bot identity, side, round/tick, attacker/victim/weapon/damage source, position/velocity, active grenade/attack state and the previous five seconds of route/handoff/controller logs. Separate own HE/fire, fall/world, bomb explosion, teamkill, plugin slay and parser misclassification. Event names/fields are hypotheses until checked against actual parser/schema; world death alone is not proof of suicide. Compare native/v1/L and routes on/off, isolating one variable at a time. Prioritize 'stop during a primed grenade' as a hypothesis, not an established cause. Report confirmed/ruled-out/not-tested with evidence, smallest proposed fix and tests; do not apply that fix in the diagnosis task. Keep recordings out of Git. Read/save prompt context outside checkout, delete only your addressed consumed prompt in the findings commit and update SPEC.

## Prompt 4 — service/frontend MVP closure

Pull main, read SPEC and this handoff. Reuse the existing service, scoring and replay code; do not build another viewer. Check live halftime/round event accounting against the authoritative CS2 score and attach real recorded clone traces with driver/model provenance. Prove one real-player/clone comparison and a native/default baseline on the same clock; label source replay, simulated trace and neural candidate differently. Add offline stock-voice commentary if consented real-player packs are unavailable, keep keys out of Git, make an offline fallback and record backup demo video. Run three cold-start rehearsals, including missing trace/failed match/restart cases; report exact results. Coordinate game-machine actions with Tom. Return remaining gates rather than claiming mock tests prove gameplay.

## Full-spec backlog / finish checklist

- Capture and score a real clone match; record default-bot comparison; validate purchases and handoff, self-kills, both clones and both sides.
- Verify generated candidate converter/viewer integration with the latest passing donor model; manually approve geometry/timing/input/utility; do not count old review samples as deployed neural routes.
- Broky generative training/evaluation; per-player quirk and human-limit evidence; human blind panel with predeclared sample size and uncertainty (not 'failure to reject chance means human indistinguishable').
- Replay with required media/commentary and backup; clone-v-clone second; document video-vs-map limitation explicitly if scope is reduced.
- Confirm lobby/match/profile page owners; heatmap, habits/scouting and Atlas similar-player search where required.
- Hosting/domain/local fallback, DEV article, sponsor checklist, business/pitch explanation and accurate current roster claims. Verify external requirements at delivery; do not buy services or accept terms without required authorization.
- License/third-party notices based on actual component provenance; voice consent and verified account prerequisites; do not fabricate licensed assets.

No arbitrary completion percentage or hour guarantee: gameplay stability, real-match evidence and fresh model evaluation are unresolved dependencies. The shortest credible MVP path is the existing recorded-habit clone plus real replay/proof, with neural results separately and honestly presented. Closing the full adaptive learned-clone spec is additional work.

## Recipient cleanup and reporting

Save needed instructions outside the checkout. After consuming YOUR continuation handoff, remove only handoffs/mvp-round4-continuation.md on your task branch, update the temporary SPEC row and commit the cleanup with your work. Do not remove Tom's prompt or another agent's handoff. Research, designs and source documentation are durable: do not delete those. Never commit demos, weights, raw datasets or keys. Pull before editing SPEC, preserve teammates' changes and report ran/read/proposed separately. Current recovered research/plan is design work, not an implemented training improvement or a newly executed experiment.
