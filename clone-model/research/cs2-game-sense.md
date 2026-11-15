> Recovery note (Codex, 2026-11-15): preserved Claude's combined local report after its usage limit. Citations and proposed thresholds are inherited, not independently revalidated in full. ReGameDLL_CS is CS1.6/Condition Zero, not the installed CS2 implementation. Treat its hearing constants as configurable hypotheses. See the continuation handoff for causality, measurement-resolution and acceptance corrections.

# Turn game sense into numbers a bot can learn

"Game sense" can be broken into about nine behaviours, and each one can be computed from a demo file. They are: moving quietly near enemies, reacting to damage and noise, pointing the crosshair where enemies will appear, choosing peeks, using varied utility, varying strategy between rounds, trading teammates, managing the clock and money, and not hurting yourself.

Almost none of these behaviours has a published pro baseline. The exceptions are aim measures from stats sites, a few trade and opening-duel figures, and old CS:GO round statistics. So most thresholds in this report are proposals, and the real targets must be measured from donk's and broky's own demos before training.

On sound, Valve has never published a hearing distance for CS2. The built-in bot's ancestor, whose code is public, hears footsteps at a fixed 1,100 game units and ignores walls. That rule is a usable first model of "could the enemy hear this".

On methods, the evidence points one way. The failures you see (no reaction to sound, the same tactic every round, loud running) come mostly from missing inputs and from how futures are selected during training, not from a missing reasoning module. Add sound and last-seen-enemy inputs, condition the model on a sampled per-round strategy label, and change the selection rule. Then judge the bot on situation-specific statistics, a human-vs-bot classifier, a player-identification classifier and a small blind human study.

Finally, the chess evidence says per-player fine-tuning on very little data overfits, and helps least for top players. With about 47 rounds per player, the per-player part should be a small correction on top of the shared pro model, weighted toward the moments where the player differs most from that model.

A note on words used throughout. A "unit" is the game's distance unit, about one inch. "u/s" means units per second. A "tick" is one server update; CS2 demos usually record 64 ticks per second. "CS:GO" marks numbers from the older game that may not hold in CS2.

## Nine behaviours, each with a test you can run on a demo

The table below is the core deliverable. Each row is one behaviour, the test you compute from demo data, a threshold, and where the threshold comes from.

"Published" means a stats site, paper or Valve states it. "Community" means a guide states it without a test method. "Proposal" means it comes from the research notes and must be tuned on pro demos before you trust it.

| Behaviour | What to compute from the demo | Threshold | Status |
|---|---|---|---|
| Moving quietly | Label each tick "audible step" if on ground, not crouched, walk key not held, horizontal speed above about 0.52–0.55 × the weapon's top speed. Report the share of ticks spent audible while the nearest enemy is within 1,100 units. | 1,100 units audible range | Community figure, matches the bot's code value |
| Moving quietly | Distance to nearest enemy at the moment the player switches from running to walking | Target is the pro's own distribution | Proposal |
| Reacting to damage | After a hit the player survives: heading change over 45°, or speed under 50 u/s, or distance to attacker growing, within 3 s. Also: fires back within 500 ms; is more than 100 units away 2 s later; dies within 3 s. | 45°, 50 u/s, 3 s, 500 ms, 100 units | Proposal |
| Reacting to noise | Enemy runs, jumps, reloads or switches weapon within 1,100 units: does the listener's view turn toward the source within 1 s, and does the listener stop running? | 1 s | Proposal |
| Reacting to information (team) | CT rotation delay: time from first T utility, sighting or CT death on a site until each other CT's distance to that site falls by at least 200 units over 2 s | 200 units, 2 s | Proposal |
| Reacting to information (team) | Plan abandonment: after a T dies untraded within 5 s, does the team still enter the same site within 15 s? | 5 s, 15 s | Proposal |
| Crosshair placement | Angle in degrees between view direction and enemy head at the first tick the enemy is visible. Median per match. | Lower is better. FACEIT level 10 average 6.72; levels 5–8 average 7.46 | Published (Leetify definition, Refrag numbers) |
| Time to damage | Seconds from first visibility to first damage. Drop values of 1 s or more. Median. | 400–500 ms is "really fast" | Published (Leetify) |
| Pre-aim | Share of ticks in contested areas where the view points within 5° of a common hidden enemy position that is not yet visible | 5° | Proposal |
| Angle-clearing order | Order in which the crosshair visits common positions on entering an area (for example Ramp onto A site) | Compare with pro sequences | Proposal |
| Counter-strafing | Share of rifle shots, fired while an enemy is visible and not crouched, at under 34% of weapon top speed | Over 90% is strong | Published metric (Leetify, Refrag); 34% is a community rule, not Valve's |
| Peek type | Per exposure (ticks visible to an enemy): jiggle = under 200 ms, back to cover, no shot; wide = start speed over 0.8 × top speed and over 64 units of lateral travel; jump = airborne | 200 ms, 0.8 ×, 64 units | 200 ms is community; the rest is proposal |
| Information then commit | Share of wide peeks preceded within 3 s by a jiggle of the same angle | 3 s | Proposal |
| Re-peek | After a fight and return to cover, share of next peeks within 5 s from the same spot (within 32 units) and view (within 10°) | 5 s, 32 units, 10° | Proposal |
| Off-angle | CT hold position more than 150 units from the most common pro hold for that spot | 150 units | Proposal |
| Utility before peek | Opening duel counts as supported if a teammate's flash burst within 2.0 s before the peeker's first shot and an enemy within 1,000 units was blind | 2.0 s, 1,000 units | Proposal |
| Flash quality | Enemies blinded per flash, counting blinds over 1.1 s; teammates blinded per flash, same rule | 1.1 s | Published (Leetify) |
| Defensive smoke | CT smoke counts as stopping a push if an enemy is within 800 units when it blooms | 800 units | Published (Leetify) |
| Execute timing | Spread between first and last smoke landing on a site in one execute | Under 3 s | Proposal |
| Utility variety | Cluster throws by (throw position, landing position). Shannon entropy of cluster use per half. Shannon entropy is a number that is zero when one option is always chosen and rises as choices spread out. | Pro value to be measured | Proposal |
| Strategy variety | Zone sequence each T visits in the first 40 s, clustered per round; entropy per half; and the share of consecutive rounds with the same route and grenade set | Pro value to be measured | Proposal |
| CT position change | Share of rounds where the zone held at 20 s differs from the previous round | Pro value to be measured | Proposal |
| Fake rate | Two or more T utility pieces land at site X, then the bomb is planted at site Y | — | Proposal |
| Trading | Kill of the killer by the victim's teammate within 5 s; also report the share within 2 s | 5 s | 5 s is HLTV's older sub-rating window; 2 s is proposal |
| Spacing | During an execute, distance from each T to the nearest T teammate; share of time under 300 and over 1,200 units | 300, 1,200 units | Proposal |
| Commit time | Round clock when the third T enters a site zone | Pro distribution | Proposal |
| Saving | When predicted win chance falls below 10%, does the player move away and stop fighting? | 10% | Proposal |
| Self-damage | Damage events where attacker equals victim (own HE, own molotov) or the damage type is fall | Fall damage starts at 151 units of drop | 151 units is CS:GO, Valve wiki |

Most aim metrics have public definitions. Leetify defines crosshair placement as the median distance, in degrees, the crosshair moves from first seeing an enemy to first damaging them ([Leetify](https://leetify.com/blog/leetify-stats-glossary)). Refrag reports **6.72 for FACEIT level 10 against 7.46 for levels 5–8** for a closely related measure, without stating units or sample size ([Refrag](https://refrag.gg/blog/three-stats-that-separate-level-10-faceit-cs2)). Copying these definitions exactly lets you compare your bots against public numbers.

The hard part of these aim metrics is deciding when an enemy is "seen". Leetify first used radar updates, which lag by up to 500 ms. It now replays positions at each shot or hit and checks whether any part of the enemy's body or gun was visible ([Leetify](https://leetify.com/blog/enemy-actually-spotted/)). Your pipeline needs its own ray trace from eye to enemy against Mirage geometry. Every metric marked "visible" in the table depends on it.

The counter-strafe threshold of 34% of top speed is a community rule. Valve never published it ([Leetify](https://leetify.com/blog/leetify-stats-glossary); [turbosmurfs](https://turbosmurfs.gg/?p=8949)). Check it against CS2's weapon data files before using it as a hard label.

Utility has one usable pro scale. HLTV's 2025 data puts the top-10 players at **146 to 219 utility damage per 24 rounds**, led by apEX at 218.6 ([skin.club repost of HLTV](https://community.skin.club/en/news/best-cs2-players-by-utility-damage-per-24-rounds-in-2025)). Neither donk nor broky is on the list. Spirit's zont1x is fifth at 166.6, which suggests Spirit's utility load sits with teammates, not donk.

The standard Mirage A execute uses three smokes: CT spawn entrance, Jungle and Stairs. Coaches say they should land together, before anyone enters ([noping.com](https://noping.com/blog/smokes-no-mirage-cs2-lineups-flashes-e-execute-a-para-faceit); [exitlag](https://www.exitlag.com/blog/cs2-mirage-smokes/)). A bot that always throws the same three smokes in the same order scores near zero on the utility-variety entropy metric. That metric directly measures your "same smoke and flash every round" complaint.

Strategy variety has no published pro number at all. No source measures how often pro teams change routes, fake, or move CT positions between rounds. A University of Victoria thesis found four distinct play styles per side by clustering pro CS:GO data, but only its summary was read ([UVic](https://dspace.library.uvic.ca/items/b3d6a385-3f91-4bf1-ad3b-24189fce292d)).

The richest public demo dataset for setting baselines is ESTA (Esports Trajectory and Action dataset). It has **1,558 pro CS:GO demos, 278 of them on Mirage**, with positions, view direction, active smokes and fires, and a blinded flag per player ([ESTA paper](https://ar5iv.labs.arxiv.org/html/2209.09861)). It records only 2 frames per second and needs the old parser version awpy 1.3.1 ([ESTA GitHub](https://github.com/pnxenopoulos/esta)). It is good enough for route, rotation and spacing baselines. It is too coarse for peek and reaction timing, which need your own 64-tick CS2 demos.

ESTA also gives clock baselines. The average pro round lasts **94 s**, and **about 30% of rounds include a bomb plant** ([ESTA paper](https://ar5iv.labs.arxiv.org/html/2209.09861)). Old 2020 data shows top teams won about **76% to 79% of 5-versus-4 rounds** ([scope.gg](https://blog.scope.gg/realizing-the-advantage-en)). Treat both as CS:GO-era.

Trading has one anchored window. HLTV's rating sub-components defined trade denials and failed trades on a **5-second, two-kill window** ([Liquipedia](https://liquipedia.net/counterstrike/HLTV)). The current Rating 3.0 window is not public. A coaching guide says the trade chance is mostly gone after about 1 s ([farmskins](https://farmskins.github.io/posts/qvOM41r_eXOWxNkj)). That is why the table reports both 5 s (comparable to HLTV) and 2 s (tight trades).

### What the two target players look like in numbers

donk is an aggressive entry rifler, meaning the player who takes the first fight. He won **72.8% of opening duels at IEM Katowice 2024** ([ggrecon](https://www.ggrecon.com/articles/team-spirits-donk-victory-in-numbers/)). He also posted **0.24 opening kills per round in the EPL Season 21 group stage, against 0.16 for the next player** ([ggscore](https://ggscore.com/en/csgo/news/67001)). And he won 65.3% of opening duels at BLAST Rivals Spring 2025 ([ggscore](https://ggscore.com/en/csgo/news/68437)).

donk also dies a lot: **0.68 deaths per round at the 2024 Copenhagen Major**, while Spirit won 70% of rounds when he got the opening kill ([esports.gg](https://esports.gg/opinion/counter-strike-2/donks-copenhagen-major-stats-2024)). A donk clone that survives too often has lost part of his style. His crosshair placement sat only at the **34th percentile** among about 308 pros in a February 2024 analysis of Leetify data ([Nomiun](https://nomiun.substack.com/p/which-cs-pros-have-the-best-aim)). So "good game sense" for donk does not mean textbook crosshair placement.

broky is an AWPer, meaning the team's sniper. On CT side FaZe used him to anchor one site, which a commentator called "far more predictable" ([Hotspawn](https://www.hotspawn.com/counter-strike/news/brokys-dysphoria-in-faze-how-can-he-be-revived)).

His form has dropped. His HLTV rating was **1.04 over 173 maps in 2025 and 0.98 over 84 maps in 2026**, and FaZe benched him on 25 June 2026 ([dust2.us](https://www.dust2.us/news/75762/official-faze-part-ways-with-broky-after-seven-years)). Pick the date range of his demos on purpose, because 2026 demos show a player in poor form.

No source gives Mirage-specific positions, routes or utility numbers for either player. These must come from their own demos.

## CS2 publishes no sound distances; the bot uses five fixed ranges

### What Valve has said about CS2 sound

Valve's patch notes describe sound only in relative terms. The most useful line, from 9 November 2023, says jump-landing sounds now have **"the same maximum audible distance as footstep sounds"** ([Valve](https://store.steampowered.com/news/app/730/view/5302486387996463019)). So one range number covers both footsteps and landings.

Valve also reduced occlusion twice. Occlusion means the game muffling sound because walls or floors stand between source and listener. The cuts came on 13 September 2023 and 7 February 2024 ([Valve](https://store.steampowered.com/news/app/730/view/5211283418279022276); [Valve](https://store.steampowered.com/news/app/730/view/5589599109259623924)). So a model of "can the enemy hear this" should depend mainly on distance, with only a mild penalty for walls.

Two recent changes affect how you label demos. Since **22 September 2026, players can reload silently by holding the reload key, and un-scoping a sniper rifle no longer makes a sound** ([Valve](https://store.steampowered.com/news/app/730/view/1844751498216924)). Demos recorded before that date can treat every reload as loud. Demos after it need a way to tell silent reloads apart, for example by how long the reload takes, since Valve says silent reloads "take quite a bit longer" without a number ([Valve](https://store.steampowered.com/news/app/730/view/1844751498216926)).

Community guides disagree on footstep range. Figures include about 1,100 units ([csdb.gg](https://csdb.gg/guides/audio-guide/)), 800–900 units ([bo3.gg](https://bo3.gg/articles/how-to-move-silently-in-cs2-shift-walk-crouch-and-sound-control)), and about 20 m ([csgo-guides.com](https://csgo-guides.com/gameplay/sound)). None states a test method.

The 1,100 figure is the best proxy, because it equals the bot's hard-coded footstep range (described below). It is still unconfirmed for CS2. The exact value lives in compiled sound files inside the game's archives, which nobody in this research opened.

Walking with Shift is silent, and walk speed is about half of run speed ([csdb.gg](https://csdb.gg/guides/movement-guide/)). Guides disagree on crouch-walking: one says silent, another says faint at close range ([bo3.gg](https://bo3.gg/articles/how-to-move-silently-in-cs2-shift-walk-crouch-and-sound-control); [csgo-guides.com](https://csgo-guides.com/gameplay/sound)).

Top running speeds are well agreed: knife 250 u/s, pistols 240, AK-47 215, M4s 225, AWP 200 ([counterstrikewiki](https://counterstrikewiki.com/Movement_Mechanics)). The walk multiplier of 0.52 and crouch multiplier of 0.34 rest on one weak source, a mod that copies CS2 movement ([Quiet Walk mod](https://modrinth.com/mod/quiet-walk)).

This is why the "audible step" label in the table scales with the weapon's top speed instead of using one fixed number. In CS 1.6 the code silences footsteps at or below 150 u/s total speed ([ReGameDLL pm_shared.cpp](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/pm_shared/pm_shared.cpp)). A fixed 150 would mislabel a walking knife (130 u/s) and a scoped AWP. Where the demo parser exposes the walk-button flag, use it instead of a speed cut-off.

CS2 has a server event called `player_sound`, with fields for the player, a radius, a duration and whether it is a step ([CounterStrikeSharp docs](https://docs.cssharp.dev/api/CounterStrikeSharp.API.Core.EventPlayerSound.html)). The fields are undocumented, and nobody has confirmed whether demos record this event. If they do, it replaces the speed-based guess with ground truth. Check this first.

### How the built-in bot hears

CS2's bot code is closed. Its ancestor, Valve's CCSBot from Counter-Strike 1.6, is public as part of ReGameDLL_CS (an open-source rewrite of the 1.6 game code). CS2 still reads a bot profile file (`botprofile.db`) with the same attribute names, including reaction time and aggression ([CS2-Bot-Improver](https://github.com/ed0ard/CS2-Bot-Improver/blob/main/overrides/Medium/botprofile.db)). So the CS2 bot probably keeps the same noise logic, though exact constants may differ. Confirm with the bot debug view before relying on it.

The two popular CS2 bot plugins add no hearing logic of their own. A code search for sound, noise, hear, footstep and similar words found nothing in either ([CS2-Smarter-Bot](https://github.com/ed0ard/CS2-Smarter-Bot); [CS2-Bot-Improver](https://github.com/ed0ard/CS2-Bot-Improver)).

The bot hears through a fixed range per event type, measured as straight-line distance with **no wall check** ([ReGameDLL bot_util.cpp](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/game_shared/bot/bot_util.cpp); [cs_bot_event.cpp](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/bot/cs_bot_event.cpp)):

| Event | Range (units) | Priority |
|---|---|---|
| Normal gunfire | 2,000 | High |
| Knife, silenced or quiet weapon | 1,000 | High |
| AWP shot, HE grenade explosion | 99,999 (anywhere) | High |
| Flashbang or smoke bursting | 1,000 | Low |
| Grenade bounce | 500 | Low |
| Breaking glass or wood, doors | 1,100 | Medium |
| Footstep, reload, scope zoom, fall-damage landing, empty-gun click | 1,100 | Low |

In that code, a footstep is only sent when the player is running, not crouched, at over 150 u/s horizontal speed. A landing is only sent if it causes fall damage ([ReGameDLL player.cpp](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/player.cpp)). Teammates' noises are ignored.

The bot remembers **one noise at a time**. Within 3 s of the last noise, a new noise replaces it only if it is at least as high priority and closer. The bot blurs the heard position by up to 400 units at 2,000 units of distance, so the error grows with distance at 0.2 × distance ([cs_bot_event.cpp](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/bot/cs_bot_event.cpp)). It cannot act on a noise until its profile's reaction time has passed ([cs_bot.h](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/bot/cs_bot.h)).

Whether to walk over and investigate is a dice roll every 0.25 s. The chance is **1 − distance / 2,000**, minus 0.05 per living teammate (capped at 0.5) once three or more teammates are alive ([cs_bot_listen.cpp](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/bot/cs_bot_listen.cpp)). The code comment says another teammate is presumably closer and will check it out.

Several gates block investigation. The bot does not investigate in the early "safe" part of the round, which ends 18.75–25 s in, depending on aggression ([cs_bot.cpp](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/bot/cs_bot.cpp); [cs_bot_init.cpp](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/bot/cs_bot_init.cpp)). While hiding, it reacts only to noises within 100 + 400 × aggression units, so 100 to 500 units. A noise more than 120 units above or below is judged by walking distance, and ignored if that walk is longer than 1,500 units.

A bot holding an angle **holds first and pushes the noise only after a hold timer** ([cs_bot_hide.cpp](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/bot/states/cs_bot_hide.cpp)).

The bot's head turns separately from its feet. Threatening gunfire within 1,000 units makes it look at the noise and pause normal looking around for 2–4 s. Other recent noises make it look toward the noise, or toward the nearest spot enemies are expected to come from, for 1–2 s. That rises to 2–5 s while hiding, and 5–15 s if one enemy is left ([cs_bot_vision.cpp](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/bot/cs_bot_vision.cpp); [cs_bot_listen.cpp](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/bot/cs_bot_listen.cpp)).

When it does investigate, the bot **walks quietly if it is within 1,500 units of the noise, two or fewer teammates are alive, and it is not in a hurry**. Otherwise it runs ([cs_bot_investigate_noise.cpp](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/bot/states/cs_bot_investigate_noise.cpp)).

This design gives you a ready-made, cheap hearing model for your training features. It is listed as recommendation 1 in the next section. Its main weakness is that it hears through walls further than a human does in CS2, since CS2 muffles sound through walls and the bot does not.

## Inputs, strategy labels and selection rules give the model game sense

The question was how to make an imitation-learned model act as if it had game sense, without training explicit reasoning. The evidence ranks the fixes in three tiers: inputs first, then strategy conditioning, then the training selection rule and extra prediction targets.

### The model cannot react to what it cannot perceive

Pearce and Zhu built a pixel-input behaviour-cloning agent for CS:GO deathmatch. Behaviour cloning means training a model to copy recorded human actions. The authors list its failures plainly: it had **no audio, so it could not react to shots or footsteps**; it forgot enemies that went behind cover, even with a memory layer added; and it ignored teammates firing in a direction ([Pearce & Zhu, CoG 2022](https://ieee-cog.org/2022/assets/papers/paper_45.pdf)). These match your symptoms. All three are missing-input or missing-memory problems.

Justesen and colleagues fixed the audio gap in a CS-like shooter. They gave the agent **8 directional audio sensors for each of 5 sound types**: footsteps and jumps, shots, bomb beeps, grenade explosions, and bomb drops ([Justesen et al. 2024](https://arxiv.org/html/2501.00078)). They trained on 48.6 hours of play with behaviour cloning only, no reinforcement learning. In a blind test with 20 judges watching 15-second clips, **30% of bot clips were judged human, against 60% of real human clips**.

Your model, CS-NET v4, is a 138.7M-parameter transformer that predicts 4-second movement and view token sequences at 4 Hz. As described in the research brief, its inputs are game state, depth rays and positions, with no sound events. Recommendation 1 follows directly.

**Recommendation 1, add perception features.**

First, a per-tick "heard noise" token for each enemy event inside the bot's range table: type, direction, distance, age in seconds, and the 0.2 × distance position blur.

Second, a "last seen enemy" token: position and seconds since last seen, per enemy.

Third, teammate cues: teammate firing direction, and teammate damage or deaths in the last few seconds.

Fourth, utility state: active smokes and fires, and the blinded flag on each player.

Fifth, the round clock, team money, and the predicted win chance.

These cost no new training method. They directly target "never reacts to being shot or to hearing enemies".

One caution about memory. In MLMove, a movement model by Durst and colleagues trained on pro CS:GO play, adding the player's own recent history made results worse. Map-occupancy distance rose from **8.2 to 11.8**, and the authors blame an "inertia problem": the model learns to keep doing what it just did ([Durst et al. 2024](https://arxiv.org/html/2408.13934)). Feed the model memory of the *world* (last-seen enemies, recent noises). Do not feed it its own recent actions.

The same paper found that letting each player's representation attend to all ten players mattered. Removing that worsened occupancy distance from 8.2 to 10.3 ([Durst et al. 2024](https://arxiv.org/html/2408.13934)).

### Sample a strategy per round so the model cannot fall into one

AlphaStar, DeepMind's StarCraft II agent, faced the same "one tactic" risk. Its policy was conditioned on a strategy summary taken from a real human game, called z. z held the first 20 build-order items plus running totals, and it was sampled from human data at play time. During supervised training **z was set to zero 10% of the time**, so the model also works without it ([Vinyals et al. 2019, Nature](https://doi.org/10.1038/s41586-019-1724-z); [secondary summary](https://cyk1337.github.io/notes/2019/07/21/RL/DRL/Decipher-AlphaStar-on-StarCraft-II)). A follow-up, TStarBot-X, reports its supervised agent beat the built-in Elite bot 90% of the time with either zero z or z sampled from 174 human games ([TStarBot-X](https://arxiv.org/pdf/2011.13729v1)).

**Recommendation 2, condition on a per-round strategy label.**

For each of the player's rounds, build a label from: which zones the player visits in the first 20–40 s, the first utility thrown and where, the buy type, and the walk-to-run ratio near enemies.

At play time, sample a label from that player's real rounds. In training, zero it 10% of the time.

Classifier-free guidance can then make the chosen strategy stronger at sampling time. Classifier-free guidance means training with and without the label, then pushing the output further in the direction the label adds ([Ho & Salimans](https://arxiv.org/abs/2207.12598)). This is an established general method; no CS result for it was found.

This converts "always mid to A" into a sampling problem. Strategy variety then matches the player's real spread across rounds.

### The current selection rule likely causes the repetition

CS-NET v4 uses expert iteration. Expert iteration means generating candidate behaviours, keeping the best ones, and training on them ([Anthony et al.](https://arxiv.org/abs/1705.08439)). Your version samples 8 futures and keeps the one closest to the real path.

Keeping the single closest future, state after state, narrows the model's output each round of training. That narrowing is a known failure called mode collapse. If the distance counts position only, view direction is never selected for, which explains the reported drift in view turning. These two diagnoses come from the research notes' reasoning, not from a measured CS result.

**Recommendation 3, change what "best of 8" means.**

First, include view-angle error in the selection distance, and raise the penalty for drifting from the base model on view tokens specifically.

Second, select within the round's sampled strategy label rather than toward one path, so different labels keep different futures.

Third, add rejection filters, not new targets. Reject a future if its walk-to-run ratio near enemies exceeds the player's own ratio in similar states (the "loud running" fix). Also reject it if its predicted change in win chance is strongly negative.

The win-chance filter needs a win-probability model. Xenopoulos and colleagues trained one on about 55 million pro game states; **XGBoost reached a test AUC of 0.79**, and team equipment value and remaining health were the strongest inputs ([Xenopoulos et al. 2020](https://ar5iv.labs.arxiv.org/html/2011.01324)). AUC measures how well a model ranks wins above losses, where 0.5 is chance and 1 is perfect. On ESTA, the best Mirage log loss was **0.430** ([ESTA paper](https://ar5iv.labs.arxiv.org/html/2209.09861)). Log loss measures how wrong the predicted probabilities are; lower is better.

The two research notes disagree on which ESTA model won. One says a simple neural network; the other says LightGBM had the lowest log loss on every map. Check the ESTA paper's table before choosing.

Use this model as a filter, not as a target to maximise. It only sees coarse state like health, equipment and positions. It will not reward checking an angle or walking quietly. Pushed hard, it would pull the clone toward "optimal" play and away from the player's quirks.

### Extra prediction targets build hidden-state awareness

**Recommendation 4, add auxiliary losses.** An auxiliary loss is an extra prediction the model is trained to make, alongside its main output, so that it learns useful internal features.

Two targets fit game sense. First, predict where each enemy is now, using only what the player could know. Second, predict whether an enemy sound event will occur in the next second.

These force the model to represent hidden enemies without any explicit reasoning step. Pearce's agent carried an extra value-prediction head as a precedent, but no ablation of its effect was reported ([Pearce & Zhu](https://ieee-cog.org/2022/assets/papers/paper_45.pdf)). No CS paper measures the gain from enemy-position prediction, so treat this as a strong idea with no measured CS evidence.

Two further options are weaker for this project.

The first is a discriminator reward (GAIL). GAIL trains a classifier to tell expert behaviour from agent behaviour and uses its output as reward ([Ho & Ermon](https://arxiv.org/abs/1606.03476)). With 47 rounds per player it would overfit. A single classifier trained on all pro data is more realistic, and it doubles as an evaluation tool.

The second is DAgger. DAgger means rolling out the learner and having the expert relabel the states it visits ([Ross et al.](http://www.ri.cmu.edu/pub_files/2011/4/Ross-AISTATS11-NoRegret.pdf)). It needs an expert you can query, and you cannot query donk. Your penalty for drifting from the base model already plays the relabelling role.

Action heads that keep several distinct options instead of averaging them deserve a look if outputs blur between two paths. Examples are Behavior Transformers and Diffusion Policy ([BeT](https://arxiv.org/abs/2206.11251); [Diffusion Policy](https://arxiv.org/abs/2303.04137)). Pearce found that predicting mouse movement as a continuous number "led to undesirable behaviour" by averaging between two paths, and switched to discrete choices ([Pearce & Zhu](https://ieee-cog.org/2022/assets/papers/paper_45.pdf)). Your token output already avoids this.

The items marked as general ML methods above (GAIL, DAgger, expert iteration, Behavior Transformers, Diffusion Policy, classifier-free guidance) were cited from the papers' canonical links but were not re-read during this research. Check them before quoting details.

## Human judges fail alone; use four layers of evaluation

Human-likeness tests run by humans alone are unreliable.

In the 2012 BotPrize contest, in the game Unreal Tournament 2004, the best bots scored **52.2% "humanness", while real human players scored only 41.4%** ([Singularity Hub](https://singularityhub.com/2012/10/08/turing-test-prize-has-two-winners/)). The judges failed to recognise humans, which shows why any human study needs human-versus-human control pairs.

The Navigation Turing Test, by Devlin and colleagues in a commercial game, fared better with side-by-side clips. **Judges picked the human over a reinforcement-learning agent 84% and 77% of the time** in two studies ([Devlin et al. 2021](https://arxiv.org/pdf/2105.09637)).

The same paper trained automatic classifiers to tell human trajectories from agent ones. The best reached **85% accuracy**, and simple position-only models were the most robust. But when asked which of two agents was more human, the classifiers **disagreed with human judges, with negative rank correlations of about −0.1 to −0.25**. A classifier can flag "this is a bot". It cannot rank two bot versions against each other.

MLMove's evaluation is the closest template for CS. Fifteen high-rank players ranked replay clips, and the rankings were turned into TrueSkill scores. TrueSkill is a rating system built from pairwise comparisons. MLMove was rated **16% to 59% more human-like** than a scripted bot and the commercial bot ([Durst et al. 2024](https://arxiv.org/html/2408.13934)).

MLMove also matched pro play on statistics measured by Earth Mover's Distance (EMD). EMD is a distance between two distributions; lower means closer to pro play.

| Statistic | MLMove | Scripted bot | Built-in bot |
|---|---|---|---|
| Map occupancy | 8.2 | 14.7 | 15.2 |
| Kill locations | 6.7 | 15.4 | 16.4 |
| Shots per kill | 2.1 | 5.6 | 4.9 |

The paper's lifetime row (4.9 / 7.8 / 1.1) contradicts its own text, which says MLMove matched lifetimes best ([Durst et al. 2024](https://arxiv.org/html/2408.13934)). Do not lean on that row.

MLMove also found that **judges playing against bots were too absorbed to judge movement; watching replays worked better**.

**Recommendation 5, evaluate in four layers.**

The first layer is statistics. For every metric in the behaviour table, compute the distance (EMD or Jensen-Shannon divergence) between the bot's self-play distribution and the cloned player's real distribution on Mirage. Jensen-Shannon divergence is another distance between distributions. Run this after every training run; it is the cheapest layer and tells you which behaviour broke.

The second layer is a human-versus-bot classifier. Train one position-and-view classifier on all pro data against bot data. Use it only as a regression test: "did this run become easier to spot?" Never use it to choose between two bot versions.

The third layer is player identification. Train a classifier, or reuse per-player models, to name which pro produced a round. A good donk clone should be identified as donk. A clone identified as "generic pro" has lost its quirks. The chess results in the next section show this works.

The fourth layer is a small human study. Use side-by-side replay clips judged by experienced CS players, with a certainty scale. Mix in human-versus-human pairs to measure the judges' own baseline. Have judges watch, not play.

The first three layers can be computed automatically from demos. Only the fourth needs people.

## Prioritise quirks by measuring where the player beats the pro model

The best evidence on separating one player's style from shared skill comes from chess.

McIlroy-Young and colleagues fine-tuned a population model of human chess moves (Maia) on single players. Personalised models were **4–5 percentage points more accurate** at predicting each player's moves. They could pick the right player out of 400 with **98% accuracy from 100 games, and 86% from 10 games** ([McIlroy-Young et al. 2022](https://arxiv.org/pdf/2008.10086)).

The same study carries two warnings for your setup. At **1,000 games per player, personalisation lost to the shared model, 0.497 against 0.527 accuracy**; it only helped from 5,000 games upward. And personalising grandmasters "did not yield the same accuracy gains", likely because top players play close to optimal moves that the shared model already predicts.

donk and broky are the CS equivalent of grandmasters, and you have about 47 rounds each. A CS round holds many more decisions than a chess game, so the comparison is not one-to-one. Still, the direction is clear: heavy per-player tuning on this little data will overfit.

The CS evidence agrees. Pearce found pre-training on large, noisy data was worth roughly ten times as much clean expert data. Pre-training plus 2 hours of expert data matched what about 20 hours would give from a generic start ([Pearce & Zhu](https://ieee-cog.org/2022/assets/papers/paper_45.pdf)). The shared base model carries most of the competence. The per-player part should be small.

The chess paper also gives a way to find quirks. For each move, compare its probability under the personalised model with its probability under the shared model. The log-odds ratio between them marks the "idiosyncratic" moves. Restricting to the player's mistakes raised identification accuracy slightly, from 0.983 to 0.989, so **mistakes are among a player's most identifying behaviours** ([McIlroy-Young et al. 2022](https://arxiv.org/pdf/2008.10086)).

For donk, that suggests his high death rate and risky opening duels are part of what makes him donk. They are not noise to be trained away.

**Recommendation 6, weight training toward quirks.**

Step one. For every state in the player's rounds, compute log p_player(action) − log p_base(action). That is, how much more likely the action is under the per-player model (the LoRA adapter, a small set of low-rank weights added to the base model) than under the shared base model.

Step two. Weight the per-player loss toward states with large positive values. Those are the quirks.

Step three. Rely on the penalty for drifting from the base model (the KL penalty, which measures how far one probability distribution moves from another) everywhere else. That keeps shared technique.

Step four. Compute the player's behaviour statistics from the behaviour table and compare each with the spread across all pros. Statistics more than about 1.5–2 standard deviations from the pro average are candidate quirks. Put those into the strategy label and the evaluation targets. Statistics near the average should come from the base model. The 1.5–2 cut-off is a proposal.

Step five, if adapters still overfit. Replace per-player adapters with a learned style vector per player, trained jointly on all pros' data. Then 47 rounds only move a short vector, not thousands of adapter weights. This follows the chess authors' suggestion of pooling data across similar players.

No paper measures this separation for an FPS pro. All of this section's numbers come from chess, plus Pearce's general pre-training result.

## Conclusion

The research changes where the effort should go. The instinct is to see "no game sense" as a reasoning gap and reach for planning or explicit tactics. The evidence says most of the gap is perceptual and statistical. The model was never told what an enemy can hear or what it last saw. And the training loop rewards one path per state, which squeezes out the variety pros show.

The built-in bot looks dumb, but it is useful here. Its range table, single noise slot, distance-scaled position blur and "walk when close and few teammates are left" rule are a cheap, citable hearing model to compute as input features.

The largest open risk is not the method but the baselines. Almost every threshold in the behaviour table is a proposal. donk's own metrics break textbook norms: middling crosshair placement and a high death rate. So the first job is to run the table's metrics on the players' real Mirage demos and on a pro population. Only then do "game sense" and "quirk" have targets the bot can be judged against.

The facts to confirm before building on them are: whether CS2 demos contain the `player_sound` event; the true CS2 footstep range and silent-speed threshold; and the 34% accuracy threshold against CS2 weapon data.
