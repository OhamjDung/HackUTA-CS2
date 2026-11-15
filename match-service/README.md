# Match service

The Server API from the team's Interface specs doc (section 2). The endpoints and JSON are the same
whichever backend runs the match:

- **`mock`** (default): no game. A match steps through `starting` → `ready` → `live` → `ended` on
  timers, round winners are random, the join link points at `127.0.0.1`, and there is no recording.
- **`cs2`**: a real CS2 with CS2-Bot-Improver. See [Running with real CS2](#running-with-real-cs2).
  **Not run against a real game yet.**

Matches live in memory and vanish on restart.

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
| `GET /matches/{id}/events` | Every event sent so far, for testing without a webhook receiver (not in the spec) |
| `GET /demos/{id}.dem` | The match recording (cs2 backend, once the match has ended) |
| `GET /health` | Which backend runs; for cs2, whether the console answers and when game state last arrived |
| `POST /gsi` | cs2 backend only: where CS2 sends game state |

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

## Running with real CS2

**Status: written and tested against a fake console only. Nobody has run it with CS2 yet.**

Until the CloneDirector plugin exists, each clone is played by its `stand_in_bot`, a built-in
CS2-Bot-Improver bot. `donk_v1` and `broky_v1` use the bots named `donk` and `broky`, which
CS2-Bot-Improver already ships. A clone without `stand_in_bot` is rejected in this mode.

How it controls the game:
- **Commands out** through CS2's network console: start CS2 with `-netconport 2121`. Not confirmed
  that CS2 still supports this. If it doesn't, add another channel in `console.py` (RCON, or a
  small plugin); nothing else changes.
- **Events in** through CS2's Game State Integration: CS2 POSTs the map, phase and scores to `/gsi`.

What a match does: switch to the map and mode, wait for CS2 to report the map, set team names
(`Alpha` starts CT, `Bravo` starts T, so scores follow teams across halftime), kick bots, add each
stand-in with `bot_add_ct "<name>"` / `bot_add_t "<name>"`, put the person at the PC on their team
(or in spectator for bot vs bot), mark the match `ready`, then after the warmup start recording and
end warmup. Scores and the end of the match come from game state. One match at a time; at most one
human (the person at the CS2 PC).

Setup on the CS2 machine:
1. Copy `gsi/gamestate_integration_matchservice.cfg` into `game/csgo/cfg/` in the CS2 folder.
   Change `token` and, if the service runs on another machine, the address in `uri`.
2. Add `-netconport 2121` to CS2's launch options.
3. Run the service:
   ```bash
   MATCH_BACKEND=cs2 GSI_TOKEN=<token> CS2_DEMO_DIR="<CS2 folder>/game/csgo" \
     uv run uvicorn match_service.main:app --host 0.0.0.0 --port 8000
   ```
4. Open `GET /health`. It says whether the console answers and when game state last arrived.

| Setting | Default | What it does |
| --- | --- | --- |
| `MATCH_BACKEND` | `mock` | `mock` or `cs2` |
| `CS2_CONSOLE_HOST`, `CS2_CONSOLE_PORT` | `127.0.0.1`, 2121 | Where the CS2 console listens |
| `GSI_TOKEN` | `change-me` | Must match `token` in the game state config file |
| `CS2_DEMO_DIR` | not set | Folder where CS2 saves `match_<id>.dem`; served at `demo_url` |
| `CS2_MAP_LOAD_SECONDS` | 90 | How long to wait for CS2 to report the map before failing |
| `WARMUP_SECONDS` | 5 | Time in `ready` before the match goes live |
| `SERVER_IP`, `SERVER_PORT` | `127.0.0.1`, 27015 | What goes in `server` and `join_link` |

Not checked yet: that CS2 accepts `-netconport`, the exact game state CS2 sends on a map change,
where CS2 saves recordings, and that `jointeam` and the team-name commands behave as written.

## Tests

```bash
uv run pytest
```
