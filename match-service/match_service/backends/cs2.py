"""CS2 backend: runs the match in a real CS2 with CS2-Bot-Improver installed.

How it talks to the game:
- Commands go out through a ConsoleChannel (see console.py): change map, add bots, and (with
  CS2_RECORD=tv) record.
- Events come back through CS2's Game State Integration (GSI): CS2 POSTs JSON with the map phase
  and team scores to this service's /gsi endpoint. The config file is in gsi/ in this folder.

Who plays each clone (CS2_BOTS):
- `stand_in` (default): its `stand_in_bot`, a built-in CS2-Bot-Improver bot added with
  `bot_add_ct "<name>"` / `bot_add_t "<name>"`. Ran in CS2 on Tom's PC (SPEC.md section 3).
- `clone`: Arjun's CloneDirector plugin, with `clone_add <clone_id> <t|ct>`. CloneDirector refuses
  commands from a player's console, and netcon is the player's console, so these go through the
  MatchBridge plugin (`clone_channel`). The service then asks MatchBridge for the bot list until
  each clone's bot (named after its personality) is on its team. Not run in CS2.
"""

import asyncio
import logging
import time
from collections import Counter
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from ..console import ConsoleChannel, UnsafeCommand
from ..core import Emit, MatchRecord, Settings, now
from ..drivers import describe
from ..models import Clone, MatchCreate, Score, Server
from ..replay import Trace, gsi_players

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

    def __init__(self, settings: Settings, emit: Emit, channel: ConsoleChannel,
                 clone_channel: ConsoleChannel | None = None):
        if settings.cs2_record not in ("off", "tv"):
            raise ValueError(f"CS2_RECORD must be off or tv, not {settings.cs2_record!r}")
        if settings.cs2_bots not in ("stand_in", "clone"):
            raise ValueError(f"CS2_BOTS must be stand_in or clone, not {settings.cs2_bots!r}")
        if settings.cs2_routes not in ("recorded", "generated"):
            raise ValueError(f"CS2_CLONE_ROUTES must be recorded or generated, not {settings.cs2_routes!r}")
        self.s = settings
        self.emit = emit
        self.ch = channel
        # Where clone_add goes: the MatchBridge plugin (the same channel when CS2_CONSOLE=plugin).
        self.clone_ch = clone_channel or channel
        self.current: MatchRecord | None = None
        self.bot_names: dict[str, str] = {}  # clone_id -> bot name, for the current match
        # True once the service has ended warmup and restarted the game. Before that, CS2 may already
        # report `live` (Bot Mode can skip warmup), but those rounds aren't the match.
        self.started = False
        self.gsi: dict = {}
        self.gsi_at: datetime | None = None

    # --- called by the API --------------------------------------------------------------------

    def busy(self) -> bool:
        return self.current is not None and self.current.active

    def validate(self, body: MatchCreate, clones: dict[str, Clone], others: list[MatchRecord]) -> list[str]:
        errors = []
        if len(body.players) > 1:
            errors.append("The cs2 backend allows at most one human player: the person at the CS2 machine")
        if self.s.cs2_bots == "clone" and body.clones and body.map != "de_mirage":
            errors.append("CloneDirector supports de_mirage only")
        unplayable = {c.clone_id: info.reason for c in body.clones if c.clone_id in clones
                      and not (info := describe(clones[c.clone_id], self.s)).playable}
        if unplayable and self.s.cs2_bots == "stand_in":
            errors.append(f"No stand_in_bot in the profile of: {', '.join(unplayable)}")
        elif unplayable:
            errors += [f"{cid} cannot be played: {why}" for cid, why in unplayable.items()]
        return errors

    def start(self, record: MatchRecord, clones: dict[str, Clone]) -> None:
        self.current = record
        self.started = False
        record.trace = Trace(record.match.match_id, record.match.map, "gsi", self.s.cs2_bots)
        self._round_live: int | None = None
        self._round_t0 = 0.0
        # CloneDirector names the bot after the personality: stand_in_bot, else display_name.
        self.bot_names = {p.clone_id: clones[p.clone_id].stand_in_bot or (
                              clones[p.clone_id].display_name if self.s.cs2_bots == "clone" else None)
                          for p in record.match.players if p.is_clone}
        record.task = asyncio.create_task(self._run(record))

    async def stop(self, record: MatchRecord) -> None:
        if record.task:
            record.task.cancel()
        try:
            await self.ch.send(self._record_stop() + ["bot_kick"])  # stop recording, remove the bots
        except (OSError, asyncio.TimeoutError) as exc:
            log.warning("could not send stop commands: %s", exc)

    def _record_stop(self) -> list[str]:
        return ["tv_stoprecord"] if self.s.cs2_record == "tv" else []

    def demo_path(self, match_id: str) -> Path | None:
        if not self.s.demo_dir or self.s.cs2_record == "off":
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
        result = {
            "backend": self.name,
            "bots": self.s.cs2_bots,
            "console": {"kind": self.s.cs2_console, "host": self.s.cs2_console_host,
                        "port": self.s.console_port(), **console},
            "gsi": {"last_update": self.gsi_at, "map": map_name(self.gsi),
                    "phase": (self.gsi.get("map") or {}).get("phase")},
            "current_match": self.current.match.match_id if self.busy() else None,
        }
        if self.s.cs2_bots == "clone" and self.clone_ch is not self.ch:
            try:
                ok = await self.clone_ch.query("matchbridge_ping") == "match-service-check"
                result["clone_console"] = {"kind": "plugin", "port": self.s.cs2_plugin_port, "reachable": ok}
            except (OSError, asyncio.TimeoutError) as exc:
                result["clone_console"] = {"kind": "plugin", "port": self.s.cs2_plugin_port,
                                           "reachable": False, "error": str(exc)}
        return result

    async def handle_gsi(self, payload: dict) -> None:
        """Apply one game state update from CS2."""
        self.gsi, self.gsi_at = payload, now()
        record = self.current
        if not record or record.match.status not in ("ready", "live"):
            return
        m = record.match
        game_map = payload.get("map") or {}
        phase = game_map.get("phase")

        if m.status == "ready" and phase == "live" and self.started:
            m.status = "live"
            await self.emit(record, "match.live", {})
        if m.status != "live":
            return

        ct, t = game_map.get("team_ct") or {}, game_map.get("team_t") or {}
        swapped = ct.get("name") == START_NAME["T"] or t.get("name") == START_NAME["CT"]
        ct_score, t_score = int(ct.get("score", 0)), int(t.get("score", 0))
        # Our score is keyed by the side each team STARTED on.
        target = self._target_score(m.score, ct_score, t_score, swapped)
        self._record_positions(record, payload)
        await self._advance_score(record, target)

        if phase == "gameover":
            await self._finish(record)

    def _record_positions(self, record: MatchRecord, payload: dict) -> None:
        """Add the players' positions to the match trace, while a round is being played.

        Time is seconds since this round's freeze time ended, as seen by the service. CS2 sends
        positions (`allplayers`) only to a spectator, so a match with a human playing has no trace.
        """
        trace = record.trace
        phase = (payload.get("round") or {}).get("phase")
        round_no = int((payload.get("map") or {}).get("round", 0) or 0) + 1
        if phase != "live" or trace is None:
            if trace is not None:
                trace.live_round = None
            return
        if self._round_live != round_no:
            self._round_live, self._round_t0 = round_no, time.monotonic()
        t = time.monotonic() - self._round_t0
        clone_of = {name: cid for cid, name in self.bot_names.items() if name}
        for p in gsi_players(payload):
            trace.add(round_no, t, p["name"], p["team"], p["x"], p["y"], clone_of.get(p["name"]), p["alive"])
        trace.live_round = round_no

    # --- the match ----------------------------------------------------------------------------

    async def _run(self, record: MatchRecord) -> None:
        m = record.match
        try:
            # GOTV must be on before the map loads for tv_record to work.
            tv = ["tv_enable 1"] if self.s.cs2_record == "tv" else []
            await self.ch.send(["game_type 0", f"game_mode {GAME_MODE[m.mode]}"] + tv + [f"map {m.map}"])
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
        if self.s.cs2_bots == "stand_in":
            for p in m.players:
                if p.is_clone:
                    commands.append(f'bot_add_{p.team.lower()} "{self.bot_names[p.clone_id]}"')
        humans = [p for p in m.players if not p.is_clone]
        commands.append(f"jointeam {JOINTEAM[humans[0].team] if humans else 1}")
        try:
            await self.ch.send(commands)
        except UnsafeCommand as exc:
            return await self._fail(record, str(exc))
        except (OSError, asyncio.TimeoutError) as exc:
            return await self._fail(record, f"Lost the CS2 console while adding bots ({exc!r})")
        if self.s.cs2_bots == "clone" and (error := await self._add_clones(m)):
            return await self._fail(record, error)

        m.server = Server(ip=self.s.server_ip, port=self.s.base_port)
        m.join_link = f"steam://connect/{self.s.server_ip}:{self.s.base_port}"
        m.status = "ready"
        await self.emit(record, "match.ready", {"server": m.server.model_dump(), "join_link": m.join_link})

        await asyncio.sleep(self.s.warmup_seconds)
        # End warmup, then restart so round 1 starts with the bots in place and the score at 0-0.
        # CS2-Bot-Improver's own team commands (Commands.txt) also end with `mp_restartgame 1`.
        try:
            start = ["mp_warmup_end", "mp_restartgame 1"]
            if self.s.cs2_record == "tv":
                start.append(f"tv_record {self.demo_name(m.match_id)}")
            await self.ch.send(start)
        except (OSError, asyncio.TimeoutError) as exc:
            return await self._fail(record, f"Lost the CS2 console while starting the match ({exc!r})")
        # Ignore game state until the restart has happened (it takes 1 s), so old scores don't count.
        await asyncio.sleep(self.s.restart_seconds)
        self.started = True
        # From here, game state updates (handle_gsi) move the match to live, count rounds, and end it.

    async def _add_clones(self, m) -> str | None:
        """Send clone_add for each clone, then wait until each one's bot is on its team.

        CloneDirector says a sent clone_add doesn't prove the bot attached. A new bot with the
        personality's name on the right team, right after bot_kick, is the closest check MatchBridge
        can give; CloneDirector's own `clone_list` output can't be read back. Returns an error or None.
        """
        clones = [p for p in m.players if p.is_clone]
        if not clones:
            return None
        want = Counter((self.bot_names[p.clone_id], JOINTEAM[p.team]) for p in clones)
        try:
            # Always set the route source: CloneDirector keeps the last one in memory, so a match after
            # a `generated` one would otherwise still play generated routes.
            routes = [f"clone_routes {self.s.cs2_routes}"]
            await self.clone_ch.send(routes + [f"clone_add {p.clone_id} {p.team.lower()}" for p in clones])
            loop = asyncio.get_running_loop()
            deadline = loop.time() + self.s.clone_join_seconds
            while True:
                have = Counter((b.get("name"), b.get("team")) for b in await self.clone_ch.bots())
                missing = want - have
                if not missing:
                    return None
                if loop.time() >= deadline:
                    break
                await asyncio.sleep(0.5)
        except (OSError, asyncio.TimeoutError) as exc:
            return (f"Can't reach the MatchBridge plugin for CloneDirector ({exc!r}). Is MatchBridge installed, "
                    "and does CS2_PLUGIN_TOKEN (or CS2_CONSOLE_PASSWORD) match its token?")
        late = sorted({p.clone_id for p in clones if (self.bot_names[p.clone_id], JOINTEAM[p.team]) in missing})
        return (f"These clones did not join within {self.s.clone_join_seconds:.0f} s: {', '.join(late)}. "
                "Check the CloneDirector lines in the CS2 console, or run clone_list there.")

    @staticmethod
    def _target_score(current: Score, ct_score: int, t_score: int, swapped_by_name: bool) -> Score:
        """Which of CS2's two side scores belongs to which starting side.

        The team names say whether the sides have swapped, but at halftime CS2 sent an update where
        the names had swapped and the scores had not (Tom's match 09a357d5a255: 7-1 became 7-7 and
        six extra round.ended events). Scores never go down, so only a reading where neither team's
        score drops is possible. Of those, take the one that adds the fewest rounds; the team names
        only break a tie. An update that fits neither reading is ignored.
        """
        straight, crossed = Score(CT=ct_score, T=t_score), Score(CT=t_score, T=ct_score)
        options = [s for s in (straight, crossed) if s.CT >= current.CT and s.T >= current.T]
        if not options:
            return current
        preferred = crossed if swapped_by_name else straight
        return min(options, key=lambda s: (s.CT + s.T, s is not preferred))

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
            if self._record_stop():
                await self.ch.send(self._record_stop())
        except (OSError, asyncio.TimeoutError) as exc:
            log.warning("could not stop recording: %s", exc)
        m.status = "ended"
        if record.trace is not None:
            record.trace.live_round = None
            if self.s.trace_dir:
                record.trace.save(self.s.trace_dir)
        if self.s.cs2_record != "off":
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
