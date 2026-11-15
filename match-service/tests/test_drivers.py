"""How each clone would be played (drivers.py), and the seam a trained model plugs into.

The game, CloneDirector and MatchBridge are fakes here. Nothing ran in CS2.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from match_service.console import RecordingChannel
from match_service.main import create_app
from tests.test_clones import NAMES, start
from tests.test_cs2 import ASH, settings, wait_for

REPO_CLONES = Path(__file__).resolve().parents[2] / "clones"


def listing(client):
    return {c["clone_id"]: c for c in client.get("/clones").json()}


def test_stand_in_mode_lists_who_can_be_played(tmp_path):
    with TestClient(create_app(settings(tmp_path), channel=RecordingChannel())) as client:
        clones = listing(client)
    assert clones["donk_v1"]["playable"] and clones["donk_v1"]["driver"] == "stand_in"
    assert clones["donk_v1"]["label"] == "stand-in bot (donk)"
    # Profiles with no stand-in bot are listed but flagged, so the demo pages can hide them.
    assert clones["ash_v1"]["playable"] is False and "stand-in" in clones["ash_v1"]["reason"]
    assert clones["donk_v1"]["model"] is None  # existing fields are unchanged


def test_mock_lists_everyone_as_playable(tmp_path):
    from match_service.core import Settings
    with TestClient(create_app(Settings(backend="mock"))) as client:
        assert all(c["playable"] and c["driver"] == "mock" for c in client.get("/clones").json())


def test_clone_mode_uses_clone_director_and_recorded_routes(tmp_path):
    s = settings(tmp_path, cs2_bots="clone", clones_dir=REPO_CLONES)
    with TestClient(create_app(s, channel=RecordingChannel(), clone_channel=RecordingChannel())) as client:
        donk = listing(client)["donk_v1"]
    assert donk["driver"] == "clone_director" and donk["playable"] and "recorded" in donk["label"]


def test_generated_routes_need_a_model_in_the_profile(tmp_path):
    """The seam for trained models: a clone only plays generated routes once its profile names a model."""
    clones_dir = tmp_path / "clones"
    clones_dir.mkdir()
    for clone_id, name in NAMES.items():
        profile = json.loads((REPO_CLONES / f"{clone_id}.json").read_text())
        profile["model"] = "cs-net-v4+identity/donk" if clone_id == "donk_v1" else None
        (clones_dir / f"{clone_id}.json").write_text(json.dumps(profile))
    main, bridge = RecordingChannel(), RecordingChannel({"donk_v1": "donk"})
    s = settings(tmp_path, cs2_bots="clone", clones_dir=clones_dir, cs2_routes="generated", clone_join_seconds=0.3)
    with TestClient(create_app(s, channel=main, clone_channel=bridge)) as client:
        clones = listing(client)
        assert clones["donk_v1"]["playable"] and clones["donk_v1"]["model"] == "cs-net-v4+identity/donk"
        assert clones["broky_v1"]["playable"] is False and "model" in clones["broky_v1"]["reason"]
        # Asking for the clone with no model is refused before anything is sent to the game.
        refused = client.post("/matches", json={"map": "de_mirage", "mode": "wingman",
                                                "clones": [{"clone_id": "broky_v1", "team": "T"},
                                                           {"clone_id": "donk_v1", "team": "CT"}]})
        assert refused.status_code == 422 and "broky_v1" in str(refused.json())
        assert main.sent == []  # the refused request sent nothing
        ok = {"map": "de_mirage", "mode": "wingman", "players": [{"steam_id": ASH, "team": "T"}],
              "clones": [{"clone_id": "donk_v1", "team": "CT"}]}
        wait_for(client, start(client, main, ok), "ready")
    # The route source is chosen first, then the clone is added.
    assert bridge.sent == ["clone_routes generated", "clone_add donk_v1 ct"]


def test_recorded_routes_are_set_explicitly(tmp_path):
    """CloneDirector keeps its route source between matches, so `recorded` is sent too."""
    s = settings(tmp_path, cs2_bots="clone", clones_dir=REPO_CLONES, clone_join_seconds=0.3)
    main, bridge = RecordingChannel(), RecordingChannel(NAMES)
    with TestClient(create_app(s, channel=main, clone_channel=bridge)) as client:
        wait_for(client, start(client, main), "ready")
    assert bridge.sent == ["clone_routes recorded", "clone_add donk_v1 ct", "clone_add broky_v1 t"]


def test_unknown_route_source_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="CS2_CLONE_ROUTES"):
        create_app(settings(tmp_path, cs2_routes="learned"), channel=RecordingChannel())
