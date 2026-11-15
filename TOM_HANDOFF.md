# Tom's session handoff, 14 Nov 2026

State of Tom's PC (the demo machine) and what is left. Evidence labels: **ran** = seen in this
session, **read** = from the spec or docs, **not run**.

## State right now
- CS2 is open in Bot Mode on de_mirage. Bots: donk (slot 5, CT) and broky (slot 6, T), added by
  console commands, not by the match service.
- Match service is **not running**. Claude Code stopped it when the PC ran low on memory.
- Launch options in Steam: `-netconport 2121 -usercon`. Anti-cheat is off in Bot Mode: never join an
  online match like this. Auto-updates for CS2 were not switched off yet.
- Bot base: CS2-Bot-Improver v1.4.9 in `game\csgo`. The launcher is `Panel.exe` in
  `C:\Users\Hi\Downloads\CS2BotImprover-v1.4.9\extracted`.
- Not installed in the game: the CloneDirector plugin.

## Ran
- netcon works. Game state reaches the match service. `start-cs2.ps1` works on Windows.
- Ash's fix works: with `record` removed, a wingman donk-vs-broky match went `ready`, `live`, and the
  score counted (CT 1, T 0 after round 1). Bots move on screen.
- The `record` console command froze the client clock and crashed CS2 once. Do not send it.
- Playback gate, step 1: `!record test`, `!stoprecord` (saved 962 ticks), `!replay 1 test` made a bot
  walk the recorded path.
- Playback gate, step 2: `!replay <slot> donk_v1_t_2393226_r13` (a converted file from `clones/`)
  loads and the bot moves. **Not confirmed:** that it runs the real route. The first try was on a bot
  on CT and it walked into a wall, which fits a T-side route played from CT spawn. A second try was
  made with broky (T side); Tom reports it "seems to be loading". Nobody has said what the path
  looked like.
- Audit of the clone files against the real held-back matches: `CLONE_AUDIT.md`, pushed.

## Not run
- Whether the game accepts the converter's guessed fields. A real recording differs from ours in
  `EntityFlags` (65665 vs 1), `Commands[].Fields` (24-59 vs 0), `InputHistory` (about 157k
  characters vs empty), `Subticks` (22 vs none), `MouseDx/Dy`, `MoveType`. Raw data: Tom's
  `data/audit/test_real_recording.json.br` (not in git: `data/` is ignored).
- Wingman ending by itself at 9 rounds. The service was killed first.
- `-Record tv` (GOTV) and whether `match<id>.dem` appears.
- CloneDirector in CS2; `clone_add`.

## Next steps, in order
1. Watch one replay of the converted route from T spawn and say whether it follows Palace to A.
2. If it fails, give Arjun the real recording so the converter can copy its field values.
3. Restart the service and run the wingman match to the end (9 rounds), then try `-Record tv`.
4. Install CloneDirector (`clone-director/README.md`) and try `clone_add donk_v1 t`.

## Things to know
- Bot slot numbers change when bots are re-added. Check `status` in the console first.
- The bot base's random fill bots (for example tomiko, swerzieN) replace donk and broky if the
  match ends or restarts. Re-add with: `bot_kick`, `bot_add_ct "donk"`, `bot_add_t "broky"`,
  `mp_restartgame 1`.
- Everything up to commit `23cc091` is pushed. This file is not committed.
