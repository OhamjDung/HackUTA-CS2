"""Mock match service.

Implements the Server API from the Interface specs doc, but fakes the CS2 server:
a match steps through starting -> ready -> live -> ended on timers, with random
round results. Swap the simulator for real server control later; the endpoints stay.
"""

import asyncio
import json
import logging
import os
import random
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    ROUNDS_TO_WIN,
    TEAM_SIZE,
    Clone,
    Event,
    Match,
    MatchCreate,
    MatchPlayer,
    Server,
)

log = logging.getLogger("match_service")

DEFAULT_CLONES_DIR = Path(__file__).resolve().parent.parent / "sample_clones"


@dataclass
class Settings:
    start_seconds: float = 3.0
    warmup_seconds: float = 5.0
    round_seconds: float = 3.0
    server_ip: str = "127.0.0.1"
    base_port: int = 27015
    public_url: str = "http://localhost:8000"
    clones_dir: Path = DEFAULT_CLONES_DIR

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ
        return cls(
            start_seconds=float(env.get("MOCK_START_SECONDS", cls.start_seconds)),
            warmup_seconds=float(env.get("MOCK_WARMUP_SECONDS", cls.warmup_seconds)),
            round_seconds=float(env.get("MOCK_ROUND_SECONDS", cls.round_seconds)),
            server_ip=env.get("MOCK_SERVER_IP", cls.server_ip),
            base_port=int(env.get("MOCK_BASE_PORT", cls.base_port)),
            public_url=env.get("MOCK_PUBLIC_URL", cls.public_url).rstrip("/"),
            clones_dir=Path(env.get("CLONES_DIR", DEFAULT_CLONES_DIR)),
        )


@dataclass
class MatchRecord:
    match: Match
    callback_url: str | None
    mock_fail: bool
    events: list[Event] = field(default_factory=list)
    task: asyncio.Task | None = None


def load_clones(clones_dir: Path) -> dict[str, Clone]:
    """Read clone profiles (<clone_id>.json, the format in the specs doc, section 1)."""
    clones: dict[str, Clone] = {}
    for path in sorted(clones_dir.glob("*.json")):
        data = json.loads(path.read_text())
        clone = Clone(
            clone_id=data["clone_id"],
            display_name=data["display_name"],
            source=data["source"],
        )
        clones[clone.clone_id] = clone
    return clones


def now() -> datetime:
    return datetime.now(timezone.utc)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    matches: dict[str, MatchRecord] = {}
    used_ports: set[int] = set()
    http: dict[str, httpx.AsyncClient] = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        http["client"] = httpx.AsyncClient(timeout=5.0)
        yield
        for record in matches.values():
            if record.task and not record.task.done():
                record.task.cancel()
        await http["client"].aclose()

    app = FastAPI(
        title="Match service (mock)",
        version="0.1.0",
        description="Server API from the Interface specs doc, with a simulated CS2 server.",
        lifespan=lifespan,
    )
    # The UI and lobby run on other origins during the hackathon.
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    def clones() -> dict[str, Clone]:
        # Re-read on each call so new profiles from AR show up without a restart.
        return load_clones(settings.clones_dir)

    async def emit(record: MatchRecord, event: str, data: dict) -> None:
        ev = Event(match_id=record.match.match_id, event=event, data=data, sent_at=now())
        record.events.append(ev)
        if not record.callback_url:
            return
        try:
            await http["client"].post(record.callback_url, json=ev.model_dump(mode="json"))
        except httpx.HTTPError as exc:
            log.warning("callback to %s failed: %s", record.callback_url, exc)

    def free_port() -> int:
        port = settings.base_port
        while port in used_ports:
            port += 1
        used_ports.add(port)
        return port

    def release(match: Match) -> None:
        if match.server:
            used_ports.discard(match.server.port)

    async def simulate(record: MatchRecord) -> None:
        m = record.match
        await asyncio.sleep(settings.start_seconds)
        if record.mock_fail:
            m.status, m.error = "failed", "Mock failure: the server did not start"
            await emit(record, "match.failed", {"error": m.error})
            return

        port = free_port()
        m.server = Server(ip=settings.server_ip, port=port)
        m.join_link = f"steam://connect/{settings.server_ip}:{port}"
        m.status = "ready"
        await emit(record, "match.ready", {"server": m.server.model_dump(), "join_link": m.join_link})

        await asyncio.sleep(settings.warmup_seconds)
        m.status = "live"
        await emit(record, "match.live", {})

        rng = random.Random(m.match_id)
        to_win = ROUNDS_TO_WIN[m.mode]
        while max(m.score.CT, m.score.T) < to_win:
            await asyncio.sleep(settings.round_seconds)
            winner = rng.choice(["CT", "T"])
            setattr(m.score, winner, getattr(m.score, winner) + 1)
            m.round += 1
            await emit(record, "round.ended", {"round": m.round, "winner": winner, "score": m.score.model_dump()})

        m.status = "ended"
        m.demo_url = f"{settings.public_url}/demos/{m.match_id}.dem"
        release(m)
        winner = "CT" if m.score.CT > m.score.T else "T"
        await emit(record, "match.ended", {"reason": "finished", "winner": winner,
                                           "score": m.score.model_dump(), "demo_url": m.demo_url})

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
        record.task = asyncio.create_task(simulate(record))
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
        if record.task:
            record.task.cancel()
        m.status = "ended"
        release(m)
        await emit(record, "match.ended", {"reason": "stopped", "score": m.score.model_dump(), "demo_url": None})
        return {"status": m.status}

    # Mock only: lets callers see what was sent to their callback_url without running a receiver.
    @app.get("/matches/{match_id}/events", response_model=list[Event])
    async def list_events(match_id: str):
        return get_record(match_id).events

    return app


app = create_app()
