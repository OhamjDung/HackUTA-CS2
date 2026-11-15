import time

import pytest
from fastapi.testclient import TestClient

from match_service.main import Settings, create_app

ASH = "76561198000000001"
FRIEND = "76561198000000002"


@pytest.fixture
def client():
    fast = Settings(start_seconds=0.01, warmup_seconds=0.01, round_seconds=0.001)
    with TestClient(create_app(fast)) as c:
        yield c


def wait_for(client, match_id, status, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        m = client.get(f"/matches/{match_id}").json()
        if m["status"] == status:
            return m
        time.sleep(0.01)
    raise AssertionError(f"match never reached {status}; last: {m['status']}")


def wingman(**extra):
    body = {
        "map": "de_mirage",
        "mode": "wingman",
        "players": [{"steam_id": ASH, "team": "CT"}],
        "clones": [{"clone_id": "ash_v1", "team": "CT"}, {"clone_id": "pro_awper_v1", "team": "T"}],
    }
    body.update(extra)
    return body


def test_lists_sample_clones(client):
    ids = {c["clone_id"] for c in client.get("/clones").json()}
    assert ids == {"ash_v1", "pro_rifler_v1", "pro_awper_v1", "donk_v1", "broky_v1"}


def test_match_runs_to_the_end(client):
    created = client.post("/matches", json=wingman())
    assert created.status_code == 201
    assert created.json()["status"] == "starting"
    match_id = created.json()["match_id"]

    m = wait_for(client, match_id, "ended")
    assert max(m["score"]["CT"], m["score"]["T"]) == 9  # wingman: first to 9
    assert m["round"] == m["score"]["CT"] + m["score"]["T"]
    assert m["join_link"] == "steam://connect/127.0.0.1:27015"
    assert m["demo_url"] is None  # the mock records nothing
    assert {p["display_name"] for p in m["players"] if p["is_clone"]} == {"Ash", "Pro AWPer (sample)"}

    events = [e["event"] for e in client.get(f"/matches/{match_id}/events").json()]
    assert events[:2] == ["match.ready", "match.live"]
    assert events[-1] == "match.ended"
    assert events.count("round.ended") == m["round"]


def test_mock_fail(client):
    match_id = client.post("/matches", json=wingman(mock_fail=True)).json()["match_id"]
    m = wait_for(client, match_id, "failed")
    assert m["error"] and m["join_link"] is None
    assert [e["event"] for e in client.get(f"/matches/{match_id}/events").json()] == ["match.failed"]


def test_stop(client):
    slow = Settings(start_seconds=0.01, warmup_seconds=0.01, round_seconds=10)
    with TestClient(create_app(slow)) as c:
        match_id = c.post("/matches", json=wingman()).json()["match_id"]
        wait_for(c, match_id, "live")
        assert c.post(f"/matches/{match_id}/stop").json() == {"status": "ended"}
        assert c.get(f"/matches/{match_id}").json()["status"] == "ended"
        assert c.post(f"/matches/{match_id}/stop").status_code == 409
        last = c.get(f"/matches/{match_id}/events").json()[-1]
        assert last["event"] == "match.ended" and last["data"]["reason"] == "stopped"


def test_two_live_matches_get_different_ports():
    slow = Settings(start_seconds=0.01, warmup_seconds=10, round_seconds=10)
    with TestClient(create_app(slow)) as c:
        a = c.post("/matches", json=wingman()).json()["match_id"]
        b = c.post("/matches", json=wingman()).json()["match_id"]
        ports = {wait_for(c, a, "ready")["server"]["port"], wait_for(c, b, "ready")["server"]["port"]}
        assert ports == {27015, 27016}


@pytest.mark.parametrize("change, message", [
    ({"clones": [{"clone_id": "nobody", "team": "T"}]}, "Unknown clone_id"),
    ({"players": [{"steam_id": ASH, "team": "CT"}, {"steam_id": ASH, "team": "T"}]}, "more than once"),
    ({"clones": [{"clone_id": "ash_v1", "team": "CT"}]}, "Team T is empty"),
    ({"players": [{"steam_id": ASH, "team": "CT"}, {"steam_id": FRIEND, "team": "CT"}]}, "wingman allows 2"),
])
def test_rejects_bad_matches(client, change, message):
    r = client.post("/matches", json=wingman(**change))
    assert r.status_code == 422
    assert any(message in e for e in r.json()["detail"])


def test_rejects_bad_steam_id_and_map(client):
    assert client.post("/matches", json=wingman(players=[{"steam_id": "123", "team": "CT"}])).status_code == 422
    assert client.post("/matches", json=wingman(map="Mirage!")).status_code == 422


def test_unknown_match(client):
    assert client.get("/matches/nope").status_code == 404
