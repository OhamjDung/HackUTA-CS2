"""Values that end up in console commands can't smuggle in a second command."""

import asyncio
import json

import pytest

from match_service.console import NetconChannel, PluginChannel, RconChannel, RecordingChannel, UnsafeCommand, check
from match_service.core import load_clones

BAD = ['bot_add_ct "x"; rcon_password stolen', 'bot_add_ct "x"\nquit', "say hi\rquit"]


@pytest.mark.parametrize("command", BAD)
def test_check_refuses_second_commands(command):
    with pytest.raises(UnsafeCommand):
        check(["mp_warmup_end", command])


def test_check_allows_normal_commands():
    ok = ['bot_add_ct "donk"', 'mp_teamname_1 "Alpha"', "map de_mirage", "record match_1"]
    assert check(ok) == ok


def test_every_channel_refuses_before_connecting():
    # Port 1 has nothing listening: a channel that tried to connect would raise ConnectionError.
    channels = [NetconChannel("127.0.0.1", 1), RconChannel("127.0.0.1", 1, "pw"),
                PluginChannel("127.0.0.1", 1, "tok"), RecordingChannel()]
    for channel in channels:
        with pytest.raises(UnsafeCommand):
            asyncio.run(channel.send(["status", BAD[0]]))
    assert channels[-1].sent == []


def write(folder, clone_id, stand_in):
    (folder / f"{clone_id}.json").write_text(json.dumps(
        {"clone_id": clone_id, "display_name": clone_id, "source": "pro", "stand_in_bot": stand_in}))


def test_bad_stand_in_bot_profile_is_skipped(tmp_path):
    write(tmp_path, "good", "donk")
    write(tmp_path, "quote", 'donk"; quit; "')
    write(tmp_path, "newline", "donk\nquit")
    write(tmp_path, "space", "two words")
    assert list(load_clones(tmp_path)) == ["good"]
