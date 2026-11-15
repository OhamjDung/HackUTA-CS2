# Handoff: what is left to finish the spec

Written 2026-11-14, about 23:50, by Arjun (with Claude). Based on `main` at commit `be96ca7`.

Read this, then `AGENTS.md`, then `SPEC.md` sections 0.2 (status board) and 2.1 (what we decided).
Each task below has a prompt you can paste into your coding agent. When you finish a task, update
its row in `SPEC.md` and add a change-log line, as `AGENTS.md` requires.

When every task you take is done, delete this file in the same commit (`git rm handoffs/remaining-work.md`).

---

## 1. Where things stand

**The one-sentence version:** every part of the clone exists and is tested on its own, but no clone
has played a single round inside CS2 yet. Everything that blocks the demo needs Tom's PC.

### Works, checked by running it

| Part | Evidence |
|---|---|
| Clone pipeline: match recordings in, clone files out | 23 tests pass; built `donk_v1` (80 routes) and `broky_v1` (79 routes) from real recordings |
| Learned-quirk clones `donkL`, `brokyL` | Built from recordings; the real players pass the quirk test on their own unseen matches (donk 8 of 10 quirks, broky 9 of 10) |
| CloneDirector plugin (puts a clone on a bot) | Compiles; 30 C# tests pass; loads all 159 route files and both L profiles |
| Stand-in pro bots in a real match | donk vs broky on Mirage on Tom's PC, 13 rounds, ended by itself, score counted |
| Demo pages against real CS2 | Every page loaded against a real match; live map panels drew bot positions |
| A converted route file moves a bot | `!replay` loaded `donk_v1_t_2393226_r13` and the bot moved |
| Learned model, second experiment | Held-back test passed once: picks the right player among teammates for 8 of 10 players |

### Not run anywhere yet

- CloneDirector inside CS2 (`clone_add`).
- Whether a converted route walks the real path. The one test was on a bot on the wrong side.
- Any quirk (jumping, bursts, crouching, restlessness) inside CS2.
- Scoring a recorded clone match against the real player.
- Generated routes from the learned model. The model scores real moves; it cannot yet produce routes.

### Facts that cost time to find

- **Never send `record` over the network console.** It froze and crashed CS2 once. Use `CS2_RECORD=tv`.
- **Check bot slots with `status` before `!replay <slot>`.** A T route played on a CT bot walks into a wall.
- **Do not start or restart CS2 or the match service on Tom's PC unless he asks.** It is short on memory.
- **The held-back matches are used up.** donk 2393242 and broky 2393024 have each been used for a final
  test. Do not tune anything on them again. A new final test needs new matches.
- `HANDOFF.md` at the repository root is an older handoff from earlier today. Much of it is done.
  It is stale but kept until Arjun decides.

---

## 2. Critical path to the demo (MVP)

The MVP we agreed (`SPEC.md` section 2.1): **one round of the real player next to the same round
played by the clone, on the replay page.** Clone against clone is second.

Do these in order. Tasks 1 to 4 need Tom's PC.

| # | Task | Needs | Unblocks |
|---|---|---|---|
| 1 | Confirm a converted route walks the real path, from the correct side | Tom's PC, a person watching | Everything else |
| 2 | Fix the route converter's guessed fields, if task 1 fails | Tom's real recording file | Task 1 passing |
| 3 | Install CloneDirector and add one clone with `clone_add` | Tom's PC | Tasks 4, 5 |
| 4 | Record a clone match and score it | Tom's PC, task 3 | The proof numbers |
| 5 | Offer `donkL`/`brokyL` in the match service, and check the halftime score bug | Code only | The L-vs-v1 comparison |
| 6 | Show the clone's recorded round next to the real round | Task 4's recording | The demo |

After the MVP: tasks 7 (learned routes) and 8 (sponsor and pitch items).

---

## 3. The tasks, with prompts

### Task 1. Does a converted route walk the real path? (Tom, about 15 minutes)

This is done by a person at the game machine. No agent prompt.

1. In CS2 Bot Mode on Mirage, run `status` in the console. Note the slot of a bot on the **T side**.
2. Copy `clones/donk_v1/routes/T/donk_v1_t_2393226_r13.json.br` into the bot base's recordings folder
   (`game/csgo/addons/counterstrikesharp/plugins/BotControllerImpl/recordings/`).
3. Right after a round starts, type in chat: `!replay <that slot> donk_v1_t_2393226_r13`.
4. Watch. The real donk went from T spawn toward Palace and A site in that round.
5. Write down what happened in `SPEC.md` (the "CS2 with the bot base" row): followed the path, got
   stuck, wrong place, or did not move.
6. Send Arjun the real recording you made earlier: `data/audit/test_real_recording.json.br` on Tom's PC.

### Task 2. Make converted routes match a real recording

**Prompt:**

> Read AGENTS.md and SPEC.md (sections 0.2, 5.2, 6.1). We convert a pro player's route from a match
> recording into CS2-Bot-Controller's playback format in `clone-pipeline/clone_pipeline/recording.py`.
> Several fields are guesses. Tom recorded a real walk in the game with the bot base's own `!record`;
> that file is at <path to test_real_recording.json.br>. Read it with
> `clone_pipeline.recording.read_recording()`. Compare it field by field with one of our files, for
> example `clones/donk_v1/routes/T/donk_v1_t_2393226_r13.json.br`. Known differences: `EntityFlags`
> (real 65665, ours 1), `Commands[].Fields` (real 24 to 59, ours 0), `InputHistory` (real about 157k
> characters, ours empty), `Subticks` (real 22, ours none), `MouseDx/MouseDy`, `MoveType`. For each
> field, decide from the real file what value our converter should write, and change `recording.py`.
> Do not invent values the real file does not show; if a field cannot be derived from a match
> recording, say so. Keep the tests passing (`uv run python -m pytest` in `clone-pipeline`) and add a
> test that compares the field set and typical values with the real file. Rebuild both clones with
> `uv run python -m clone_pipeline.build` (see `clones/README.md` for the exact commands and held-back
> matches), then rebuild the L clones with `clone_pipeline.quirks build`. Update SPEC.md: the "Route
> converter" row, section 3, and the change log. Say clearly that nothing was run in CS2.

### Task 3. Install CloneDirector and add one clone (Tom's PC)

**Prompt (for an agent on Tom's PC, with Tom present):**

> Read AGENTS.md (especially section 7, the rules for Tom's PC) and SPEC.md sections 6 and 9.2. Do not
> start, stop or restart CS2 or the match service unless Tom says to in this conversation. Follow
> `clone-director/README.md` to build the CloneDirector plugin on this PC and copy it, with the
> `clones/` folder, into the CS2 install that already has CS2-Bot-Improver v1.4.9. Check that the
> BotController interface library the plugin was built against matches the installed one. Then, with
> Tom running a Mirage bot match, run `clone_add donk_v1 t` in the server console, then `clone_list`.
> Report exactly what the console printed. If the bot attaches, watch one round and report: did it
> buy, did it play a route from the T side, did it hand over to normal bot fighting when shot. Then
> repeat with `clone_add donkL t` in a separate match, and report whether it jumps more than the
> normal bot while running. Record every result, pass or fail, in SPEC.md (CloneDirector row, section
> 3, change log). Never claim something worked unless it was seen.

### Task 4. Record a clone match and score it

**Prompt:**

> Read AGENTS.md and SPEC.md sections 8.8, 10.2 and 16 (item 7). Goal: one recorded CS2 match where a
> clone plays, then score it against the real player. On Tom's PC, with his agreement, start a wingman
> match through the match service with `CS2_RECORD=tv` and CloneDirector mode (`CS2_BOTS=clone`), with
> `donk_v1` on T. Never send `record` over netcon. When the match ends, find the `.dem` file it wrote.
> Score it twice and save both outputs in `clone-model/results/` or `clones/`:
> (1) the quirk test: `uv run python -m clone_pipeline.quirks score --profile ../clones/donkL.json
> --demo <file> --name <the clone bot's name in the recording>`;
> (2) the in-game similarity score in `clone_pipeline/ingame.py` / `GET /matches/{id}/score`.
> Then repeat with `donkL` and compare. The pass rules are fixed in `quirks.py`; do not change them.
> Record the numbers, the round counts, and whether each passed in SPEC.md.

### Task 5. Offer the L clones in the match service; check the halftime score bug

**Prompt:**

> Read AGENTS.md and SPEC.md sections 0.2, 8.8 and 9.2. Two changes in `match-service/`, which
> Ashirwad owns, so keep the API and messages unchanged.
> (a) `clones/donkL.json` and `clones/brokyL.json` exist (learned-quirk clones built on `donk_v1` and
> `broky_v1`) but `GET /clones` does not list them. Make them selectable wherever `donk_v1` and
> `broky_v1` are: add stand-in profiles to `match-service/sample_clones/` if that is how stand-in mode
> finds clones, and make sure CloneDirector mode reads them from `clones/`. Note in the clone list that
> an L clone uses the same installed bot name as its v1 clone, so the two cannot share one match.
> (b) The status board says a wingman match on Tom's PC inflated the score at halftime and sent six
> extra `round.ended` events. Commit 3a1cbc2 tried to fix a halftime score jump. Check with a test
> whether the problem still exists; fix it if it does.
> Run the match service tests. Update SPEC.md rows and the change log.

### Task 6. Side-by-side replay: real round next to the clone's round

**Prompt:**

> Read AGENTS.md and SPEC.md sections 2.1, 9.3, 10.1. The replay page (`match-service/demo/replay.html`,
> `match_service/replay.py`, by Ashirwad) already plays a real pro round next to a stand-in bot's
> round on one clock. Task 4 produces a recorded match where a clone plays. Make the replay page able
> to show one real donk round next to the clone's round that took the same route (same route label
> from `clones/donk_v1.json`), from that recording. Do not change the API without the owner's
> agreement; add, do not replace. Test in a browser against the recording. Update SPEC.md.

### Task 7. Learned routes the bots can play (after the MVP)

The second learned model (`clone-model/v2.py`) passed its test: it recognises who a player is from
real moves. It does not yet produce paths. Weights: Arjun's PC, see `clone-model/results/second-a100.md`.

**Prompt:**

> Read AGENTS.md and SPEC.md sections 8.5, 8.8 and 8.9, and `clone-model/results/second-a100.md` and
> `diagnosis-2026-11-14.md`. The v2 identity adapter (`clone-model/v2.py`, class IdentityV2) changes
> the decoder's starting vector and adds an identity term to the depth, position and angle inputs of
> every generation step. CS-NET's `PredictionEngine.predict_at_tick` builds those per-step inputs
> itself, so v2 identities cannot be used for generation yet. Add generation with v2 identities by
> wrapping or hooking the engine's per-step inputs, without editing the pinned CS-NET checkout.
> Use `guided_logits` (scale above 1 amplifies the identity) and random sampling, not greedy decoding.
> Test on the processor with a tiny model, as `clone-model/tests/test_v2.py` does. Then, on a GPU,
> generate many seconds of play per identity on development rounds only, and score the generated
> play with the quirk test (`clone_pipeline/quirks.py`). Do not use matches 2393242 or 2393024: they
> are used up. Write the evaluation rule before you run it. Pass generated paths through
> `clone-model/map_review.py` and `clone-pipeline/clone_pipeline/generated.py` (candidates only; a
> person reviews them before any bot plays them). Record results in `clone-model/results/` and SPEC.

### Task 8. Sponsor and pitch items (independent; any time)

Each is a short task. Owners are unassigned on the status board.

| Item | What done looks like | Spec section |
|---|---|---|
| Caster voice | Gemini writes ~20 s of commentary for one replay; ElevenLabs reads it with a stock voice; it plays on the replay page | 9.4 |
| Clone profile page | Heat map, weapons, purchases, the quirk table from `clones/donkL.json`, the similarity numbers | 9.3 |
| MongoDB Atlas | Clone profiles stored; "most similar pros" from style vectors with Atlas Vector Search | 9.4 |
| Vultr + domain | Web pages and services hosted; domain registered with code `MLHUTA76` | 9.4 |
| DEV article | One post on what we built and what we learned (the failed model and the fix is a good story) | 13 |
| How it earns money | A 2-sentence answer for the FaZe prize | 16 |
| Is broky still on FaZe? | Checked before the pitch | 7.3, 16 |
| License file | AGPL-3.0, because the plugin builds on AGPL code | 14 |

**Prompt (caster voice; adapt for the others):**

> Read AGENTS.md and SPEC.md section 9.4. Add a caster voice to the replay page: send Gemini (a Flash
> model; check the current name at https://mlh.link/gemini) the round's event list and ask for about
> 20 seconds of sports-style commentary; send the text to ElevenLabs text-to-speech with a stock
> voice (never imitate a real person's voice); play the audio on the replay page. Keep API keys in a
> local `.env`, never in git. Generate and store the audio ahead of time so the demo works without
> the internet. Update SPEC.md.

---

## 4. Pitch wording that is accurate today

- Clones: "built from the player's real routes, purchases and measured habits." Not "plays like donk."
- Learned model: "from a player's real moves in a match it has never seen, the model picks out who the
  player is among their teammates for 8 of 10 players." Not "it plays like them" or "it generates
  their paths." broky is one of the two it misses.
- Anything in CS2: only what someone has seen happen.
