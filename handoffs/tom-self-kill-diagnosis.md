# Prompt for Tom's agent: why do the clone bots kill themselves?

Addressed to Tom. Paste the prompt below into your coding agent. **Delete this file after use**, in the
same commit as your findings, to keep the repository clean.

---

You are working in the HackUTA-CS2 repository on Tom's PC, where CS2 and the bot base run. Read
`AGENTS.md` (especially section 7) and `SPEC.md` sections 0 and 8 before you do anything.

## The problem

Testers report that the clone bots (`donk_v1`, `broky_v1`, `donkL`, `brokyL`) kill themselves. Nobody
has yet recorded how. Your job is to **diagnose it, not fix it**: find out how the deaths happen, with
evidence, and report. Do not change plugin code or bot profiles in this task.

## Rules for this task

- Do not start, stop or restart CS2, the launcher or the match service unless Tom asks you to.
- Never send `record` to CS2 over the network console. Use the match service's `tv` setting or the bot
  base's chat commands for a GOTV recording.
- Check bot slots with `status` before any `!replay <slot>`.
- Check free memory before a live run. Ask Tom to close heavy apps if under 4 GiB is free.
- Keep "ran it", "read it" and "assumed it" separate in everything you write.
- No `.dem` files, videos or weights in git.

## Step 1: get evidence of the deaths

Use an existing GOTV recording of a clone match if Tom has one; otherwise ask Tom to run one private
bot-versus-bot match on Mirage with GOTV on (at least 8 rounds; the clones on both sides if possible).

With `demoparser2` (already used in `clone-pipeline/clone_pipeline/parse.py`), list every death of a
clone bot. For each one, record: round, tick, victim, attacker, `weapon`, `assister`, whether attacker
== victim, whether the attacker is missing or the world, and `headshot`. Self-kills in CS2 demos show up
as one of:

| Kind | How it shows in `player_death` |
|---|---|
| Own grenade (HE) | attacker == victim, weapon `hegrenade` |
| Own fire (molotov, incendiary) | attacker == victim, weapon `inferno` |
| Fall damage | no attacker or attacker == victim, weapon `world` or `worldspawn` |
| Bomb explosion | weapon `planted_c4` |
| Console suicide or slay by a plugin | attacker == victim, weapon `world`, often no damage events before it |
| Team kill | attacker on the victim's team |

Count each kind, per clone and per side.

## Step 2: what the bot was doing in the 5 seconds before each self-kill

For each self-kill, from the demo: the bot's positions, speed, `move_type`, active weapon,
grenade throws (`weapon_fire` with grenade weapons, `hegrenade_detonate`, `inferno_startburn`), damage
taken (`player_hurt` with its `weapon` and `dmg_health`), and jumps.

From the CloneDirector console log (`[CloneDirector]` lines, and `clone_list` output if captured): was a
recorded route playing, which route (`route=` key and file), and why it stopped (`reason=`).

Plugin logs are in `addons/counterstrikesharp/logs/log-all<date>.txt`.

## Step 3: test these suspected causes (read from the code, none verified)

1. **Route stopped in the middle of a grenade throw.** `CloneDirectorPlugin.cs` stops playback when the
   bot is hurt, deals damage, or an enemy fires within 1200 units (`Combat.NearbyShotRadius`). If that
   happens while the replay holds a pulled grenade, the game's own bot takes over a bot that is holding
   a live grenade and may drop it or throw it at its feet. Evidence: the self-kill's grenade was thrown
   within 1 second after a `reason=hurt`, `dealt damage` or `enemy fired nearby` stop.
2. **The replay throws the pro's grenade, then walks into it.** The route replays the pro's inputs at
   the pro's timing, but the bot does not start at exactly the pro's position, so a molotov or HE can
   land closer than it did for the pro. Evidence: self-damage from `inferno` or `hegrenade` while a
   route was still playing.
3. **Drift off a ledge.** Replayed inputs drift from the recorded path (Tom measured within 11 units on
   one T route; other routes are unmeasured). On Mirage, drops such as palace, connector or the ladder
   room can then cause fall damage. Evidence: fall damage while a route is playing, at those places.
4. **The quirk nudges or jumps.** `ApplyRestlessQuirk` sidesteps for 350 ms and `ApplyJumpQuirk`
   presses jump, both only when no route is playing. Evidence: fall damage within 1 second of one of these
   (add a temporary log line only if Tom agrees, and remove it afterwards).
5. **A plugin slays stuck bots.** CS2-Smarter-Bot says it "fixes most bot stuck issues". Check whether
   anything in the installed bot base (CS2-Bot-Improver, Smarter-Bot, NadeSystem) slays or respawns
   stuck bots. Evidence: a `world` death with no damage before it, while the bot had not moved.
6. **Bomb deaths counted as self-kills.** Evidence: weapon `planted_c4`.

## What to report

Write `handoffs/tom-self-kill-findings.md` with:

- the table of self-kill kinds and counts, and the matches and rounds it covers;
- for each cause above: confirmed (with the evidence), ruled out (with the evidence), or not tested;
- the most likely cause, and the smallest fix you would make, **not applied**;
- anything you could not check.

Then update `SPEC.md` (status row "Self-kill diagnosis", change log line) in the same commit, delete this
prompt file in that commit, and push.


## Round4 training follow-up (2026-11-15, Arjun/Codex)

Two offline neural development runs (donk and broky) are separate from the live playback layer. Do not assume a new model checkpoint is installed or that retraining caused/fixed these deaths. Record exact profile, driver, plugin version, route source and installed DLL hashes in your findings.

After collecting non-invasive death timelines, propose a controlled routes-on/routes-off/native comparison to Tom. If the same bot reacts to sounds with routes off and fails during recorded playback, that isolates controller ownership as the likely adaptability problem. It is evidence to investigate, not proof of a precise mechanism. Keep side, spawn, economy, opponents and scenario comparable; report confounders.

Do not change route mode in the middle of a primed grenade: the command itself stops playback and can confound or create the suspected problem. Arrange mode changes before a controlled round with Tom's approval, with no active grenade state. Do not send console record over netcon. Capture input ownership, attack/release state and the five seconds before the death. Diagnose first, then propose a minimal fix and regression scenario; do not patch live code in this diagnosis task.
