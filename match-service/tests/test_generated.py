"""Generated-path review files (cs2.clone.review.v1) on the replay page. Synthetic data only."""

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from match_service.core import Settings
from match_service.generated import ReviewInvalid, ReviewLibrary, ReviewNotFound
from match_service.main import create_app


def trace(dx: float, dy: float, identity: int | None = None, channels: bool = True) -> dict:
    """A 1 s path at 0.25 s steps, moving (dx, dy) per step from (100, 200)."""
    path = [[round(0.25 * i, 3), 100 + dx * i, 200 + dy * i, -168.0] for i in range(1, 5)]
    out = {"path": path, "end_stopped_at": None if identity is None else -1}
    if identity is not None:
        out["identity_id"] = identity
    if channels:
        out |= {"yaw_degrees": [0.0] * 4, "pitch_degrees": [0.0] * 4,
                "alive_values": [1.0] * 4, "firing_values": [0.0] * 4}
    return out


def case(player="donk", match_id="2393237", round_id=4, own=(10, 0)) -> dict:
    return {"player": player, "steam_id": "1", "match_id": match_id, "round_id": round_id, "side": "CT",
            "context_tick": 159, "seconds_into_round": 40.25, "start_position": [100.0, 200.0, -168.0],
            "actual": trace(0, 10),
            "predictions": {"own": trace(*own, identity=2), "other": trace(10, 0, identity=1),
                            "base": trace(10, 0, identity=0)}}


def review(**top) -> dict:
    data = {"format": "cs2.clone.review.v1", "split": "dev", "deployed": False, "manual_review_required": True,
            "identity_quality": "not_established", "selected_step": 400, "map": "de_mirage",
            "interval_seconds": 0.25, "interpretation": "Diagnostic samples.",
            "cases": [case(), case(player="broky", match_id="2392601", round_id=1, own=(0, 5))]}
    return data | top


def write(folder: Path, name: str, data: dict) -> str:
    folder.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(data).encode()
    (folder / name).write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def check_file(sha: str, **over) -> dict:
    return {"format": "cs2.clone.review-check.v1", "review_sha256": sha,
            "note": "Automated geometry check only; a person must still review paths before use.",
            "cases": [{"case": 0, "player": "donk", "match_id": "2393237", "round_id": 4,
                       "traces": {"actual": {"auto_check_passed": True, "reasons": []},
                                  "own": {"auto_check_passed": False, "reasons": ["crosses a wall at 0.75 s"]},
                                  "other": {}, "base": {}}}]} | over


def client(folder: Path) -> TestClient:
    return TestClient(create_app(Settings(backend="mock", review_dir=folder)))


def test_listing_and_one_case_with_matching_check(tmp_path):
    sha = write(tmp_path, "review-dev.json", review())
    write(tmp_path, "review-dev.check.json", check_file(sha))
    with client(tmp_path) as c:
        listing = c.get("/replay/generated").json()
        assert listing["identity_test"] == "failed" and "Not the player's style" in listing["note"]
        assert listing["ignored"] == []
        [f] = listing["files"]
        assert f["file"] == "review-dev.json" and f["check_file"] == "review-dev.check.json" and f["sha256"] == sha
        assert [(x["player"], x["match_id"], x["round_id"], x["side"]) for x in f["cases"]] == [
            ("donk", "2393237", 4, "CT"), ("broky", "2392601", 1, "CT")]
        first = f["cases"][0]
        assert first["selected_step"] == 400 and first["identity_quality"] == "not_established"
        assert first["seconds"] == 1.0 and first["seconds_into_round"] == 40.25
        assert first["auto_check"] == {"actual": True, "own": False, "other": None, "base": None}
        assert f["cases"][1]["auto_check"] is None  # the check file has no entry for case 1

        d = c.get("/replay/generated/review-dev.json/0").json()
        assert set(d["traces"]) == {"actual", "own", "other", "base"}
        own = d["traces"]["own"]
        # The shared start at t=0, then the model's steps; [t, x, y] like the other replay paths.
        assert own["path"][0] == [0.0, 100.0, 200.0] and own["path"][1] == [0.25, 110.0, 200.0]
        assert d["traces"]["actual"]["path"][-1] == [1.0, 100.0, 240.0]
        assert own["identity_id"] == 2 and own["seconds"] == 1.0
        assert own["same_path_as"] == ["other", "base"] and d["traces"]["actual"]["same_path_as"] == []
        assert own["distance_to_actual"]["points"] == 4 and own["distance_to_actual"]["final"] == pytest.approx(56.6, abs=0.1)
        assert own["auto_check"] == {"auto_check_passed": False, "reasons": ["crosses a wall at 0.75 s"]}
        assert d["traces"]["other"]["auto_check"] is None
        assert d["check"]["file"] == "review-dev.check.json" and "a person must still review" in d["check"]["note"]

        d1 = c.get("/replay/generated/review-dev.json/1").json()
        assert d1["traces"]["own"]["same_path_as"] == [] and d1["traces"]["own"]["auto_check"] is None
        assert c.get("/replay/generated/review-dev.json/2").status_code == 404
        assert c.get("/replay/generated/missing.json/0").status_code == 404


def test_check_with_other_sha_is_not_used(tmp_path):
    write(tmp_path, "review-dev.json", review())
    write(tmp_path, "stale.check.json", check_file("0" * 64))
    with client(tmp_path) as c:
        listing = c.get("/replay/generated").json()
        assert listing["files"][0]["check_file"] is None
        assert listing["files"][0]["cases"][0]["auto_check"] is None
        assert listing["ignored"] == [{"file": "stale.check.json",
                                       "reason": "review_sha256 matches no review file here"}]
        d = c.get("/replay/generated/review-dev.json/0").json()
        assert d["check"] is None and d["traces"]["own"]["auto_check"] is None


def test_check_that_names_a_different_round_is_not_used(tmp_path):
    sha = write(tmp_path, "review-dev.json", review())
    bad = check_file(sha)
    bad["cases"][0]["round_id"] = 9
    write(tmp_path, "review-dev.check.json", bad)
    with client(tmp_path) as c:
        listing = c.get("/replay/generated").json()
        assert listing["files"][0]["check_file"] is None
        assert "round_id 9" in listing["ignored"][0]["reason"]


@pytest.mark.parametrize("change, reason", [
    ({"format": "cs2.clone.review.v2"}, "format is 'cs2.clone.review.v2'"),
    ({"split": "test"}, "split must be 'dev'"),
    ({"deployed": True}, "deployed must be false"),
    ({"deployed": None}, "deployed must be false"),
    ({"cases": [case(match_id="2393242")]}, "held-out match 2393242"),  # donk's holdout
    ({"cases": [case(), case(player="broky", match_id=2393024)]}, "held-out match 2393024"),  # broky's
    ({"cases": []}, "no cases"),
])
def test_wrong_files_are_rejected(tmp_path, change, reason):
    write(tmp_path, "bad.json", review(**change))
    with client(tmp_path) as c:
        listing = c.get("/replay/generated").json()
        assert listing["files"] == []
        [ignored] = listing["ignored"]
        assert ignored["file"] == "bad.json" and reason in ignored["reason"]
        assert c.get("/replay/generated/bad.json/0").status_code == 422


def test_bad_paths_are_rejected(tmp_path):
    lib = ReviewLibrary(tmp_path)
    for broken in ({"path": []}, {"path": [[0.25, 1, "x", 0]]}, {"path": [[0.5, 1, 2, 0], [0.25, 1, 2, 0]]},
                   {"path": [[0.25, float("nan"), 2, 0]]}):
        data = review()
        data["cases"][0]["predictions"]["own"] = broken
        write(tmp_path, "r.json", data)
        with pytest.raises(ReviewInvalid):
            lib.case("r.json", 0)
    write(tmp_path, "r.json", review(cases=[{**case(), "start_position": None}]))
    with pytest.raises(ReviewInvalid, match="start_position"):
        lib.case("r.json", 0)
    (tmp_path / "r.json").write_text("{not json")
    with pytest.raises(ReviewInvalid, match="not JSON"):
        lib.case("r.json", 0)


def test_missing_optional_channels_and_traces(tmp_path):
    data = review()
    c0 = data["cases"][0]
    c0["actual"] = trace(0, 10, channels=False)
    del c0["predictions"]["base"]
    del c0["steam_id"], c0["context_tick"]
    write(tmp_path, "review-dev.json", data)
    with client(tmp_path) as c:
        assert c.get("/replay/generated").json()["files"][0]["cases"][0]["steam_id"] is None
        d = c.get("/replay/generated/review-dev.json/0").json()
        assert d["traces"]["base"] is None and d["traces"]["actual"]["channels"] == []
        assert d["traces"]["own"]["channels"] == ["yaw_degrees", "pitch_degrees", "alive_values", "firing_values"]
        assert d["traces"]["own"]["same_path_as"] == ["other"]


def test_path_traversal_is_refused(tmp_path):
    reviews, outside = tmp_path / "reviews", tmp_path / "outside"
    write(reviews, "ok.json", review())
    write(outside, "secret.json", review())
    (reviews / "link.json").symlink_to(outside / "secret.json")
    lib = ReviewLibrary(reviews)
    for name in ["../outside/secret.json", "..", "..json", "/etc/passwd", "a\\b.json", ".hidden.json",
                 "ok.json/../ok.json", "link.json", "ok.txt"]:
        with pytest.raises(ReviewNotFound):
            lib.case(name, 0)
    assert lib.case("ok.json", 0)["file"] == "ok.json"
    with client(reviews) as c:
        listing = c.get("/replay/generated").json()
        assert [f["file"] for f in listing["files"]] == ["ok.json"]
        assert any(i["file"] == "link.json" for i in listing["ignored"])
        for url in ["/replay/generated/..%2Foutside%2Fsecret.json/0", "/replay/generated/%2E%2E/0",
                    "/replay/generated/link.json/0", "/replay/generated/..%5Coutside%5Csecret.json/0"]:
            assert c.get(url).status_code == 404, url


def test_no_folder_lists_nothing(tmp_path):
    with client(tmp_path / "nothing-here") as c:
        listing = c.get("/replay/generated").json()
        assert listing["files"] == [] and listing["ignored"] == []
        assert listing["folder"].endswith("nothing-here")
        assert c.get("/replay/generated/x.json/0").status_code == 404


def test_default_review_dir_is_git_ignored_data():
    s = Settings()
    assert s.review_dir.parts[-2:] == ("data", "reviews")
    repo = Path(__file__).resolve().parents[2]
    assert s.review_dir == repo / "data" / "reviews"
    assert "data/" in (repo / ".gitignore").read_text().splitlines()


def test_replay_page_has_the_generated_view(tmp_path):
    with client(tmp_path) as c:
        page = c.get("/demo/replay.html").text
        assert 'data-tab="gen"' in page and "/replay/generated" in page
        assert "identity test failed" in page and "not used in the game" in page
        assert "Generated path overlay" not in page  # the disabled placeholder is gone
        assert "learned-clones-a100-v1" in page
