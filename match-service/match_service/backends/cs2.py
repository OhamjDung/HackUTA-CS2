"""CS2 backend: runs the match in a real CS2 with CS2-Bot-Improver installed.

How it talks to the game:
- Commands go out through a ConsoleChannel (see console.py): change map, add bots, start recording.
- Events come back through CS2's Game State Integration (GSI): CS2 POSTs JSON with the map phase
  and team scores to this service's /gsi endpoint. The config file is in gsi/ in this folder.

Until the CloneDirector plugin exists, each clone is played by its `stand_in_bot`: a built-in
CS2-Bot-Improver bot added with `bot_add_ct "<name>"` / `bot_add_t "<name>"` (SPEC.md 9.2).

None of the CS2 side of this file has been run against a real game yet (SPEC.md section 3).
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from ..console import ConsoleChannel
from ..core import Emit, MatchRecord, Settings, now
from ..models import Clone, MatchCreate, Score, Server

log = logging.getLogger("match_service.cs2")

# Team names set at the start, so the scores stay with the right team after sides swap at halftime.
# "Team 1" in CS2 starts on CT.
START_NAME = {"CT": "Alpha", "T": "Bravo"}
JOINTEAM = {"CT": 3, "T": 2}  # jointeam 1 = spectator
GAME_MODE = {"competitive": 1, "wingman": 2}  # with game_type 0


def map_name(gsi: dict) -> str | None:
    return (gsi.get("map") or {}).get("name")


class Cs2Backend:
    name = "cs2"

    def __init__(self, settings: Settings, emit: Emit, channel: ConsoleChannel):
        self.s = settings
        self.emit = emit
        self.ch = channel
        self.current: MatchRecord | None = None
        self.stand_ins: dict[str, str] = {}  # clone_id -> bot name, for the current match
        self.gsi: dict = {}
        self.gsi_at: datetime | None = None

    # --- called by the API --------------------------------------------------------------------

    def busy(self) -> bool:
        return self.current is not None and self.current.active

    def validate(self, body: MatchCreate, clones: dict[str, Clone], others: list[MatchRecord]) -> list[str]:
        errors = []
        if len(body.players) > 1:
            errors.append("The cs2 backend allows at most one human player: the person at the CS2 machine")
        missing = [c.clone_id for c in body.clones if c.clone_id in clones and not clones[c.clone_id].stand_in_bot]
        if missing:
            errors.append(f"No stand_in_bot in the profile of: {', '.join(missing)}")
        return errors

    def start(self, record: MatchRecord, clones: dict[str, Clone]) -> None:
        self.current = record
        self.stand_ins = {p.clone_id: clones[p.clone_id].stand_in_bot
                          for p in record.match.players if p.is_clone}
        record.task = asyncio.create_task(self._run(record))

    async def stop(self, record: MatchRecord) -> None:
        if record.task:
            record.task.cancel()
        try:
            await self.ch.send(["stop", "bot_kick"])  # stop recording, remove the bots
        except (OSError, asyncio.TimeoutError) as exc:
            log.warning("could not send stop commands: %s", exc)

    def demo_path(self, match_id: str) -> Path | None:
        if not self.s.demo_dir:
            return None
        return self.s.demo_dir / f"{self.demo_name(match_id)}.dem"

    @staticmethod
    def demo_name(match_id: str) -> str:
        return f"match_{match_id}"

    async def health(self) -> dict:
        try:
            out = await self.ch.query("echo match-service-check", wait_seconds=1.0)
            console = {"reachable": True, "echoed": "match-service-check" in out, "output": out[-500:]}
        except (OSError, asyncio.TimeoutError) as exc:
            console = {"reachable": False, "error": str(exc)}
        return {
            "backend": self.name,
            "console": {"kind": self.s.cs2_console, "host": self.s.cs2_console_host,
                        "port": self.s.console_port(), **console},
            "gsi": {"last_update": self.gsi_at, "map": map_name(self.gsi),
                    "phase": (self.gsi.get("map") or {}).get("phase")},
            "current_match": self.current.match.match_id if self.busy() else None,
        }

    async def handle_gsi(self, payload: dict) -> None:
        """Apply one game state update from CS2."""
        self.gsi, self.gsi_at = payload, now()
        record = self.current
        if not record or record.match.status not in ("ready", "live"):
            return
        m = record.match
        game_map = payload.get("map") or {}
        phase = game_map.get("phase")

        if m.status == "ready" and phase == "live":
            m.status = "live"
            await self.emit(record, "match.live", {})
        if m.status != "live":
            return

        ct, t = game_map.get("team_ct") or {}, game_map.get("team_t") or {}
        swapped = ct.get("name") == START_NAME["T"] or t.get("name") == START_NAME["CT"]
        ct_score, t_score = int(ct.get("score", 0)), int(t.get("score", 0))
        # Our score is keyed by the side each team STARTED on.
        target = Score(CT=t_score if swapped else ct_score, T=ct_score if swapped else t_score)
        await self._advance_score(record, target)

        if phase == "gameover":
            await self._finish(record)

    # --- the match ----------------------------------------------------------------------------

    async def _run(self, record: MatchRecord) -> None:
        m = record.match
        try:
            await self.ch.send(["game_type 0", f"game_mode {GAME_MODE[m.mode]}", f"map {m.map}"])
        except (OSError, asyncio.TimeoutError) as exc:
            hint = {"netcon": "Is CS2 running with -netconport?",
                    "rcon": "Is rcon_password set in CS2, and does the password match?",
                    "plugin": "Is the MatchBridge plugin installed, and does the token match?"}[self.s.cs2_console]
            return await self._fail(record, f"Can't reach the CS2 console ({self.s.cs2_console}) at "
                                            f"{self.s.cs2_console_host}:{self.s.console_port()} ({exc!r}). {hint}")

        # If CS2 is already on this map, first wait for the reload to drop it, so bots aren't added to
        # the old map just before it reloads. Not checked how GSI reports a reload; capped at 20 s.
        if map_name(self.gsi) == m.map:
            if not await self._wait_for(lambda g: map_name(g) != m.map, min(20.0, self.s.map_load_seconds)):
                log.info("no map unload seen in game state; continuing")
        if not await self._wait_for(lambda g: map_name(g) == m.map, self.s.map_load_seconds):
            return await self._fail(record, f"CS2 did not report map {m.map} within {self.s.map_load_seconds:.0f} s. "
                                            "Check the game state integration file and GSI_TOKEN.")

        commands = [
            "mp_autoteambalance 0",
            "mp_limitteams 0",
            f'mp_teamname_1 "{START_NAME["CT"]}"',
            f'mp_teamname_2 "{START_NAME["T"]}"',
            "bot_quota_mode normal",
            "bot_quota 0",
            "bot_kick",
        ]
        for p in m.players:
            if p.is_clone:
                commands.append(f'bot_add_{p.team.lower()} "{self.stand_ins[p.clone_id]}"')
        humans = [p for p in m.players if not p.is_clone]
        commands.append(f"jointeam {JOINTEAM[humans[0].team] if humans else 1}")
        try:
            await self.ch.send(commands)
        except (OSError, asyncio.TimeoutError) as exc:
            return await self._fail(record, f"Lost the CS2 console while adding bots ({exc!r})")

        m.server = Server(ip=self.s.server_ip, port=self.s.base_port)
        m.join_link = f"steam://connect/{self.s.server_ip}:{self.s.base_port}"
        m.status = "ready"
        await self.emit(record, "match.ready", {"server": m.server.model_dump(), "join_link": m.join_link})

        await asyncio.sleep(self.s.warmup_seconds)
        try:
            await self.ch.send([f"record {self.demo_name(m.match_id)}", "mp_warmup_end"])
        except (OSError, asyncio.TimeoutError) as exc:
            return await self._fail(record, f"Lost the CS2 console while starting the match ({exc!r})")
        # From here, game state updates (handle_gsi) move the match to live, count rounds, and end it.

    async def _advance_score(self, record: MatchRecord, target: Score) -> None:
        m = record.match
        # One round.ended per round, even if an update was missed. Scores never go down.
        while m.score.CT < target.CT or m.score.T < target.T:
            winner = "CT" if m.score.CT < target.CT else "T"
            setattr(m.score, winner, getattr(m.score, winner) + 1)
            m.round += 1
            await self.emit(record, "round.ended", {"round": m.round, "winner": winner, "score": m.score.model_dump()})

    async def _finish(self, record: MatchRecord) -> None:
        m = record.match
        try:
            await self.ch.send(["stop"])  # stop recording
        except (OSError, asyncio.TimeoutError) as exc:
            log.warning("could not stop recording: %s", exc)
        m.status = "ended"
        m.demo_url = f"{self.s.public_url}/demos/{m.match_id}.dem"
        winner = "CT" if m.score.CT > m.score.T else "T" if m.score.T > m.score.CT else None
        await self.emit(record, "match.ended", {"reason": "finished", "winner": winner,
                                                "score": m.score.model_dump(), "demo_url": m.demo_url})

    async def _fail(self, record: MatchRecord, error: str) -> None:
        m = record.match
        m.status, m.error = "failed", error
        await self.emit(record, "match.failed", {"error": error})

    async def _wait_for(self, condition: Callable[[dict], bool], timeout: float) -> bool:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            if condition(self.gsi):
                return True
            await asyncio.sleep(0.1)
        return condition(self.gsi)
