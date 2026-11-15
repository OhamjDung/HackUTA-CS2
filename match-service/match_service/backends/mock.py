"""Mock backend: no game. A match steps through its states on timers with random round winners.

Each round also gets a simulated trace for the replay pages: every player walks a real recorded
route for its side (its own clone's routes when the clone has data), marked `simulated`.
"""

import asyncio
import random
import time

from ..core import Emit, MatchRecord, Settings
from ..replay import RouteLibrary, Trace, simulated_round
from ..models import ROUNDS_TO_WIN, Clone, Match, MatchCreate, Server


class MockBackend:
    name = "mock"

    def __init__(self, settings: Settings, emit: Emit, library: RouteLibrary | None = None):
        self.s = settings
        self.emit = emit
        self.library = library or RouteLibrary(settings.clone_data_dir)
        self.used_ports: set[int] = set()

    def busy(self) -> bool:
        return False  # the mock runs any number of matches at once

    def validate(self, body: MatchCreate, clones: dict[str, Clone], others: list[MatchRecord]) -> list[str]:
        return []

    def start(self, record: MatchRecord, clones: dict[str, Clone]) -> None:
        record.trace = Trace(record.match.match_id, record.match.map, "simulated")
        record.task = asyncio.create_task(self._simulate(record))

    def demo_path(self, match_id: str):
        return None  # the mock records nothing

    async def stop(self, record: MatchRecord) -> None:
        if record.task:
            record.task.cancel()
        self._release(record.match)

    async def health(self) -> dict:
        return {"backend": self.name}

    def _free_port(self) -> int:
        port = self.s.base_port
        while port in self.used_ports:
            port += 1
        self.used_ports.add(port)
        return port

    def _release(self, match: Match) -> None:
        if match.server:
            self.used_ports.discard(match.server.port)

    async def _simulate(self, record: MatchRecord) -> None:
        m = record.match
        await asyncio.sleep(self.s.start_seconds)
        if record.mock_fail:
            m.status, m.error = "failed", "Mock failure: the server did not start"
            await self.emit(record, "match.failed", {"error": m.error})
            return

        port = self._free_port()
        m.server = Server(ip=self.s.server_ip, port=port)
        m.join_link = f"steam://connect/{self.s.server_ip}:{port}"
        m.status = "ready"
        await self.emit(record, "match.ready", {"server": m.server.model_dump(), "join_link": m.join_link})

        await asyncio.sleep(self.s.warmup_seconds)
        m.status = "live"
        await self.emit(record, "match.live", {})

        rng = random.Random(m.match_id)
        route_rng = random.Random(f"{m.match_id}-routes")
        trace = record.trace
        to_win = ROUNDS_TO_WIN[m.mode]
        while max(m.score.CT, m.score.T) < to_win:
            n = m.round + 1
            simulated_round(self.library, trace, n, m.players, route_rng)
            trace.reveal[n] = (time.monotonic(), self.s.round_seconds)
            trace.live_round = n
            await asyncio.sleep(self.s.round_seconds)
            winner = rng.choice(["CT", "T"])
            setattr(m.score, winner, getattr(m.score, winner) + 1)
            m.round += 1
            await self.emit(record, "round.ended", {"round": m.round, "winner": winner, "score": m.score.model_dump()})

        m.status = "ended"
        m.demo_url = f"{self.s.public_url}/demos/{m.match_id}.dem"
        trace.live_round = None
        if self.s.trace_dir:
            trace.save(self.s.trace_dir)
        self._release(m)
        winner = "CT" if m.score.CT > m.score.T else "T"
        await self.emit(record, "match.ended", {"reason": "finished", "winner": winner,
                                                "score": m.score.model_dump(), "demo_url": m.demo_url})
