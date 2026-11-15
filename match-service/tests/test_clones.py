"""CS2_BOTS=clone: clones played by Arjun's CloneDirector, through the MatchBridge plugin.

Uses the real data-built profiles in ../clones (no stand_in_bot; the bot is named after
display_name). The game, CloneDirector and MatchBridge are fakes here; nothing ran in CS2.
"""

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from match_service.console import PluginChannel, RecordingChannel
from match_service.main import create_app, make_clone_channel
from tests.test_cs2 import gsi, settings, wait_for, wait_sent, wingman

REPO_CLONES = Path(__file__).resolve().parents[2] / "clones"
NAMES = {"donk_v1": "donk_v1", "broky_v1": "broky_v1"}  # each clone has its own bot entry


def clone_app(tmp_path, personalities=NAMES, **extra):
    main, bridge = RecordingChannel(), RecordingChannel(personalities)
    s = settings(tmp_path, cs2_bots="clone", clones_dir=REPO_CLONES, clone_join_seconds=0.3, **extra)
    return create_app(s, channel=main, clone_channel=bridge), main, bridge


def start(client, main, body=None):
    match_id = client.post("/matches", json=body or wingman(players=[])).json()["match_id"]
    wait_sent(main, "map de_mirage")
    gsi(client)
    return match_id


def test_clone_match_uses_clone_add_through_the_plugin(tmp_path):
    app, main, bridge = clone_app(tmp_path)
    with TestClient(app) as client:
        match_id = start(client, main)
        wait_for(client, match_id, "ready")
        # The ordinary commands stay on netcon; only CloneDirector's go through MatchBridge.
        assert "bot_kick" in main.sent and not any(c.startswith("bot_add") for c in main.sent)
        assert bridge.sent == ["clone_routes recorded", "clone_add donk_v1 ct", "clone_add broky_v1 t"]
        assert main.sent.index("bot_kick") < main.sent.index("jointeam 1")
        wait_sent(main, "mp_restartgame 1")


def test_clone_that_never_joins_fails_the_match(tmp_path):
    app, main, _ = clone_app(tmp_path, personalities={"donk_v1": "donk_v1"})  # broky never appears
    with TestClient(app) as client:
        match_id = start(client, main)
        m = wait_for(client, match_id, "failed")
        assert "broky_v1" in m["error"] and "donk_v1" not in m["error"]
        assert "mp_warmup_end" not in main.sent


def test_clone_on_the_wrong_team_does_not_count(tmp_path):
    app, main, bridge = clone_app(tmp_path)
    with TestClient(app) as client:
        bridge.personalities = {"broky_v1": "broky_v1"}
        bridge.bot_list = [{"name": "donk", "team": 2}]  # a donk bot, but on T; donk_v1 wants CT
        match_id = start(client, main)
        assert "donk_v1" in wait_for(client, match_id, "failed")["error"]


def test_plugin_unreachable(tmp_path):
    app, main, bridge = clone_app(tmp_path)
    bridge.fail_with = ConnectionRefusedError("refused")
    with TestClient(app) as client:
        match_id = start(client, main)
        assert "MatchBridge" in wait_for(client, match_id, "failed")["error"]


def test_clone_mode_rules(tmp_path):
    app, _, _ = clone_app(tmp_path)
    with TestClient(app) as client:
        r = client.post("/matches", json=wingman(map="de_inferno"))
        assert r.status_code == 422 and any("de_mirage" in e for e in r.json()["detail"])
        # The data-built profiles have no stand_in_bot; clone mode doesn't need one.
        assert {c["clone_id"] for c in client.get("/clones").json()} >= {"donk_v1", "broky_v1"}
        assert client.get("/health").json()["bots"] == "clone"


def test_make_clone_channel(tmp_path):
    assert make_clone_channel(settings(tmp_path)) is None  # stand-in mode
    assert make_clone_channel(settings(tmp_path, cs2_bots="clone", cs2_console="plugin")) is None
    ch = make_clone_channel(settings(tmp_path, cs2_bots="clone", cs2_console_password="pw"))
    assert isinstance(ch, PluginChannel) and (ch.port, ch.token) == (27100, "pw")
    ch = make_clone_channel(settings(tmp_path, cs2_bots="clone", cs2_console_password="pw", cs2_plugin_token="tok"))
    assert ch.token == "tok"


def test_plugin_bot_list_against_a_fake_matchbridge():
    async def handle(reader, writer):
        assert (await reader.readline()).decode().strip() == "auth tok"
        writer.write(b"ok\n")
        assert (await reader.readline()).decode().strip() == "matchbridge_bots"
        writer.write(b'[{"name": "donk", "team": 3}, {"name": "broky", "team": 2}]\n')
        await writer.drain()
        writer.close()

    async def scenario():
        server = await asyncio.start_server(handle, "127.0.0.1", 0)
        try:
            return await PluginChannel("127.0.0.1", server.sockets[0].getsockname()[1], "tok").bots()
        finally:
            server.close()

    assert asyncio.run(scenario()) == [{"name": "donk", "team": 3}, {"name": "broky", "team": 2}]
