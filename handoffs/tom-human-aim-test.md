# Tom: test the human-aim fix for the clones

Written 2026-11-15 by Arjun (with Claude), for Tom. Needs `main` at the commit that added this file.
Background: `clone-model/ROUND3_DESIGN.md`, sections 1 and 6 (step 1).

**Delete this file when you are done:** `git rm handoffs/tom-human-aim-test.md`, in the same commit where
you record your results in `SPEC.md`.

---

## 1. What changed, and what we want to know

Arjun watched `donk_v1` against `donkL` and saw two problems: `donkL` walks backwards a lot, and it
flicks onto targets like an aimbot.

**Cause of the flicks (found in the files):** your tool copied the bot base's `donk` and `broky`
entries for the clones. Those entries have no limit on how fast the aim can speed up, and zero
reaction time. In a simulation of the bot's aim, a 90-degree flick takes 0.14 s and peaks at
4,219 °/s. No measured pro turns faster than about 1,500 °/s.

**Suspected cause of the backwards walking:** `donkL`'s restlessness rule (it sidesteps the bot when
it has been still for 2 s, and the bot then walks back to its spot while aiming at its angle).

**What is new on `main`:**

1. `clone-director/tools/add_clone_bot_entries.py` now gives the four clone entries (`donk_v1`,
   `donkL`, `broky_v1`, `brokyL`) human aim settings. The original `donk` and `broky` entries are not
   changed. It also replaces clone entries that already exist, so you can run it on your patched file.
2. `donkL` and `brokyL` no longer use the restlessness rule or the crouch-at-burst rule. They keep jump
   rate and burst length.
3. A new check: `uv run python -m clone_pipeline.limits check`. It measures a bot in a match recording
   against 9 limits taken from 50 real pros, and prints pass or fail for each. Every real pro passes it.

**The question:** with the new settings, does the bot stay inside human limits, and does it look human
to you?

## 2. Rules for this PC (unchanged)

- Anti-cheat is off in Bot Mode. Never join an online match in this mode.
- Never send `record` over the network console. Use `-Record tv`.
- You decide when CS2 and the match service start and stop.
- Close browser tabs before a run; low memory killed the service before.

---

## 3. Steps

### Step 1. Record the "before" match (optional, but it makes the result clear)

With your current setup, unchanged, start the service with recording on, from `match-service\`:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-cs2.ps1 -Bots clone -Record tv -Open
```

Run one wingman match: `donk_v1` on CT, `donkL` on T. When it ends, find `match_<id>.dem` in `game\csgo\`.
If no file appears, `-Record tv` does not work on your PC: note that, skip to step 2, and judge by eye.

### Step 2. Install the new bot settings

1. Pull: `git pull origin main`.
2. **Close CS2.**
3. Make a copy of your current `game\csgo\overrides\botprofile.vpk` (the one with your clone entries).
4. From the repository root:

```powershell
pip install vpk
python clone-director/tools/add_clone_bot_entries.py "<CS2 folder>\game\csgo\overrides\botprofile.vpk"
```

   It writes `botprofile.vpk.new` next to the original. Replace `botprofile.vpk` with it.
5. Copy the updated `clones\donkL.json` and `clones\brokyL.json` from the repository into the
   CloneDirector plugin's `clones\` folder (the plugin code did not change; only these two files did).
6. Start CS2 in Bot Mode again.

### Step 3. Record the "after" match

Same as step 1: one wingman match, `donk_v1` on CT, `donkL` on T, with `-Record tv`.

While it plays, **watch both bots**. Write down:
- Does `donkL` still walk backwards a lot?
- Do the bots still snap onto targets instantly, or do they now take a moment to aim?
- Anything else that looks robotic.

### Step 4. Run the check

From `clone-pipeline\`, on the "after" recording (and the "before" one, if you have it):

```powershell
uv run python -m clone_pipeline.limits check --name donkL --like donk <path to match_<id>.dem>
uv run python -m clone_pipeline.limits check --name donk_v1 --like donk <path to match_<id>.dem>
```

Each prints PASS or FAIL, one line per limit, the bot's value, the limit, and real donk's own range.
A check with too few samples says so instead of passing or failing.

What to look at first:

| Line | What it means | Before the fix (expected) |
|---|---|---|
| `turn_p999`, `turn4_p999` | How fast the aim turns | Probably FAIL |
| `turn_accel_p999` | How fast the turn speeds up | Probably FAIL |
| `flick_time_p05_s` | How quickly it lands a big flick | Probably FAIL, if it flicked enough |
| `backwards_share_of_moving` | Share of moving time walking backwards | donkL: FAIL if the restlessness rule was the cause |

### Step 5. If it still fails

The aim settings are at the top of `clone-director/tools/add_clone_bot_entries.py`, in `HUMAN_AIM`.
They are starting values. If turning is still too fast, lower `LookAngleStiffnessAttacking` (600) or
`LookAngleMaxAccelAttacking` (20000). If it now aims too slowly to look like a pro, raise them a little.
Rerun the tool (step 2) and record again. Keep each value inside the human limits, and note every
change you try.

---

## 4. Report back

Record the results in `SPEC.md` (the "Round 3 design" row, section 3, and the change log), then delete
this file in the same commit. Post in Discord:

```text
Human-aim test:
-Record tv made a .dem: yes/no
donkL check: PASS/FAIL, failed lines: ...
donk_v1 check: PASS/FAIL, failed lines: ...
By eye: still walking backwards? yes/no. Still snapping? yes/no. Other: ...
Values changed in HUMAN_AIM (if any): ...
```

## 5. Prompt for your coding agent (optional)

> Read AGENTS.md (section 7, rules for Tom's PC), clone-model/ROUND3_DESIGN.md sections 1 and 6, and
> handoffs/tom-human-aim-test.md. Help me run that handoff's steps on this PC. Do not start, stop or
> restart CS2 or the match service unless I say so in this conversation. Never send `record` over
> netcon. When I give you a match recording, run `clone_pipeline.limits check` for donkL and donk_v1
> with `--like donk` and explain each failed line in plain words. Record every result, pass or fail, in
> SPEC.md, then delete handoffs/tom-human-aim-test.md in the same commit. Never write that something
> worked unless it was measured or I saw it.
