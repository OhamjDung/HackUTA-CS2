import json
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from match_service.feedback import feedback_for
from match_service.main import Settings, create_app
from match_service.puzzles import (PuzzleStore, daily_pick, is_solved, needed_kills, new_ratings,
                                   validate_puzzle)


def samples(points, hp=100, weapon="ak47", fire=()):
    """points: [(t, x, y)]"""
    return [{"t": t, "x": x, "y": y, "z": 0, "yaw": 0, "pitch": 0, "hp": hp, "weapon": weapon,
             "fire": t in fire} for t, x, y in points]


def make_puzzle(pid="p1", kills=1, died=True, alone=True, **extra):
    """Hero (CT) walks toward two T players and dies at t=8. A teammate is near or far."""
    hero_pts = [(t / 2, 100 + t * 30, 0) for t in range(0, 17)]           # t = 0..8, moving at 60 u/s
    hero = {"slot": 1, "name": "hero", "side": "CT", "hero": True,
            "start": {"health": 100, "armor": 100, "money": 800, "weapons": ["ak47", "flashbang"]},
            "track": samples(hero_pts, fire=(7.0, 7.5))}
    mate_x = 3000 if alone else 150
    mate = {"slot": 2, "name": "mate", "side": "CT", "track": samples([(t / 2, mate_x, 0) for t in range(17)])}
    e1 = {"slot": 6, "name": "e1", "side": "T", "track": samples([(t / 2, 900, 0) for t in range(17)])}
    e2 = {"slot": 7, "name": "e2", "side": "T", "track": samples([(t / 2, 800, 300) for t in range(17)])}
    hero_dead = hero["track"][-1]
    hero_dead["hp"] = 0
    events = [{"t": 8.0, "type": "kill", "attacker": "e1", "victim": "hero", "weapon": "ak47"}]
    puzzle = {"id": pid, "title": "Test moment", "map": "de_mirage", "source": "user", "window_seconds": 10,
              "players": [hero, mate, e1, e2], "events": events,
              "original": {"kills": kills, "died": died, "killer": "e1", "weapon": "ak47"},
              "tags": ["retake"], **extra}
    return puzzle


# --- rules ---------------------------------------------------------------------------------------

def test_needed_kills_has_a_floor_of_one():
    assert needed_kills(0) == 1
    assert needed_kills(2) == 3


def test_solve_rule(tmp_path):
    p = validate_puzzle(make_puzzle(kills=1))
    assert is_solved(p, survived=True, kills=2)
    assert not is_solved(p, survived=True, kills=1)    # tie fails
    assert not is_solved(p, survived=False, kills=3)   # died
    assert is_solved(validate_puzzle(make_puzzle(pid="p0", kills=0)), True, 1)


def test_elo_moves_the_right_way():
    player, puzzle = new_ratings(1500, 1500, True)
    assert player == pytest.approx(1516) and puzzle == pytest.approx(1492)
    player, puzzle = new_ratings(1500, 1500, False)
    assert player == pytest.approx(1484) and puzzle == pytest.approx(1508)
    # a solve of a much harder puzzle moves the player more than an easy one
    assert new_ratings(1400, 1800, True)[0] - 1400 > new_ratings(1800, 1400, True)[0] - 1800


def test_daily_is_stable_for_a_date_and_changes_over_dates():
    ids = ["a", "b", "c", "d", "e"]
    assert daily_pick(ids, date(2026, 11, 15)) == daily_pick(list(reversed(ids)), date(2026, 11, 15))
    assert len({daily_pick(ids, date(2026, 11, d)) for d in range(1, 29)}) > 1
    assert daily_pick([], date(2026, 11, 15)) is None


@pytest.mark.parametrize("change,message", [
    (lambda p: p["players"][0].update(hero=False), "exactly one hero"),
    (lambda p: p["players"][1].update(slot=1), "share a slot"),
    (lambda p: p["players"][1].update(name="hero"), "share a name"),
    (lambda p: p.update(id="../evil"), "id must be"),
])
def test_validation_refuses_bad_puzzles(change, message):
    data = make_puzzle()
    change(data)
    with pytest.raises(ValueError, match=message):
        validate_puzzle(data)


# --- feedback ------------------------------------------------------------------------------------

def test_feedback_names_the_key_mistakes():
    items = feedback_for(validate_puzzle(make_puzzle(alone=True)).model_dump())
    ids = [i["id"] for i in items]
    assert len(items) <= 3
    assert "alone" in ids and "crossfire" in ids          # the two highest-severity rules
    assert all(i["title"] and i["detail"] and 1 <= i["severity"] <= 3 for i in items)


def test_feedback_is_quiet_when_the_hero_did_not_die():
    data = make_puzzle()
    data["events"] = []
    assert feedback_for(validate_puzzle(data).model_dump()) == []


def test_not_alone_when_a_teammate_is_close():
    ids = [i["id"] for i in feedback_for(validate_puzzle(make_puzzle(alone=False)).model_dump())]
    assert "alone" not in ids


def test_utility_rule_sees_a_thrown_flash():
    data = make_puzzle()
    data["events"].append({"t": 5.0, "type": "throw", "attacker": "hero", "weapon": "flashbang"})
    ids = [i["id"] for i in feedback_for(validate_puzzle(data).model_dump())]
    assert "no_utility" not in ids


# --- store and API -------------------------------------------------------------------------------

@pytest.fixture
def client(tmp_path):
    seed = tmp_path / "seed"
    seed.mkdir()
    (seed / "seed1.json").write_text(json.dumps(make_puzzle("seed1", source="pro")), encoding="utf-8")
    settings = Settings(puzzle_dir=tmp_path / "puzzles", puzzle_seed_dir=seed, death_dir=tmp_path / "deaths")
    with TestClient(create_app(settings)) as c:
        c.tmp = tmp_path
        yield c


def test_seed_puzzles_are_listed_with_stats(client):
    rows = client.get("/puzzles").json()
    assert [r["id"] for r in rows] == ["seed1"]
    assert rows[0]["rating"] == 1500 and rows[0]["need_kills"] == 2 and rows[0]["hero"] == "hero"
    assert client.get("/puzzles?tag=retake").json() and not client.get("/puzzles?tag=nope").json()
    assert client.get("/puzzles?sort=bad").status_code == 422


def test_action_seed_puzzles_have_full_windows_and_combat():
    seed_dir = Path(__file__).resolve().parents[1] / "seed_puzzles"
    for puzzle_id in ("pro_2393226_r9_donk", "pro_2393024_r19_broky"):
        puzzle = validate_puzzle(json.loads((seed_dir / f"{puzzle_id}.json").read_text(encoding="utf-8")))
        assert puzzle.window_seconds == 30
        hero = next(player for player in puzzle.players if player.hero)
        assert any(event.type == "kill" and event.attacker == hero.name and event.t < 30 for event in puzzle.events)
        assert len([player for player in puzzle.players if player.side != hero.side and player.start.health > 0]) >= 2


def test_get_puzzle_includes_the_document_and_feedback(client):
    body = client.get("/puzzles/seed1").json()
    assert body["puzzle"]["players"][0]["name"] == "hero" and body["feedback"]
    assert client.get("/puzzles/missing").status_code == 404
    assert client.get("/puzzles/..%2Fx").status_code == 404


def test_result_updates_ratings_streak_and_history(client):
    r = client.post("/puzzles/seed1/result", json={"player": "tom", "survived": True, "kills": 2}).json()
    assert r["solved"] and r["rating_change"] > 0 and r["player"]["streak"] == 1 and r["puzzle_rating"] < 1500
    r = client.post("/puzzles/seed1/result", json={"player": "tom", "survived": False, "kills": 3}).json()
    assert not r["solved"] and r["player"]["streak"] == 0 and r["player"]["best_streak"] == 1
    me = client.get("/players/tom").json()
    assert me["attempts"] == 2 and me["solved"] == 1
    assert [h["solved"] for h in client.get("/players/tom/history").json()] == [0, 1]
    assert client.get("/puzzles/seed1").json()["plays"] == 2


def test_votes_are_one_per_player(client):
    client.post("/puzzles/seed1/vote", json={"player": "a", "value": 1})
    client.post("/puzzles/seed1/vote", json={"player": "a", "value": 1})
    v = client.post("/puzzles/seed1/vote", json={"player": "b", "value": -1}).json()
    assert v == {"up": 1, "down": 1}
    assert client.post("/puzzles/seed1/vote", json={"player": "a", "value": 5}).status_code == 422


def test_save_a_puzzle_then_delete_it(client):
    created = client.post("/puzzles", json=make_puzzle("mine", source="user"))
    assert created.status_code == 201
    assert {r["id"] for r in client.get("/puzzles").json()} == {"seed1", "mine"}
    assert client.post("/puzzles", json=make_puzzle("mine")).status_code == 422       # id taken
    assert client.delete("/puzzles/mine").status_code == 200
    assert client.delete("/puzzles/seed1").status_code == 404                        # seed stays


def test_next_puzzle_prefers_unsolved_near_the_rating(client):
    client.post("/puzzles", json=make_puzzle("second"))
    client.post("/puzzles/seed1/result", json={"player": "tom", "survived": True, "kills": 2})
    assert client.get("/puzzles/next?player=tom").json()["id"] == "second"
    assert client.get("/puzzles/daily").json()["id"] in {"seed1", "second"}


def test_death_to_puzzle_flow(client):
    deaths = client.tmp / "deaths"
    deaths.mkdir()
    (deaths / "d1.json").write_text(json.dumps(make_puzzle("d1")), encoding="utf-8")
    assert client.get("/deaths").json()[0]["id"] == "d1"
    latest = client.get("/deaths/latest").json()
    assert latest["id"] == "d1" and latest["feedback"]
    saved = client.post("/deaths/d1/save", json={"title": "My fight", "tags": ["entry"]})
    assert saved.status_code == 201 and saved.json()["title"] == "My fight"
    assert client.get("/deaths/..%2Fsecret").status_code == 404


def test_practice_in_cs2_needs_the_cs2_backend(client):
    r = client.post("/puzzles/seed1/start", json={"player": "tom"})
    assert r.status_code == 409 and "cs2" in r.json()["detail"]


def test_multi_pov_draft_stores_footage_and_says_it_is_not_derived(client):
    slots = [{"name": "a", "side": "CT"}, {"name": "b", "side": "T"}]
    d = client.post("/puzzles/drafts", json={"title": "Clip", "slots": slots}).json()
    assert d["status"] == "awaiting_footage"
    r = client.put(f"/puzzles/drafts/{d['id']}/pov/0?ext=.mp4", content=b"x" * 100)
    assert r.status_code == 200 and r.json()["status"] == "awaiting_footage"
    r = client.put(f"/puzzles/drafts/{d['id']}/pov/1?ext=.webm", content=b"y" * 50).json()
    assert r["status"] == "needs_derivation" and "not built" in r["message"]
    assert [s["bytes"] for s in r["slots"]] == [100, 50]
    assert client.put(f"/puzzles/drafts/{d['id']}/pov/0?ext=.exe", content=b"z").status_code == 422
    assert client.put(f"/puzzles/drafts/{d['id']}/pov/5", content=b"z").status_code == 404
    assert client.put(f"/puzzles/drafts/{d['id']}/pov/0", content=b"").status_code == 422
    bad = [{"name": "a", "side": "CT"}, {"name": "a", "side": "T"}]
    assert client.post("/puzzles/drafts", json={"slots": bad}).status_code == 422
    assert (client.tmp / "puzzles" / "footage" / f"{d['id']}-0.mp4").stat().st_size == 100


def test_store_survives_a_restart(tmp_path):
    store = PuzzleStore(tmp_path)
    store.add(validate_puzzle(make_puzzle("keep")))
    store.record_attempt("keep", "tom", True, 2)
    again = PuzzleStore(tmp_path)
    assert again.player("tom")["solved"] == 1 and again.list()[0]["plays"] == 1


# --- practice in CS2 (through the MatchBridge channel) -----------------------------------------

def cs2_client(tmp_path, **extra):
    from tests.test_clones import clone_app
    seed = tmp_path / "seed"
    seed.mkdir(exist_ok=True)
    (seed / "seed1.json").write_text(json.dumps(make_puzzle("seed1", source="pro")), encoding="utf-8")
    game = tmp_path / "plugin" / "puzzles"
    app, main, bridge = clone_app(tmp_path, puzzle_dir=tmp_path / "puzzles", puzzle_seed_dir=seed,
                                  death_dir=tmp_path / "deaths", game_puzzle_dir=game, **extra)
    return app, main, bridge, game


def test_spectator_scene_uses_all_tracks_and_does_not_record_an_attempt(tmp_path):
    from tests.test_cs2 import gsi
    app, main, bridge, game = cs2_client(tmp_path)
    with TestClient(app) as client:
        gsi(client)
        response = client.post('/scenes/seed1/start')
        assert response.status_code == 200, response.text
        run_id = response.json()['attempt_id']
        assert bridge.sent[-1] == f'scene_load {run_id}'
        assert len(json.loads((game / f'{run_id}.json').read_text())['players']) == len(make_puzzle()['players'])
        assert client.post('/puzzles/seed1/start', json={'player': 'tom'}).status_code == 409
        assert client.post(f'/puzzles/{run_id}/result', json={'survived': True, 'kills': 0}).status_code == 200
        assert client.get('/players/spectator').json()['attempts'] == 0


def test_start_copies_the_puzzle_and_sends_puzzle_load_through_the_plugin(tmp_path):
    from tests.test_cs2 import gsi
    app, main, bridge, game = cs2_client(tmp_path)
    with TestClient(app) as client:
        gsi(client)   # CS2 is already on de_mirage
        r = client.post("/puzzles/seed1/start", json={"player": "tom"})
        assert r.status_code == 200 and r.json()["started"]
        run_id = bridge.sent[-1].split()[-1]
        assert bridge.sent[-1] == f"puzzle_load {run_id}" and bridge.sent[-1] not in main.sent
        assert json.loads((game / f"{run_id}.json").read_text(encoding="utf-8"))["id"] == run_id
        # the plugin reports back without a name: the result is saved under the player who started it
        client.post(f"/puzzles/{run_id}/result", json={"survived": True, "kills": 2})
        assert client.get("/players/tom").json()["solved"] == 1


def test_start_loads_the_puzzle_map_and_joins_a_team_when_cs2_is_elsewhere(tmp_path):
    import threading, time
    from tests.test_cs2 import gsi
    app, main, bridge, game = cs2_client(tmp_path, map_load_seconds=5.0)
    with TestClient(app) as client:
        def report_map():   # CS2 reports the map once the service has asked for it
            deadline = time.monotonic() + 5
            while "map de_mirage" not in main.sent and time.monotonic() < deadline:
                time.sleep(0.02)
            gsi(client)
        threading.Thread(target=report_map).start()
        r = client.post("/puzzles/seed1/start", json={"player": "tom"})
        assert r.status_code == 200, r.text
        assert main.sent.index("map de_mirage") < main.sent.index("jointeam 3")
        assert bridge.sent[-1].startswith("puzzle_load run_")


def test_start_says_so_when_the_map_never_loads(tmp_path):
    app, main, bridge, game = cs2_client(tmp_path, map_load_seconds=0.2)
    with TestClient(app) as client:
        r = client.post("/puzzles/seed1/start", json={"player": "tom"})
        assert r.status_code == 409 and "de_mirage" in r.json()["detail"], r.text
        assert "puzzle_load seed1" not in bridge.sent


def test_plugin_command_sends_the_command_not_only_a_ping():
    import asyncio
    from match_service.console import PluginChannel

    async def run():
        got = []

        async def handle(reader, writer):
            while line := (await reader.readline()).decode().strip():
                got.append(line)
                writer.write(b"pong\n" if line == "matchbridge_ping" else b"ok\n")
                await writer.drain()
            writer.close()

        server = await asyncio.start_server(handle, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        await PluginChannel("127.0.0.1", port, "tok").send(["puzzle_load seed1"])
        server.close()
        return got

    assert asyncio.run(run()) == ["auth tok", "puzzle_load seed1"]


def test_a_death_can_be_retried_without_saving_it(tmp_path):
    app, main, bridge, game = cs2_client(tmp_path)
    deaths = tmp_path / "deaths"
    deaths.mkdir()
    (deaths / "death_1.json").write_text(json.dumps(make_puzzle("death_1")), encoding="utf-8")
    with TestClient(app) as client:
        from tests.test_cs2 import gsi
        gsi(client)
        assert client.post("/deaths/death_1/start", json={"player": "tom"}).status_code == 200
        assert bridge.sent[-1].startswith("puzzle_load run_")
        assert [r["id"] for r in client.get("/puzzles").json()] == ["seed1"]   # not added to the library


def test_start_without_the_plugin_channel_says_so(tmp_path):
    from match_service.main import create_app
    from match_service.console import RecordingChannel
    from tests.test_cs2 import settings
    seed = tmp_path / "seed"
    seed.mkdir()
    (seed / "seed1.json").write_text(json.dumps(make_puzzle("seed1")), encoding="utf-8")
    s = settings(tmp_path, puzzle_dir=tmp_path / "puzzles", puzzle_seed_dir=seed, game_puzzle_dir=tmp_path / "g")
    with TestClient(create_app(s, channel=RecordingChannel())) as client:   # stand-in bots: netcon only
        r = client.post("/puzzles/seed1/start", json={"player": "tom"})
        assert r.status_code == 409 and "MatchBridge" in r.json()["detail"]


def test_game_attempt_callbacks_are_correlated_and_cannot_be_replayed(tmp_path):
    from tests.test_cs2 import gsi
    app, main, bridge, game = cs2_client(tmp_path)
    with TestClient(app) as client:
        gsi(client)
        assert client.post("/puzzles/seed1/start", json={"player": "tom"}).status_code == 200
        run_id = bridge.sent[-1].split()[-1]
        assert run_id != "seed1"
        assert client.post("/puzzles/seed1/start", json={"player": "other"}).status_code == 409
        r = client.post(f"/puzzles/{run_id}/result", json={"survived": True, "kills": 2})
        assert r.status_code == 200 and r.json()["solved"]
        assert client.get("/players/tom").json()["attempts"] == 1
        assert client.post(f"/puzzles/{run_id}/result", json={"survived": True, "kills": 2}).status_code == 404
        assert client.post("/puzzles/seed1/start", json={"player": "other"}).status_code == 200
        assert client.post(f"/puzzles/{run_id}/result", json={"survived": True, "kills": 2}).status_code == 404
        assert client.get("/players/other").json()["attempts"] == 0


def test_unsaved_death_result_is_accepted_without_adding_to_library(tmp_path):
    from tests.test_cs2 import gsi
    app, main, bridge, game = cs2_client(tmp_path)
    deaths = tmp_path / "deaths"
    deaths.mkdir()
    (deaths / "death_1.json").write_text(json.dumps(make_puzzle("death_1")), encoding="utf-8")
    with TestClient(app) as client:
        gsi(client)
        assert client.post("/deaths/death_1/start", json={"player": "tom"}).status_code == 200
        run_id = bridge.sent[-1].split()[-1]
        r = client.post(f"/puzzles/{run_id}/result", json={"survived": False, "kills": 3})
        assert r.status_code == 200 and not r.json()["solved"]
        assert [p["id"] for p in client.get("/puzzles").json()] == ["seed1"]


def test_timed_out_attempt_allows_retry_and_rejects_late_result(tmp_path, monkeypatch):
    import match_service.puzzle_routes as routes
    from tests.test_cs2 import gsi
    clock = [1000.0]
    monkeypatch.setattr(routes.time, "monotonic", lambda: clock[0])
    app, main, bridge, game = cs2_client(tmp_path)
    with TestClient(app) as client:
        gsi(client)
        assert client.post("/puzzles/seed1/start", json={"player": "tom"}).status_code == 200
        old_id = bridge.sent[-1].split()[-1]
        clock[0] += 121
        assert client.post("/puzzles/seed1/start", json={"player": "other"}).status_code == 200
        assert client.post(f"/puzzles/{old_id}/result", json={"survived": True, "kills": 2}).status_code == 404
        assert client.get("/players/other").json()["attempts"] == 0


def test_failed_plugin_command_releases_the_attempt(tmp_path):
    from tests.test_cs2 import gsi
    app, main, bridge, game = cs2_client(tmp_path)
    with TestClient(app) as client:
        gsi(client)
        bridge.fail_with = OSError("offline")
        assert client.post("/puzzles/seed1/start", json={"player": "tom"}).status_code == 409
        bridge.fail_with = None
        assert client.post("/puzzles/seed1/start", json={"player": "tom"}).status_code == 200


def test_attempt_status_distinguishes_manual_results_and_completed_game(tmp_path):
    from tests.test_cs2 import gsi
    app, main, bridge, game = cs2_client(tmp_path)
    with TestClient(app) as client:
        gsi(client)
        started = client.post("/puzzles/seed1/start", json={"player": "tom"}).json()
        run_id = started["attempt_id"]
        assert client.get(f"/puzzle-attempts/{run_id}").json()["state"] == "pending"
        client.post("/puzzles/seed1/result", json={"player": "tom", "survived": True, "kills": 2})
        assert client.get(f"/puzzle-attempts/{run_id}").json()["state"] == "pending"
        client.post(f"/puzzles/{run_id}/result", json={"survived": False, "kills": 1})
        state = client.get(f"/puzzle-attempts/{run_id}").json()
        assert state["state"] == "finished" and not state["result"]["solved"]
