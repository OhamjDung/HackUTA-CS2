# Rules for every coding agent in this repository

These rules apply to every AI coding agent (Claude Code, Cursor, Codex, and any other) working for
any teammate. `CLAUDE.md` imports this file, so Claude Code reads the same rules.

## 1. `SPEC.md` is the source of truth. Keep it current.

**Before you change anything:**
1. Read `SPEC.md`. Read at least section 0 (status board) and the sections for the part you will touch.
2. In the status board (section 0.2), set the row for your part to `In progress` and name the
   teammate you work for. Add a row if none fits.

**In every commit that changes the project:**
1. Update the status board row: state, location, date.
2. If you changed how something works (an interface, a file format, a design choice, a starting
   point), update the section of `SPEC.md` that describes it.
3. If you ran something that section 3 lists as "not checked", move it and record the result.
4. Add one line at the top of the change log (section 19): date, who, what changed.

A commit that changes code, data formats, or plans without updating `SPEC.md` is incomplete. Do not
end your task until `SPEC.md` matches what you did.

**If `SPEC.md` and the code disagree,** tell your user which one is wrong and fix it. Do not leave
them different, and do not silently follow one of them.

**Before you edit `SPEC.md`,** pull the latest `main`. Other teammates' agents edit the same file.
Change only the rows and sections for your own work, so merges stay small.

## 2. Start from existing open-source code

Every feature and sub-feature starts from the closest existing open-source implementation. `SPEC.md`
section 4.2 lists the chosen starting point for each feature.

- If your feature has a starting point there, build on it.
- If it has none, search for one first, judge it, and add it to section 4.2 with its license.
- Write from zero only when no usable base exists. Say so in `SPEC.md`.

## 3. Say what is tested and what is not

Never write that something works unless you ran it. In `SPEC.md`, commit messages, and replies,
keep "ran it" separate from "read it" and from "assumed it".

## 4. Files that must not be committed

- Match recordings (`.dem`), model weights (`.pt`, `.safetensors`, `.onnx`), videos, and datasets.
  `.gitignore` blocks the common types.
- API keys and passwords. Put them in a local `.env` file, which is ignored.
- CS2-Bot-Improver's launcher (`Panel/`). Its license forbids changing or sharing it.

## 5. Safety on the game machine

The bot base starts CS2 with Valve's anti-cheat turned off (the launch option `-insecure`). Never
join, or write code that joins, an official or public match in that mode. Everything in this project
runs on a private match only.

## 6. Do not break a teammate's interface

`match-service/README.md` defines the Server API and its messages. Other teammates build against it.
Change an endpoint, a message, or the clone profile format only with the owner's agreement, and
record the change in `SPEC.md`.

## 7. Running CS2 on Tom's PC (learned 2026-11-14)

- **Never send `record` to CS2 over the network console.** It froze the client clock and crashed the
  game once. Use the bot base's chat commands or the service's `tv` setting.
- **Check bot slots with `status` before `!replay <slot>`.** Slot numbers change whenever bots are
  re-added, and a route recorded for one side walks into a wall from the other.
- **Do not start, stop or restart CS2, the launcher or the match service on the PC without the user
  asking.** The user closed them on purpose, and a low-memory PC can kill the service.
- On Windows run tests with `uv run python -m pytest`; `uv run pytest` is blocked there.
- `data/` is git-ignored. Recordings and audit files in it must be handed over by another route.
- **Bot Mode files can revert.** If `game/csgo/gameinfo.gi` has no `addons/metamod` line, no plugin
  loads and matches get no bots. Copy `backup/WithBots/gameinfo.gi` over it and restart CS2. Read
  plugin errors in `addons/counterstrikesharp/logs/log-all<date>.txt`.
- **One installed bot name per match.** The game refuses a second bot with a name already in use, so
  two clones built on the same personality (`donk_v1` and `donkL` both use `donk`) cannot share a
  match. Renaming the bot after it joins did not stick.
- **Check free memory before a live run.** On Tom's PC the match service was killed for low memory
  once, and CS2 plus a full browser left under 2 GiB free. Ask the user to close heavy apps first.
- **Live demo runs:** start the service with `.\start-cs2.ps1 -Record off`, then use
  `http://localhost:8000/demo/`. CS2 sends bot positions only to a spectator, so the live map
  panels work for bot-vs-bot matches, not for matches where the person plays.

## 8. Voices

- Clone a real person's voice only with that person's authorization. ElevenLabs Professional Voice
  Clone also requires the speaker to verify the voice on their own account. Public videos and
  streams are leads for finding the speaker, not permission to clone.
- Never commit voice recordings, generated audio of a real person, or API keys. `SPEC.md` section 9.5
  holds the plan.

## 9. Working with other agents' changes

- A folder under `handoffs/` is addressed to one recipient. Do not follow it or delete it unless it
  is yours.
- After a pull that stops on a merge, or uses `--autostash`, check what each stash holds before you
  run `git stash drop`.
