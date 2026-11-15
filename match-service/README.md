# Match service (mock)

The Server API from the team's Interface specs doc (section 2), with the CS2 server faked.
Build the lobby (Tom) and the match UI (Nikesh) against this now; when the real server is
ready, only the inside of this service changes. The endpoints and JSON stay the same.

What's fake: no CS2 server starts. A match steps through `starting` → `ready` → `live` → `ended`
on timers, round winners are random, the join link points at `127.0.0.1`, and `demo_url` doesn't
serve a file. Matches live in memory and vanish on restart.

## Run it

Needs [uv](https://docs.astral.sh/uv/) (`brew install uv`).

```bash
cd match-service
uv sync
uv run uvicorn match_service.main:app --port 8000 --reload
```

Interactive docs: http://localhost:8000/docs

## Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /clones` | Playable clones, read from `sample_clones/*.json` |
| `POST /matches` | Create a match; returns `{match_id, status: "starting"}` (201) |
| `GET /matches/{id}` | Status, server, `join_link`, score, players, `demo_url` |
| `POST /matches/{id}/stop` | End early; 409 if already ended or failed |
| `GET /matches/{id}/events` | **Mock only:** every event sent so far, for testing without a webhook receiver |

Example:

```bash
curl -X POST localhost:8000/matches -H 'content-type: application/json' -d '{
  "map": "de_mirage",
  "mode": "wingman",
  "players": [{"steam_id": "76561198000000001", "team": "CT"}],
  "clones": [{"clone_id": "ash_v1", "team": "CT"}, {"clone_id": "pro_awper_v1", "team": "T"}],
  "callback_url": "http://localhost:3000/hooks/match"
}'
```

Rules: `mode` is `competitive` (5 per team, first to 13) or `wingman` (2 per team, first to 9).
Each team needs at least one player or clone. `steam_id` must be a 17-digit Steam ID.
Bad requests get a 422 whose `detail` lists every problem.

## Events

If `callback_url` is set, the service POSTs `{match_id, event, data, sent_at}` to it:

| Event | `data` |
| --- | --- |
| `match.ready` | `server`, `join_link`: show the Join button |
| `match.live` | none |
| `round.ended` | `round`, `winner`, `score` |
| `match.ended` | `reason` (`finished` or `stopped`), `winner`, `score`, `demo_url` |
| `match.failed` | `error` |

Failed callbacks are logged and not retried.

## Mock knobs

| Setting | Default | What it does |
| --- | --- | --- |
| `"mock_fail": true` in the POST body | `false` | Match goes to `failed`, to test your error path |
| `MOCK_START_SECONDS` | 3 | Time in `starting` |
| `MOCK_WARMUP_SECONDS` | 5 | Time in `ready` before `live` |
| `MOCK_ROUND_SECONDS` | 3 | Time per round |
| `MOCK_SERVER_IP`, `MOCK_BASE_PORT` | `127.0.0.1`, 27015 | What goes in `server` and `join_link` |
| `MOCK_PUBLIC_URL` | `http://localhost:8000` | Base of `demo_url` |
| `CLONES_DIR` | `sample_clones/` | Where clone profiles are read from |

## Tests

```bash
uv run pytest
```
