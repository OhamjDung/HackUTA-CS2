"""Death coach (coach.py): advice text, chat commands, Gemini and ElevenLabs calls. All against fakes."""

import asyncio
import json
import os
import time

import httpx
from fastapi.testclient import TestClient

from match_service.coach import (CHAT_LINE, Coach, CoachSettings, chat_lines, clean_text, death_summary,
                                 read_env_file)
from match_service.console import RecordingChannel, check
from match_service.feedback import feedback_for
from match_service.main import Settings, create_app

from .test_puzzles import make_puzzle

SEED = "pro_2393226_r7_donk"


class FakeSink:
    def __init__(self):
        self.audio = b""

    async def play(self, chunks):
        async for c in chunks:
            self.audio += c


def fake_apis(gemini_text="Throw your molotov before you peek, and wait for a trade.", gemini_status=200):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if "generativelanguage" in request.url.host:
            if gemini_status != 200:
                return httpx.Response(gemini_status, text="boom")
            return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": gemini_text}]}}]})
        if "elevenlabs" in request.url.host:
            return httpx.Response(200, content=b"\x01\x00" * 600)
        return httpx.Response(404)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler)), calls


def make_coach(tmp_path, client, said, **kw):
    async def say(commands):
        said.extend(check(commands))
    s = CoachSettings(**{"gemini_api_key": "", "elevenlabs_api_key": "", "elevenlabs_voice_id": "", **kw})
    sink = FakeSink()
    return Coach(s, tmp_path, lambda: client, say, sink), sink


# --- text ------------------------------------------------------------------------------------------

def test_clean_text_removes_command_breakers_and_markdown():
    t = clean_text('**Peek** with a flash;\nquit "now"\x00 `ok`')
    assert ";" not in t and '"' not in t and "\n" not in t and "*" not in t and "`" not in t
    assert t == "Peek with a flash quit now ok"
    assert len(clean_text("word " * 200)) <= 223


def test_chat_lines_are_short_safe_say_commands():
    lines = chat_lines("You " + "really " * 60 + "should trade.")
    assert 1 <= len(lines) <= 2
    assert all(l.startswith("say [Coach] ") and len(l) - len("say ") <= CHAT_LINE for l in lines)
    assert lines[-1].endswith("...")
    check(lines)  # the console channels accept them


def test_summary_has_killer_utility_and_findings():
    p = make_puzzle()
    s = death_summary(p, feedback_for(p))
    assert s["killed_by"] == {"name": "e1", "weapon": "ak47"}
    assert s["utility_carried"] == ["flashbang"] and s["utility_thrown"] == []
    assert s["player"]["weapon_at_death"] == "ak47"
    assert s["alive_near_at_death_units"]["enemies"][0]["name"] in ("e1", "e2")
    assert any("team" in f["title"] for f in s["rule_findings"])


def test_env_file_is_read_and_environment_wins(tmp_path):
    f = tmp_path / ".env"
    f.write_text('# keys\nGEMINI_API_KEY="g-key"\nexport ELEVENLABS_API_KEY=e-key\nELEVENLABS_VOICE_ID=v1\n')
    assert read_env_file(f)["GEMINI_API_KEY"] == "g-key"
    s = CoachSettings.from_env({"ELEVENLABS_VOICE_ID": "v2", "COACH_VOICE": "off"}, env_file=f)
    assert s.gemini_api_key == "g-key" and s.elevenlabs_api_key == "e-key" and s.elevenlabs_voice_id == "v2"
    assert s.enabled and not s.can_speak()
    assert not CoachSettings.from_env({"COACH": "off"}).enabled
    assert read_env_file(tmp_path / "missing") == {}


# --- one death -------------------------------------------------------------------------------------

def test_without_keys_the_rule_finding_goes_to_chat_and_nothing_is_called(tmp_path):
    client, calls = fake_apis()
    said = []
    coach, sink = make_coach(tmp_path, client, said)
    r = asyncio.run(coach.coach(make_puzzle()))
    assert r["source"] == "rules" and r["chat"] and not r["voice"]
    assert said and said[0].startswith("say [Coach] ")
    assert calls == [] and sink.audio == b""


def test_gemini_writes_the_advice_and_elevenlabs_speaks_it(tmp_path):
    client, calls = fake_apis()
    said = []
    coach, sink = make_coach(tmp_path, client, said, gemini_api_key="g-key",
                             elevenlabs_api_key="e-key", elevenlabs_voice_id="voice123")
    r = asyncio.run(coach.coach(make_puzzle()))
    assert r["source"] == "gemini" and r["chat"] and r["voice"] and not r["errors"]
    assert said == ["say [Coach] Throw your molotov before you peek, and wait for a trade."]
    gem, eleven = calls
    assert gem.headers["x-goog-api-key"] == "g-key" and "key=" not in str(gem.url)
    body = json.loads(gem.content)
    assert "systemInstruction" in body and body["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "MINIMAL"}
    assert json.loads(body["contents"][0]["parts"][0]["text"])["killed_by"]["name"] == "e1"
    assert eleven.url.path == "/v1/text-to-speech/voice123/stream"
    assert eleven.url.params["output_format"] == "pcm_24000" and eleven.headers["xi-api-key"] == "e-key"
    assert json.loads(eleven.content) == {"text": r["text"], "model_id": "eleven_flash_v2_5"}
    assert len(sink.audio) == 1200


def test_gemini_failure_falls_back_to_rules(tmp_path):
    client, _ = fake_apis(gemini_status=500)
    said = []
    coach, _ = make_coach(tmp_path, client, said, gemini_api_key="g-key")
    r = asyncio.run(coach.coach(make_puzzle()))
    assert r["source"] == "rules" and said


def test_trash_talk_uses_match_style_and_roasts_even_without_gemini(tmp_path):
    client, calls = fake_apis()
    s = CoachSettings(gemini_api_key="g-key", voice=False, chat=False)
    coach = Coach(s, tmp_path, lambda: client, None, FakeSink(),
                  match=lambda: {"human_team": "CT", "clones": [], "coach_style": "trash_talk"})
    asyncio.run(coach.coach(make_puzzle()))
    body = json.loads(calls[0].content)
    assert "roast" in body["systemInstruction"]["parts"][0]["text"].lower()

    no_key = Coach(CoachSettings(voice=False, chat=False), tmp_path, lambda: client, None, FakeSink(),
                   match=lambda: {"human_team": "CT", "clones": [], "coach_style": "trash_talk"})
    result = asyncio.run(no_key.coach(make_puzzle()))
    assert result["text"].startswith("Nice try")


def test_match_coach_style_is_scoped_and_validated(tmp_path):
    settings = Settings(puzzle_dir=tmp_path / "p", death_dir=tmp_path / "d", coach=CoachSettings(enabled=True))
    with TestClient(create_app(settings)) as client:
        body = {"map": "de_mirage", "mode": "wingman", "players": [{"steam_id": "76561198000000000", "team": "CT"}],
                "clones": [{"clone_id": "donk_v1", "team": "T"}]}
        match_id = client.post("/matches", json=body).json()["match_id"]
        assert client.put(f"/coach/matches/{match_id}/style", json={"style": "trash_talk"}).status_code == 200
        assert client.get("/coach").json()["match"]["coach_style"] == "trash_talk"
        assert client.put(f"/coach/matches/{match_id}/style", json={"style": "other"}).status_code == 422
        assert client.put("/coach/matches/missing/style", json={"style": "advice"}).status_code == 404


def test_gemini_text_cannot_inject_console_commands(tmp_path):
    client, _ = fake_apis(gemini_text='Nice try"; quit; say "pwned\nkill')
    said = []
    coach, _ = make_coach(tmp_path, client, said, gemini_api_key="g-key")
    asyncio.run(coach.coach(make_puzzle()))
    assert said == ["say [Coach] Nice try quit say pwned kill"]


def test_chat_failure_still_speaks(tmp_path):
    client, _ = fake_apis()

    async def broken(commands):
        raise ConnectionError("console gone")
    s = CoachSettings(elevenlabs_api_key="e", elevenlabs_voice_id="v")
    sink = FakeSink()
    r = asyncio.run(Coach(s, tmp_path, lambda: client, broken, sink).coach(make_puzzle()))
    assert not r["chat"] and r["voice"] and sink.audio and "console gone" in r["errors"][0]


# --- watching the deaths folder --------------------------------------------------------------------

def test_watcher_coaches_each_new_death_once_and_skips_old_ones(tmp_path):
    client, _ = fake_apis()
    said = []
    coach, _ = make_coach(tmp_path, client, said)
    (tmp_path / "before.json").write_text(json.dumps(make_puzzle("before")))

    async def run():
        coach.seen = {p.name for p in coach._files()}  # what start() does
        (tmp_path / "new.json").write_text(json.dumps(make_puzzle("new")))
        stale = tmp_path / "stale.json"
        stale.write_text(json.dumps(make_puzzle("stale")))
        old = time.time() - 120
        os.utime(stale, (old, old))
        first = await coach.check_once()
        second = await coach.check_once()
        return first, second

    first, second = asyncio.run(run())
    assert [r["death_id"] for r in first] == ["new"] and second == []


# --- routes ----------------------------------------------------------------------------------------

def test_routes_on_the_cs2_backend_send_chat_through_matchbridge(tmp_path):
    main, bridge = RecordingChannel(), RecordingChannel()
    deaths = tmp_path / "deaths"
    deaths.mkdir()
    (deaths / "d1.json").write_text(json.dumps(make_puzzle("d1")))
    settings = Settings(backend="cs2", cs2_bots="clone", death_dir=deaths, puzzle_dir=tmp_path / "p",
                        coach=CoachSettings(enabled=True))
    with TestClient(create_app(settings, channel=main, clone_channel=bridge)) as client:
        status = client.get("/coach").json()
        assert status["enabled"] and status["chat"] and not status["gemini"] and not status["voice"]
        r = client.post("/coach/deaths/d1").json()
        assert r["source"] == "rules" and r["chat"]
        assert bridge.sent and all(c.startswith("say [Coach] ") for c in bridge.sent)
        assert main.sent == []
        assert client.post(f"/coach/puzzles/{SEED}").json()["death_id"] == SEED
        assert client.post("/coach/deaths/nope").status_code == 404
        assert client.get("/coach").json()["last"]["death_id"] == SEED


def test_mock_backend_has_no_chat(tmp_path):
    settings = Settings(puzzle_dir=tmp_path / "p", death_dir=tmp_path / "d", coach=CoachSettings(enabled=True))
    with TestClient(create_app(settings)) as client:
        assert not client.get("/coach").json()["chat"]
        r = client.post(f"/coach/puzzles/{SEED}").json()
        assert r["text"] and not r["chat"]


# --- whose voice ----------------------------------------------------------------------------------

from match_service.coach import player_of, speaker_for  # noqa: E402

VOICES = {"donk": "voice-donk", "broky": "voice-broky"}


def test_player_of_strips_clone_versions():
    assert [player_of(c) for c in ("donk_v1", "donk_v2", "donkL", "donkL2", "donkLF", "brokyL", "broky_v1")] == \
        ["donk"] * 5 + ["broky"] * 2
    assert player_of(None) is None


def test_voices_come_from_one_variable_per_player(tmp_path):
    s = CoachSettings.from_env({"ELEVENLABS_API_KEY": "e", "ELEVENLABS_VOICE_DONK": "vd",
                                "ELEVENLABS_VOICE_BROKY": "vb", "ELEVENLABS_VOICE_ID": "vdef"})
    assert s.voices == {"donk": "vd", "broky": "vb"} and s.can_speak()
    assert s.voice_for("donk") == "vd" and s.voice_for("ash") == "vdef" and s.voice_for(None) == "vdef"
    assert CoachSettings.from_env({"ELEVENLABS_VOICE_DONK": "vd"}).voice_for("broky") is None


def test_teammate_clone_speaks_before_the_opponent():
    match = {"human_team": "CT", "clones": [{"clone_id": "brokyL", "team": "T"}, {"clone_id": "donk_v2", "team": "CT"}]}
    assert speaker_for(make_puzzle(), match, VOICES) == {"player": "donk", "clone_id": "donk_v2", "relation": "teammate"}
    alone = {"human_team": "CT", "clones": [{"clone_id": "brokyL2", "team": "T"}]}
    assert speaker_for(make_puzzle(), alone, VOICES)["relation"] == "opponent"
    assert speaker_for(make_puzzle(), alone, VOICES)["player"] == "broky"


def test_without_a_match_the_death_file_names_pick_the_voice():
    p = make_puzzle()
    p["players"][1]["name"] = "donkL"   # the teammate
    p["players"][2]["name"] = "broky_v1"  # an enemy
    assert speaker_for(p, None, VOICES)["player"] == "donk"
    assert speaker_for(make_puzzle(), None, VOICES) is None


def test_the_matched_players_voice_is_used_for_speech_and_chat(tmp_path):
    client, calls = fake_apis()
    said = []
    s = CoachSettings(gemini_api_key="g", elevenlabs_api_key="e", elevenlabs_voice_id="vdef", voices=dict(VOICES))
    sink = FakeSink()

    async def say(commands):
        said.extend(check(commands))
    match = {"human_team": "T", "clones": [{"clone_id": "brokyLF", "team": "T"}, {"clone_id": "donkL", "team": "CT"}]}
    r = asyncio.run(Coach(s, tmp_path, lambda: client, say, sink, match=lambda: match).coach(make_puzzle()))
    assert r["speaker"]["player"] == "broky" and r["voice_id"] == "voice-broky" and r["voice"]
    gem, eleven = calls
    assert json.loads(json.loads(gem.content)["contents"][0]["parts"][0]["text"])["speaking_as"]["player"] == "broky"
    assert eleven.url.path == "/v1/text-to-speech/voice-broky/stream"
    assert said[0].startswith("say [broky AI] ")


def test_poseidon_uses_god_voice_and_roast_with_advice(tmp_path):
    client, calls = fake_apis()
    s = CoachSettings(gemini_api_key="g", elevenlabs_api_key="e", voices={"poseidon": "god-voice"})
    match = {"human_team": "CT", "clones": [{"clone_id": "poseidon", "team": "T"}]}
    result = asyncio.run(Coach(s, tmp_path, lambda: client, None, FakeSink(), match=lambda: match).coach(make_puzzle()))
    assert result["voice_id"] == "god-voice" and result["voice"]
    prompt = json.loads(calls[0].content)["systemInstruction"]["parts"][0]["text"].lower()
    assert "poseidon" in prompt and "roast" in prompt and "advice" in prompt
    assert calls[1].url.path.endswith('/god-voice/stream')


def test_no_voice_for_the_player_and_no_default_stays_quiet(tmp_path):
    client, calls = fake_apis()
    s = CoachSettings(elevenlabs_api_key="e", voices={"donk": "vd"})
    match = {"human_team": "CT", "clones": [{"clone_id": "broky_v1", "team": "CT"}]}
    r = asyncio.run(Coach(s, tmp_path, lambda: client, None, FakeSink(), match=lambda: match).coach(make_puzzle()))
    assert r["voice_id"] is None and not r["voice"] and calls == []


def test_the_running_match_picks_the_voice_through_the_api(tmp_path):
    settings = Settings(start_seconds=0.01, warmup_seconds=0.01, round_seconds=30, puzzle_dir=tmp_path / "p",
                        death_dir=tmp_path / "d", coach=CoachSettings(enabled=True, voices=dict(VOICES)))
    with TestClient(create_app(settings)) as client:
        body = {"map": "de_mirage", "mode": "wingman", "players": [{"steam_id": "76561198000000001", "team": "T"}],
                "clones": [{"clone_id": "broky_v1", "team": "T"}, {"clone_id": "donk_v1", "team": "CT"}]}
        assert client.post("/matches", json=body).status_code == 201
        assert client.get("/coach").json()["match"]["human_team"] == "T"
        r = client.post(f"/coach/puzzles/{SEED}").json()
        assert r["speaker"] == {"player": "broky", "clone_id": "broky_v1", "relation": "teammate"}
        assert r["voice_id"] == "voice-broky"  # no ElevenLabs key here, so nothing is spoken
        assert not r["voice"]


def test_env_files_accept_bom_utf16_aliases_and_a_second_file(tmp_path):
    first, second = tmp_path / "service.env", tmp_path / "root.env"
    first.write_bytes("﻿ELEVENLABS_VOICE_DONK=vd\nGEMINI_API_KEY=\n".encode("utf-8"))
    second.write_bytes("GOOGLE_API_KEY=g-root\r\nXI_API_KEY=e-root\r\nELEVENLABS_VOICE_DONK=other\r\n".encode("utf-16"))
    s = CoachSettings.from_env({}, env_file=[first, second])
    assert s.voices == {"donk": "vd"}  # the first file wins
    assert s.gemini_api_key == "g-root" and s.elevenlabs_api_key == "e-root"  # empty line does not hide the other file
    assert CoachSettings.from_env({"GEMINI_API_KEY": "env"}, env_file=[first, second]).gemini_api_key == "env"
