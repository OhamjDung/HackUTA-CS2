# Replay QA report — 14 November 2026

The mock demo is usable on desktop for the normal path. Independent QA found replay failure
handling and stale selection defects, narrow-screen overflow, and several trace edge cases.
**No implementation was changed.** There are no confirmed normal-path blockers. Suggested owner
fixes below have not been applied or tested.

## Evidence and coverage

Ran on macOS Darwin 24.6.0 with headless Chromium **131.0.6778.33**, Playwright **1.49.1**,
Python 3.14.0. Service code was unchanged from `a2caf02`; initial checkout/cleanup base was
`58c5dde`. Browser results record `24fce4d` after merging Arjun's unrelated model export changes.
The subsequent model-only merge does not alter the tested service. Raw evidence is ignored under
`data/replay-qa/` in this task checkout, not committed.

Exact setup and commands are in README.md. Verification commands:

```sh
cd match-service
uv sync --group dev
uv run python -m pytest -q
uv run python -m pytest ../tools/replay-qa/test_edges.py -q
uv run python -m pytest ../tools/replay-qa/test_edges.py --runxfail -q
# From repository root, with the loopback mock running per README:
node tools/replay-qa/browser.cjs
```

- Existing service suite: **47 passed**, one dependency deprecation warning.
- Added edge suite: **3 passed, 8 strict expected failures**; `--runxfail` exposes the eight
  failures. An expected failure is evidence of an unresolved issue, not a passing product check.
- Browser matrix: **31 checks: 22 passed, 9 failed desired-behavior checks**, covering all five pages at 1366×768 and 390×844, both players,
  T/CT, wingman/competitive, all three replay tabs, start/ready/live/end, failure, stopping during
  starting/live, second-stop 409, reload, play/pause/seek/speed, paused/playing selection changes,
  empty/error states, labels, basic keyboard controls, and polling after ending/leaving.
  See `data/replay-qa/browser/results.json` for individual outcomes and screenshot filenames.
- All **159** committed route files have finite coordinates, side-correct metadata and monotonic
  timestamps sampled at **8 Hz**. Unknown match/clone/recording IDs return 404 in checked requests.
- A separate actual-browser probe captured both radar draw calls receiving **5 seconds** from
  one player clock (`selector-and-clock.json`). Short-path interpolation clamps to its final
  point while a longer path advances; it does not loop or normalize the shorter path's duration.
- Simulated badges are visible; closest-round wording is descriptive; proof columns label the
  player-versus-self ceiling and leave clone/baseline results “not measured”. The map is occupied
  route cells, not verified map geometry; the page describes positions rather than video.
- Keyboard Enter starts a play match, Home/End seek the replay, and end/leave polling stopped in
  the observed run. Closing the browser resets viewport overrides.

## Major: confirmed replay/state defects

| ID | Minimal reproduction and observed result | Expected behavior / proposed narrow owner fix | Source and evidence |
|---|---|---|---|
| QA-1 | In a temporary library, list a missing `.json.br`, an empty `Ticks` array, or invalid Brotli; call `closest('sample','T',[[0,0,0],[1,1,1],[2,2,2]])`. Missing file gives `None` then subscripting fails; empty data fails `min()`; corrupt bytes escape the decoder. | Skip unavailable/empty paths and translate corrupt input to an unavailable route with a diagnostic. Ensure compare/outline/mock simulation use the same guarded read. Do not edit real clone files to reproduce. | `match_service/replay.py:54`, `:90`, `:98`, `:111`, `:205`; three strict xfails; `edge-failures.txt`. |
| QA-6 | Open recorded rounds, select donk/broky and immediately change T/CT. Browser requests a recording from the prior selection under the new clone ID: e.g. `No recorded round broky_v1_ct_2392601_r01 for donk_v1`, uncaught. | Snapshot clone/side per request, await route-list refresh, and discard stale responses using a request generation. Loading/404 should visibly resolve. | `demo/replay.html:224`, `:228`, `:233`; browser page-error log and `selector-and-clock.json`. |
| QA-7 | Load a populated real-vs-bot comparison, then select a synthetic empty trace (runner injects only a local empty trace fixture). Round/bot selectors empty but previous bot title and paths remain. | Clear `vs`/`cc` state, title/score/canvases and player controls when no playable round exists; display an empty-state message. | `demo/replay.html:142`, `:155`, `:165`, `:203`; `empty-trace-stale-panels.png`. |
| QA-8 | On real-vs-bot replay, force only `/compare` to return HTTP 500 with `{"detail":"synthetic compare error"}`, then change bot. Browser raises uncaught error and retains previous panel with no visible explanation. | Catch comparison/route-load failures, clear stale output, show error and retry state. No backend error was injected into a real game. | `demo/replay.html:163`, `:166`, `:236`; `compare-error.png`, structured page errors. |
| QA-9 | Start a match from Play vs a bot, then reload the page. Match continues in API but match card disappears; there is no URL or existing-match selector to recover it there. | Save match ID in query/state and attach on load, as watch already does; offer existing-match selection if appropriate. | `demo/play.html:57`, `:67`, `:85`; `play-reload-loses-match.png`. |

## Minor: confirmed limits and synthetic robustness cases

| ID | Reproduction / actual result | Proposed narrow owner fix | Source and evidence |
|---|---|---|---|
| QA-2 | Synthetic GSI `position: "nan, inf, 0"` passes `gsi_players`; `Trace.add(..., NaN, ...)` retains it. Python JSON output can become invalid for browser JSON, and drawing/scoring can fail. No such real-game payload was observed. | Reject nonfinite time/coordinates at ingestion and validate decoded route coordinates. | `match_service/replay.py:134`, `:181`; two strict xfails. |
| QA-3 | Synthetic trace: alive at 0 s, dead at 1 s, alive again at 2 s in the same round. A new path point is appended while `died_at=1` remains. | Once death is recorded, stop that round's path unless an explicit respawn policy exists. | `match_service/replay.py:141`; one strict xfail. |
| QA-4 | Stop a live mock. Match status ends, but its trace retains `live_round`, and configured `TRACE_DIR` gets no saved file. | Finalize trace and persist it in the stop path, alongside natural finish. | `backends/mock.py:38`; one strict xfail. |
| QA-5 | A finished mock announces `demo_url=/demos/<id>.dem`; the mock never records and that URL returns 404. This is a misleading mock contract limitation, not a failure to record a real match. | Prefer existing nullable `demo_url=null`, or explicitly identify the URL as a placeholder. | `backends/mock.py:35`, `:91`; one strict xfail. |
| QA-10 | At 390 px, watch scroll width was 468 px, replay 493 px (depends on match option length), proof 396 px; index/play fit. Replay selector and table content extend outside the card. | Give flexible selects/grid children `min-width:0;max-width:100%`, wrap long metadata and put wide tables in scroll containers. | `demo/style.css:51`, `demo/replay.html:25`, `demo/proof.html:23`; `mobile-watch.png`, `mobile-replay.png`, `mobile-proof.png`; replay screenshot visually inspected. |
| QA-11 | Replay scrubber and speed select accept keyboard input but have neither associated labels nor `aria-label`. | Add explicit accessible names (“Replay time”, “Playback speed”), ideally with time text for the slider. | `demo/common.js:187`; browser DOM check. Screen-reader output was not tested. |
| QA-12 | Proof displays `AIM SKILL (0–1) 1` without explaining that it is an unmeasured maximum base-bot setting. Model section says “needs” model / run swap test although first identity experiment already failed in current SPEC. | Label aim as a setting, state unmeasured player skill, and report the existing failed model test separately from the null playable-model field. Preserve honest simulated/ceiling labels. | `demo/proof.html:44`, `:81`; `proof-desktop.png`; current SPEC 5.3 and 8.6. |

## HTTP example

With the mock running, this uses no callback or outside service:

```sh
curl -s http://127.0.0.1:8011/matches -H 'Content-Type: application/json' \
  -d '{"map":"de_mirage","mode":"wingman","players":[],"clones":[{"clone_id":"donk_v1","team":"CT"},{"clone_id":"broky_v1","team":"T"}]}'
# Retain returned match_id, discover players/rounds rather than assuming them:
curl -s http://127.0.0.1:8011/matches/MATCH_ID/trace
curl -s 'http://127.0.0.1:8011/matches/MATCH_ID/compare?round=1&player=donk'
```

The runner retains exact match IDs, event counts and final scores in its structured output.
The compared real round is selected from build recordings; it is not a held-out identity test.
No mock route or distance establishes player likeness, learned movement or professional skill.

## Not tested

No CS2, plugin, game service, Steam, installer or teammate computer was started or controlled.
GSI spectator `allplayers`, real bot playback, game purchases, true match scores/recordings,
CloneDirector/MatchBridge loading, combat and in-game skill remain unverified by this QA.
No GPU/frontend showcase or neural-model test was run. Only Chromium was used; Safari/Firefox,
real mobile devices, screen readers and prolonged load testing remain untested.

## Forwardable note

Ashirwad: normal mock demos and both replay panels work on desktop; 47 existing tests pass.
Please prioritize missing/corrupt-route guards and replay selection/error/empty-state handling.
The independent harness and screenshots reproduce the issues above. QA did not modify your
implementation or interfaces and does not claim that any proposed fix is verified.
