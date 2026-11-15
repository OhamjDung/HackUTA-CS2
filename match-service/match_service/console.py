"""Ways to send console commands to CS2.

NetconChannel talks to CS2's network console: start CS2 with `-netconport <port>` and it accepts
plain-text commands over TCP, one per line, and streams console output back. This is how it works
in other Source games; whether CS2 still supports it is NOT checked yet (SPEC.md section 3). If it
doesn't, add a channel that talks to a small CounterStrikeSharp plugin instead. Nothing else in the
service needs to change, because everything goes through `send` and `query`.
"""

import asyncio
from typing import Protocol


class ConsoleChannel(Protocol):
    async def send(self, commands: list[str]) -> None: ...

    async def query(self, command: str, wait_seconds: float = 1.0) -> str: ...


class NetconChannel:
    def __init__(self, host: str, port: int, connect_timeout: float = 3.0):
        self.host, self.port, self.connect_timeout = host, port, connect_timeout

    async def _open(self):
        return await asyncio.wait_for(asyncio.open_connection(self.host, self.port), self.connect_timeout)

    async def send(self, commands: list[str]) -> None:
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


class RecordingChannel:
    """Keeps every command instead of sending it. For tests and for working without CS2."""

    def __init__(self):
        self.sent: list[str] = []
        self.fail_with: Exception | None = None

    async def send(self, commands: list[str]) -> None:
        if self.fail_with:
            raise self.fail_with
        self.sent.extend(commands)

    async def query(self, command: str, wait_seconds: float = 1.0) -> str:
        await self.send([command])
        return ""
