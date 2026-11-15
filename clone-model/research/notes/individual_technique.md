# Individual technique of pro CS2 players, as measurable behaviour in demo files

Scope note: "unit" below means a Hammer unit, the game's distance unit (about 1 inch). "u/s" means units per second. A "tick" is one server simulation step; CS2 demos are usually recorded at 64 ticks per second. Numbers marked [CS:GO] come from the older game and may not hold in CS2. Numbers marked [community] come from guide sites, not from Valve or from a measured study.

Overall honesty note: I found no published study that measures pro walking share, angle-clearing order, or reaction to being shot from demos. The analytics platforms publish definitions for aim metrics (crosshair placement, time to damage, counter-strafing) but not for sound or positioning behaviour. Most of the "how pros do it" material is coaching opinion. Thresholds for those parts are my proposals, and they are listed under Inferences.

## Sound discipline: run vs shift-walk vs crouch

### Takeaway
Running is the only footstep movement that enemies hear; walking (holding Shift) is silent and crouch-walking is nearly silent, and running is audible to roughly 1100 units according to one community source. No source publishes how often pros walk or how close to enemies they switch, so this must be measured from our own demos.

### Cited Findings
- Walking with Shift is "silent to enemies". Running is audible within about 1100 units (about 28 metres). Crouching makes a faint sound "at close range". Jumping/landing makes a loud sound audible at long range. Weapon switch, reload, AWP/Scout zoom, grenade pin pull, bomb plant/defuse and weapon drop also make sound. No source for the 1100-unit figure is given [community, CS2] — [csdb.gg, What actions make a sound](https://csdb.gg/blog/insights/what-actions-make-a-sound-enemies-can-hear-in-cs2)
- A different community article gives footstep audible range as about 8–12 metres depending on surface; this conflicts with the 1100-unit figure. Neither is a Valve number — summarised from search results pointing to [csdb.gg audio guide](https://csdb.gg/guides/audio-guide/) and [cs2guide sound cues](https://cs2guide.pages.dev/gameplay-mechanics/sound-cues-information)
- Knife speeds: running 250 u/s, walking 130 u/s, crouch-walking 85 u/s [community wiki] — [bo3.gg knife wiki](https://bo3.gg/wiki/knife-t); [counterstrikewiki Knife](https://counterstrikewiki.com/Knife). The 130/250 ratio is 0.52, so walking speed is about 52% of the weapon's run speed (my arithmetic; no source states 52% directly, and csdb only says walking is "roughly half" of running — [csdb.gg movement guide](https://csdb.gg/guides/movement-guide/)).
- Run speeds per weapon (u/s) [community, CS2]: knife/C4 250, most pistols 240, Desert Eagle 230, SMGs 230–245, shotguns 215–225, AK-47 215, M4A4/M4A1-S 225, AWP 200, Negev/M249 195 — [csdb.gg movement guide](https://csdb.gg/guides/movement-guide/)
- Silent landing rules [CS:GO, Valve wiki, reported via search snippet; page returned 403 to direct fetch]: jumping onto a ledge 9 units or higher (11 at 128 tick) lands silently; running off a drop of 47 units or less (46 at 128 tick) lands silently — [Valve CS:GO Mapper's Reference](https://developer.valvesoftware.com/wiki/CS:GO_Mapper%27s_Reference). A CS2 guide says the 9-unit rule carries over to CS2 — [swap.gg jump height in CS2](https://swap.gg/blog/player-jump-height-in-cs2)
- The pro-movement paper (Durst et al., 2024) models movement with three speed levels in its 97-option action space but does not report walk or crouch shares; movement commands were not in the logs and were inferred from position and velocity — [arXiv 2408.13934](https://arxiv.org/html/2408.13934v1)

### Inferences
- Proposed label per tick (from velocity in the demo, horizontal speed only): "silent walk" if on ground, not ducking, and speed ≤ 0.55 × weapon run speed; "run" if speed > 0.55 × weapon run speed; "crouch" if the duck flag is set. Use the walk button flag from the demo's button field if the parser exposes it; it is more reliable than a speed cut-off.
- Proposed sound-risk metric: share of ticks spent running while the nearest enemy is within 1100 units (the community audible range). Report it per round phase (before first contact vs after). Compare bot vs pro on the same map regions.
- Proposed "switch distance" metric: for each round, the distance to the nearest enemy (or nearest likely enemy position, see next section) at the tick where the player switches from running to walking. The distribution of this distance in donk/broky demos is the target for the bot.
- Proposed "silence duration" metric: length in seconds of continuous walking/crouching/still segments, split by side (T/CT) and by whether an enemy is within 1100 units.
- Proposed "sound events" metric: count of loud non-footstep sounds near enemies (landing from more than 47 units, weapon switch, reload, scope) within 1100 units of an enemy. The 1100 figure for these is my extension; no source gives their ranges.

### Gaps
- No Valve-confirmed footstep audible distance or speed threshold for footsteps in CS2. Confirm by testing on a private server or by reading CS2 game files.
- No published statistic on how often pros walk, by role or side, or how far from contact they switch. Nothing found from Leetify, Scope.gg, HLTV, Refrag or academic papers.
- CS2 walk speeds for weapons other than the knife were not found.

## Checking and clearing angles, crosshair placement, pre-aim

### Takeaway
The platforms measure crosshair placement as how far (in degrees) the crosshair has to move from first seeing an enemy to first damaging them; lower is better. Leetify uses the median per match, Refrag reports about 6.7 for FACEIT level 10 players, and pre-aim of hidden positions is not a published metric anywhere I found.

### Cited Findings
- Leetify definition: crosshair placement "measures the average distance (in degrees) your crosshair moved" from first seeing the enemy until first damaging them; outliers removed by using the median; lower is better — [Leetify stats glossary](https://leetify.com/blog/leetify-stats-glossary)
- Leetify definition: time to damage "measures the average time it took you from seeing the enemy player to first dealing damage to them". Any value of 1 s or more is excluded; median used. Leetify says it is not reaction time but a combination of accuracy, crosshair placement and reaction time — [Leetify stats glossary](https://leetify.com/blog/leetify-stats-glossary)
- How Leetify decides "enemy seen": earlier it used server radar events, which update at a set rate and lag 0–500 ms (examples given: 421 ms and 82 ms). Now it replays player positions at each significant event (a hurt or a shot) to check whether any part of the enemy's body or gun was visible, how far the crosshair was from the enemy at first sighting vs at the event, and whether the attacker recently saw the enemy. Exact ray-trace rules are not given. Leetify says 400–500 ms time to damage is "actually really fast" — [Leetify, Enemy actually spotted](https://leetify.com/blog/enemy-actually-spotted/)
- Refrag "Initial Crosshair Placement": where the crosshair sits just before a duel, compared with where the enemy appears; lower is better. FACEIT level 10 average 6.72 vs level 5–8 average 7.46 (9.9% gap). Units are not stated (likely degrees). Sample size not stated — [Refrag, three stats that separate level 10](https://refrag.gg/blog/three-stats-that-separate-level-10-faceit-cs2)
- Leetify-based pro analysis (Feb 2024, CS2, players with ≥30 HLTV matches, about 308 players): donk was at the 34th percentile for crosshair placement; broky was below average in most aim categories; AWPers generally score worse on crosshair placement. Only percentiles are given, not raw degrees — [Nomiun Substack, Which CS pros have the best aim](https://nomiun.substack.com/p/which-cs-pros-have-the-best-aim)
- Opinion: good crosshair placement "reduces the distance you need to flick by 50-90%" — [csdb.gg advanced mechanics guide](https://csdb.gg/guides/advanced-mechanics-guide/)
- Scope.gg tracks time to kill and first-bullet accuracy but I found no published formula — [scope.gg compare](https://scope.gg/compare); [scope.gg headshot stats](https://scope.gg/headshot-stats)
- Standing eye height is 64.09 units, standing height 72, crouched height 54 [CS:GO, Valve wiki, via search snippet] — [Valve CS:GO Mapper's Reference](https://developer.valvesoftware.com/wiki/CS:GO_Mapper%27s_Reference)
- Mirage A clearing order from one guide (opinion): A Ramp, Tetris, A Default, Triple Box, Stairs — summarised from search results for [gamehub Mirage guide](https://gamehub-al9.pages.dev/guides/cs2-map-guide-mirage). Palace exit: pre-aim the corner where defenders commonly hold — same search. Dignitas (CS:GO era): most Ts enter A from Ramp and Palace — [Dignitas, Mirage: How to hold A site](https://dignitas.gg/articles/blogs/CSGO/8807/mirage-how-to-hold-a-site)
- The pro-movement paper used a rule-based aim module, not a learned one: with no enemy visible it aims using a probabilistic map of where enemies are likely to be (predictive aim); with an enemy visible it tracks one target and fires when the crosshair is on the enemy's bounding box — [arXiv 2408.13934](https://arxiv.org/html/2408.13934v1)

### Inferences
- Crosshair placement metric to compute from demos: at the first tick an enemy becomes visible (needs a visibility check against map geometry, e.g. a ray trace from eye to enemy head/chest), compute the angle in degrees between the view direction and the direction to the enemy's head. Report median per match. Separately report vertical error (pitch) to test "head height" placement.
- Time to damage: ticks from first visibility to first damage event, divided by tick rate; drop values ≥ 1 s; use the median. This copies Leetify's definition.
- Pre-aim metric (not published anywhere; my proposal): build a list of common hidden positions on Mirage from pro demos (the places where enemies were first seen or killed most often). At each tick, check whether the view direction points within about 5° of a common position that is not yet visible. "Pre-aim share" = share of ticks, while moving through a contested area, that the crosshair points at such a position. The 5° value is a guess to be tuned on pro data.
- Angle-clearing sequence metric: for each area entry (e.g. Ramp → A site), record the order in which the crosshair visits each common position. Compare the order and timing with pro sequences. This directly addresses "never checks angles".

### Gaps
- No platform publishes a pre-aim metric or the visibility rules in detail.
- No measured raw crosshair-placement values for donk or broky; only percentiles.
- No demo-measured clearing order for Mirage from any pro; only guide opinions.

## Peeking technique and counter-strafing

### Takeaway
Shots are accurate only when speed is below about 34% of the weapon's max speed, and Leetify and Refrag both measure this as the share of rifle shots fired below that speed; jiggle peeks expose the player for roughly 100–200 ms.

### Cited Findings
- Leetify "proper counter-strafing": a good shot has velocity below 34% of the weapon's max speed, "34% is when inaccuracy kicks in". Only rifle shots fired while an enemy is spotted count; crouched shots excluded. Metric = good shots / all such shots — [Leetify stats glossary](https://leetify.com/blog/leetify-stats-glossary)
- Valve has never published the 34% number; it is a community rule. One guide puts it at about 88 u/s for rifles; another gives 73.1 u/s for the AK-47 (34% of 215). One guide claims counter-strafing gets below the threshold in 1–2 frames instead of about 10 — summarised from search results incl. [turbosmurfs counter-strafe guide](https://turbosmurfs.gg/?p=8949) and [gamertagmythras counter-strafe guide](https://gamertagmythras.com/blog/counter-strike-2/cs2-movement-counter-strafing-guide)
- Natural deceleration without counter-strafing takes "about 100ms" [community] — [csdb.gg advanced mechanics guide](https://csdb.gg/guides/advanced-mechanics-guide/)
- Refrag says counter-strafing above 90% is strong and names donk as an excellent counter-strafer, without numbers — [Refrag counter-strafing blog](https://refrag.gg/blog/counter-strafing-the-key-to-precision-aim-in-counter-strike-2)
- Jiggle peek: briefly strafing past an angle and back, exposure "roughly 100-200ms" — [csdb.gg advanced mechanics guide](https://csdb.gg/guides/advanced-mechanics-guide/); another csdb page says each exposure is under 200 ms — [csdb.gg movement guide](https://csdb.gg/guides/movement-guide/)
- Shoulder peek: show only the edge of the model to bait an AWP shot; then "roughly 1.5 seconds before they can fire again" — [csdb.gg advanced mechanics guide](https://csdb.gg/guides/advanced-mechanics-guide/)
- Wide peek: fully committing to swing past an angle at maximum speed; Ferrari peek: wide peek at max speed without pre-aiming — [csdb.gg advanced mechanics guide](https://csdb.gg/guides/advanced-mechanics-guide/). Sources disagree on "jump peek": Dignitas calls it a jump-and-strafe back for information; SteamAnalyst uses it for a running jump past an angle — [Dignitas, improve your peeks](https://dignitas.gg/articles/cs2-how-to-improve-your-peeks); [SteamAnalyst peeking guide](https://www.steamanalyst.com/guides/cs2-shooting-peeking-movement-guide)
- Opinion: "a jiggle peek asks a question, while a wide peek commits to an answer" (use small peeks for information, wide peeks once you know where the enemy is) — summarised from [metabot.gg peeking guide](https://metabot.gg/en/cs2/guides/cs2-peeking-guide-wide-jiggle-shoulder)

### Inferences
- Counter-strafe metric: for each rifle shot while an enemy is visible and not crouched, horizontal speed at the shot tick / weapon max speed; "good" if < 0.34. Report the share. Target from Refrag: > 90% is strong.
- Peek classifier from demo data, for each "exposure" (a continuous run of ticks where the player is visible to at least one enemy): jiggle = exposure < 200 ms and the player returns to cover without firing; shoulder = exposure < 200 ms, and only a small part of the hitbox visible (needs per-bone visibility); wide = speed at exposure start > 0.8 × max speed and lateral travel past the corner larger than a threshold to tune (e.g. 64 units); jump peek = airborne during the exposure. These thresholds are my proposals.
- Proposed info-then-commit metric: share of wide peeks preceded within 3 s by a jiggle/shoulder peek of the same angle.

### Gaps
- No published share of each peek type for pros.
- No Valve-confirmed accuracy threshold; the 34% value should be checked against CS2 weapon data files.

## Reacting to danger: being shot, hearing enemies

### Takeaway
I found no published measurement of how pros respond to taking damage or hearing enemies. Only coaching opinion exists, so the reaction must be measured from our own demos.

### Cited Findings
- The pro-movement paper measured "mistakes" such as leaving high ground or abandoning defensive positions; its learned model's mistake rate was close to humans and well below the other bots. It also measured player lifetimes, kill locations and shots per kill as distribution distances (lower is closer to human): map occupancy 8.2 (learned model) vs 15.2 (shipped CS:GO bot); kill locations 6.7 vs 16.4 [CS:GO, Dust2, Retakes only] — [arXiv 2408.13934](https://arxiv.org/html/2408.13934v1)
- The same paper notes its model only uses the current state as input, to avoid the model repeating recent actions — [arXiv 2408.13934](https://arxiv.org/html/2408.13934v1)

### Inferences
- Proposed "reaction to damage" metrics, from each player_hurt event where the victim survives: (1) time until the victim's velocity direction points away from the attacker (retreat) or toward cover; (2) whether the victim fires back within 500 ms; (3) whether the victim is at a different position (more than 100 units away) 2 s later; (4) whether the victim dies within 3 s. Compare distributions bot vs pro.
- Proposed "reaction to sound" metric: when an enemy within 1100 units runs, jumps, reloads or switches weapon (all are events or inferable from demo data), measure whether the listener's view direction turns toward the sound source within 1 s, and whether the listener stops running.

### Gaps
- No data on how fast pros reposition after damage, or how often they fall back vs hold.
- No source covers the CS2 movement slow-down when hit (tagging) with numbers.

## Off-angles, re-peeking, varying positions

### Takeaway
Off-angles (holding from an unexpected spot) and avoiding re-peeking the same angle are standard coaching advice, but no source publishes a measured rate for pros.

### Cited Findings
- Off-angle: moving to an unexpected position so the enemy must adjust aim, buying "precious milliseconds"; no number given — [csdb.gg advanced mechanics guide](https://csdb.gg/guides/advanced-mechanics-guide/)

### Inferences
- Off-angle metric: for each CT hold position, how far it is (in units) from the most common hold positions in all pro demos on the same spot; an off-angle is a hold more than some distance (tune, e.g. 150 units) from the mode, or with a view direction different from the common one.
- Re-peek metric: after a peek where the player took or dealt damage and went back to cover, the share of times the next peek within 5 s is from the same position (within 32 units) and view direction (within 10°).
- Position-variety metric: entropy of hold positions per player per site across rounds of a match.

### Gaps
- No published pro rates for off-angles, re-peeks or variety.

## Avoiding self-damage: own grenades and fall damage

### Takeaway
Fall damage starts at about 151 units of drop (crouch-jump-off case) in CS:GO, and self-damage from own grenades is measurable directly from damage events; I found no published rate for pros.

### Cited Findings
- Smallest drop that causes damage: 151 units for crouch-then-jump-off-and-stay-crouched [CS:GO]. Running-off damage at 128 tick is roughly 9.525 × √height − 139.25 [CS:GO] — [Valve CS:GO Mapper's Reference](https://developer.valvesoftware.com/wiki/CS:GO_Mapper%27s_Reference) (via search snippet; direct fetch returned 403)
- Leetify tracks teammates flashed per flashbang (blind > 1.1 s), HE damage per HE, and unused utility value on death, but I found no published definition for self-damage or team damage — [Leetify stats glossary](https://leetify.com/blog/leetify-stats-glossary)

### Inferences
- Self-damage metric: count of player_hurt events where attacker == victim (own HE, own molotov) or the damage type is fall, per round. Pro baseline must be computed from our demos.
- Team-flash metric: copy Leetify's teammates-flashed-per-flash with the 1.1 s blind threshold.

### Gaps
- No published pro rate for self-damage or fall damage.
- No confirmed CS2 fall-damage thresholds; the CS:GO ones may have changed.

## Analytics platform metric definitions (exact text where available)

### Takeaway
Leetify publishes the clearest definitions (crosshair placement, time to damage, counter-strafing, spray accuracy, utility, trades). Refrag publishes level comparisons. Scope.gg, HLTV and bo3.gg did not give formulas in what I found.

### Cited Findings
- Leetify spray accuracy: a spray is 3 or more shots; rifles only; only shots while an enemy is spotted; hits / all spray shots — [Leetify stats glossary](https://leetify.com/blog/leetify-stats-glossary)
- Leetify utility: flashbangs leading to kills (enemy flashed by you then killed by your team; blinds under 1.1 s excluded); enemies flashed per flash (blind > 1.1 s); flash blind duration (longest enemy blind per flash, averaged); HE damage per HE; unused utility on death (value left in inventory, averaged over deaths); CT smokes that stopped a push (an enemy within 800 units of the smoke when it blooms, divided by CT smokes) — [Leetify stats glossary](https://leetify.com/blog/leetify-stats-glossary)
- Leetify trades: trade kill opportunities ("How many times did you have the chance to trade a teammate?"), attempts and successes; traded deaths with the same three parts from the dying player's view. The window for "chance to trade" is not stated — [Leetify stats glossary](https://leetify.com/blog/leetify-stats-glossary)
- Leetify's enemy-seen logic applies to games analysed on or after 2020-10-04 — [Leetify, Enemy actually spotted](https://leetify.com/blog/enemy-actually-spotted/)
- Refrag: Opening Success (first duel of the round) level 10 average 2.50 per match vs 2.11 for level 5–8; Trade Kill Success (killing the enemy who just killed a teammate) 2.43 vs 2.03 — [Refrag, three stats](https://refrag.gg/blog/three-stats-that-separate-level-10-faceit-cs2)

### Inferences
- These definitions can be copied directly as evaluation metrics for the bots, so bot vs pro scores are comparable to public numbers.

### Gaps
- Did not fetch awpy documentation, HLTV rating 2.x/3.0 definitions, or bo3.gg/Skybox metric pages in this pass; their exact definitions are not in these notes.
- Leetify's trade time window, Scope.gg's time-to-kill formula and HLTV's definitions were not found.
