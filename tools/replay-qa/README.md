# Independent mock replay QA

This tests the existing match service and demo pages. It does not change their implementation.
It starts from the repository's FastAPI/TestClient/pytest facilities and uses Playwright
(Apache-2.0) for real Chromium interaction. There is no second viewer or game integration.

## Reproduce

From the repository root, synchronize and test the service:

```sh
cd match-service
uv sync --group dev
uv run python -m pytest -q
uv run python -m pytest ../tools/replay-qa/test_edges.py -q
```

The edge suite has strict `xfail` cases for confirmed bugs: an unexpected pass fails the suite
so an owner can remove the marker after fixing the implementation. `--runxfail` exposes every
underlying failure. Temporary synthetic route fixtures never alter committed clone data.
The real-route check reads all 159 files, including coordinates, time sampling and side metadata.

In another terminal, from `match-service/`, start only this local mock:

```sh
MATCH_BACKEND=mock CLONES_DIR="$(pwd)/../clones" \
TRACE_DIR="$(pwd)/../data/replay-qa/traces" \
MOCK_START_SECONDS=0.4 MOCK_WARMUP_SECONDS=0.4 MOCK_ROUND_SECONDS=0.5 \
uv run uvicorn match_service.main:app --host 127.0.0.1 --port 8011
```

From the repository root, install the isolated browser runtime and run:

```sh
npm install --prefix data/replay-qa/runtime playwright@1.49.1 --no-audit --no-fund
node data/replay-qa/runtime/node_modules/playwright/cli.js install chromium
node tools/replay-qa/browser.cjs
```

The runner refuses a non-mock `/health`. It uses only `127.0.0.1:8011`, creates disposable
matches without callbacks, and writes screenshots and structured results under ignored
`data/replay-qa/browser/`. It exits 1 when expected behavior fails; this is a bug report,
not a green claim about the product. `PLAYWRIGHT_MODULE` can name another Playwright installation;
`QA_OUT` overrides the artifact directory. Closing its browser resets viewport changes.

Allow a few minutes: four full matches finish naturally, then UI/state/edge checks run.
No game, credentials, GPU, model checkpoint or raw demo is required. Stop only this mock's
uvicorn process when finished. Existing matches are in memory; the runner synthesizes an empty
match list for the empty-start case so it can be rerun against the same mock.

See [REPORT.md](REPORT.md) for confirmed findings, source locations and proposed owner fixes.
Do not interpret expected failures or mock traces as successful CS2 verification.
