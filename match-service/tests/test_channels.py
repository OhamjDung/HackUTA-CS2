"""The fallback console channels (RCON and the MatchBridge plugin), each against a fake server that
speaks the same protocol. These check the Python side only, not CS2 or the C# plugin."""

import asyncio
import struct

import pytest

from match_service.console import PluginChannel, RconChannel, server_side

MATCH_COMMANDS = ["game_type 0", "map de_mirage", 'bot_add_ct "donk"', "jointeam 3", "record match_1", "stop"]


def test_server_side_translation():
    assert server_side(MATCH_COMMANDS, jointeam_command="matchbridge_jointeam") == [
        "game_type 0", "tv_enable 1", "map de_mirage", 'bot_add_ct "donk"',
        "matchbridge_jointeam 3", "tv_record match_1", "tv_stoprecord"]
    # Over RCON nothing can move the player at the PC, so jointeam is dropped.
    assert "jointeam 3" not in server_side(MATCH_COMMANDS, jointeam_command=None)
    assert not any(c.startswith("matchbridge") for c in server_side(MATCH_COMMANDS, jointeam_command=None))


# --- RCON -------------------------------------------------------------------------------------

def packet(req_id: int, kind: int, body: str = "") -> bytes:
    payload = struct.pack("<ii", req_id, kind) + body.encode() + b"\x00\x00"
    return struct.pack("<i", len(payload)) + payload


async def fake_rcon_server(password: str, received: list[str]):
    async def handle(reader, writer):
        try:
            while True:
                size = struct.unpack("<i", await reader.readexactly(4))[0]
                data = await reader.readexactly(size)
                req_id, kind = struct.unpack("<ii", data[:8])
                body = data[8:-2].decode()
                if kind == 3:  # login
                    writer.write(packet(req_id, 0))
                    writer.write(packet(req_id if body == password else -1, 2))
                elif kind == 2:  # command
                    received.append(body)
                    writer.write(packet(req_id, 0, f"ran {body}"))
                await writer.drain()
        except asyncio.IncompleteReadError:
            writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    return server, server.sockets[0].getsockname()[1]


def test_rcon_channel():
    received: list[str] = []

    async def scenario():
        server, port = await fake_rcon_server("secret", received)
        channel = RconChannel("127.0.0.1", port, "secret")
        await channel.send(MATCH_COMMANDS)
        out = await channel.query("echo hi")
        server.close()
        return out

    assert asyncio.run(scenario()) == "ran echo hi"
    assert received == server_side(MATCH_COMMANDS, jointeam_command=None) + ["echo hi"]


def test_rcon_wrong_password():
    async def scenario():
        server, port = await fake_rcon_server("secret", [])
        try:
            await RconChannel("127.0.0.1", port, "nope").send(["status"])
        finally:
            server.close()

    with pytest.raises(ConnectionError, match="password"):
        asyncio.run(scenario())


# --- MatchBridge plugin ----------------------------------------------------------------------

async def fake_plugin(token: str, received: list[str]):
    """Behaves like MatchBridge.cs."""
    async def handle(reader, writer):
        first = (await reader.readline()).decode().strip()
        if first != f"auth {token}":
            writer.write(b"denied\n")
            await writer.drain()
            writer.close()
            return
        writer.write(b"ok\n")
        while line := (await reader.readline()).decode().strip():
            if line == "matchbridge_ping":
                writer.write(b"pong\n")
            else:
                received.append(line)
                writer.write(b"ok\n")
            await writer.drain()
        writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    return server, server.sockets[0].getsockname()[1]


def test_plugin_channel():
    received: list[str] = []

    async def scenario():
        server, port = await fake_plugin("tok", received)
        channel = PluginChannel("127.0.0.1", port, "tok")
        await channel.send(MATCH_COMMANDS)
        check = await channel.query("echo match-service-check")
        server.close()
        return check

    assert asyncio.run(scenario()) == "match-service-check"
    assert received == server_side(MATCH_COMMANDS, jointeam_command="matchbridge_jointeam")


def test_plugin_wrong_token():
    async def scenario():
        server, port = await fake_plugin("tok", [])
        try:
            await PluginChannel("127.0.0.1", port, "nope").send(["status"])
        finally:
            server.close()

    with pytest.raises(ConnectionError, match="refused the token"):
        asyncio.run(scenario())
