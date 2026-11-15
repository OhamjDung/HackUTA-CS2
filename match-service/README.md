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
- **Commands out** through one of three channels (`CS2_CONSOLE`). Try them in this order:
  1. `netcon` (default): CS2's network console. Start CS2 with `-netconport 2121`. **Works:** Tom
     ran it in Bot Mode on Windows on 2026-11-14.
  2. `rcon`: Valve's remote console protocol. Start CS2 with `-usercon` and run
     `rcon_password <password>` in its console. Not confirmed that CS2 answers RCON in Bot Mode.
  3. `plugin`: the MatchBridge plugin in `plugin/MatchBridge/`, for CounterStrikeSharp (which
     CS2-Bot-Improver installs). It runs each command inside the game. It must be built once with
     the .NET SDK (8 or newer; SDK 10 also builds CloneDirector).

  With `rcon` and `plugin` the commands run on the server side, where `jointeam` doesn't exist.
  With `plugin`, `jointeam` becomes
  `matchbridge_jointeam`, which moves the person at the PC. With `rcon` nothing can move them, so
  they pick a team themselves.
- **Events in** through CS2's Game State Integration: CS2 POSTs the map, phase and scores to `/gsi`.

Console safety: every channel refuses a command containing a newline, `\r` or `;` before it
connects, because those would start a second command. Clone profiles whose `stand_in_bot` is not a
plain name (letters, digits, `_`, `.`, `-`; at most 32) are skipped with a warning when profiles load.

What a match does: switch to the map and mode, wait for CS2 to report the map, set team names
(`Alpha` starts CT, `Bravo` starts T, so scores follow teams across halftime), kick bots, add each
stand-in with `bot_add_ct "<name>"` / `bot_add_t "<name>"`, put the person at the PC on their team
(or in spectator for bot vs bot), mark the match `ready`, then after the warmup send
`mp_warmup_end` and `mp_restartgame 1` (and `tv_record` with `CS2_RECORD=tv`). Game state is
ignored until 2 s after the
restart (`CS2_RESTART_SECONDS`), because Bot Mode can report `live` before the match starts. Scores
and the end of the match come from game state. One match at a time; at most one
human (the person at the CS2 PC).

### Setup on the CS2 machine (Windows)

`start-cs2.ps1` does the setup and starts the service. It needs [uv](https://docs.astral.sh/uv/)
(`winget install --id=astral-sh.uv -e`). From the `match-service` folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-cs2.ps1                  # netcon
powershell -ExecutionPolicy Bypass -File .\start-cs2.ps1 -Console rcon    # RCON
powershell -ExecutionPolicy Bypass -File .\start-cs2.ps1 -Console plugin  # MatchBridge
powershell -ExecutionPolicy Bypass -File .\start-cs2.ps1 -Record tv       # try GOTV recording
```

It finds the CS2 folder through Steam (or pass `-Cs2Dir "<folder>"`), installs the game state
config into `game\csgo\cfg` with a random token, prints what CS2 needs for the chosen channel, and
with `-Console plugin` builds MatchBridge (if `dotnet` is installed) and copies it into
`game\csgo\addons\counterstrikesharp\plugins\MatchBridge\` with its `matchbridge.json`. The RCON
password and plugin token default to the game state token; set them with `-ConsolePassword`.
Restart CS2 after the first run so it reads the new files. The service listens on `127.0.0.1`, so
only the CS2 PC can reach it. Add `-Listen 0.0.0.0` only when another machine (the lobby on a
teammate's laptop) needs it: then anyone on the same network can create and stop matches. Then open `GET /health`: it says whether
the console answers and when game state last arrived. **The script has not been run on Windows
yet.**

By hand, on any system:
1. Copy `gsi/gamestate_integration_matchservice.cfg` into `game/csgo/cfg/` in the CS2 folder.
   Change `token` and, if the service runs on another machine, the address in `uri`.
2. Set up the channel as listed above.
3. Run the service:
   ```bash
   MATCH_BACKEND=cs2 CS2_CONSOLE=netcon GSI_TOKEN=<token> CS2_DEMO_DIR="<CS2 folder>/game/csgo" \
     uv run uvicorn match_service.main:app --host 0.0.0.0 --port 8000
   ```

To build MatchBridge by hand: install the .NET SDK (8 or newer), run `dotnet build plugin/MatchBridge -c Release`,
then copy `plugin/MatchBridge/bin/Release/net8.0/MatchBridge.dll` and a `matchbridge.json` (see
`matchbridge.example.json`; set your own token) into
`game/csgo/addons/counterstrikesharp/plugins/MatchBridge/`. It listens on 127.0.0.1 only.

| Setting | Default | What it does |
| --- | --- | --- |
| `MATCH_BACKEND` | `mock` | `mock` or `cs2` |
| `CS2_CONSOLE` | `netcon` | `netcon`, `rcon` or `plugin` |
| `CS2_CONSOLE_HOST` | `127.0.0.1` | Where the channel listens |
| `CS2_CONSOLE_PORT` | 2121 / 27015 / 27100 | Default depends on `CS2_CONSOLE` |
| `CS2_CONSOLE_PASSWORD` | not set | RCON password, or the MatchBridge token |
| `GSI_TOKEN` | `change-me` | Must match `token` in the game state config file |
| `CS2_RECORD` | `off` | `off` or `tv` (GOTV; not tried in CS2) |
| `CS2_DEMO_DIR` | not set | Folder where CS2 saves `match_<id>.dem`; served at `demo_url` |
| `CS2_MAP_LOAD_SECONDS` | 90 | How long to wait for CS2 to report the map before failing |
| `CS2_RESTART_SECONDS` | 2 | How long to ignore game state after `mp_restartgame 1` |
| `WARMUP_SECONDS` | 5 | Time in `ready` before the match goes live |
| `SERVER_IP`, `SERVER_PORT` | `127.0.0.1`, 27015 | What goes in `server` and `join_link` |

**Recording (`CS2_RECORD`).** `off` by default: nothing is recorded and `demo_url` is `null`.
`tv` records with GOTV: `tv_enable 1` before the map, `tv_record match_<id>` at the start,
`tv_stoprecord` at the end; not yet tried in CS2. The player's own `record` command is never sent:
over netcon it froze CS2's client clock about 7 s after the map loaded (game state stuck at round 0,
bots frozen on screen), and sent by hand it crashed CS2 once.

Ran in CS2 (Tom, Bot Mode, 2026-11-14): netcon commands, game state arriving at `/health`, and a
wingman bot-vs-bot match that loaded the map, added `donk` and `broky`, set the team names and went
`ready` then `live`. **Broken in that run:** the score stayed 0-0 and game state stayed at round 0
in freeze time while CS2 reset rounds about every 30 s; `status` counted the two bots as humans; and
`record` was accepted but no `.dem` file appeared. Cause found by Tom: the `record` command (see
above). Without it, donk and broky move and fight. `start-cs2.ps1` ran as written, and the restart
fix gave `ready` then `live` in the right order. Not yet seen: scores counting through `/gsi` with
recording off.

Not checked yet: that it answers RCON in Bot Mode; that MatchBridge
builds and loads (it has never been compiled), and that running commands through `Server.NextFrame`
and moving the player with `ChangeTeam` work; the exact game state CS2 sends on a map change; that
`tv_record` writes a `.dem` file in Bot Mode, and where; and that `jointeam` and the team-name commands
behave as written. The RCON and plugin channels are tested against fake servers only.

## Tests

```bash
uv run pytest
```

On Windows PCs where Application Control blocks `uv run pytest`, use `uv run python -m pytest`.
