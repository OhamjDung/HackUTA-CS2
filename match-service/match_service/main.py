"""Match service.

Implements the Server API (README.md). The endpoints are the same whatever runs the match:
- MATCH_BACKEND=mock (default): no game; matches are simulated on timers.
- MATCH_BACKEND=cs2: a real CS2 with CS2-Bot-Improver, controlled through its console, with events
  from CS2's Game State Integration. See backends/cs2.py.
"""

import logging
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .backends.cs2 import Cs2Backend
from .backends.mock import MockBackend
from .console import ConsoleChannel, NetconChannel, PluginChannel, RconChannel
from .core import MatchRecord, Settings, load_clones, now
from .models import TEAM_SIZE, Clone, Event, Match, MatchCreate, MatchPlayer

log = logging.getLogger("match_service")


def make_channel(settings: Settings) -> ConsoleChannel:
    host, port, password = settings.cs2_console_host, settings.console_port(), settings.cs2_console_password
    if settings.cs2_console == "netcon":
        return NetconChannel(host, port)
    if settings.cs2_console == "rcon":
        return RconChannel(host, port, password)
    if settings.cs2_console == "plugin":
        return PluginChannel(host, port, password)
    raise ValueError(f"Unknown CS2_CONSOLE {settings.cs2_console!r}; use 'netcon', 'rcon' or 'plugin'")


def create_app(settings: Settings | None = None, channel: ConsoleChannel | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    matches: dict[str, MatchRecord] = {}
    http: dict[str, httpx.AsyncClient] = {}

    async def emit(record: MatchRecord, event: str, data: dict) -> None:
        ev = Event(match_id=record.match.match_id, event=event, data=data, sent_at=now())
        record.events.append(ev)
        if not record.callback_url:
            return
        try:
            await http["client"].post(record.callback_url, json=ev.model_dump(mode="json"))
        except httpx.HTTPError as exc:
            log.warning("callback to %s failed: %s", record.callback_url, exc)

    if settings.backend == "mock":
        backend = MockBackend(settings, emit)
    elif settings.backend == "cs2":
        channel = channel or make_channel(settings)
        backend = Cs2Backend(settings, emit, channel)
    else:
        raise ValueError(f"Unknown MATCH_BACKEND {settings.backend!r}; use 'mock' or 'cs2'")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        http["client"] = httpx.AsyncClient(timeout=5.0)
        yield
        for record in matches.values():
            if record.task and not record.task.done():
                record.task.cancel()
        await http["client"].aclose()

    app = FastAPI(
        title=f"Match service ({backend.name})",
        version="0.2.0",
        description="Server API from the Interface specs doc. Backend: " + backend.name,
        lifespan=lifespan,
    )
    # The UI and lobby run on other origins during the hackathon.
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.state.backend = backend

    def clones() -> dict[str, Clone]:
        # Re-read on each call so new profiles show up without a restart.
        return load_clones(settings.clones_dir)

    def get_record(match_id: str) -> MatchRecord:
        record = matches.get(match_id)
        if not record:
            raise HTTPException(404, f"No match with id {match_id}")
        return record

    @app.get("/clones", response_model=list[Clone])
    async def list_clones():
        return list(clones().values())

    @app.post("/matches", status_code=201)
    async def create_match(body: MatchCreate):
        if backend.busy():
            raise HTTPException(409, "CS2 is already running a match. Stop it first.")
        available = clones()
        errors: list[str] = []

        unknown = [c.clone_id for c in body.clones if c.clone_id not in available]
        if unknown:
            errors.append(f"Unknown clone_id: {', '.join(unknown)}")
        steam_ids = [p.steam_id for p in body.players]
        if len(steam_ids) != len(set(steam_ids)):
            errors.append("A steam_id appears more than once")
        clone_ids = [c.clone_id for c in body.clones]
        if len(clone_ids) != len(set(clone_ids)):
            errors.append("A clone_id appears more than once")

        size = TEAM_SIZE[body.mode]
        for team in ("CT", "T"):
            count = sum(p.team == team for p in body.players) + sum(c.team == team for c in body.clones)
            if count > size:
                errors.append(f"Team {team} has {count} players; {body.mode} allows {size}")
            if count == 0:
                errors.append(f"Team {team} is empty")
        errors += backend.validate(body, available, list(matches.values()))
        if errors:
            raise HTTPException(422, errors)

        players = [MatchPlayer(team=p.team, is_clone=False, steam_id=p.steam_id, display_name=p.steam_id)
                   for p in body.players]
        players += [MatchPlayer(team=c.team, is_clone=True, clone_id=c.clone_id,
                                display_name=available[c.clone_id].display_name) for c in body.clones]

        match = Match(match_id=uuid.uuid4().hex[:12], status="starting", map=body.map, mode=body.mode,
                      players=players, created_at=now())
        record = MatchRecord(match=match, callback_url=str(body.callback_url) if body.callback_url else None,
                             mock_fail=body.mock_fail)
        matches[match.match_id] = record
        backend.start(record, available)
        return {"match_id": match.match_id, "status": match.status}

    @app.get("/matches/{match_id}", response_model=Match)
    async def get_match(match_id: str):
        return get_record(match_id).match

    @app.post("/matches/{match_id}/stop")
    async def stop_match(match_id: str):
        record = get_record(match_id)
        m = record.match
        if m.status in ("ended", "failed"):
            raise HTTPException(409, f"Match is already {m.status}")
        await backend.stop(record)
        m.status = "ended"
        await emit(record, "match.ended", {"reason": "stopped", "score": m.score.model_dump(), "demo_url": None})
        return {"status": m.status}

    # Not in the spec: lets callers see what was sent to their callback_url without running a receiver.
    @app.get("/matches/{match_id}/events", response_model=list[Event])
    async def list_events(match_id: str):
        return get_record(match_id).events

    @app.get("/demos/{match_id}.dem")
    async def get_demo(match_id: str):
        get_record(match_id)
        path = backend.demo_path(match_id)
        if not path or not path.is_file():
            raise HTTPException(404, "No recording for this match" +
                                ("" if path else " (this backend does not record, or CS2_DEMO_DIR is not set)"))
        return FileResponse(path, media_type="application/octet-stream", filename=f"{match_id}.dem")

    # CS2's Game State Integration posts here (see gsi/ for the config file). cs2 backend only.
    @app.post("/gsi", include_in_schema=backend.name == "cs2")
    async def game_state(request: Request):
        if backend.name != "cs2":
            raise HTTPException(404, "Game state is only used by the cs2 backend")
        payload = await request.json()
        if (payload.get("auth") or {}).get("token") != settings.gsi_token:
            raise HTTPException(401, "Wrong or missing GSI token")
        await backend.handle_gsi(payload)
        return {"ok": True}

    # Which backend runs, and for cs2: can we reach the console, and when did game state last arrive.
    @app.get("/health")
    async def health():
        return await backend.health()

    return app


app = create_app()
