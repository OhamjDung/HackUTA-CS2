"""Playing against one clone must not bring a random extra bot (match_service/backends/cs2.py, _settle_bots).

The bot base fills a bot quota of 2, so one clone alone gets a random second bot; two clones (bot vs bot)
already fill it. The fix kicks the extra bots by name and sets the quota to the number of clones.
The game is a fake here. Nothing ran in CS2 in these tests.
"""

import pytest
from fastapi.testclient import TestClient

from match_service.console import RecordingChannel
from match_service.main import create_app
from tests.test_cs2 import ASH, gsi, settings, wait_for, wait_sent

STATUS = """   0    00:40    0    0     active 786432 'Chickencup'
   1 [NoChan]    0    0     active      0 'broky'
   2 [NoChan]    0    0     active      0 '{extra}'
65535 [NoChan]    0    0 challenging      0 ''
"""
ONE_CLONE = {"map": "de_mirage", "mode": "wingman", "players": [{"steam_id": ASH, "team": "CT"}],
             "clones": [{"clone_id": "broky_v1", "team": "T"}]}


def play(tmp_path, status_text, body=ONE_CLONE, **extra):
    channel = RecordingChannel()
    channel.status_text = status_text
    with TestClient(create_app(settings(tmp_path, **extra), channel=channel)) as client:
        match_id = client.post("/matches", json=body).json()["match_id"]
        wait_sent(channel, "map de_mirage")
        gsi(client)
        wait_for(client, match_id, "ready")
    return channel.sent


def test_extra_bot_is_kicked_and_quota_set_to_the_clone_count(tmp_path):
    sent = play(tmp_path, STATUS.format(extra="Yamii"))
    assert 'bot_kick "Yamii"' in sent and "bot_quota 1" in sent
    # The kick comes first: lowering the quota first would remove a random bot, possibly the clone.
    assert sent.index('bot_kick "Yamii"') < sent.index("bot_quota 1")
    assert 'bot_kick "broky"' not in sent


def test_no_extra_bot_still_fixes_the_quota(tmp_path):
    sent = play(tmp_path, STATUS.format(extra="").replace("2 [NoChan]    0    0     active      0 ''\n", ""))
    assert "bot_quota 1" in sent and not [c for c in sent if c.startswith('bot_kick "')]


def test_nothing_is_kicked_if_the_clone_is_not_there(tmp_path):
    # If the clone's bot is not in `status`, an unknown bot might be the clone under another name.
    status = STATUS.format(extra="Yamii").replace("'broky'", "'somebody'")
    sent = play(tmp_path, status)
    assert not [c for c in sent if c.startswith('bot_kick "')] and "bot_quota 1" not in sent


def test_unusual_bot_name_is_left_alone(tmp_path):
    sent = play(tmp_path, STATUS.format(extra="a b"))
    assert not [c for c in sent if c.startswith('bot_kick "')] and "bot_quota 1" not in sent


def test_two_clones_set_the_quota_to_two(tmp_path):
    status = STATUS.format(extra="").replace("2 [NoChan]    0    0     active      0 ''\n",
                                             "2 [NoChan]    0    0     active      0 'donk'\n")
    body = {"map": "de_mirage", "mode": "wingman", "players": [],
            "clones": [{"clone_id": "donk_v1", "team": "CT"}, {"clone_id": "broky_v1", "team": "T"}]}
    sent = play(tmp_path, status, body)
    assert "bot_quota 2" in sent and not [c for c in sent if c.startswith('bot_kick "')]


def test_bots_that_come_back_after_the_restart_are_kicked_again(tmp_path):
    """Tom's 2026-11-15 run: four bots in a two-clone wingman match. The bot base refills on mp_restartgame."""
    import time
    channel = RecordingChannel()
    two = STATUS.format(extra="").replace("2 [NoChan]    0    0     active      0 ''\n",
                                          "2 [NoChan]    0    0     active      0 'donk'\n")
    channel.status_text = two
    body = {"map": "de_mirage", "mode": "wingman", "players": [],
            "clones": [{"clone_id": "donk_v1", "team": "CT"}, {"clone_id": "broky_v1", "team": "T"}]}
    with TestClient(create_app(settings(tmp_path, cs2_recheck_seconds=(0.3,)), channel=channel)) as client:
        match_id = client.post("/matches", json=body).json()["match_id"]
        wait_sent(channel, "map de_mirage")
        gsi(client)
        wait_for(client, match_id, "ready")
        wait_sent(channel, "mp_restartgame 1")
        assert not [c for c in channel.sent if c.startswith('bot_kick "')]
        # The restart brings two random bots back.
        channel.status_text = two + "   3 [NoChan]    0    0     active      0 'Yamii'\n   4 [NoChan]    0    0     active      0 'Rex'\n"
        deadline = time.time() + 3
        while 'bot_kick "Rex"' not in channel.sent and time.time() < deadline:
            time.sleep(0.02)
    sent = channel.sent
    assert 'bot_kick "Yamii"' in sent and 'bot_kick "Rex"' in sent
    assert sent.index('bot_kick "Rex"') > sent.index("mp_restartgame 1")
    assert sent[-1] == "bot_quota 2" or "bot_quota 2" in sent[sent.index('bot_kick "Rex"'):]
    assert 'bot_kick "donk"' not in sent and 'bot_kick "broky"' not in sent
