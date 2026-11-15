"""Ways to send console commands to CS2. Pick one with CS2_CONSOLE.

- `netcon` (default): CS2's network console. Start CS2 with `-netconport <port>` and it accepts
  plain-text commands over TCP, one per line, and streams console output back. This is how it works
  in other Source games; whether CS2 still supports it is NOT checked (SPEC.md section 3).
- `rcon`: Valve's RCON protocol. Not checked whether Bot Mode accepts it.
- `plugin`: the MatchBridge plugin in plugin/MatchBridge, which runs inside CS2 on
  CounterStrikeSharp (which CS2-Bot-Improver already installs). The most likely to work, but it
  must be built and installed first.

Everything in the service goes through `send` and `query`, so switching changes nothing else.
"""

import asyncio
import json
from typing import Protocol

# A newline or `;` ends a console command, so a value containing one could run a second command.
UNSAFE = ("\n", "\r", ";", "\0")


class UnsafeCommand(ValueError):
    pass


def check(commands: list[str]) -> list[str]:
    """Refuse the whole batch, before anything is sent, if any command could run a second one."""
    for c in commands:
        if any(ch in c for ch in UNSAFE):
            raise UnsafeCommand(f"refusing console command with a newline or ';': {c!r}")
    return commands


class ConsoleChannel(Protocol):
    async def send(self, commands: list[str]) -> None: ...

    async def query(self, command: str, wait_seconds: float = 1.0) -> str: ...


class NetconChannel:
    def __init__(self, host: str, port: int, connect_timeout: float = 3.0):
        self.host, self.port, self.connect_timeout = host, port, connect_timeout

    async def _open(self):
        return await asyncio.wait_for(asyncio.open_connection(self.host, self.port), self.connect_timeout)

    async def send(self, commands: list[str]) -> None:
        check(commands)
        reader, writer = await self._open()
        try:
            writer.write("".join(f"{c}\n" for c in commands).encode())
            await writer.drain()
            # Give the game a moment to read before the connection closes.
            await asyncio.sleep(0.2)
        finally:
            writer.close()
            await writer.wait_closed()

    async def query(self, command: str, wait_seconds: float = 1.0) -> str:
        """Send one command and return whatever console output arrives within wait_seconds."""
        check([command])
        reader, writer = await self._open()
        try:
            writer.write(f"{command}\n".encode())
            await writer.drain()
            chunks: list[bytes] = []
            loop = asyncio.get_running_loop()
            deadline = loop.time() + wait_seconds
            while (left := deadline - loop.time()) > 0:
                try:
                    chunk = await asyncio.wait_for(reader.read(4096), left)
                except asyncio.TimeoutError:
                    break
                if not chunk:
                    break
                chunks.append(chunk)
            return b"".join(chunks).decode(errors="replace")
        finally:
            writer.close()
            await writer.wait_closed()


def server_side(commands: list[str], jointeam_command: str | None) -> list[str]:
    """Rewrite client-only commands for channels that run commands on the server side.

    RCON and the MatchBridge plugin run commands as the server, not as the player at the PC, so:
    - `record <name>` / `stop` (a player's own recording) become `tv_record <name>` / `tv_stoprecord`.
      The backend no longer sends them (CS2_RECORD), but other callers might.
    - `jointeam <n>` moves the player at the PC. Only the plugin can do that (`jointeam_command`);
      over RCON it is dropped and the player picks a team by hand.
    """
    out: list[str] = []
    for c in commands:
        word, _, rest = c.partition(" ")
        if word == "record":
            out.append(f"tv_record {rest}")
        elif c == "stop":
            out.append("tv_stoprecord")
        elif word == "jointeam":
            if jointeam_command:
                out.append(f"{jointeam_command} {rest}")
        else:
            out.append(c)
    return out


class RconChannel:
    """Valve's RCON protocol, through the `rcon` library (GPLv3).

    Needs `rcon_password` set in CS2. Whether CS2's Bot Mode (the game hosting the match itself)
    accepts RCON is NOT checked; a dedicated server does.
    """

    def __init__(self, host: str, port: int, password: str, timeout: float = 3.0):
        self.host, self.port, self.password, self.timeout = host, port, password, timeout

    async def _run(self, command: str) -> str:
        from rcon.exceptions import SessionTimeout, WrongPassword
        from rcon.source import rcon

        try:
            return await asyncio.wait_for(
                rcon(command, host=self.host, port=self.port, passwd=self.password), self.timeout)
        except WrongPassword as exc:
            raise ConnectionError("RCON refused the password") from exc
        except SessionTimeout as exc:
            raise ConnectionError("RCON session timed out") from exc

    async def send(self, commands: list[str]) -> None:
        for c in check(server_side(commands, jointeam_command=None)):
            await self._run(c)

    async def query(self, command: str, wait_seconds: float = 1.0) -> str:
        return await self._run(check([command])[0])


class PluginChannel:
    """The MatchBridge plugin (plugin/MatchBridge in this folder), running inside CS2.

    Protocol: TCP to 127.0.0.1, first line `auth <token>`, then one command per line. The plugin
    answers each line with `ok` (or `denied` after a wrong token) and runs the command on the
    game's main thread. `matchbridge_jointeam <n>` moves the player at the PC to a team.
    """

    def __init__(self, host: str, port: int, token: str, timeout: float = 3.0):
        self.host, self.port, self.token, self.timeout = host, port, token, timeout

    async def _exchange(self, lines: list[str]) -> str:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(self.host, self.port), self.timeout)
        try:
            writer.write(f"auth {self.token}\n".encode())
            await writer.drain()
            first = (await asyncio.wait_for(reader.readline(), self.timeout)).decode().strip()
            if first != "ok":
                raise ConnectionError(f"MatchBridge refused the token ({first or 'no answer'})")
            replies = []
            for line in lines:
                writer.write(f"{line}\n".encode())
                await writer.drain()
                replies.append((await asyncio.wait_for(reader.readline(), self.timeout)).decode().strip())
            return "\n".join(replies)
        finally:
            writer.close()
            await writer.wait_closed()

    async def send(self, commands: list[str]) -> None:
        await self._exchange(check(server_side(commands, jointeam_command="matchbridge_jointeam")))

    async def query(self, command: str, wait_seconds: float = 1.0) -> str:
        # The plugin can't return console output, only that it ran the command.
        reply = await self._exchange(["matchbridge_ping"])
        return "match-service-check" if reply == "pong" else reply

    async def bots(self) -> list[dict]:
        """The bots in the game: [{"name": "donk", "team": 3}, ...] (team 2 = T, 3 = CT)."""
        reply = await self._exchange(["matchbridge_bots"])
        try:
            bots = json.loads(reply)
        except json.JSONDecodeError as exc:
            raise ConnectionError(f"MatchBridge sent an unexpected bot list: {reply[:200]!r}") from exc
        return [b for b in bots if isinstance(b, dict)]


class RecordingChannel:
    """Keeps every command instead of sending it. For tests and for working without CS2.

    It also acts as a fake MatchBridge: `clone_add <id> <t|ct>` adds a bot named
    `personalities[id]` to the list `bots()` returns, the way CloneDirector would.
    """

    def __init__(self, personalities: dict[str, str] | None = None):
        self.sent: list[str] = []
        self.fail_with: Exception | None = None
        self.personalities = personalities or {}
        self.bot_list: list[dict] = []
        self._seen = 0  # how many sent commands bots() has looked at

    async def bots(self) -> list[dict]:
        if self.fail_with:
            raise self.fail_with
        for c in self.sent[self._seen:]:
            word, *args = c.split()
            if word == "clone_add" and args[0] in self.personalities:
                self.bot_list.append({"name": self.personalities[args[0]], "team": 2 if args[1] == "t" else 3})
        self._seen = len(self.sent)
        return list(self.bot_list)

    async def send(self, commands: list[str]) -> None:
        if self.fail_with:
            raise self.fail_with
        self.sent.extend(check(commands))

    async def query(self, command: str, wait_seconds: float = 1.0) -> str:
        await self.send([command])
        return ""
