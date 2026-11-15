"""Replay data: real recorded rounds from ../clones, match traces, and the closest-round match."""

import time
from pathlib import Path

from fastapi.testclient import TestClient

from match_service.console import RecordingChannel
from match_service.core import Settings
from match_service.main import create_app
from match_service.replay import RouteLibrary, Trace, gsi_players
from tests.test_cs2 import TOKEN, gsi, settings, wait_for, wait_sent, wingman

REPO_CLONES = Path(__file__).resolve().parents[2] / "clones"


def test_route_library_reads_real_recordings():
    lib = RouteLibrary(REPO_CLONES)
    assert {"donk_v1", "broky_v1"} <= set(lib.clone_ids())
    first = lib.routes("donk_v1")[0]
    route = lib.route("donk_v1", first["recording"])
    assert route["side"] in ("T", "CT") and route["label"]
    assert len(route["path"]) > 100 and route["path"][1][0] == 0.125  # 8 points a second
    assert lib.route("donk_v1", "../../etc/passwd") is None and lib.profile("../x") is None
    # A path's closest real round is itself.
    best = lib.closest("donk_v1", route["side"], route["path"])
    assert best["recording"] == first["recording"] and best["score"] == 0


def test_gsi_players_and_trace():
    payload = {"allplayers": {
        "1": {"name": "donk", "team": "CT", "position": "100.0, 200.0, 5.0", "state": {"health": 100}},
        "2": {"name": "broky", "team": "T", "position": "-5, 7, 0", "state": {"health": 0}},
        "3": {"name": "bad", "team": "T", "position": "nonsense"}}}
    players = gsi_players(payload)
    assert [(p["name"], p["x"], p["alive"]) for p in players] == [("donk", 100.0, True), ("broky", -5.0, False)]
    trace = Trace("m1", "de_mirage", "gsi")
    for t in (0.0, 0.05, 0.2):  # 0.05 is dropped: about 8 points a second
        trace.add(1, t, "donk", "CT", 1, 2, "donk_v1")
    trace.add(1, 0.3, "donk", "CT", 1, 2, "donk_v1", alive=False)
    p = trace.to_json()["rounds"][0]["players"][0]
    assert [pt[0] for pt in p["path"]] == [0.0, 0.2] and p["died_at"] == 0.3


def test_cs2_trace_from_game_state(tmp_path):
    channel = RecordingChannel()
    app = create_app(settings(tmp_path, trace_dir=tmp_path / "traces"), channel=channel)
    with TestClient(app) as client:
        match_id = client.post("/matches", json=wingman(players=[])).json()["match_id"]
        wait_sent(channel, "map de_mirage")
        gsi(client)
        wait_for(client, match_id, "ready")
        wait_sent(channel, "mp_restartgame 1")
        time.sleep(0.05)

        def update(x, health=100, rnd=0, phase="live"):
            client.post("/gsi", json={"auth": {"token": TOKEN},
                "map": {"name": "de_mirage", "phase": "live", "round": rnd,
                        "team_ct": {"name": "Alpha", "score": 0}, "team_t": {"name": "Bravo", "score": 0}},
                "round": {"phase": phase},
                "allplayers": {"a": {"name": "donk", "team": "CT", "position": f"{x}, 0, 0", "state": {"health": health}},
                               "b": {"name": "broky", "team": "T", "position": "0, 0, 0", "state": {"health": 100}}}})

        update(0, phase="freezetime")  # not recorded
        update(10); time.sleep(0.15); update(20); time.sleep(0.15); update(30, health=0)
        trace = client.get(f"/matches/{match_id}/trace").json()
        assert trace["source"] == "gsi" and trace["live_round"] == 1
        donk = next(p for p in trace["rounds"][0]["players"] if p["name"] == "donk")
        assert donk["clone_id"] == "donk_v1" and [pt[1] for pt in donk["path"]] == [10, 20] and donk["died_at"]

        c = client.get(f"/matches/{match_id}/compare", params={"round": 1, "player": "donk"}).json()
        assert c["bot"]["name"] == "donk"  # sample clones have no routes dir here, so real may be any donk round
        assert client.get("/matches").json()[0]["has_trace"]

        gsi(client, phase="gameover", ct=("Alpha", 9))
        wait_for(client, match_id, "ended")
        assert (tmp_path / "traces" / f"{match_id}.json").is_file()


def test_mock_match_has_simulated_trace(tmp_path):
    s = Settings(backend="mock", start_seconds=0.01, warmup_seconds=0.01, round_seconds=0.01)
    with TestClient(create_app(s)) as client:
        match_id = client.post("/matches", json=wingman(players=[])).json()["match_id"]
        assert client.get(f"/matches/{match_id}/trace").json()["rounds"] == []  # exists before live
        wait_for(client, match_id, "ended")
        trace = client.get(f"/matches/{match_id}/trace").json()
        assert trace["source"] == "simulated" and len(trace["rounds"]) == max(trace_scores(client, match_id)) + min(trace_scores(client, match_id))
        names = {p["name"] for p in trace["rounds"][0]["players"]}
        assert names == {"donk", "broky"}
        c = client.get(f"/matches/{match_id}/compare", params={"round": 1, "player": "donk"}).json()
        assert c["real"]["score"] < 80  # the mock walked a real donk route, shifted a little


def trace_scores(client, match_id):
    s = client.get(f"/matches/{match_id}").json()["score"]
    return s["CT"], s["T"]


def test_replay_endpoints_and_demo_pages(tmp_path):
    with TestClient(create_app(Settings(backend="mock"))) as client:
        assert {c["clone_id"] for c in client.get("/replay/clones").json()} >= {"donk_v1", "broky_v1"}
        prof = client.get("/replay/clones/donk_v1").json()
        assert prof["similarity"]["player_vs_self"]["T"]["rounds"]
        routes = client.get("/replay/clones/donk_v1/routes").json()
        assert routes and "file" not in routes[0]
        assert client.get(f"/replay/clones/donk_v1/routes/{routes[0]['recording']}").json()["path"]
        assert client.get("/replay/clones/nobody/routes").status_code == 404
        assert len(client.get("/replay/outline").json()["cells"]) > 500
        for page in ["index.html", "play.html", "watch.html", "replay.html", "proof.html", "common.js"]:
            assert client.get(f"/demo/{page}").status_code == 200
        assert client.get("/", follow_redirects=False).headers["location"] == "/demo/"
