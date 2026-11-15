"""Match service.

Implements the Server API (README.md). The endpoints are the same whatever runs the match:
- MATCH_BACKEND=mock (default): no game; matches are simulated on timers.
- MATCH_BACKEND=cs2: a real CS2 with CS2-Bot-Improver, controlled through its console, with events
  from CS2's Game State Integration. See backends/cs2.py.
"""

import json
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .backends.cs2 import Cs2Backend
from .backends.mock import MockBackend
from .console import ConsoleChannel, NetconChannel, PluginChannel, RconChannel
from .core import MatchRecord, Settings, load_clones, now
from .drivers import describe
from .generated import ReviewInvalid, ReviewLibrary, ReviewNotFound
from .coach import Coach
from .puzzle_routes import add_puzzle_routes
from .puzzles import ID_RE, NotFound, validate_puzzle
from .models import TEAM_SIZE, Clone, CloneInfo, Event, Match, MatchCreate, MatchPlayer
from .replay import RouteLibrary
from .scoring import ScoringUnavailable, score_player

DEMO_DIR = Path(__file__).resolve().parent.parent / "demo"
GENERATED_NOTE = ("Development examples from a model whose held-out identity test failed (SPEC.md 8.6). "
                  "Not the player's style, not collision-approved, and not used in the game.")

log = logging.getLogger("match_service")


def setup_log_file(path: Path) -> None:
    """Send this service's log lines (and httpx's request lines: URL and status, never keys) to the
    console and to `path`, at INFO. Uvicorn's own access log is unchanged. Safe to call twice."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    for name in ("match_service", "httpx"):
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        if any(getattr(h, "_match_log", False) for h in logger.handlers):
            continue
        for handler in (logging.FileHandler(path, encoding="utf-8"), logging.StreamHandler()):
            handler.setFormatter(fmt)
            handler._match_log = True
            logger.addHandler(handler)
        logger.propagate = False


def make_channel(settings: Settings) -> ConsoleChannel:
    host, port, password = settings.cs2_console_host, settings.console_port(), settings.cs2_console_password
    if settings.cs2_console == "netcon":
        return NetconChannel(host, port)
    if settings.cs2_console == "rcon":
        return RconChannel(host, port, password)
    if settings.cs2_console == "plugin":
        return PluginChannel(host, port, password)
    raise ValueError(f"Unknown CS2_CONSOLE {settings.cs2_console!r}; use 'netcon', 'rcon' or 'plugin'")


def make_clone_channel(settings: Settings) -> ConsoleChannel | None:
    """The MatchBridge channel for CloneDirector commands, when it isn't the main channel."""
    if settings.cs2_bots != "clone" or settings.cs2_console == "plugin":
        return None
    token = settings.cs2_plugin_token or settings.cs2_console_password
    return PluginChannel(settings.cs2_console_host, settings.cs2_plugin_port, token)


def create_app(settings: Settings | None = None, channel: ConsoleChannel | None = None,
               clone_channel: ConsoleChannel | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    if settings.log_file:
        setup_log_file(settings.log_file)
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

    library = RouteLibrary(settings.clone_data_dir)
    reviews = ReviewLibrary(settings.review_dir)
    if settings.backend == "mock":
        backend = MockBackend(settings, emit, library)
    elif settings.backend == "cs2":
        channel = channel or make_channel(settings)
        backend = Cs2Backend(settings, emit, channel, clone_channel or make_clone_channel(settings))
    else:
        raise ValueError(f"Unknown MATCH_BACKEND {settings.backend!r}; use 'mock' or 'cs2'")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        http["client"] = httpx.AsyncClient(timeout=5.0)
        coach.start()
        yield
        await coach.stop()
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

    @app.get("/clones", response_model=list[CloneInfo])
    async def list_clones():
        # The profile plus how it would be played now (drivers.py). Existing fields are unchanged.
        return [describe(c, settings) for c in clones().values()]

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

    # --- Replay data (not in the Interface specs doc; used by the demo pages in demo/) -----------

    @app.get("/matches")
    async def list_matches():
        """Every match since the service started, newest first."""
        out = [{"match_id": r.match.match_id, "status": r.match.status, "map": r.match.map,
                "mode": r.match.mode, "score": r.match.score.model_dump(), "round": r.match.round,
                "created_at": r.match.created_at,
                "players": [p.display_name + ("" if p.is_clone else " (human)") for p in r.match.players],
                "has_trace": bool(r.trace and r.trace.rounds)} for r in matches.values()]
        return sorted(out, key=lambda m: m["created_at"], reverse=True)

    def trace_json(match_id: str) -> dict:
        record = matches.get(match_id)
        if record and record.trace:
            return record.trace.to_json()
        if settings.trace_dir and match_id.isalnum():
            saved = settings.trace_dir / f"{match_id}.json"
            if saved.is_file():
                return json.loads(saved.read_text())
        raise HTTPException(404, f"No trace for match {match_id}")

    @app.get("/matches/{match_id}/trace")
    async def get_trace(match_id: str):
        """Each player's path per round: [[seconds into the round, x, y], ...]."""
        return trace_json(match_id)

    @app.get("/matches/{match_id}/compare")
    async def compare(match_id: str, round: int, player: str):
        """One bot's round next to the real player's closest recorded round on the same side."""
        trace = trace_json(match_id)
        rnd = next((r for r in trace["rounds"] if r["round"] == round), None)
        bot = next((p for p in (rnd or {}).get("players", []) if p["name"] == player), None)
        if not bot:
            raise HTTPException(404, f"No player {player!r} in round {round}")
        real = library.closest(bot["clone_id"], bot["team"], bot["path"]) if bot["clone_id"] else None
        return {"match_id": match_id, "round": round, "source": trace["source"], "bot": bot, "real": real,
                "note": None if real else "No recorded rounds for this player on this side"}

    @app.get("/matches/{match_id}/score")
    async def score(match_id: str, player: str):
        """How close one clone's rounds in this match are to the real player (SPEC 10.2).

        `player` is the bot's name or clone_id in the trace. The result compares the trace with
        the real player's held-back match; `ceiling` is the real player against himself. A trace
        with `bots: "stand_in"` measures a default bot (the baseline), `"clone"` the clone.
        """
        trace = trace_json(match_id)
        found = next((p for r in trace["rounds"] for p in r["players"]
                      if player in (p["name"], p.get("clone_id"))), None)
        if not found:
            raise HTTPException(404, f"No player {player!r} in match {match_id}")
        profile = library.profile(found["clone_id"]) if found.get("clone_id") else None
        try:
            return score_player(trace, found, profile)
        except ScoringUnavailable as exc:
            raise HTTPException(503, str(exc))

    @app.get("/replay/clones")
    async def replay_clones():
        """Clones that have recorded rounds (the clone pipeline's output)."""
        out = []
        for cid in library.clone_ids():
            prof = library.profile(cid)
            out.append({"clone_id": cid, "display_name": prof.get("display_name"), "rounds": prof.get("rounds"),
                        "routes": len(library.routes(cid))})
        return out

    @app.get("/replay/clones/{clone_id}")
    async def replay_clone(clone_id: str):
        prof = library.profile(clone_id)
        if not prof:
            raise HTTPException(404, f"No clone data for {clone_id}")
        keep = ["clone_id", "display_name", "source", "map", "rounds", "weapons", "aggression", "aim_skill",
                "reaction_ms", "positions", "route_shares", "similarity", "source_games", "model",
                "buy_plan", "quirks", "quirk_controls", "learned", "built_at", "stand_in_bot"]
        return {k: prof.get(k) for k in keep}

    @app.get("/replay/clones/{clone_id}/routes")
    async def replay_routes(clone_id: str):
        if not library.profile(clone_id):
            raise HTTPException(404, f"No clone data for {clone_id}")
        return [{k: v for k, v in r.items() if k != "file"} for r in library.routes(clone_id)]

    @app.get("/replay/clones/{clone_id}/routes/{recording}")
    async def replay_route(clone_id: str, recording: str):
        route = library.route(clone_id, recording)
        if not route:
            raise HTTPException(404, f"No recorded round {recording} for {clone_id}")
        return route

    @app.get("/replay/outline")
    async def replay_outline():
        """Grid cells covered by any recorded route: a rough map shape for drawing."""
        return library.outline()

    @app.get("/replay/generated")
    async def generated_list():
        """The model's offline generated-path review files in REVIEW_DIR, and their cases.

        Development examples only, from a model whose identity test failed (SPEC 8.6). Files that
        are not a dev, undeployed cs2.clone.review.v1 file, or that include a held-out match, are
        listed under `ignored` with the reason.
        """
        return {**reviews.listing(), "identity_test": "failed", "note": GENERATED_NOTE}

    @app.get("/replay/generated/{file}/{case}")
    async def generated_case(file: str, case: int):
        """One case: the real path and the own / other / base generated paths from a shared start."""
        try:
            return {**reviews.case(file, case), "identity_test": "failed", "note": GENERATED_NOTE}
        except ReviewNotFound as exc:
            raise HTTPException(404, str(exc))
        except ReviewInvalid as exc:
            raise HTTPException(422, str(exc))

    app.state.puzzles = add_puzzle_routes(app, settings, backend)  # replay puzzles (puzzle_routes.py)

    # Death coach (coach.py, SPEC.md section 9.7). Chat goes through MatchBridge when the service has it,
    # so `say` runs on the server console; with netcon only, it is said from the player's console.
    async def coach_say(commands: list[str]) -> None:
        await backend.clone_ch.send(commands)

    def coach_match() -> dict | None:
        """The running match's clones and the person's team, so the coach speaks in the right voice."""
        live = [r for r in matches.values() if r.active]
        if not live:
            return None
        players = live[-1].match.players
        human = next((p.team for p in players if not p.is_clone), None)
        return {"human_team": human,
                "clones": [{"clone_id": p.clone_id, "team": p.team} for p in players if p.is_clone]}

    coach = Coach(settings.coach, settings.death_dir, lambda: http["client"],
                  coach_say if backend.name == "cs2" else None, match=coach_match)
    app.state.coach = coach

    def read_puzzle_file(folder: Path, death_id: str) -> dict:
        path = folder / f"{death_id}.json"
        if not ID_RE.match(death_id) or not path.is_file():
            raise HTTPException(404, f"No death {death_id}")
        try:
            return validate_puzzle(json.loads(path.read_text(encoding="utf-8"))).model_dump()
        except (ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(422, f"Death {death_id} is invalid: {exc}")

    @app.get("/coach")
    async def coach_status():
        """Whether the coach is on, which parts have keys, and the last advice it gave."""
        return coach.status()

    @app.post("/coach/deaths/{death_id}")
    async def coach_death(death_id: str):
        """Coach a saved death again (chat and voice), e.g. to try the voice without dying in CS2."""
        return await coach.coach(read_puzzle_file(settings.death_dir, death_id))

    @app.post("/coach/puzzles/{puzzle_id}")
    async def coach_puzzle(puzzle_id: str):
        """Coach the original death of a library puzzle (the seed puzzles work without CS2)."""
        try:
            puzzle = app.state.puzzles.load(puzzle_id)
        except NotFound:
            raise HTTPException(404, f"No puzzle {puzzle_id}")
        except ValueError as exc:
            raise HTTPException(422, f"Puzzle {puzzle_id} is invalid: {exc}")
        return await coach.coach(puzzle.model_dump())

    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse("/demo/")

    if DEMO_DIR.is_dir():
        app.mount("/demo", StaticFiles(directory=DEMO_DIR, html=True), name="demo")

    return app


app = create_app()
