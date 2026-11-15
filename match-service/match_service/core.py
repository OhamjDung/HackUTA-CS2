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

from .models import Clone, Event, Match

log = logging.getLogger("match_service")

DEFAULT_CLONES_DIR = Path(__file__).resolve().parent.parent / "sample_clones"

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
    # cs2 backend only
    cs2_console: str = "netcon"  # netcon, rcon or plugin (see console.py)
    cs2_console_host: str = "127.0.0.1"
    cs2_console_port: int | None = None  # None: 2121 for netcon, 27015 for rcon, 27100 for plugin
    cs2_console_password: str = ""  # RCON password, or the MatchBridge plugin's token
    gsi_token: str = "change-me"
    demo_dir: Path | None = None
    map_load_seconds: float = 90.0
    restart_seconds: float = 2.0  # wait after mp_restartgame before trusting game state

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
            clones_dir=Path(env.get("CLONES_DIR", DEFAULT_CLONES_DIR)),
            cs2_console=env.get("CS2_CONSOLE", cls.cs2_console),
            cs2_console_host=env.get("CS2_CONSOLE_HOST", cls.cs2_console_host),
            cs2_console_port=int(env["CS2_CONSOLE_PORT"]) if env.get("CS2_CONSOLE_PORT") else None,
            cs2_console_password=env.get("CS2_CONSOLE_PASSWORD", cls.cs2_console_password),
            gsi_token=env.get("GSI_TOKEN", cls.gsi_token),
            demo_dir=Path(demo_dir) if demo_dir else None,
            map_load_seconds=float(env.get("CS2_MAP_LOAD_SECONDS", cls.map_load_seconds)),
            restart_seconds=float(env.get("CS2_RESTART_SECONDS", cls.restart_seconds)),
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
            )
        except ValidationError as exc:
            log.warning("skipping clone profile %s: %s", path.name, exc)
            continue
        clones[clone.clone_id] = clone
    return clones


def now() -> datetime:
    return datetime.now(timezone.utc)
