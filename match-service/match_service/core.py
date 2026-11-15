"""Shared pieces: settings, the in-memory match record, and clone loading."""

import asyncio
import json
import logging
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from .coach import CoachSettings
from .models import Clone, Event, Match

log = logging.getLogger("match_service")

DEFAULT_CLONES_DIR = Path(__file__).resolve().parent.parent / "sample_clones"
# The clone pipeline's output (profiles plus recorded routes), used for replays.
DEFAULT_CLONE_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "clones"
# The model's offline generated-path review files (clone-model/review.py). data/ is git-ignored.
DEFAULT_REVIEW_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "reviews"
# Replay puzzles: committed seed puzzles, the user's saved puzzles, and deaths saved by CloneDirector.
DEFAULT_PUZZLE_SEED_DIR = Path(__file__).resolve().parent.parent / "seed_puzzles"
DEFAULT_PUZZLE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "puzzles"
DEFAULT_DEATH_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "deaths"

# Local secrets for the coach (GEMINI_API_KEY, ELEVENLABS_*). Git-ignored.
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
ROOT_ENV_FILE = ENV_FILE.parent.parent / ".env"  # also read; match-service/.env wins

# emit(record, event_name, data) records an event and sends it to the match's callback_url.
Emit = Callable[["MatchRecord", str, dict], Awaitable[None]]


@dataclass
class Settings:
    # Which game backend runs matches: "mock" (simulated) or "cs2" (a real CS2 on this machine or the LAN).
    backend: str = "mock"
    start_seconds: float = 3.0
    warmup_seconds: float = 5.0
    round_seconds: float = 3.0
    server_ip: str = "127.0.0.1"
    base_port: int = 27015
    public_url: str = "http://localhost:8000"
    clones_dir: Path = DEFAULT_CLONES_DIR
    clone_data_dir: Path = DEFAULT_CLONE_DATA_DIR  # real recorded routes for the replay pages
    trace_dir: Path | None = None  # where finished match traces are saved; None keeps them in memory
    review_dir: Path = DEFAULT_REVIEW_DIR  # generated-path review files for the replay page
    puzzle_seed_dir: Path = DEFAULT_PUZZLE_SEED_DIR
    puzzle_dir: Path = DEFAULT_PUZZLE_DIR
    # Where CloneDirector writes a death (the last 10 seconds) and reads a puzzle to play. Set both to the
    # plugin folder's `deaths` and `puzzles` folders on the CS2 PC; by default they are under data/.
    death_dir: Path = DEFAULT_DEATH_DIR
    game_puzzle_dir: Path | None = None  # None: the service does not copy puzzles to the game
    # cs2 backend only
    cs2_console: str = "netcon"  # netcon, rcon or plugin (see console.py)
    cs2_console_host: str = "127.0.0.1"
    cs2_console_port: int | None = None  # None: 2121 for netcon, 27015 for rcon, 27100 for plugin
    cs2_console_password: str = ""  # RCON password, or the MatchBridge plugin's token
    gsi_token: str = "change-me"
    demo_dir: Path | None = None
    # How to record the match. `off`: no recording, demo_url is null. `tv`: GOTV (tv_record), not
    # tested in CS2. The player's own `record` is not offered: over netcon it froze CS2's client
    # and once crashed it (Tom's run, SPEC.md section 3).
    cs2_record: str = "off"
    map_load_seconds: float = 90.0
    restart_seconds: float = 2.0  # wait after mp_restartgame before trusting game state
    # Who plays a clone. `stand_in`: the built-in bot named in `stand_in_bot`. `clone`: Arjun's
    # CloneDirector plugin (`clone_add`), which takes commands from the server console only, so
    # those commands go through the MatchBridge plugin even when everything else uses netcon.
    cs2_bots: str = "stand_in"
    cs2_plugin_port: int = 27100
    cs2_plugin_token: str = ""  # empty: use cs2_console_password
    clone_join_seconds: float = 20.0  # how long to wait for every clone bot to join
    # How long to wait for every clone bot to show in `status` before removing extra bots (see _settle_bots).
    cs2_settle_seconds: float = 6.0
    # After "Practice in CS2" loads the puzzle's map: wait for the plugins and the player to load
    # before joining a team and sending puzzle_load. Not measured; 5 s is a guess.
    puzzle_settle_seconds: float = 5.0
    # Which route files CloneDirector plays: `recorded` (cut from the player's matches) or `generated`
    # (written by a trained model; needs `model` in the profile). See drivers.py.
    cs2_routes: str = "recorded"
    # Death coach (coach.py): advice in CS2 chat and in the user's voice after the person dies. Off unless
    # set; from_env turns it on (COACH=off turns it off) and reads keys from match-service/.env too.
    coach: CoachSettings = field(default_factory=lambda: CoachSettings(enabled=False))
    # MATCH_LOG_FILE: also write the service's own log lines (coach, CS2 backend, outgoing HTTP) to this
    # file, at INFO. start-cs2.ps1 sets it to data/logs/match-service.log so the logs can be sent back.
    log_file: Path | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ
        demo_dir = env.get("CS2_DEMO_DIR")
        return cls(
            backend=env.get("MATCH_BACKEND", cls.backend),
            start_seconds=float(env.get("MOCK_START_SECONDS", cls.start_seconds)),
            warmup_seconds=float(env.get("WARMUP_SECONDS", env.get("MOCK_WARMUP_SECONDS", cls.warmup_seconds))),
            round_seconds=float(env.get("MOCK_ROUND_SECONDS", cls.round_seconds)),
            server_ip=env.get("SERVER_IP", env.get("MOCK_SERVER_IP", cls.server_ip)),
            base_port=int(env.get("SERVER_PORT", env.get("MOCK_BASE_PORT", cls.base_port))),
            public_url=env.get("PUBLIC_URL", env.get("MOCK_PUBLIC_URL", cls.public_url)).rstrip("/"),
            clones_dir=Path(env.get("CLONES_DIR") or (
                DEFAULT_CLONE_DATA_DIR if env.get("MATCH_BACKEND") == "cs2"
                and env.get("CS2_BOTS") == "clone" else DEFAULT_CLONES_DIR)),
            clone_data_dir=Path(env.get("CLONE_DATA_DIR", DEFAULT_CLONE_DATA_DIR)),
            trace_dir=Path(env["TRACE_DIR"]) if env.get("TRACE_DIR") else None,
            review_dir=Path(env.get("REVIEW_DIR") or DEFAULT_REVIEW_DIR),
            puzzle_seed_dir=Path(env.get("PUZZLE_SEED_DIR") or DEFAULT_PUZZLE_SEED_DIR),
            puzzle_dir=Path(env.get("PUZZLE_DIR") or DEFAULT_PUZZLE_DIR),
            death_dir=Path(env.get("PUZZLE_DEATH_DIR") or DEFAULT_DEATH_DIR),
            game_puzzle_dir=Path(env["PUZZLE_GAME_DIR"]) if env.get("PUZZLE_GAME_DIR") else None,
            cs2_console=env.get("CS2_CONSOLE", cls.cs2_console),
            cs2_console_host=env.get("CS2_CONSOLE_HOST", cls.cs2_console_host),
            cs2_console_port=int(env["CS2_CONSOLE_PORT"]) if env.get("CS2_CONSOLE_PORT") else None,
            cs2_console_password=env.get("CS2_CONSOLE_PASSWORD", cls.cs2_console_password),
            gsi_token=env.get("GSI_TOKEN", cls.gsi_token),
            demo_dir=Path(demo_dir) if demo_dir else None,
            cs2_record=env.get("CS2_RECORD", cls.cs2_record),
            map_load_seconds=float(env.get("CS2_MAP_LOAD_SECONDS", cls.map_load_seconds)),
            restart_seconds=float(env.get("CS2_RESTART_SECONDS", cls.restart_seconds)),
            cs2_bots=env.get("CS2_BOTS", cls.cs2_bots),
            cs2_plugin_port=int(env.get("CS2_PLUGIN_PORT", cls.cs2_plugin_port)),
            cs2_plugin_token=env.get("CS2_PLUGIN_TOKEN", cls.cs2_plugin_token),
            clone_join_seconds=float(env.get("CS2_CLONE_JOIN_SECONDS", cls.clone_join_seconds)),
            cs2_routes=env.get("CS2_CLONE_ROUTES", cls.cs2_routes),
            cs2_settle_seconds=float(env.get("CS2_SETTLE_SECONDS", cls.cs2_settle_seconds)),
            puzzle_settle_seconds=float(env.get("CS2_PUZZLE_SETTLE_SECONDS", cls.puzzle_settle_seconds)),
            coach=CoachSettings.from_env(dict(env), env_file=[ENV_FILE, ROOT_ENV_FILE]),
            log_file=Path(env["MATCH_LOG_FILE"]) if env.get("MATCH_LOG_FILE") else None,
        )


    def console_port(self) -> int:
        return self.cs2_console_port or {"netcon": 2121, "rcon": 27015, "plugin": 27100}[self.cs2_console]


@dataclass
class MatchRecord:
    match: Match
    callback_url: str | None
    mock_fail: bool
    events: list[Event] = field(default_factory=list)
    task: asyncio.Task | None = None
    trace: "Trace | None" = None  # where each player went, per round (replay.py)

    @property
    def active(self) -> bool:
        return self.match.status in ("starting", "ready", "live")


def load_clones(clones_dir: Path) -> dict[str, Clone]:
    """Read clone profiles (<clone_id>.json). Extra fields in the file are ignored here."""
    clones: dict[str, Clone] = {}
    for path in sorted(clones_dir.glob("*.json")):
        data = json.loads(path.read_text())
        try:
            clone = Clone(
                clone_id=data["clone_id"],
                display_name=data["display_name"],
                source=data["source"],
                stand_in_bot=data.get("stand_in_bot"),
                model=data.get("model"),
            )
        except ValidationError as exc:
            log.warning("skipping clone profile %s: %s", path.name, exc)
            continue
        clones[clone.clone_id] = clone
    return clones


def now() -> datetime:
    return datetime.now(timezone.utc)
