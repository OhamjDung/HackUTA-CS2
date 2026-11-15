# Tom: install and test the four Odyssey bots

For Tom's agent, from Arjun/Codex, 2026-11-15. Delete this temporary handoff after consuming it, in the
same commit that records findings in SPEC.md. The persistent design is `clones/ODYSSEY.md`.

The user's new roster matches the UI IDs exactly:

- `poseidon` /The Tempest: impossible, damage-immune boss.
- `odysseus` /The Strategist: pro-strength target, small explicit superhuman edge (1.08x enemy-player damage).
- `menelaus` /The Warlord: medium, slower/less precise than the top bots, normal damage.
- `telemachus` /The Heir: easy/beginner, 650ms reaction setting and deliberately loose aim, normal damage.

Fourteen authored quirks each, with trait rationale and actual control mapping, are in the profiles and
`clones/ODYSSEY.md`. These are authored/native-AI personas, **not neural models**. No pro routes are copied.
Keep the user's existing custom ElevenLabs voices and your trash-talk work. This change creates no voices,
API keys, audio or competing voice system. Use the four clone IDs as keys in your voice/trash-talk map.

## Read and install

1. Read AGENTS.md, SPEC.md and `clones/ODYSSEY.md`. Pull main and preserve your local changes. Rebuild
   with .NET 10 and `-p:BotControllerApiPath=<your installed shared BotControllerApi.dll>`, as in the
   director README. Deploy the updated **CloneDirector.dll and CloneDirector.Core.dll** together,
   using your existing plugin folder; back up the previous pair. Coordinate with Tom before modifying
   or restarting his running game/service. This is not authorization to launch them unasked.
2. Copy `poseidon.json`, `odysseus.json`, `menelaus.json`, `telemachus.json` into the configured director
   profiles folder and make them available to the service's `CLONES_DIR`. Preserve existing profiles.
3. With CS2 closed, back up `overrides/botprofile.vpk`; run the updated
   `clone-director/tools/add_clone_bot_entries.py` from a checkout containing the four JSON profiles.
   It writes a `.new` archive by default; verify/replace using the established workflow. It adds four
   separately named copies of the donk template, with distinct per-character overrides from the JSON.
   `--plain` still applies Odyssey overrides; it only removes L2/LF human-aim overrides. Existing v2
   entries and original pro entries stay unchanged. Check `gameinfo.gi`/botprofile after a crash.
4. Start the service only when Tom asks. From `match-service/` in PowerShell, set
   `$env:CS2_CLONE_ROUTES = 'recorded'`, then run `.\start-cs2.ps1 -Bots clone -Record off`.
   The script has no `-Routes` parameter; route source is an environment setting.
   Use the usual private Mirage Bot Mode. Never use global god/difficulty cvars or public matchmaking.
   `recorded` is the existing global route mode: Odyssey has no routes, so native AI acts throughout;
   existing real-player clones still use their recorded routes. Generated mode and stand-in mode are
   refused by the service for Odyssey. Calling bare `bot_add` is insufficient for damage rules.
5. Add through the existing match service or `clone_add poseidon ct` etc. Expect an `Attached` log and
   `ODYSSEY <id> difficulty=... invulnerable=... damage_multiplier=...`. Check current slots with `status`
   and `clone_list`. The latter also prints blocked/boosted damage-event counters; these should advance
   during the relevant tests. A counter proves the handler ran, not correct health/armor results.
   Service/compile success alone is not proof that the new DLL actually loaded.

## Private acceptance checklist

- First verify ordinary damage against a normal bot/human. Then test Poseidon: a lethal headshot,
  sustained rifle fire, HE/fire, knife and available environmental/C4 damage must not reduce health
  or kill him. The shield is pre-damage, not delayed regeneration. A restart/respawn/new pawn must
  retain the shield only for the attached Poseidon. No other bot/human should become immune.
- Test Odysseus damage against an enemy under identical weapon/range/armor conditions with/without the
  profile multiplier; log the callback path and expected 1.08 scale before armor/engine rounding.
  Friendly fire, self damage and unbound humans must not receive that outgoing boost. Menelaus and
  Telemachus must remain normally killable. Do not infer the scale from one rounded health number.
- Verify per-bot native Skill/reaction/aim/aggression/teamwork values were installed, not merely JSON
  metadata. Odyssey bots all inheriting identical pro defaults indicates a missing VPK update.
- Check T and CT buying, affordable force/full plans and the `m4a1_silencer` alias. No free-money cvars.
  Observe native utility use, burst spacing, crouch, extra travel jumps and quiet approach decisions;
  the native AI may also act independently. These are starting targets, not measured exact shares.
- Calibrate difficulty with the same player/opponent/map conditions and multiple rounds. The required
  order is easy Telemachus <medium Menelaus <superhuman Odysseus <damage-immune Poseidon. Skill numbers
  alone do not prove that order. Keep native-global difficulty fixed and change only the relevant
  authored profile/entry when tuning. Preserve character contrast and record changes/reasons.
- The voice/trash-talk key must match the actual clone_id for all four, including `telemachus` spelling.
  The Odyssey UI already uses these IDs; its placeholder Challenge/Play flow may still need wiring to
  the existing match-creation endpoint in your/frontend owner's work. No frontend flow was changed here.
- Compare a normal donk/broky clone after loading/unloading the new plugin: no immunity/boost or native
  setting changes should leak. Test an Odyssey bot alongside a recorded-route pro clone.
- Do not wait indefinitely for Poseidon to die: use an explicit duration/stop condition for his survival
  challenge. Damage immunity does not prevent entity removal/admin slay/map cleanup or override bomb
  objective scoring. Do not add respawns that fight round cleanup.

Use native chat recording/GOTV only through the established supported path; never send `record` over
netcon. No server run, VPK replacement or voice call has been performed by Arjun's agent for this task.
Record actual CS2 findings, installed hashes, failures and any calibrated settings in SPEC.md, then push.

## Prompt to paste

Read `handoffs/tom-odyssey-bots.md`, AGENTS.md and `clones/ODYSSEY.md`. Integrate the four authored
Odyssey bots with my existing voices/trash talk and match-start flow. Their IDs are poseidon, odysseus,
menelaus and telemachus. Preserve existing pro clones and my other work. Install the updated director
and native entries through the established workflow when I authorize touching my game, then run the
private acceptance checklist. Do not claim neural training or calibrated pro skill. Verify Poseidon's
pre-damage immunity and Odysseus's 8% enemy damage edge without affecting humans or other clones. Record
evidence and remaining gaps in SPEC.md. Delete only this consumed temporary handoff after reporting.
