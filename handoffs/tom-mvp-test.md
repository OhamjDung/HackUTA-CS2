# Tom: test whether the MVP works on your PC

Written 2026-11-14 by Arjun (with Claude), for Tom. Based on `main` at commit `e99afbb` or later.

**Delete this file when you are done:** `git rm handoffs/tom-mvp-test.md`, in the same commit where you
record your results in `SPEC.md`. That keeps the repository clean.

---

## 1. What this test answers

The MVP is: **one round of the real player, shown next to the same round played by our clone.**

Every part of a clone is built and tested on its own. But no clone has played a round inside CS2.
Only your PC can find out whether it does. This test answers three questions, in order:

1. Does one of our converted route files make a bot walk the real player's path?
2. Does the CloneDirector plugin attach a clone to a bot, buy its items, and play its route?
3. Can we record a match with a clone in it, and score how much it plays like the real player?

If 1 and 2 pass, the MVP works. If 1 fails, stop at step 2 below and send Arjun the file it asks for.

## 2. Rules for this PC

- **Anti-cheat is off in Bot Mode.** Never join an online match in this mode.
- **Never send `record` over the network console.** It froze and crashed CS2 once. Use `-Record tv`.
- **Run `status` in the console before every `!replay <slot>`.** Slot numbers change when bots are
  re-added, and a T route played on a CT bot walks into a wall.
- **You decide when CS2 and the match service start and stop.** If your coding agent wants to restart
  either, it must ask you first.
- **Do not commit recordings (`.dem`), model weights, or anything in `data/`.**

## 3. Before you start

1. Pull: `git pull origin main`.
2. Have ready: CS2 with CS2-Bot-Improver v1.4.9 in Bot Mode (already on your PC), the .NET SDK 10
   (only for step 3), and `uv` (already used for the match service).
3. If the bot base's filler bots replaced donk and broky, re-add them in the console:
   `bot_kick`, `bot_add_ct "donk"`, `bot_add_t "broky"`, `mp_restartgame 1`.

---

## 4. The steps

### Step 1. Does a converted route walk the real path? (about 15 minutes, no code)

Last time the route ran on a CT bot and walked into a wall. This time use the correct side.

1. Start a Bot Mode match on Mirage. Run `status`. Note the slot number of a bot on **T**.
2. Copy `clones/donk_v1/routes/T/donk_v1_t_2393226_r13.json.br` into the bot base's recordings folder:
   `game\csgo\addons\counterstrikesharp\plugins\BotControllerImpl\recordings\`.
3. Right after a round starts (freeze time just ended), type in chat:
   `!replay <T slot> donk_v1_t_2393226_r13`
4. Watch that bot. In the real round, donk left T spawn toward **Palace**, then **A site**.

| What you see | Result |
|---|---|
| The bot heads to Palace and on toward A | **Pass.** Go to step 3. |
| It moves, but the wrong way, or stops, or gets stuck | **Fail.** Do step 2, then still try step 3. |
| It does not move at all | **Fail.** Do step 2. Copy the exact chat reply. |

If you can, try a second file the same way, from CT this time, with a CT bot:
`clones/donk_v1/routes/CT/` (any file).

### Step 2. If step 1 failed: send Arjun your real recording

Our converter guesses some fields. Your real `!record` file shows the right values.

- The file: `data\audit\test_real_recording.json.br` on your PC (from your earlier `!record test`).
  If it is gone, make a new one: `!record test`, walk for 10 seconds, `!stoprecord`. It saves into
  the same recordings folder as step 1, named `test.json.br`.
- Send it to Arjun on Discord. **Do not commit it.**

### Step 3. Install CloneDirector and add one clone (about 30 minutes)

CloneDirector is our plugin. It puts a clone's purchases and routes onto a bot, then lets the bot
base fight normally.

**Build** (PowerShell, from the repository root). Use the interface file from **your** installed bot base:

```powershell
$api = '<CS2 folder>\game\csgo\addons\counterstrikesharp\shared\BotControllerApi\BotControllerApi.dll'
dotnet build clone-director/CloneDirector.csproj -c Release "-p:BotControllerApiPath=$api"
dotnet test clone-director/Tests/CloneDirector.Tests.csproj -c Release "-p:BotControllerApiPath=$api"
```

The tests should report 30 passed.

**Install:**

1. Create `game\csgo\addons\counterstrikesharp\plugins\CloneDirector\`.
2. Copy into it, from `clone-director\bin\Release\net10.0\`: `CloneDirector.dll`, `CloneDirector.Core.dll`,
   `CloneDirector.deps.json`, `CloneDirector.runtimeconfig.json`. Also copy `clone-director\LICENSE`
   and `clone-director\THIRD_PARTY.md`. **Do not copy `BotControllerApi.dll` there.**
3. Copy the repository's whole `clones\` folder into that same `CloneDirector\` folder.
4. Restart CS2 in Bot Mode (your call when) so the plugin loads.

**Add a clone.** In a Mirage Bot Mode match, in the **server console** (not chat):

```text
clone_add donk_v1 t
clone_list
```

Then let one full round play and watch the donk bot.

| Check | What to look for |
|---|---|
| Plugin loaded | The console does not print `BotController API version 1 is unavailable` |
| Bot attached | `clone_list` shows `clone=donk_v1` with a slot number |
| Bought its items | On a full-buy round: an AK-47, armour, grenades |
| Played a route | Next round, it walks a T route on its own; `clone_list` shows the route name |
| Handed over | When shot at, it stops the route and fights like a normal bot; `clone_list` shows why it stopped |

If buying looks wrong, test one purchase directly: `bc_buy <slot> ak47 vesthelm`.

**Then the learned-quirk clone.** Start a new match (the two cannot share one), and run
`clone_add donkL t`. It is `donk_v1` plus five measured habits. The easiest one to see: **it jumps
about 4 times a minute while running**, where a normal bot almost never does.

### Step 4. Record a clone match and score it (about 30 minutes)

Start the match service in clone mode with recording on. From `match-service\`, when you are ready:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-cs2.ps1 -Bots clone -Record tv -Open
```

1. On the demo page, start a wingman match with `donk_v1` on T.
2. When it ends, find the recording: a `match_<id>.dem` file in `game\csgo\`. (`-Record tv` has never
   been tried. If no file appears, note that and stop here.)
3. Score it, from `clone-pipeline\`:

```powershell
uv run python -m clone_pipeline.quirks score --profile ..\clones\donkL.json --demo <path to the .dem> --name <the donk bot's name in that match>
```

It prints a "who is it?" rank and how many of donk's quirks the bot showed. Save the output.

4. Repeat with `donkL` on T and compare the two.

---

## 5. Report back

Record every result in `SPEC.md`, pass or fail: the "CS2 with the bot base installed" row, the
"CloneDirector plugin" row, section 3 ("What is checked and what is not"), and one change-log line.
Then delete this file in the same commit.

Also post a short summary in Discord:

```text
Step 1 route (T side): pass / fail — what the bot did
Step 3 clone_add donk_v1: attached yes/no, bought yes/no, route yes/no, handed over yes/no
Step 3 donkL jumping: seen yes/no
Step 4 recording: .dem made yes/no; quirk score donk_v1 = ..., donkL = ...
```

**How to read it:**
- Steps 1 and 3 pass: **the MVP works.** Next is the side-by-side replay with the recording.
- Step 1 fails, step 3 attaches: the plugin works but routes need the converter fix from step 2.
- Step 3 does not attach: copy the console output exactly; that is what we need to fix it.

---

## 6. Prompt for your coding agent (optional)

Paste this into Claude Code on your PC if you want help with steps 3 and 4:

> Read AGENTS.md (especially section 7, rules for Tom's PC), SPEC.md sections 0.2, 6 and 9.2, and
> handoffs/tom-mvp-test.md. Help me run steps 3 and 4 of that handoff on this PC. Do not start, stop
> or restart CS2 or the match service unless I say so in this conversation. Never send `record` over
> netcon. Build CloneDirector against the BotControllerApi.dll from my installed bot base, run its
> tests, and tell me exactly which files to copy where. When I paste console output, tell me what it
> means. Record every result, pass or fail, in SPEC.md (the two rows named in section 5 of the
> handoff, section 3, and the change log), then delete handoffs/tom-mvp-test.md in the same commit.
> Never write that something worked unless I saw it happen.
