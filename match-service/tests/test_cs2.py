"""The cs2 backend, driven by a fake console (RecordingChannel) and hand-written game state updates.

These tests check the service's own logic. They do not prove that CS2 accepts these commands or
sends game state in this shape; that needs a run on the real game (SPEC.md section 3).
"""

import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from match_service.console import NetconChannel, RecordingChannel
from match_service.core import Settings
from match_service.main import create_app

TOKEN = "test-token"
ASH = "76561198000000001"


def settings(tmp_path, **extra):
    base = dict(backend="cs2", cs2_settle_seconds=0.0, puzzle_settle_seconds=0.0, warmup_seconds=0.01, map_load_seconds=1.0, restart_seconds=0.0, gsi_token=TOKEN, demo_dir=tmp_path)
    base.update(extra)
    return Settings(**base)


@pytest.fixture
def game(tmp_path):
    channel = RecordingChannel()
    with TestClient(create_app(settings(tmp_path), channel=channel)) as client:
        yield client, channel


def gsi(client, phase="warmup", ct=("Alpha", 0), t=("Bravo", 0), map_name="de_mirage", token=TOKEN):
    payload = {"auth": {"token": token}, "map": {
        "name": map_name, "phase": phase,
        "team_ct": {"name": ct[0], "score": ct[1]}, "team_t": {"name": t[0], "score": t[1]}}}
    return client.post("/gsi", json=payload)


def wait_for(client, match_id, status, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        m = client.get(f"/matches/{match_id}").json()
        if m["status"] == status:
            return m
        time.sleep(0.01)
    raise AssertionError(f"never reached {status}; last: {m['status']} {m.get('error')}")


def wait_sent(channel, command, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if command in channel.sent:
            return
        time.sleep(0.01)
    raise AssertionError(f"{command!r} never sent; sent: {channel.sent}")


def wingman(**extra):
    body = {"map": "de_mirage", "mode": "wingman",
            "players": [{"steam_id": ASH, "team": "CT"}],
            "clones": [{"clone_id": "donk_v1", "team": "CT"}, {"clone_id": "broky_v1", "team": "T"}]}
    body.update(extra)
    return body


def events(client, match_id):
    return [e["event"] for e in client.get(f"/matches/{match_id}/events").json()]


@pytest.mark.parametrize("record", ["off", "tv"])
def test_full_match(tmp_path, record):
    channel = RecordingChannel()
    with TestClient(create_app(settings(tmp_path, cs2_record=record), channel=channel)) as client:
        full_match(client, channel, tmp_path, record)


def full_match(client, channel, tmp_path, record):
    tv = record == "tv"
    match_id = client.post("/matches", json=wingman()).json()["match_id"]

    wait_sent(channel, "map de_mirage")
    assert channel.sent[:4 if tv else 3] == ["game_type 0", "game_mode 2"] + (["tv_enable 1"] if tv else []) + ["map de_mirage"]
    assert gsi(client).status_code == 200  # CS2 reports the map is loaded

    m = wait_for(client, match_id, "ready")
    assert 'bot_add_ct "donk"' in channel.sent and 'bot_add_t "broky"' in channel.sent
    assert "jointeam 3" in channel.sent  # the human joins CT
    assert channel.sent.index("bot_kick") < channel.sent.index('bot_add_ct "donk"')
    assert m["join_link"] == "steam://connect/127.0.0.1:27015"
    wait_sent(channel, "mp_restartgame 1")
    if tv:
        wait_sent(channel, f"tv_record match_{match_id}")
    # The player's own `record` froze CS2 in Tom's run; it must never be sent.
    assert not any(c.startswith("record") for c in channel.sent)

    gsi(client, phase="live")
    wait_for(client, match_id, "live")

    gsi(client, phase="live", ct=("Alpha", 1))
    gsi(client, phase="live", ct=("Alpha", 3), t=("Bravo", 1))  # two updates missed: still one event per round
    m = client.get(f"/matches/{match_id}").json()
    assert m["score"] == {"CT": 3, "T": 1} and m["round"] == 4

    # Halftime: sides swap. Alpha (started CT) is now on T. The score stays with the team.
    gsi(client, phase="live", ct=("Bravo", 1), t=("Alpha", 3))
    gsi(client, phase="live", ct=("Bravo", 2), t=("Alpha", 3))
    assert client.get(f"/matches/{match_id}").json()["score"] == {"CT": 3, "T": 2}

    (tmp_path / f"match_{match_id}.dem").write_bytes(b"demo")
    gsi(client, phase="gameover", ct=("Bravo", 2), t=("Alpha", 9))
    m = wait_for(client, match_id, "ended")
    assert m["score"] == {"CT": 9, "T": 2} and m["round"] == 11
    assert (channel.sent[-1] == "tv_stoprecord") if tv else ("tv_stoprecord" not in channel.sent)

    evs = events(client, match_id)
    assert evs[:2] == ["match.ready", "match.live"] and evs[-1] == "match.ended"
    assert evs.count("round.ended") == 11
    if tv:
        assert client.get(m["demo_url"].replace("http://localhost:8000", "")).content == b"demo"
    else:
        assert m["demo_url"] is None
        assert client.get(f"/demos/{match_id}.dem").status_code == 404


@pytest.mark.parametrize("glitch", ["names_first", "scores_first"])
def test_halftime_swap_glitch(game, glitch):
    """Tom's match 09a357d5a255: at halftime one update had the team names swapped but not the scores.
    The service jumped from 7-1 to 7-7. The true result was 9-1 in 10 rounds."""
    client, channel = game
    match_id = client.post("/matches", json=wingman(players=[])).json()["match_id"]
    wait_sent(channel, "map de_mirage")
    gsi(client)
    wait_for(client, match_id, "ready")
    wait_sent(channel, "mp_restartgame 1")
    gsi(client, phase="live")
    wait_for(client, match_id, "live")

    gsi(client, phase="live", ct=("Alpha", 7), t=("Bravo", 1))  # Alpha (started CT) leads 7-1
    if glitch == "names_first":
        gsi(client, phase="live", ct=("Bravo", 7), t=("Alpha", 1))  # names swapped, scores not yet
    else:
        gsi(client, phase="live", ct=("Alpha", 1), t=("Bravo", 7))  # scores swapped, names not yet
    gsi(client, phase="live", ct=("Bravo", 1), t=("Alpha", 7))      # both swapped
    assert client.get(f"/matches/{match_id}").json()["score"] == {"CT": 7, "T": 1}

    gsi(client, phase="live", ct=("Bravo", 1), t=("Alpha", 8))
    gsi(client, phase="live", ct=("Bravo", 2), t=("Alpha", 8))  # Bravo wins one after the swap
    gsi(client, phase="gameover", ct=("Bravo", 2), t=("Alpha", 9))
    m = wait_for(client, match_id, "ended")
    assert m["score"] == {"CT": 9, "T": 2} and m["round"] == 11
    assert events(client, match_id).count("round.ended") == 11


def test_live_before_start_is_ignored(tmp_path):
    # Seen on Tom's PC: Bot Mode reported `live` 0.2 s after ready, before the service ended warmup.
    channel = RecordingChannel()
    app = create_app(settings(tmp_path, warmup_seconds=0.5, restart_seconds=0.3), channel=channel)
    with TestClient(app) as client:
        match_id = client.post("/matches", json=wingman()).json()["match_id"]
        wait_sent(channel, "map de_mirage")
        gsi(client)
        wait_for(client, match_id, "ready")
        gsi(client, phase="live", ct=("Alpha", 2))  # rounds played before the match starts
        assert client.get(f"/matches/{match_id}").json()["status"] == "ready"

        wait_sent(channel, "mp_restartgame 1")
        gsi(client, phase="live", ct=("Alpha", 2))  # still within the restart wait
        assert client.get(f"/matches/{match_id}").json()["status"] == "ready"

        time.sleep(0.4)
        gsi(client, phase="live")  # after the restart: 0-0
        m = wait_for(client, match_id, "live")
        assert m["score"] == {"CT": 0, "T": 0} and m["round"] == 0


def test_bot_vs_bot_spectates(game):
    client, channel = game
    body = wingman(players=[], clones=[{"clone_id": "donk_v1", "team": "CT"}, {"clone_id": "broky_v1", "team": "T"}])
    match_id = client.post("/matches", json=body).json()["match_id"]
    wait_sent(channel, "map de_mirage")
    gsi(client)
    wait_for(client, match_id, "ready")
    assert "jointeam 1" in channel.sent


def test_one_match_at_a_time(game):
    client, _ = game
    client.post("/matches", json=wingman())
    assert client.post("/matches", json=wingman()).status_code == 409


def test_rejects_what_cs2_cannot_do(game):
    client, _ = game
    two_humans = wingman(players=[{"steam_id": ASH, "team": "CT"}, {"steam_id": "76561198000000002", "team": "T"}],
                         clones=[{"clone_id": "donk_v1", "team": "CT"}])
    r = client.post("/matches", json=two_humans)
    assert r.status_code == 422 and any("at most one human" in e for e in r.json()["detail"])

    no_stand_in = wingman(clones=[{"clone_id": "ash_v1", "team": "CT"}, {"clone_id": "broky_v1", "team": "T"}])
    r = client.post("/matches", json=no_stand_in)
    assert r.status_code == 422 and any("No stand_in_bot" in e for e in r.json()["detail"])


def test_console_unreachable(tmp_path):
    channel = RecordingChannel()
    channel.fail_with = ConnectionRefusedError("refused")
    with TestClient(create_app(settings(tmp_path), channel=channel)) as client:
        match_id = client.post("/matches", json=wingman()).json()["match_id"]
        m = wait_for(client, match_id, "failed")
        assert "Can't reach the CS2 console" in m["error"]
        assert events(client, match_id) == ["match.failed"]


def test_map_never_loads(tmp_path):
    with TestClient(create_app(settings(tmp_path, map_load_seconds=0.2), channel=RecordingChannel())) as client:
        match_id = client.post("/matches", json=wingman()).json()["match_id"]
        assert "did not report map" in wait_for(client, match_id, "failed")["error"]


def test_wrong_token(game):
    client, _ = game
    assert gsi(client, token="nope").status_code == 401


def test_stop(game):
    client, channel = game
    match_id = client.post("/matches", json=wingman()).json()["match_id"]
    wait_sent(channel, "map de_mirage")
    gsi(client)
    wait_for(client, match_id, "ready")
    assert client.post(f"/matches/{match_id}/stop").json() == {"status": "ended"}
    assert channel.sent[-1] == "bot_kick" and "stop" not in channel.sent
    # The game is free again.
    assert client.post("/matches", json=wingman()).status_code == 201


def test_gsi_is_404_on_mock():
    with TestClient(create_app(Settings())) as client:
        assert client.post("/gsi", json={}).status_code == 404


def test_netcon_channel_against_a_fake_console():
    """NetconChannel speaks plain lines over TCP. A tiny local server stands in for CS2."""
    received: list[str] = []

    async def scenario():
        async def handle(reader, writer):
            while line := await reader.readline():
                text = line.decode().strip()
                received.append(text)
                if text.startswith("echo "):
                    writer.write(f"{text[5:]}\n".encode())
                    await writer.drain()
            writer.close()

        server = await asyncio.start_server(handle, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        channel = NetconChannel("127.0.0.1", port)
        await channel.send(["bot_kick", 'bot_add_ct "donk"'])
        out = await channel.query("echo hello", wait_seconds=0.3)
        server.close()
        return out

    out = asyncio.run(scenario())
    assert received == ["bot_kick", 'bot_add_ct "donk"', "echo hello"]
    assert "hello" in out
