# Task 2: independent replay and demo QA without CS2

## Outcome

Test the existing local demo and replay flow against the mock backend. Return a prioritized, reproducible bug report plus a small CPU-only smoke/regression harness where useful. No CS2, GPU, raw demos or model weights are needed. This is a secondary task, not permission to replace the replay implementation.

## Ownership

Ashirwad owns match-service/ and its demo pages; Nikesh owns frontend/. Own tools/replay-qa/ and a small summary under handoffs/ or docs/. Keep screenshots, logs and runtime data under ignored data/replay-qa/ and hand them over separately. Do not edit existing match-service/frontend source or API formats without asking their owner through Arjun. Report proposed fixes with exact locations. Never control Tom's/Arjun's running game, use their credentials, or connect the mock to a real game.

Starting points: match-service/demo/{index,watch,play,replay,proof}.html, common.js, style.css; match_service/replay.py; tests/test_replay.py; README.md and SPEC.md sections 3, 9 and 10. The latest repo already has these pages; do not build another replay viewer.

## Setup

Clone/pull main and create branch friend/replay-qa. Install Python 3.11+ and uv from official sources. At the repository root, enter match-service/:

PowerShell:
```powershell
uv sync --group dev
$env:MATCH_BACKEND='mock'
$env:CLONES_DIR=(Resolve-Path ..\clones).Path
$env:TRACE_DIR=(Join-Path (Resolve-Path ..).Path 'data\replay-qa\traces')
uv run python -m pytest
uv run uvicorn match_service.main:app --host 127.0.0.1 --port 8011
```

Use a second terminal for HTTP checks. Browser: http://127.0.0.1:8011/demo/ . API docs: http://127.0.0.1:8011/docs . Use port 8011 so this cannot accidentally target another local service on 8000. Bind only to loopback. Do not run start-cs2.ps1; the mock server needs no game.

On macOS/Linux use export for the same environment variables and absolute paths for CLONES_DIR/TRACE_DIR. Check the current README if dependencies/settings changed. If uv sync --group dev is not accepted by the current pyproject, inspect its groups and use the documented equivalent rather than changing dependencies blindly.

A basic valid request (send with a JSON-aware HTTP client, or the API docs):
```json
{"map":"de_mirage","mode":"wingman","players":[],"clones":[{"clone_id":"donk_v1","team":"CT"},{"clone_id":"broky_v1","team":"T"}]}
```
POST it to /matches, retain match_id, inspect GET /matches/{id}, /events, /trace, and /compare?round=1&player=<URL-encoded-player-name> when data is available. No callback_url is needed; do not send callbacks to someone else's service. Discover exact available player names/rounds from the trace instead of assuming them. The page may use relative URLs; verify actual requests in browser tools.

## Test matrix

1. Fresh start: all demo pages load, clone selectors populate, and no uncaught JS errors or failed local assets. Test donk and broky, both teams, wingman and competitive modes where supported. Record browser/version, OS and source commit.
2. State transitions: starting, ready, live, ended; stop during starting/live; stop twice; simulated failure (mock_fail when supported). Loading/empty/error states should resolve and explain what happened. Reload or reopen the page while a match is running and after it ends.
3. Replay: recorded-round selection on both sides; real-versus-bot and clone-versus-clone tabs; play/pause, seek to start/end, speed changes, change round/player while paused and playing. Both panels must use the same displayed time. Test unequal path lengths and empty traces. A finished short path should not loop/restart or silently speed up to fit the other.
4. Provenance: mock traces must remain clearly marked simulated. A closest recorded route is selected by similarity and is usually a build recording, not a held-out identity test. No mock score or copied route may be presented as learned-player accuracy, live CS2 evidence or professional skill. Note misleading labels with screenshots and exact text.
5. Data integrity: verify 8 Hz route sampling, finite coordinates/times, monotonic timestamps, route side correctness, invalid clone/recording IDs, nonexistent matches, missing paths and death/end behavior. Do not describe 2D traces as first-person video. Do not judge the map outline as a true map geometry: it is occupied route cells.
6. Browser behavior: test approximately 1366x768 and a narrow 390px viewport, keyboard-only essential controls, readable labels, no accidental overlay blockers and no runaway repeated requests after leaving/reopening a page. Reset any viewport overrides afterward.
7. Honest limits: GSI allplayers arrives from a spectator in real CS2 and has not yet been verified. Mock success does not verify this, bot playback, recording, plugin loading, real scores or combat.

Where you find a deterministic defect, provide the smallest input and observable expected/actual behavior. For parser/trace cases, write a tiny **synthetic** fixture/regression script in your own tools directory using existing functions, with no raw replay data committed. Do not add tests that merely reimplement the function or depend on wall-clock sleeps unnecessarily. Corrupt/missing-file tests must use copies in a temporary folder; never damage the repo's real clone files.

## Deliverables and acceptance

- A concise report ordered by impact: blocker, major, minor. Each issue has exact reproduction steps/URLs, inputs, expected/actual result, evidence, source location and proposed narrow fix. Separate confirmed failures from suspicions.
- Exact test commands/counts, browser screenshots and HTTP examples; preserve raw screenshots/logs outside Git.
- A runnable smoke harness if it adds coverage beyond the existing tests. Use existing Python test/client facilities or an established browser testing tool; follow AGENTS.md's open-source starting-point rule.
- SPEC row/changelog for your QA work only. Keep implementation owner rows unchanged and do not claim that backend or UI is fixed because your report exists.
- Branch/PR URL and a short message Arjun can forward to Ashirwad. Do not send messages to teammates yourself unless Arjun explicitly instructs you to.

Estimate 1-2 focused hours. This can run while Task 1's raw demos download. If you have time for only one task, prioritize Task 1's independent habit evidence and weapon-role fix.

## Paste this prompt into your coding assistant

You are independently testing Arjun's CS2 clone project on a separate computer without CS2. Repository: https://github.com/OhamjDung/HackUTA-CS2.git . Read 00-START-HERE.md, this Task 2 document, current AGENTS.md, SPEC.md and match-service/README.md. Pull current main and create branch friend/replay-qa. Run the existing mock backend locally on 127.0.0.1:8011 with the real repository clone files, never start CS2 or a bot installer. Follow the test matrix above across watch/play/replay/proof pages, including state transitions, empty/error paths, synchronized replay controls and honest simulated-data labels. Ashirwad owns match-service/ and Nikesh owns frontend/: do not replace their pages or modify their implementations/API without owner coordination through Arjun. Own tools/replay-qa/ and a concise report. Use existing tests/functions and established tools; add only meaningful synthetic regression cases. Capture screenshots and exact reproduction inputs, rank issues by impact, and clearly distinguish confirmed failures from untested real-game behavior. Keep runtime traces/screenshots/datasets out of Git and send them separately. Pull before editing only your SPEC row/relevant section/changelog, keep commits short, push your branch and return its URL plus the report and verification commands. Do not merge to main or message other teammates without explicit instruction.
