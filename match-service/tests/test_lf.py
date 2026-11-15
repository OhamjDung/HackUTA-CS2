"""donkLF and brokyLF: clones that name the Round 4 adapter, whose paths are not route files yet.

The game, CloneDirector and MatchBridge are fakes here. Nothing ran in CS2.
"""

import json

from fastapi.testclient import TestClient

from match_service.console import RecordingChannel
from match_service.main import create_app
from tests.test_cs2 import settings
from tests.test_drivers import REPO_CLONES, listing

SHA = "82f8ad3590394492e8f5ae5af42c9bef70523a1178cd32a16d60ba5849169e3a"


def test_a_named_model_with_no_routes_yet_plays_recorded_and_is_not_playable_as_generated(tmp_path):
    clones_dir = tmp_path / "clones"
    clones_dir.mkdir()
    profile = json.loads((REPO_CLONES / "donk_v1.json").read_text())
    profile.update(clone_id="donkLF", display_name="donkLF", stand_in_bot="donkLF",
                   model={"name": "round4-development-v1", "routes_generated": False})
    (clones_dir / "donkLF.json").write_text(json.dumps(profile))

    recorded = settings(tmp_path, cs2_bots="clone", clones_dir=clones_dir)
    with TestClient(create_app(recorded, channel=RecordingChannel(), clone_channel=RecordingChannel())) as client:
        info = listing(client)["donkLF"]
    assert info["playable"] and "not converted to routes yet" in info["label"]

    generated = settings(tmp_path, cs2_bots="clone", clones_dir=clones_dir, cs2_routes="generated")
    with TestClient(create_app(generated, channel=RecordingChannel(), clone_channel=RecordingChannel())) as client:
        info = listing(client)["donkLF"]
    assert info["playable"] is False and "no generated routes" in info["reason"]


def test_repo_lf_profiles_match_their_ids_and_name_the_release():
    for player in ("donk", "broky"):
        d = json.loads((REPO_CLONES / f"{player}LF.json").read_text())
        assert d["clone_id"] == d["display_name"] == d["stand_in_bot"] == f"{player}LF"
        assert d["model"]["routes_generated"] is False and d["model"]["player"] == player
        assert d["model"]["asset_sha256"] == SHA
