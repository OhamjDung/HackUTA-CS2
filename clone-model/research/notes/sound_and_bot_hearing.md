# CS2 sound mechanics and how the built-in bot hears and reacts to noise

Research date: 2026-11-15.

Every value below carries one of four labels:

- **[SOURCE]** means the value is read from source code I downloaded and read myself.
- **[VALVE]** means the value is from Valve's own patch notes.
- **[COMMUNITY]** means the value is from a community guide or wiki. None of these guides gave a test method unless I say so.
- **[INFERRED]** means I reasoned it out. It is not stated by any source.

Code references are to ReGameDLL_CS (an open-source rewrite of the Counter-Strike 1.6 game code, which includes Valve's CCSBot bot), branch `master`, fetched 2026-11-15. Line numbers are from that fetch and can drift in later commits.

Valve patch-note lines come from the official Steam news feed for CS2 (app 730). I pulled it through `api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid=730`. Each note is linked as `store.steampowered.com/news/app/730/view/<id>`.

---

## Q1. CS2 footstep and action-sound mechanics: thresholds, distances, walls, and 2023–2026 changes

### Takeaway
Valve has never published numeric hearing distances or a "silent below X units/second" threshold for CS2. Its patch notes only describe these values relative to each other. The most useful one says that jump-landing sounds have had the same maximum audible distance as footsteps since 2023-11-09.

The community-quoted figure of about 1100 units for running footsteps matches the bot's own hard-coded footstep range of 1100 [SOURCE]. Treat it as a plausible proxy, not a confirmed CS2 value.

Two stealth changes landed in September 2026, after most guides were written:
- You can now reload silently by holding the reload key.
- Un-scoping no longer makes a sound.

### Cited Findings

**Footstep audibility: distance and speed threshold (community, no method given)**
- Running footsteps are "audible within approximately 1100 units (roughly 28 meters)" [COMMUNITY] — [csstatlab / csdb guides, via search summary](https://csstatlab.com/academy/gameplay/sound-cues); [csdb.gg audio guide](https://csdb.gg/guides/audio-guide/)
- Other guides disagree:
  - Running audible about 20 m [COMMUNITY] — [csgo-guides.com](https://csgo-guides.com/gameplay/sound)
  - 800–900 units [COMMUNITY] — [bo3.gg silent-movement guide](https://bo3.gg/articles/how-to-move-silently-in-cs2-shift-walk-crouch-and-sound-control)
  - 8–12 m in another guide [COMMUNITY] — [Steam guide "CS2 Audio Awareness"](https://steamcommunity.com/sharedfiles/filedetails/?id=3570507879)
  - None of these states how it was measured. I could not open the bo3.gg, Steam-guide, TalkEsport or Fandom pages directly: they returned 403, 402, 429 or an empty page to automated fetches.
- Community guides agree that walking with Shift is silent, and that walking speed is "roughly half" of run speed. One guide says only that movement "is only silent below a speed threshold", with no number [COMMUNITY] — [csdb.gg audio guide](https://csdb.gg/guides/audio-guide/)
- Guides disagree on crouch-walking. One says it is silent. Another says it is "quieter than walking but still produces faint sound at close range" [COMMUNITY] — [bo3.gg](https://bo3.gg/articles/how-to-move-silently-in-cs2-shift-walk-crouch-and-sound-control); [csgo-guides.com](https://csgo-guides.com/gameplay/sound)
- A CS2 game event called `player_sound` exists and can be listened to from server plugins. It has the fields `Userid`, `Radius` (int), `Duration` (float) and `Step` (bool). The field meanings are not documented [SOURCE: API docs] — [CounterStrikeSharp EventPlayerSound](https://docs.cssharp.dev/api/CounterStrikeSharp.API.Core.EventPlayerSound.html)

**Valve patch notes on sound distance and occlusion**

Occlusion means the game muffling or blocking a sound because walls or floors stand between the source and the listener.

- 2023-06-30 (Limited Test):
  - "Added distance effects to all positional sound sources."
  - "Fixed bug where sometimes sounds would not respect the occlusion values of surrounding geometry…"
  - "Added unique audio occlusion layer to help with vertical sound positioning in Nuke." [VALVE] — [Steam news 5124582150132496487](https://store.steampowered.com/news/app/730/view/5124582150132496487)
- 2023-06-06: "Player's own footstep sounds are now predicted on the client for a latency-independent experience." [VALVE] — [Steam news 5151601211245593238](https://store.steampowered.com/news/app/730/view/5151601211245593238)
- 2023-09-13: "Lowered occlusion and distance effects for gunfire, footsteps and reloads." [VALVE] — [Steam news 5211283418279022276](https://store.steampowered.com/news/app/730/view/5211283418279022276)
- 2023-09-16: "Adjusted silenced weapon falloff". Falloff is how fast a sound gets quieter with distance. The same note also "Tuned the vertical audio occlusion of grenade sounds in Nuke and Vertigo" [VALVE] — [Steam news 5480373588787876749](https://store.steampowered.com/news/app/730/view/5480373588787876749)
- 2023-09-27: "Adjusted vertical audio occlusion boundaries in Nuke and Vertigo" [VALVE] — [Steam news 5220291886484673985](https://store.steampowered.com/news/app/730/view/5220291886484673985)
- 2023-10-17:
  - "Reduced falloff distance of knife impact and swish sounds"
  - "Various tweaks and bug fixes around occlusion filters and footstep clarity" [VALVE] — [Steam news 5218041989037110376](https://store.steampowered.com/news/app/730/view/5218041989037110376)
- 2023-11-09:
  - "Changed jump land sounds to have the same maximum audible distance as footstep sounds"
  - "Changed volume falloff curve of jump landing sounds to better convey distance"
  - "Reduced the maximum audible distance of grenade bounce sounds"
  - "Improved occlusion filter quality" [VALVE] — [Steam news 5302486387996463019](https://store.steampowered.com/news/app/730/view/5302486387996463019)
- 2023-11-30:
  - "Further refined falloff distance curves and volume of grenade bounces"
  - "Increased audible distance of breaking glass window sounds" [VALVE] — [Steam news 5395937983662696560](https://store.steampowered.com/news/app/730/view/5395937983662696560)
- 2024-02-07: "Further reduced occlusion effects" [VALVE] — [Steam news 5589599109259623924](https://store.steampowered.com/news/app/730/view/5589599109259623924)
- 2024-08-19: "The jump-throw confirmation grunt sound can now be heard by other players nearby" [VALVE] — [Steam news 6909171012611544764](https://store.steampowered.com/news/app/730/view/6909171012611544764)
- 2024-10-02: "Fixed an issue where step sounds would play for the local player but fail to broadcast to other players and vice-versa" [VALVE] — [Steam news 6350729003492169791](https://store.steampowered.com/news/app/730/view/6350729003492169791)
- 2025-09-03: "Fixed an issue where player sounds would not visualize correctly on the minimap". So CS2 draws player sounds on the minimap [VALVE] — [Steam news 1809869180014591](https://store.steampowered.com/news/app/730/view/1809869180014591)
- 2025-10-01: "Keychains will now slightly jolt when a player makes an audible footstep sound." [VALVE] — [Steam news 1811772772457461](https://store.steampowered.com/news/app/730/view/1811772772457461)
- 2025-10-29: "Added scope in/out sound prediction to play immediately for local player." [VALVE] — [Steam news 1815034432852394](https://store.steampowered.com/news/app/730/view/1815034432852394)
- 2026-04-01:
  - "Mix adjustments to help accentuate jump landing sounds during combat."
  - "Vertical occlusion is now more gradual at the edges of transition points in Nuke and Vertigo." [VALVE] — [Steam news 1828894815556043](https://store.steampowered.com/news/app/730/view/1828894815556043)
- 2026-04-20: "Fixed a bug that allowed silently climbing ladders at run speed by sporadically tapping movement keys." [VALVE] — [Steam news 1830163047267301](https://store.steampowered.com/news/app/730/view/1830163047267301)
- 2026-05-20: "Adjusted material blending to improve accuracy of footstep sounds." Material blending decides which surface sound a footstep uses where two floor materials meet [VALVE] — [Steam news 1833334318567523](https://store.steampowered.com/news/app/730/view/1833334318567523)
- 2026-07-20: "The bomb damage health preview is now revealed when the bomb becomes audible." [VALVE] — [Steam news 1838407329267700](https://store.steampowered.com/news/app/730/view/1838407329267700)
- 2026-09-22:
  - "Players can now reload silently (but slowly) by pressing and holding the reload key."
  - "Un-scoping a sniper weapon no longer produces a sound." [VALVE] — [Steam news 1844751498216924](https://store.steampowered.com/news/app/730/view/1844751498216924)
  - The blog post for that update says silent reloads "take quite a bit longer". It gives no exact duration [VALVE] — [Steam news 1844751498216926](https://store.steampowered.com/news/app/730/view/1844751498216926)
- 2026-10-08: "Fixed the sound event during silent reload for Desert Eagle" [VALVE] — [Steam news 1846018067931597](https://store.steampowered.com/news/app/730/view/1846018067931597)
- 2026-10-28:
  - Added a Hold/Toggle option for Silent Reload Mode.
  - "Fixed various cases where the first sound of a reload was audible irrespective if a user requested a silent reload or not." [VALVE] — [Steam news 1847920302232686](https://store.steampowered.com/news/app/730/view/1847920302232686)
- Third-party summaries also report a July 2026 footstep "distance curve" mix pass. I found no matching line in Valve's feed, so treat it as unverified — [cs2news.gg](https://cs2news.gg/cs2-update/cs2-update-2026-07-08-382cfd2)

**Weapon fire, defuse, plant and weapon switch**
- I found no Valve or source-code number for CS2 gunfire distance, defuse sound, plant sound or weapon-switch sound distance.
- Valve notes only mention related changes:
  - "Each grenade now has unique higher-fidelity sounds for draw, inspect, pin-pull, and throw" (2025-09-16) [VALVE] — [Steam news 1811138915340164](https://store.steampowered.com/news/app/730/view/1811138915340164)
  - A new C4 equip sound (2026-04-01) [VALVE] — [Steam news 1828894815556043](https://store.steampowered.com/news/app/730/view/1828894815556043)

### Inferences
- [INFERRED] For a demo-based "can the enemy hear this" label, footstep range and landing range should be the same value, because Valve made them equal in November 2023. The landing sound is louder close up: Valve says it is "accentuated during combat" and has its own falloff curve.
- [INFERRED] From 2026-09-22 onward, a reload is not always loud. Demos recorded after that date need a way to tell a silent reload from a normal one, for example by how long the reload takes. Demos from before that date can treat every reload as audible.
- [INFERRED] In CS2, walls muffle sound but do not block it, and Valve reduced the occlusion effect twice (2023-09-13 and 2024-02-07). So a model of what the enemy can hear should mostly depend on distance, with only a mild penalty for walls between the two players. This matches the CS 1.6 bot, which ignores walls completely (see Q3).

### Gaps
- No primary source gives CS2's exact footstep distance in units or its exact silent-speed threshold. Valve stores sound radii in compiled sound-event files inside the game's VPK archives, which I could not open here.
- No community test with a stated method was reachable. The pages that might hold one blocked automated fetching.
- I found no values for how far defuse, plant, scope-in or weapon-switch sounds carry in CS2.
- The meaning of `player_sound.Radius` is undocumented. Someone needs to check whether CS2 demos actually record this event.

---

## Q2. Movement speeds and the speed at which a player is silent

### Takeaway
CS2's top running speeds by weapon are well agreed among community sources:

| Holding | Top speed (units/second) |
|---|---|
| Knife | 250 |
| Pistols | 240 |
| AK-47 | 215 |
| M4A4 and M4A1-S | 225 |
| AWP | 200 (100 when scoped) |

The CS2 silent-speed threshold is not published anywhere I could find.

In CS 1.6, the game code makes footsteps silent at or below a total speed of 150 units/second [SOURCE].

### Cited Findings
- Speeds by weapon group [COMMUNITY]. The page cites no sources and was last edited 2026-02-21 — [counterstrikewiki.com Movement_Mechanics](https://counterstrikewiki.com/Movement_Mechanics)
  - Knife 250
  - Pistols 240
  - SMGs 230–240
  - Rifles 210–225
  - AWP 200 (scoped 100)
  - Machine guns 195
  - Shotguns 210–225
- Individual values [COMMUNITY] — [farmskins speed table](https://farmskins.github.io/posts/CXyq3SjPOEICci4T); [profilerr](https://profilerr.net/how-to-show-velocity-in-cs2/)
  - AK-47 215, M4A4 225, M4A1-S 225, Galil 215, AWP 200 (scoped 100)
  - SG 553 210, SSG 08 230
  - csdb.gg also lists grenade-in-hand at 245–250 — [csdb.gg rifles](https://csdb.gg/weapons/rifle/)
  - Outlier: one csdb.gg blog gives the AWP as about 150. This conflicts with every other source — [csdb.gg blog](https://csdb.gg/blog/insights/when-to-run-with-knife-in-cs2)
- Walking speed (Shift) is about 52% of top speed, and crouching about 34%. My only source for this is a third-party mod that copies CS2 movement [COMMUNITY, weak]. These multipliers are widely repeated in the community but I found no primary source — [Quiet Walk mod](https://modrinth.com/mod/quiet-walk)
- One guide gives knife crouch speed as about 85 units/second, which equals 250 × 0.34 [COMMUNITY] — [search summary of guides incl. bo3.gg](https://bo3.gg/articles/how-to-move-silently-in-cs2-shift-walk-crouch-and-sound-control)
- **CS 1.6 footstep sound gate** [SOURCE]. In `PM_UpdateStepSound`, the code reads `speed = Length(pmove->velocity); if (speed <= 150.0) { pmove->flTimeStepSound = 400; return; }`. So no step sound plays at or below 150 units/second of total 3D speed. — [ReGameDLL pm_shared.cpp ~L393–397](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/pm_shared/pm_shared.cpp)
  - The step volume (`fvol`) is 0.35–0.7 depending on surface and ladder state. The gap between steps (`flTimeStepSound`) is 300–600 ms.
- **CS 1.6 bot footstep event** [SOURCE]. The bot is told about a footstep (`TheBots->OnEvent(EVENT_PLAYER_FOOTSTEP, this)`) only while the player is in the run animation and `pev->velocity.Length2D() > 150.0f`. `Length2D` is horizontal speed, ignoring vertical movement. The crouch branch sets the walk animation (`ACT_WALK`) and never sends this event. — [ReGameDLL player.cpp L2914–2924](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/player.cpp)
- **CS 1.6 landing event** [SOURCE]. `EVENT_PLAYER_LANDED_FROM_HEIGHT` is sent only when a landing does fall damage (`flFallDamage >= 1.0f` with the fixes build flag `REGAMEDLL_FIXES`). An ordinary jump landing sends nothing to the bot. — [player.cpp ~L5411–5432](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/player.cpp)

### Inferences
- [INFERRED] In CS 1.6, the walk key scales speed by 0.52 by default (`cl_movespeedkey 0.52`, a well-known default I did not re-cite here). A knife walks at 250 × 0.52 = 130 units/second, which is below the 150 gate, so walking is silent with every weapon.
- [INFERRED] If CS2 keeps a gate relative to top speed, for example the walk multiplier of 0.52, then with an AK at 215 a player at about 112 units/second or more is audible. Using a fixed 150 instead would wrongly call a walking knife silent and a running AWP-scoped player loud. A learned model should take both horizontal speed and weapon top speed as inputs, rather than hard-coding one number.
- [INFERRED] A practical way to label a demo tick as "audible step" (a tick is one server update):
  - the player is on the ground,
  - the player is not ducking,
  - the walk button is not held,
  - and horizontal speed is above about 0.52 × the weapon's top speed.
- Then check this proxy against `player_sound` / footstep events, if the demo parser exposes them.

### Gaps
- CS2's exact silent-speed threshold, and whether it uses total 3D speed or horizontal speed only, are not confirmed by any primary source.
- I found no primary source (game data file or Valve statement) for the 0.52 walk and 0.34 crouch multipliers in CS2.

---

## Q3. How the native CS bot (CCSBot) hears and reacts: ReGameDLL source

### Takeaway
The bot hears through a list of hard-coded ranges, one per event type, measured as straight-line distance. Walls and floors are ignored. The ranges are:

| Event | Range (units) |
|---|---|
| Normal gunfire | 2000 |
| Silenced or quiet weapon | 1000 |
| AWP shot, HE grenade explosion | 99999 (heard anywhere) |
| Footstep, reload, scope zoom, fall-damage landing, dry-fire click | 1100 |

The bot keeps one remembered noise at a time. It adds a position error of up to 400 units at 2000 units of distance, scaling with distance. It cannot react until its profile reaction time has passed.

Every 0.25 s it rolls a dice to decide whether to walk over and investigate. The chance falls linearly with distance and drops further when it has more living teammates. While hiding, it only reacts to noises within 100 + 400 × aggression units.

### Cited Findings

**Hearing ranges per event: `IsGameEventAudible()`** [SOURCE] — [bot_util.cpp L639–765](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/game_shared/bot/bot_util.cpp)
- Two constants are defined: `const float ShortRange = 1000.0f; const float NormalRange = 2000.0f;` (L646–647).
- Comments in the code say: "TODO: Check weapon type (knives are pretty quiet)" and "TODO: Use actual volume, account for silencers, etc." (L651–652).
- Weapon fire (`EVENT_WEAPON_FIRED`) is high priority and hostile in every case. Range by weapon:
  - HE, smoke, flashbang, shield, C4: no fire event (return false).
  - Knife and TMP: 1000.
  - M4A1 and USP: 1000 if silenced, otherwise 2000.
  - AWP: 99999 (L693–694).
  - All other weapons: 2000.
- `EVENT_HE_GRENADE_EXPLODED`: 99999, high priority, hostile (L706–710).
- Flashbang exploded and smoke exploded: 1000, low priority, hostile (L712–722).
- `EVENT_GRENADE_BOUNCED`: 500, low priority, hostile (L724–728).
- Breaking glass, wood, metal, flesh or concrete: 1100, medium priority, hostile (L730–738).
- `EVENT_DOOR`: 1100, medium priority, not hostile (L740–744).
- `EVENT_WEAPON_FIRED_ON_EMPTY`, `EVENT_PLAYER_FOOTSTEP`, `EVENT_WEAPON_RELOADED`, `EVENT_WEAPON_ZOOMED`, `EVENT_PLAYER_LANDED_FROM_HEIGHT`: 1100, low priority, not hostile (L746–754).
- Hostage used or calling for help: 1200, medium priority.
- Where these events are sent from [SOURCE] — [player.cpp](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/player.cpp):
  - Reload event: whenever the reload animation starts (L2756).
  - Footstep: horizontal speed above 150 while running, not crouched (L2918–2922).
  - Landing: only when the landing does fall damage (L5431).

**Receiving a noise: `CCSBot::OnEvent()`** [SOURCE] — [cs_bot_event.cpp](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/bot/cs_bot_event.cpp)
- Noises made by teammates are ignored: `if (!IsEnemy(pPlayer)) return;` (L327).
- The bot hears the noise only if `newNoiseDist < range`, where `newNoiseDist` is the straight-line distance from bot to noise in 3D (L358–360). There is no line trace, so walls are never checked.
- A footstep within 300 units makes a bot holding a sniper rifle switch to its pistol (L372–373).
- **Noise memory: a single slot.** Within `shortTermMemoryTime = 3.0f` seconds of the last noise, a new noise replaces it only if:
  - its priority is at least as high, and
  - it is closer (L377–391).
- The noise is snapped to the nearest navigation-mesh area. The nav mesh is the bot's map of walkable floor. Noises off the mesh are dropped (L397–405).
- **Position error:** `maxErrorRadius = 400`, `maxHearingRange = 2000`, and `errorRadius = 400 * dist / 2000`. Random offsets in that range are added to x and y, and the point is then clamped back into the same nav area (L415–423).
- Then `m_noiseTimestamp = gpGlobals->time` (L428), which records when the noise was heard.
- Separately, if the bot's current enemy fires, dry-fires or reloads while the bot holds a knife, the bot is forced to run for 5 s (`ForceRun(5.0f)`, L267–273).
- A bot that sees a nearby teammate die attacks the killer (L71–105).

**Reaction delay: `IsNoiseHeard()`** [SOURCE] — [cs_bot.h L1136–1146](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/bot/cs_bot.h)
- The code returns true only when `gpGlobals->time - m_noiseTimestamp >= GetProfile()->GetReactionTime()`.
- Its comment reads "primitive reaction time simulation - cannot 'hear' noise until reaction time has elapsed".
- The noise state lives in these member variables (L816–822): `m_noisePosition`, `m_noiseTimestamp`, `m_noiseArea`, `m_noiseCheckTimestamp`, `m_noisePriority`, `m_isNoiseTravelRangeChecked`.

**Deciding whether to investigate: `ShouldInvestigateNoise()`** [SOURCE] — [cs_bot_listen.cpp L33–101](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/bot/cs_bot_listen.cpp)

The function returns false straight away in these cases:
- the vertical travel check has already been done for this noise,
- it is not yet well past the early "safe" part of the round,
- the bot's disposition is not `ENGAGE_AND_INVESTIGATE`. Disposition is the bot's current fighting mode.

Otherwise it re-evaluates every 0.25 s:
- **Vertical case:** if `|dz| > oneStoreyHeight = 120`, it computes the walking distance through the nav mesh. If that walk is impossible or longer than `tooFar = 1500`, it ignores the noise. Otherwise it uses the walking distance in place of the straight-line distance (L53–70).
- **While hiding:** it ignores noises farther than `100 + 400 * aggression` (L72–74). Aggression is a 0–1 value from the bot's profile.
- **Chance:** `chance = 1 - dist/2000` (`maxNoiseDist = 2000`) (L76–78).
- **Teammates:** if 3 or more teammates are alive, it subtracts `min(0.05 * friendsRemaining, 0.5)`. The code comment says one of them is "presumably … closer and will check it out" (L80–89).
- Then it checks `RANDOM_FLOAT(0,1) <= chance` (L91).

**"Safe time"** [SOURCE]
- At the start of each round, `m_safeTime = 15 + 5 * aggression` seconds (aggression is 0–1, parsed as the profile value divided by 100) — [cs_bot_init.cpp L167](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/bot/cs_bot_init.cpp); [bot_profile.cpp L339–359](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/game_shared/bot/bot_profile.cpp)
- `IsWellPastSafe()` returns `elapsed > 1.25 * m_safeTime`. That works out to 18.75–25 s into the round — [cs_bot.cpp L818–823](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/bot/cs_bot.cpp)
- If the bot sees an enemy early, safe time is reset to 2 s before the current time (L845).

**Gunfire that counts as a threat: `CanHearNearbyEnemyGunfire(range)`** [SOURCE] — [cs_bot_listen.cpp L105–134](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/bot/cs_bot_listen.cpp)

All of these must be true:
- the noise is no more than 0.5 s old,
- its priority is high,
- it is within range,
- `CanSeeNoisePosition()` is true. This traces a line from the bot's eyes to the noise point plus half a player's height, ignoring glass, so smoke does not block it (L139–151).
- If the bot is already fighting someone, the gunfire must be at least 100 units closer than that enemy (`muchCloserSq = 100²`).

**Turning the head toward a noise** [SOURCE] — [cs_bot_vision.cpp ~L410–447](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/bot/cs_bot_vision.cpp); [cs_bot_listen.cpp L155–237](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/bot/cs_bot_listen.cpp)
- In `UpdateLookAround()`, when no enemy is visible and threatening gunfire is within `noiseStartleRange = 1000`, the bot looks at the noise at high priority and pauses its normal look-around for 2–4 s.
- Otherwise `UpdateLookAtNoise()` runs for noises up to 0.5 s old. A nearby threat means an enemy seen within the last 5 s and within 750 units.
  - If the bot has line of sight, or is not hiding and a threat is nearby, it looks straight at the noise.
  - Otherwise it bends its line of sight toward the approach point nearest the noise. Approach points are the spots enemies are expected to come from.
  - It keeps looking for 1–2 s. If hiding, it looks for 2–5 s, or 5–15 s if only one enemy is left.

**The Investigate Noise state** [SOURCE] — [states/cs_bot_investigate_noise.cpp L32–139](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/bot/states/cs_bot_investigate_noise.cpp)
- On entering the state, the bot:
  - records the noise position,
  - says "heard noise" over radio chatter if the noise is not high priority, it is well past safe time, and it has not seen an enemy for a long time,
  - plans a route to the noise using `SAFEST_ROUTE`,
  - then clears the noise from memory (`ForgetNoise()`).
- On each update:
  - It switches to a newer noise only if the new one is at least 100 units closer.
  - With a knife, it runs if hurrying and walks otherwise.
  - With a gun, within 1500 units of the noise, it **walks (sneaks)** if 2 or fewer teammates are alive and it is not hurrying. Otherwise it runs.
  - Within 200 units, if it is looking at the noise spot and can see it, it calls the spot clear and goes back to Idle.
- On leaving the state, it goes back to running.

**Which states listen** [SOURCE]
- Hunt state (searching the map for enemies): `if (ShouldInvestigateNoise()) InvestigateNoise();` — [states/cs_bot_hunt.cpp ~L160](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/bot/states/cs_bot_hunt.cpp)
- Hide state (holding a spot) [SOURCE] — [states/cs_bot_hide.cpp ~L247–283](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/dlls/bot/states/cs_bot_hide.cpp)
  - It does not listen while reloading, or while it is a sniper settled at its spot.
  - It needs the `ENGAGE_AND_INVESTIGATE` disposition.
  - If it is holding a position, the first noise it hears starts a hold timer (`m_firstHeardEnemyTime`). It investigates only after `m_holdPositionTime` has passed. So the bot **holds its angle first, then pushes the sound**.
  - If it is not holding a position, it investigates at once.

**How difficulty and profile affect hearing** [SOURCE]
- The profile attributes Aggression, Skill and Teamwork are read as the value divided by 100. ReactionTime is read in seconds — [bot_profile.cpp L339–396](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/game_shared/bot/bot_profile.cpp)
- In the hearing code, only two attributes matter:
  - **ReactionTime**, the delay before a noise counts as heard.
  - **Aggression**, which sets the hiding reaction radius (100–500 units) and the safe time (15–20 s, so the bot starts investigating after 18.75–25 s).
- The hearing ranges themselves do not change with difficulty.

### Inferences
- [INFERRED] The bot effectively models audibility as a single test:
  - `heard = enemy AND dist_3d < range(event) AND now - t_event >= reactionTime`
  - `p(investigate) ≈ 1 - d/2000` (minus the teammate term), with an error spread of `0.2 × d` around the true position.
- Because the bot ignores walls, it "hears through walls" further than a human does in CS2. The only exception is a vertical offset of more than 120 units, where the walking distance is used and capped at 1500.
- [INFERRED] For the clone bots, the cheapest fix that copies this design is:
  1. Each tick, compute enemy events within range: footstep (horizontal speed above the threshold, on the ground, not crouched, not walking) at about 1100; gunfire at 2000 (1000 if silenced, unlimited for an AWP); reload at 1100; landing at the footstep range.
  2. Keep a single noise memory that lasts 3 s, ranked first by priority and then by distance.
  3. Add a reaction delay.
  4. Let the learned policy (or a gate) decide among holding, looking toward the noise, and investigating.
- [INFERRED] The bot's design also covers the "runs loudly" complaint. When near a noise with few teammates left, it walks.
  - A comparable rule for the clones: when an enemy noise was heard recently within about 1500 units, cap speed at walking speed. Do this unless the recorded pro route is in a "hurry" phase.
  - This follows the bot's own `closeToNoiseRange = 1500` and `GetFriendsRemaining() <= 2` logic.

### Gaps
- I did not read the CS:S or CS:GO versions of this code (`CCSBot::OnAudibleEvent`, `OnPlayerFootstep`, `OnWeaponFire`). Valve never released that code officially, and the user asked to rely on ReGameDLL where possible. So I cannot confirm whether the Source versions changed the 1100/2000 ranges or added footstep checks based on walking.
- The value of `m_holdPositionTime` was not extracted. It is set in the hide state's setup code, which I did not read in full.

---

## Q4. CS2 bot specifics and bot_profile.db attributes

### Takeaway
I found no public source stating that CS2's built-in bot still uses this exact noise system. CS2's bot code is closed.

The indirect evidence is strong but not proof. CS2 still reads a `botprofile.db` file in the same format as the CS 1.6 file, with the same attribute names. Third-party CS2 bot mods edit only that file and add no hearing logic of their own.

### Cited Findings
- A CS2 `botprofile.db` (as shipped by CS2-Bot-Improver) has a `Default` template with these attributes [SOURCE: data file] — [CS2-Bot-Improver overrides/Medium/botprofile.db L18–39](https://github.com/ed0ard/CS2-Bot-Improver/blob/main/overrides/Medium/botprofile.db)
  - `Skill`, `Aggression`, `ReactionTime`, `AttackDelay`, `Teamwork`
  - `AimFocusInitial`, `AimFocusDecay`, `AimFocusOffsetScale`, `AimfocusInterval`
  - `WeaponPreference`, `Cost`, `Difficulty`, `VoicePitch`, `Skin`
  - `LookAngleMaxAccel/Stiffness/Damping` (Normal and Attacking)
  - Its personality templates set Aggression and Teamwork:
    - Camper: Aggression 30, Teamwork 50
    - Sniper: 55 / 100
    - Rifle: 60 / 100
    - Rusher: 100 / 100
    - Freeman: 100 / 40
- The same profile fields exist in ReGameDLL's `BotProfile` (`m_aggression`, `m_skill`, `m_teamwork`, `m_reactionTime`, `m_attackDelay`). The CS2 file adds the AimFocus and LookAngle fields, which are not in the CS 1.6 struct [SOURCE] — [bot_profile.h L84–125](https://github.com/s1lentq/ReGameDLL_CS/blob/master/regamedll/game_shared/bot/bot_profile.h)
- Valve's CS2 notes from 2023 to 2026 mention bots only in connection with bot takeover, bot pathing in Retakes (2026-11-11), and bot-kick logic. None mention bot hearing [VALVE] — [Steam news 1849192144180746](https://store.steampowered.com/news/app/730/view/1849192144180746); [Steam news 1814309641454326](https://store.steampowered.com/news/app/730/view/1814309641454326)

### Inferences
- [INFERRED] The profile format and the attribute names (including `ReactionTime` and `Aggression`) are unchanged. CS:GO's bot was a port of the CS:S bot, which itself descends from the CS 1.6 bot. So it is likely that CS2's bot keeps the same single-slot noise memory and per-event ranges. Exact constants may differ. Confirm this by watching a CS2 bot react with `bot_debug` before relying on it.

### Gaps
- There is no public confirmation of CS2 bot hearing ranges or noise logic.
- There is no record of whether CS2 bots use the `player_sound` event or Source 2 sound occlusion.

---

## Q5. CS2-Smarter-Bot and CS2-Bot-Improver: anything about sound or noise

### Takeaway
Neither plugin contains any sound, noise or hearing logic. Both rely entirely on the game's built-in bot hearing.

### Cited Findings
- CS2-Smarter-Bot is a CounterStrikeSharp plugin. CounterStrikeSharp is a framework for writing CS2 server plugins in C#.
  - Its source files are BotFov*, BotState.Behavior / Bomb / Combat / Controller / CustomFov / Flashbang / FovPatches / Lifecycle / Movement / RushAntenna / SmokeReveal / Tick / Weapons.
  - A case-insensitive search of the downloaded files for "sound|noise|hear|footstep|audib|listen|walk|silent|quiet" found nothing.
  - Its README lists these features: keeps bots active, fixes stuck bots, improves movement, smoke spam and vision in smoke, anti-flash, field of view aligned with humans, spraying at any range, refined behaviour, and a fix for bots that aim but do not shoot. It needs CS2-Bot-Controller — [CS2-Smarter-Bot](https://github.com/ed0ard/CS2-Smarter-Bot)
- CS2-Bot-Improver is a bundle of plugins (BotAI, BotAimImprover, BotBuy, BotRandomizer, BotState, NadeSystem with per-map grenade JSON files including `de_mirage_*.json`, RoundDamageRecap), plus cfgs and botprofile.db overrides (High / Medium / Low).
  - The same search of its `.cs`, `.cfg` and `.db` files found only bot names such as "SoundOnlyGamer" and "SilentFootstepsIRL". There is no hearing code — [CS2-Bot-Improver](https://github.com/ed0ard/CS2-Bot-Improver)

### Inferences
- [INFERRED] The "reacts to sound" behaviour users see from the rule-based bot comes from the closed CS2 bot code, presumably the CCSBot logic in Q3. To copy it, model it on ReGameDLL, not on these plugins.
- [INFERRED] Smarter-Bot's field-of-view alignment and smoke-vision changes are relevant to *seeing*, not hearing. That is outside this note.

### Gaps
- I did not read the closed-source CS2-Bot-Controller dependency or its memory patches. They might change bot behaviour in native code.
