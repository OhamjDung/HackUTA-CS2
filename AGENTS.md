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
