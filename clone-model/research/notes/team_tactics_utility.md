# Team-level and decision-level game sense of pro CS2 players, as objective behaviours measurable from demos

Scope note: this file covers team tactics, utility, strategy variety, reacting to information, trading, timing and economy, and the roles of donk and broky on Mirage. Searched 2026-11-15. About 18 searches and page fetches were used. Many of the numbers the brief asked for are not published anywhere I could reach. Each such gap is listed under "Gaps". Every proposed metric and threshold under "Inferences" is my own proposal. None of them is a published standard unless a source is cited next to it.

A general finding first, because it affects every section. The richest public, demo-level dataset of pro play is ESTA (Esports Trajectory and Action dataset). It contains 1,558 pro CS:GO demos, of which 278 are Mirage. It is CS:GO only (January 2021 to May 2022). It must be read with the old parser version awpy 1.x (awpy is the open-source Python demo parser by the same author). — [ESTA GitHub](https://github.com/pnxenopoulos/esta); [ESTA paper (ar5iv)](https://ar5iv.labs.arxiv.org/html/2209.09861)

---

## 1. Utility use: standard Mirage lineups, when pros throw them, utility before peeking, utility stats

### Takeaway
The standard Mirage A execute is a three-smoke set: a smoke on the CT spawn entrance (the "CT smoke"), a smoke on Jungle, and a smoke on Stairs. These are often followed by a molotov and a pop-flash (a flash thrown so it bursts at once around a corner). The one published pro utility leaderboard I found (HLTV data for 2025) gives utility damage per 24 rounds, with a top-10 range of about 146 to 219. I found no published pro figures for "flash, then peek within X seconds", nor for when in the round pros throw each grenade. Both must be measured from demos.

### Cited Findings
- Guides agree the standard A execute uses three smokes to block three angles: CT, Jungle and Stairs. — [noping.com Mirage smokes guide](https://noping.com/blog/smokes-no-mirage-cs2-lineups-flashes-e-execute-a-para-faceit); [exitlag Mirage smokes](https://www.exitlag.com/blog/cs2-mirage-smokes/); [esports.net Mirage smokes](https://www.esports.net/news/counter-strike/cs2-mirage-smokes-guide/)
- The Jungle smoke cuts off CT rotations coming from mid and connector. The Stairs and Jungle smokes are plain left-click throws. The CT smoke is a jump-throw. — [exitlag Mirage smokes](https://www.exitlag.com/blog/cs2-mirage-smokes/); [esports.net](https://www.esports.net/news/counter-strike/cs2-mirage-smokes-guide/) (opinion/coaching, not measured)
- Coaching rule: the smokes should land together, not one at a time. The recommended order is utility, then the entry player, then the trading player, then the plant. Players should not enter while smokes are still arriving. — [noping.com](https://noping.com/blog/smokes-no-mirage-cs2-lineups-flashes-e-execute-a-para-faceit) (opinion)
- Known variations of the A execute: (a) replace the Stairs smoke with a Stairs molotov when a CT holds close; (b) a fast execute that skips mid, with instant CT, Stairs and Jungle smokes plus a molotov under balcony. — [noping.com](https://noping.com/blog/smokes-no-mirage-cs2-lineups-flashes-e-execute-a-para-faceit) (opinion)
- Lineup databases with CS2 Mirage throws (positions and landing spots) exist at csdb.gg. Those pages warn that recent map changes may move landing spots. — [csdb.gg Mirage lineups](https://csdb.gg/lineups/mirage/)
- bo3.gg has a general Mirage guide (map callouts and standard plays). — [bo3.gg Mirage guide](https://bo3.gg/articles/guide-to-mirage)
- Measured (CS2, 2025, LAN, against top-20 teams, HLTV data reposted by skin.club). Utility damage per 24 rounds, top 10: apEX (Vitality) 218.6 over 3,803 rounds; bLitz (MongolZ) 200.0 over 4,254; KSCERATO 190.5 over 3,652; xertioN 182.5 over 3,869; zont1x (Spirit) 166.6 over 2,194; huNter- 158.9; NiKo 154.6; XANTARES 147.2; MAJ3R 145.8; malbsMd 145.6. donk and broky are not in the top 10. — [skin.club repost of HLTV 2025 utility ranking](https://community.skin.club/en/news/best-cs2-players-by-utility-damage-per-24-rounds-in-2025)
- Measured (CS:GO pro, ESTA). Of all parsed actions: weapon fire 68%, damage events 13%, grenade throws 10%, flashes 6%, kills 3%, bomb events under 1%. — [ESTA paper](https://ar5iv.labs.arxiv.org/html/2209.09861)
- ESTA stores active smokes and active fires (molotov or incendiary areas) in every frame. It also stores a "blinded" flag per player. So "which smokes are up at time t" and "was the enemy blind when I peeked" can be read directly. — [ESTA paper](https://ar5iv.labs.arxiv.org/html/2209.09861)
- Flash assists: matchmaking players on csdb.gg profiles (which pull Leetify-style data; Leetify is a stats site) show flash-assist rates from 0% to 15.7%, mostly 3% to 11%. These are not pro players. — [csdb.gg example profile](https://csdb.gg/stats/76561198011223106/)

### Inferences
- Metric U1, utility before peek. Count a peek as "utility-supported" if a teammate's flash burst within 2.0 s before the first shot fired by the peeking player, and an enemy within 1,000 game units had the blinded flag set. Report the share of opening duels that are utility-supported. The 2.0 s window is my proposal. It matches the length of a full blind in CS. It should be tuned from the pro distribution, not taken as fact.
- Metric U2, execute synchrony. For each T execute on a site, find the land times of all smokes aimed at that site. Report the spread (latest minus earliest). The coaching sources say smokes should land "together". A spread under about 3 s is a reasonable first threshold, to be checked against pro demos.
- Metric U3, utility mix per round. Count smokes, flashes, HE grenades and molotovs thrown per player per round. Compare the bot's mix to the cloned player's mix on Mirage, split by side and by buy type.
- Metric U4, lineup diversity. Cluster grenade throws by (throw position, land position) on Mirage. Report the number of distinct clusters a team uses per half, and the entropy of their use. A bot that always throws the same three smokes will score near zero entropy. This directly measures the user's complaint.
- Metric U5, utility damage per 24 rounds. Compare against the HLTV scale above: about 146 to 219 for the top-10 utility users. A rifler or AWPer clone will sit well below this. donk and broky are not on the list.

### Gaps
- No published pro figure for the time gap between a flash and the following peek.
- No published pro distribution of grenade throw times within a round (for example, "A execute smokes land at 1:05 remaining").
- No published pro averages for flash assists per round or for grenades thrown per round in CS2. Leetify and HLTV hold this data, but I found no article that states it.
- No source gave per-player utility numbers for donk or broky on Mirage.

---

## 2. Strategy variety across rounds (defaults, fakes, mid-round calls, anti-stratting, CT position changes)

### Takeaway
I found no published measure of how much pro teams vary their routes or executes from round to round. There is no entropy figure and no study of CT position changes. Coaching sources describe a "default" (spread out, take map control, then commit late), but give no numbers. This must be measured from demos. ESTA's per-frame positions make it possible.

### Cited Findings
- Coaching description of a default: spread across the map to gather information and take map control. Then, with about 40 s left, converge on the weaker site with pre-planned utility. — [metabot.gg map control and round phases guide](https://metabot.gg/en/cs2/guides/cs2-map-control-round-phases-default) (opinion, no data)
- A 2025 University of Victoria thesis used a clustering method (a Gaussian mixture model, which groups data points into overlapping clusters) on pro CS:GO data. It found four distinct play styles on each side. — [UVic thesis record](https://dspace.library.uvic.ca/items/b3d6a385-3f91-4bf1-ad3b-24189fce292d) (CS:GO; I read only the summary, not the full thesis)
- A second UVic thesis analyses movement paths and camera direction of pro CS:GO players. — [UVic thesis PDF](https://dspace.library.uvic.ca/bitstreams/a127aae5-94fb-48c0-a571-8bd6ddf4ee72/download) (summary only)
- ESTA stores more than 40 attributes per player per frame, including location and view direction, at 2 frames per second. — [ESTA paper](https://ar5iv.labs.arxiv.org/html/2209.09861)
- A coaching comment on broky: as FaZe's AWPer, he was used more to anchor a site on CT side, which made him "far more predictable". — [Hotspawn on broky](https://www.hotspawn.com/counter-strike/news/brokys-dysphoria-in-faze-how-can-he-be-revived) (opinion)

### Inferences
- Metric V1, route entropy. Divide Mirage into named zones (A site, palace, ramp, mid, connector, B apartments, short, and so on). For each T round, record the zone sequence each player visits in the first 40 s. Cluster rounds by the team's combined route. Report the Shannon entropy of the route clusters per half. Shannon entropy is a number that is zero when one option is always chosen and grows as choices spread out more evenly. The user's bot ("always mid to A with the same smoke and flash") would show entropy near zero. Pros should be measured first to set the target band.
- Metric V2, repeat rate. The share of consecutive T rounds in which the team uses the same route cluster and the same grenade set. Use this as a simple complement to entropy.
- Metric V3, CT position change rate. For each player, take the zone held at 20 s into the round on CT side. Report the share of rounds where it differs from the previous round. Do this separately for the anchor player (the one who stays on a site) and for rotating players. For an AWPer like broky, also cluster the exact angle held.
- Metric V4, fake rate. Count a round as a fake if at least two T-side utility pieces land at site X, and the bomb is later planted at site Y, or most T players end up at site Y.
- V1 to V4 also fit well as training targets. One method is to condition the bot policy on a sampled "strategy" label drawn from the pro cluster distribution. This is my proposal. No source tests it.

### Gaps
- No published entropy or variety statistics for pro CS2 or CS:GO strategies.
- No published study of how often pro CT players change position between rounds.
- No published data on how often pros fake or make mid-round calls.
- I did not read the full UVic thesis, so I cannot report its cluster definitions or numbers.

---

## 3. Reacting to information (rotations, site switches, abandoning a plan on contact)

### Takeaway
I found no published study of CT rotation timing or T mid-round site switches with measured numbers. Only qualitative coaching material exists. However, ESTA (and any CS2 demo) records the needed inputs per frame: positions, the blinded flag, active smokes and fires, and damage events. Reaction behaviour can therefore be defined as "the change in movement direction after an information event".

### Cited Findings
- Coaching (qualitative): Overpass and Nuke are among the most CT-favoured maps in CS2, partly because CTs can rotate quickly there. — [Hotspawn CT side guide](https://www.hotspawn.com/counter-strike/guide/how-to-play-ct-side-in-cs2) (opinion)
- Coaching (qualitative): after the default phase, Ts converge on the weaker site with about 40 s left. — [metabot.gg](https://metabot.gg/en/cs2/guides/cs2-map-control-round-phases-default) (opinion)
- Measured (CS:GO pro, ESTA): the average round lasts 94 s. About 30% of rounds contain a bomb plant. — [ESTA paper](https://ar5iv.labs.arxiv.org/html/2209.09861)
- The op.gg CS2 two-dimensional replay viewer tracks positions, rotations, alive state, facing direction and spacing through a round. It is a viewing tool, not a published dataset. — [op.gg 2D replay](https://op.gg/cs2/2d-replay)

### Inferences
- Metric R1, reaction to damage. When a player takes damage, or a teammate within 1,500 units dies, measure the next 3 s of movement. Score a "reaction" if the player changes heading by more than 45 degrees, stops (speed below 50 units/s), or retreats (distance to the damage source grows). Report the reaction rate and the median delay. Thresholds are mine and should be tuned to pro data.
- Metric R2, CT rotation latency. Define the trigger as the first T utility landing on a site, or the first T sighting, or the first CT death on that site. Measure the time until each CT not on that site starts moving toward it (distance to site falls by at least 200 units over 2 s). Report the median per player. This captures "CTs rotate when they hear or see the enemy".
- Metric R3, T plan switch. A T round counts as a "switch" if at 40 s the majority of Ts are in zones leading to site X, and the bomb is then planted at site Y. Measure the switch rate after early contact (a T death or damage near site X) against the switch rate without contact. If pros switch more after contact, the bot should too.
- Metric R4, plan abandonment. When the first contact goes badly (a T dies with no trade within 5 s), measure whether the team still enters the same site within 15 s. The user reports the bot "never changes plan", which would show as a near-100% continuation rate.
- Sound is not stored directly in demos. It must be inferred from enemy movement speed (running players make footstep sound) and distance. In CS2, running footsteps are audible at a fixed range set by the game. I did not find a reliable published number for that range, so it is listed as a gap.

### Gaps
- No published measured CT rotation times for pros.
- No published rate of T site switches or fakes.
- No reliable source for the CS2 footstep audible distance (needed to define "heard the enemy").

---

## 4. Trading and spacing

### Takeaway
The only trade window tied to a major stats provider is HLTV's 5-second window, used in its rating system for trade denials and failed trades. Community sources use 3 to 5 s, and one coaching guide says the chance is mostly gone after about 1 s. I found no published spacing distances between teammates in an execute, and no published team trade rates for CS2.

### Cited Findings
- HLTV's rating sub-components include trade denials and failed trades, defined on a two-kill, 5-second window. — [Liquipedia: HLTV](https://liquipedia.net/counterstrike/HLTV)
- HLTV Rating 3.0 (released 20 August 2025) adds "Round Swing" (how much a player's actions change the round win probability) and an economy adjustment (credit scaled by the equipment gap in a duel). A later report says Round Swing credit depends on damage share, flash assists, and whether a kill was a trade. — [dust2.us on Rating 3.0 launch](https://www.dust2.us/news/64901/hltv-launches-rating-30); [escorenews explainer](https://escorenews.com/en/csgo/article/71475-how-hltv-rating-3-0-formula-actually-works-round-swing-and-eco-adjustment-explained); [wiki mirror of HLTV page](https://wiki.krisyotam.com/content/wikipedia_en_all_nopic_2026-03/HLTV)
- On 29 October 2025, HLTV raised the weight of kills from 12% to 25% and lowered Round Swing from 40% to 33%. A later update recalculated using 29,030 CS2 maps, 9,029 of them on LAN. — [dust2.us on Rating 3.0 update](https://dust2.us/news/67183/hltv-releases-update-for-rating-30); [winio.ai](https://winio.ai/blog/news/hltv-updates-rating-3-0-with-new-accuracy-improvements) (sources differ slightly on details; HLTV has not published the full formula)
- Community definition of an "untraded death": the enemy who killed you survives the next 3 to 5 s without being killed by your team. — [csskill.com](https://csskill.com/blog/the-silent-killer-of-your-premier-rating-the-untraded-death) (community, not HLTV)
- Coaching guide: if the trading player is more than about 1 s behind, the trade chance may be gone. — [farmskins guide on trade killing](https://farmskins.github.io/posts/qvOM41r_eXOWxNkj) (opinion)
- Coaching order for an execute: entry, then trade, then plant. — [noping.com](https://noping.com/blog/smokes-no-mirage-cs2-lineups-flashes-e-execute-a-para-faceit) (opinion)

### Inferences
- Metric T1, trade kill. A kill of the killer by a teammate of the victim within 5 s of the first death. Use 5 s so the numbers line up with HLTV. Also report the share within 2 s, to separate tight trades from late ones.
- Metric T2, trade rate. Of a team's deaths, the share that are traded under T1. Of a player's deaths, the share where a teammate was within trade range (for example, line of sight to the killer within 2 s). Compute the pro baseline from demos.
- Metric T3, execute spacing. During an execute (from the first smoke landing until the first kill), measure the distance between each T and the nearest T teammate. Report the median and the share of time under, say, 300 units and over 1,200 units. Too close means one spray or molotov hits two players. Too far means no trade. Both thresholds are my proposals and need pro data.
- Metric T4, entry-trade delay. The time between the entry player's first shot and the second player's first shot at the same area. The 1 s coaching figure gives a rough upper target.

### Gaps
- No published CS2 trade rates for top teams.
- No published distances between pro teammates in executes.
- HLTV's exact trade window for Rating 3.0 is not public. The 5 s figure is from the older sub-rating description.

---

## 5. Timing, clock and economy (when Ts commit, post-plant, saves, round win probability)

### Takeaway
There is measured pro data on round length, plant rate and round end reasons (CS:GO, ESTA). There is a working win-probability model benchmark from ESTA, including Mirage. The only man-advantage numbers I found are old (2020, CS:GO): top teams converted 5v4 rounds about 76% to 79% of the time. An academic paper shows pro teams often make spending decisions that its model rates as not optimal. I found no published "time teams commit to a site" figure.

### Cited Findings
- Measured (CS:GO pro, ESTA): average round length 94 s. About 30% of rounds contain a plant. Round end reasons: CTs eliminated 37%, T elimination 27%, bomb exploded 19%, bomb defused 12%, time ran out with no plant 5%. — [ESTA paper](https://ar5iv.labs.arxiv.org/html/2209.09861)
- Win probability model benchmark (ESTA). Inputs include: time since the last phase change, active smokes and fires, bomb site, defuse kits, equipment value, number alive, HP, armour, grenades left, and players in the bomb zone. The best log loss per map (log loss measures how wrong the predicted probabilities are; lower is better): Dust2 0.415, Nuke 0.416, Vertigo 0.424, Mirage 0.430, Ancient 0.431, Overpass 0.438, Inferno 0.442. All best results came from a simple neural network (multi-layer perceptron, MLP). — [ESTA paper](https://ar5iv.labs.arxiv.org/html/2209.09861)
- Xenopoulos, Doraiswamy and Silva, "Valuing Player Actions in Counter-Strike: Global Offensive" (IEEE Big Data 2020). It values each action by how much it changes the team's win probability. Built on over 70 million in-game events. I could not reach its numeric results. — [arXiv 2011.01324](https://arxiv.org/abs/2011.01324)
- Xenopoulos, Coelho and Silva, "Optimal Team Economic Decisions in Counter-Strike" (IJCAI 2021 workshop). It builds a round-start win-probability model from score, equipment, money and spending. It finds a pattern of sub-optimal spending by pro teams. It defines an "Optimal Spending Error" to rank teams by how close their buys are to the model's best buy. — [arXiv 2109.12990](https://arxiv.org/abs/2109.12990v1)
- Measured (CS:GO 2020, pro): BIG won 78.7% of 5v4 rounds on T side. Astralis won 75.9% of 5v4 rounds on CT side and 32.5% of 4v5 rounds on CT side. FURIA won 36.5% of 4v5 rounds on T side, the best in minority rounds. Matchmaking baseline: about 60% of 5v4 rounds won by the side with more players. Sample size not stated. — [scope.gg blog, 3 March 2021](https://blog.scope.gg/realizing-the-advantage-en) (CS:GO only)
- An informal analysis found a team's 4v5 conversion rate correlates more strongly with team success than its 5v4 conversion rate. The author says this is a tentative result. — [nomiun substack](https://nomiun.substack.com/p/how-good-are-the-stats-we-use) (opinion and informal analysis)
- Win probabilities by situation (for example, 1v1 or 2v3) are the base of HLTV Rating 3.0's Round Swing. HLTV says it made these map-specific. — [escorenews explainer](https://escorenews.com/en/csgo/article/71475-how-hltv-rating-3-0-formula-actually-works-round-swing-and-eco-adjustment-explained); [winio.ai](https://winio.ai/blog/news/hltv-updates-rating-3-0-with-new-accuracy-improvements)

### Inferences
- Metric E1, commit time. The round clock time when the third T player enters a bomb-site zone. Plot the distribution per team on Mirage. Compare the bot's distribution to the pro one. A bot that always commits at the same second shows a narrow spike.
- Metric E2, post-plant spread. After the plant, measure the number of distinct zones held by alive Ts and their mean distance from the bomb. Compare to pro rounds.
- Metric E3, save decision. When the win probability (from an ESTA-style model) for the alive Ts or CTs falls below a threshold (for example 10%), check whether players move away from the enemy and stop engaging. Report the save rate per player. The 10% threshold is my proposal.
- Metric E4, buy match. For each round, compare the bot's buy (weapon, armour, grenades) to the buy distribution of the cloned player at the same team money and score. The Optimal Spending Error from the Xenopoulos paper is a ready-made way to score team-level buys.
- Use an ESTA-style win-probability model as the critic in training. The change in win probability caused by each action (the approach in "Valuing Player Actions") gives a reward per action that rewards game sense, not just kills.

### Gaps
- No published CS2-era round win rates by man advantage for pros.
- No published pro distribution of site-commit times.
- I could not read the numeric results of "Valuing Player Actions" or the spending thresholds in "Optimal Team Economic Decisions". Only the abstracts were reachable.

---

## 6. Mirage specifics for donk (Team Spirit) and broky (FaZe)

### Takeaway
donk is an aggressive entry rifler (the player who takes the first fight). He has very high opening-duel numbers: 72.8% opening-duel win rate at IEM Katowice 2024, and 0.24 opening kills per round in an EPL S21 group stage (next best 0.16). broky is a site-anchoring AWPer. His form has fallen: 1.04 HLTV rating over 173 maps in 2025, 0.98 over 84 maps in 2026. He was benched by FaZe in June 2026 and is still under contract. I found no reliable Mirage-specific position data for either player.

### Cited Findings
- donk was HLTV's number 1 player of 2024 and number 2 of 2025. — [skin.club on HLTV 2025 ranking](https://community.skin.club/en/news/donk-the-second-player-of-the-year-in-the-hltv-2025-ranking); [wikiwand: donk](https://www.wikiwand.com/en/articles/Donk_(esports))
- IEM Katowice 2024: donk won 72.8% of opening duels (first at the event) with 59 opening kills. HLTV 2.0 rating 1.70. — [ggrecon](https://www.ggrecon.com/articles/team-spirits-donk-victory-in-numbers/)
- PGL Copenhagen Major 2024: rating 1.35 over 8 maps. Deaths per round 0.68, which is high. Spirit won 70% of rounds when donk got the opening kill. — [esports.gg](https://esports.gg/opinion/counter-strike-2/donks-copenhagen-major-stats-2024)
- EPL Season 21 group stage (2025): 0.24 opening kills per round; next best player 0.16. — [ggscore](https://ggscore.com/en/csgo/news/67001)
- BLAST Rivals Spring 2025: most opening kills per round at the event, with a 65.3% win rate in opening duels. — [ggscore](https://ggscore.com/en/csgo/news/68437)
- Playstyle (opinion): an aggressive, "maximum-resource" entry rifler. — [wikiwand: donk](https://www.wikiwand.com/en/articles/Donk_(esports)); [skin.club](https://community.skin.club/en/news/donk-the-second-player-of-the-year-in-the-hltv-2025-ranking)
- Spirit beat an opponent 13-3 on Mirage during IEM Cologne 2026 (team result, not donk's line). — [dust2.us](https://www.dust2.us/news/74697/donk-smurfs-in-stage-two-of-the-iem-cologne-major-with-an-insane-227-rating)
- Spirit's zont1x is 5th in HLTV's 2025 utility damage ranking (166.6 per 24 rounds). This suggests that on Spirit, much of the utility comes from teammates, not donk. — [skin.club utility ranking](https://community.skin.club/en/news/best-cs2-players-by-utility-damage-per-24-rounds-in-2025)
- broky: started as a rifler in 2019 and then moved to AWP. HLTV top 20 every year from 2021 to 2024. Won 10 S-tier LAN titles with FaZe, including PGL Major Antwerp 2022. — [dust2.us, 7 July 2026](https://www.dust2.us/news/75762/official-faze-part-ways-with-broky-after-seven-years); [Hotspawn](https://www.hotspawn.com/counter-strike/news/brokys-dysphoria-in-faze-how-can-he-be-revived)
- broky's ratings: 1.04 over 173 maps in 2025; 0.98 over 84 maps in 2026. FaZe benched him for the second time on 25 June 2026 in favour of JBOEN. FaZe says he "remains on the bench and under contract". — [dust2.us, 7 July 2026](https://www.dust2.us/news/75762/official-faze-part-ways-with-broky-after-seven-years)
- Playstyle (opinion): on CT side, broky's AWP was used to anchor a site, which made him predictable. He often paired with EliGE, who gave utility support. — [Hotspawn](https://www.hotspawn.com/counter-strike/news/brokys-dysphoria-in-faze-how-can-he-be-revived)
- HLTV Rating 3.0's economy adjustment lowers credit for AWP kills, because the AWPer already has the stronger weapon. This matters when comparing a broky clone's rating to riflers. — [escorenews explainer](https://escorenews.com/en/csgo/article/71475-how-hltv-rating-3-0-formula-actually-works-round-swing-and-eco-adjustment-explained)

### Inferences
- For a donk clone, the key targets are opening-duel attempt rate and win rate. Published event figures range from 65% to 73% won, and 0.24 opening kills per round at one event. The clone should also show a high deaths-per-round figure (around 0.68 at one Major). A clone that survives too much is not playing like donk.
- For a broky clone, the key targets are: AWP kill share, the share of CT rounds spent anchoring (one site zone for most of the round), and his angle choice per round (CT position change rate, metric V3). The data period matters. Data from 2026 reflects a player in poor form.
- Both players' Mirage positions must be extracted from their own demos. No published source gives them.

### Gaps
- No reliable Mirage-specific stats for donk (one rdy.gg table lists "1.5" for Mirage but its columns are unlabelled, so I did not use it).
- No published Mirage CT position for broky, and no published AWP kill share.
- No published Mirage T-side role for donk on Spirit (for example, which entry route he takes).
