# Odyssey authored bots

Four playable-profile IDs match the existing Odyssey UI exactly: `poseidon`, `odysseus`, `menelaus`,
`telemachus` (the UI spelling). Titles: The Tempest, The Strategist, The Warlord, The Heir.

These are fictional, authored personas on the existing CloneDirector/native-bot stack. They have
`source: user`, `model: null`, no source games and no recorded/generated opening routes. There was no
neural training or imitation of a real person's data. Native AI remains free to navigate, fight and
deploy utility. The existing burst, crouch, travel-jump and sound-conditioned quiet-walk controls apply.
Voices and trash talk: when the person dies in a match with one of them, the death coach speaks as that
character in its own voice (`match-service/match_service/personas.py`, `SPEC.md` section 9.7). Every clone
bot, these four included, is protected from killing itself (`SPEC.md` section 6.2).

| Character | Difficulty | Skill / reaction setting | Special rule |
|---|---|---|---|
| Poseidon | Impossible |100 /0ms | Incoming gameplay damage blocked before application |
| Odysseus | Superhuman |100 /100ms |8% extra outgoing damage to enemy players |
| Menelaus | Medium |65 /320ms | Normal damage and health |
| Telemachus | Easy |20 /650ms | Normal damage and health |

Skill/reaction/aim values are native bot-profile knobs, not measured ELO or achieved reaction times.
Odysseus is designed as a pro-strength fantasy opponent with an explicit small nonhuman damage edge
and a 44,000 configured acceleration cap; no comparison establishing that he beats donk has run.
Menelaus is intended to be a comfortable challenge; Telemachus deliberately recognizes targets later,
settles his aim slowly and oversprays. Actual difficulty depends on the installed native bot base.

Poseidon uses the documented `OnEntityTakeDamagePre` callback, not a huge health value or healing after
a lethal shot. The decision blocks all incoming gameplay damage (bullets, grenades, fall, fire, knife,
C4), scoped to his currently attached bot pawn. Humans and existing player clones get no immunity.
Odysseus's multiplier applies only to damage against enemy players, not friendly/self/world damage.
The handler stores no modified health/takedamage flags, so nothing needs restoring on unload. Admin
slays, entity removal, disconnect/map cleanup and objective/round results are not prevented. Poseidon
is unkillable by damage, not a guarantee that his team wins a bomb objective. Use a timed survival
challenge rather than waiting forever for his death.

## Character basis and interpretation

Homer supplies the traits; all CS2 habits and numerical choices below are our game design:

- Poseidon's enduring wrath and power over Odysseus's journey inspire relentless direct pressure and
  the divine shield. [Odyssey1](https://www.theoi.com/Text/HomerOdyssey1.html).
- Odysseus's resourcefulness and command inspire precision, economy and quiet utility-supported play;
  utility purchase preferences do not implement deception or specific smoke/flash lineups.
- Menelaus's veteran kingship, comradeship and hospitality inform a steadfast rifle/support style.
  [Odyssey4](https://www.theoi.com/Text/HomerOdyssey4.html).
- Telemachus's uncertainty and growth under mentorship inspire an earnest novice's hesitation and
  squad preference. His skill does not change dynamically during a match.
  [Odyssey3](https://www.theoi.com/Text/HomerOdyssey3.html).

## What consumes the quirks

`odyssey.bot_profile` → `add_clone_bot_entries.py` → installed `botprofile.vpk` entries (aim, reaction,
aggression, teamwork). `buy_plan` → existing per-bot purchase calls. `quirk_controls` → existing
CloneDirector burst/crouch/jump rules. `game_sense` → existing quiet walking near recently heard
footsteps/reloads. `odyssey.invulnerable/damage_multiplier` → new scoped pre-damage callback.
Every quirk below references a real consumed control; none is a claim of validated behavior.

Quiet-walk ranges remain the existing configurable historical hearing proxies, not calibrated CS2
audibility. Zero injected jumps/walk probability does not prohibit the native AI from doing those
actions itself. Utility lists select purchases, not new utility decision logic. Purchases remain
money-limited: one primary, then armor, then utility; no free guns or global money/difficulty cvars.

Regenerate profiles with `python clone-director/tools/make_odyssey_profiles.py`; all four are
deterministic and have 14 authored quirks each. Keep this design document aligned when changing values.

## Installation and acceptance

See [Tom's handoff](../handoffs/tom-odyssey-bots.md). This change needs **both** the updated CloneDirector
DLL/Core DLL and the patched native bot entries. A bare `bot_add_*` bypasses the director's protection.
The service refuses Odyssey in stand-in/generated modes; `-Bots clone` with `CS2_CLONE_ROUTES=recorded` uses authored
native AI for these route-free profiles and recorded routes for existing player clones in the same match.
Do not alter the existing player bots or global bot difficulty to install the roster.

Compile/unit checks do not establish live damage immunity, native setting acceptance, purchase aliases,
movement safety or difficulty balance. Those must be checked in private CS2 before claiming live readiness.
CounterStrikeSharp API 1.0.378 supports the pre-damage listener:
[official callback contract](https://docs.cssharp.dev/api/CounterStrikeSharp.API.Core.Listeners.OnEntityTakeDamagePre.html).

<!-- The per-character tables below are rendered from the authored profiles for this delivery. -->

## Poseidon — The Tempest

Wrathful, implacable sea god; overwhelming pressure rather than deception.

| # | Character quirk | Implemented control / target |
|---|---|---|
|1|The advancing tide|Native aggression 100/100; pressure appetite, not a guaranteed path. (`odyssey.bot_profile.Aggression`)|
|2|The solitary god|Native teamwork 15/100; squad preference when teammates exist. (`odyssey.bot_profile.Teamwork`)|
|3|Instant wrath|Configured reaction 0 ms, subject to the native AI and server tick. (`odyssey.bot_profile.ReactionTime`)|
|4|The unwavering trident|Aim offset scale 0.01; finite acceleration cap 999999. Calibration required. (`odyssey.bot_profile.AimFocusOffsetScale`)|
|5|No hesitation|Configured attack delay 0 ms after the native AI decides to engage. (`odyssey.bot_profile.AttackDelay`)|
|6|Rolling thunder|Burst target 12 shots, single-shot share 2%; existing trigger suppression. (`quirk_controls.shots_per_burst.value`)|
|7|Stands above mortals|Extra crouch at burst start with probability 5%; native crouching can also occur. (`quirk_controls.crouched_shot_share.value`)|
|8|No added parkour|0 extra jumps/min target while running outside combat; zero means no injected jumps. (`quirk_controls.jumps_per_min.value`)|
|9|No imposed stealth|0% walk chance per eligible second near a recent heard step/reload; memory 1s. Not global enemy awareness. (`game_sense.quiet_walk_share`)|
|10|Rifle broadside|Full-buy primary T/CT: ak47/m4a1; subject to money and alias support. (`buy_plan.T.full.aliases`)|
|11|A dangerous lean round|Eco sidearm T/CT: deagle/deagle; no armor/utility splurge. (`buy_plan.T.eco.aliases`)|
|12|Relentless force buy|Force primary T/CT: galilar/famas, then vest; subject to affordability. (`buy_plan.T.force.aliases`)|
|13|Storm provisions|Utility buy palette: hegrenade, smokegrenade, flashbang. Native AI chooses deployment; no authored lineups or fakes. (`buy_plan.CT.full.aliases`)|
|14|Divine aegis|Block incoming gameplay damage before application, including bullets, grenades, fall and C4. Not a giant health pool. (`odyssey.invulnerable`)|

## Odysseus — The Strategist

Patient, resourceful trickster and commander; precise, quiet and adaptable.

| # | Character quirk | Implemented control / target |
|---|---|---|
|1|The calculated opening|Native aggression 72/100; pressure appetite, not a guaranteed path. (`odyssey.bot_profile.Aggression`)|
|2|The allied expedition|Native teamwork 95/100; squad preference when teammates exist. (`odyssey.bot_profile.Teamwork`)|
|3|Quick recognition|Configured reaction 100 ms, subject to the native AI and server tick. (`odyssey.bot_profile.ReactionTime`)|
|4|The precise archer|Aim offset scale 0.06; finite acceleration cap 44000. Calibration required. (`odyssey.bot_profile.AimFocusOffsetScale`)|
|5|Decisive commitment|Configured attack delay 15 ms after the native AI decides to engage. (`odyssey.bot_profile.AttackDelay`)|
|6|Measured taps|Burst target 3 shots, single-shot share 58%; existing trigger suppression. (`quirk_controls.shots_per_burst.value`)|
|7|Flexible stance|Extra crouch at burst start with probability 18%; native crouching can also occur. (`quirk_controls.crouched_shot_share.value`)|
|8|Occasional traversal hop|2 extra jumps/min target while running outside combat; zero means no injected jumps. (`quirk_controls.jumps_per_min.value`)|
|9|The quiet ambush|85% walk chance per eligible second near a recent heard step/reload; memory 6s. Not global enemy awareness. (`game_sense.quiet_walk_share`)|
|10|The versatile rifle|Full-buy primary T/CT: ak47/m4a1_silencer; subject to money and alias support. (`buy_plan.T.full.aliases`)|
|11|The economical precision shot|Eco sidearm T/CT: deagle/deagle; no armor/utility splurge. (`buy_plan.T.eco.aliases`)|
|12|Resourceful close-range force buy|Force primary T/CT: mac10/mp9, then vest; subject to affordability. (`buy_plan.T.force.aliases`)|
|13|Veil and distraction|Utility buy palette: smokegrenade, flashbang, flashbang. Native AI chooses deployment; no authored lineups or fakes. (`buy_plan.CT.full.aliases`)|
|14|A mythic edge|Multiply outgoing enemy-player damage by 1.08; explicit fantasy advantage, not a learned pro rating. (`odyssey.damage_multiplier`)|

## Menelaus — The Warlord

Proud, steadfast veteran and loyal commander; direct rifle fights with dependable support.

| # | Character quirk | Implemented control / target |
|---|---|---|
|1|The direct challenge|Native aggression 58/100; pressure appetite, not a guaranteed path. (`odyssey.bot_profile.Aggression`)|
|2|The loyal commander|Native teamwork 85/100; squad preference when teammates exist. (`odyssey.bot_profile.Teamwork`)|
|3|A fair reaction window|Configured reaction 320 ms, subject to the native AI and server tick. (`odyssey.bot_profile.ReactionTime`)|
|4|The steady veteran|Aim offset scale 0.35; finite acceleration cap 12000. Calibration required. (`odyssey.bot_profile.AimFocusOffsetScale`)|
|5|Sets his shot|Configured attack delay 80 ms after the native AI decides to engage. (`odyssey.bot_profile.AttackDelay`)|
|6|Controlled rifle volleys|Burst target 5 shots, single-shot share 25%; existing trigger suppression. (`quirk_controls.shots_per_burst.value`)|
|7|The planted shield|Extra crouch at burst start with probability 50%; native crouching can also occur. (`quirk_controls.crouched_shot_share.value`)|
|8|Grounded veteran|0.5 extra jumps/min target while running outside combat; zero means no injected jumps. (`quirk_controls.jumps_per_min.value`)|
|9|Disciplined approach|45% walk chance per eligible second near a recent heard step/reload; memory 3s. Not global enemy awareness. (`game_sense.quiet_walk_share`)|
|10|The dependable rifle|Full-buy primary T/CT: ak47/m4a1; subject to money and alias support. (`buy_plan.T.full.aliases`)|
|11|The practical sidearm|Eco sidearm T/CT: p250/p250; no armor/utility splurge. (`buy_plan.T.eco.aliases`)|
|12|The affordable battle line|Force primary T/CT: galilar/famas, then vest; subject to affordability. (`buy_plan.T.force.aliases`)|
|13|Straightforward support|Utility buy palette: flashbang, hegrenade. Native AI chooses deployment; no authored lineups or fakes. (`buy_plan.CT.full.aliases`)|
|14|Armor before ornament|Primary then vesthelm before utility, both sides; a protected but normally killable veteran. (`buy_plan.T.full.aliases`)|

## Telemachus — The Heir

Earnest young learner seeking confidence; hesitant recognition, enthusiastic overfiring and simple equipment.

| # | Character quirk | Implemented control / target |
|---|---|---|
|1|The hesitant challenger|Native aggression 30/100; pressure appetite, not a guaranteed path. (`odyssey.bot_profile.Aggression`)|
|2|Seeks the company of allies|Native teamwork 65/100; squad preference when teammates exist. (`odyssey.bot_profile.Teamwork`)|
|3|Late recognition|Configured reaction 650 ms, subject to the native AI and server tick. (`odyssey.bot_profile.ReactionTime`)|
|4|The unsteady first aim|Aim offset scale 0.9; finite acceleration cap 5000. Calibration required. (`odyssey.bot_profile.AimFocusOffsetScale`)|
|5|Checks before committing|Configured attack delay 250 ms after the native AI decides to engage. (`odyssey.bot_profile.AttackDelay`)|
|6|The enthusiastic spray|Burst target 9 shots, single-shot share 8%; existing trigger suppression. (`quirk_controls.shots_per_burst.value`)|
|7|The nervous crouch|Extra crouch at burst start with probability 70%; native crouching can also occur. (`quirk_controls.crouched_shot_share.value`)|
|8|Restless travel|6 extra jumps/min target while running outside combat; zero means no injected jumps. (`quirk_controls.jumps_per_min.value`)|
|9|Forgets stealth often|20% walk chance per eligible second near a recent heard step/reload; memory 1s. Not global enemy awareness. (`game_sense.quiet_walk_share`)|
|10|The forgiving SMG|Full-buy primary T/CT: p90/p90; subject to money and alias support. (`buy_plan.T.full.aliases`)|
|11|Keeps the starting pistol|Eco sidearm T/CT: glock/hkp2000; no armor/utility splurge. (`buy_plan.T.eco.aliases`)|
|12|A modest force buy|Force primary T/CT: mac10/mp9, then vest; subject to affordability. (`buy_plan.T.force.aliases`)|
|13|One simple utility lesson|Utility buy palette: flashbang. Native AI chooses deployment; no authored lineups or fakes. (`buy_plan.CT.full.aliases`)|
|14|Slowly finds his focus|AimFocusInitial 3.0: deliberately loose initial focus; no live confidence/learning system. (`odyssey.bot_profile.AimFocusInitial`)|
