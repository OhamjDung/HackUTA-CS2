"""Map review checks on a tiny synthetic mesh (no CS-NET checkout or real map needed)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import map_review  # noqa: E402


def synthetic_map():
    pytest.importorskip("open3d")
    # Floor: z=0 over x,y in [-1000, 1000]. Wall: plane x=100 from z=0 to z=200 for y in [-1000, 1000].
    vertices = [[-1000, -1000, 0], [1000, -1000, 0], [1000, 1000, 0], [-1000, 1000, 0],
                [100, -1000, 0], [100, 1000, 0], [100, 1000, 200], [100, -1000, 200]]
    triangles = [[0, 1, 2], [0, 2, 3], [4, 5, 6], [4, 6, 7]]
    return map_review.MapGeometry.from_game_triangles(np.asarray(vertices, float), triangles)


def line(start, step, n=16):
    return np.asarray(start, float) + np.arange(n + 1)[:, None] * np.asarray(step, float)


def test_path_along_the_floor_passes():
    reasons, notes, stats = map_review.check_trace(synthetic_map(), line([0, -400, 0], [0, 50, 0]))
    assert reasons == []
    assert stats["max_horizontal_units_per_step"] == 50


def test_path_through_the_wall_fails_at_the_crossing_step():
    reasons, _, _ = map_review.check_trace(synthetic_map(), line([0, 0, 0], [30, 0, 0], 8))
    # Points at x=0,30,60,90,120: step 3 (t=1.0 s) goes from x=90 to x=120 through x=100.
    assert "wall crossing at step 3 (t=1.0 s)" in reasons
    assert all("wall crossing" not in r for r in reasons if "step 3 " not in r)


def test_floating_and_outside_points_and_speed_fail():
    geom = synthetic_map()
    reasons, _, _ = map_review.check_trace(geom, line([0, 0, 150], [0, 10, 0], 4))
    assert any(r.startswith("floating at point 0") for r in reasons)
    reasons, _, _ = map_review.check_trace(geom, [[0, 0, 0], [0, 10, 0], [5000, 0, 0]])
    assert any(r.startswith("no floor below point 2") for r in reasons)
    reasons, _, _ = map_review.check_trace(geom, line([-900, 0, 0], [0, 90, 0], 3))
    assert any(r.startswith("impossible speed at step 0") for r in reasons)


def test_long_stop_and_native_early_stop_are_notes_not_failures():
    reasons, notes, _ = map_review.check_trace(synthetic_map(), line([0, 0, 0], [0, 0, 0], 10),
                                               {"end_stopped_at": 7})
    assert reasons == []
    assert any(n.startswith("long stop over steps 0-9") for n in notes)
    assert any("native early stop" in n for n in notes)


def review_file(tmp_path, **changes):
    path = [[round(.25 * (k + 1), 3), 0.0, -400.0 + 50 * (k + 1), 0.0] for k in range(16)]
    wall = [[round(.25 * (k + 1), 3), 30.0 * (k + 1), -400.0, 0.0] for k in range(16)]
    trace = lambda p: {"path": p, "yaw_degrees": [0] * 16, "pitch_degrees": [0] * 16,
                       "alive_values": [1] * 16, "firing_values": [0] * 16, "end_stopped_at": -1}
    case = {"player": "donk", "match_id": "2393237", "round_id": 4, "side": "CT",
            "start_position": [0.0, -400.0, 0.0], "actual": trace(path),
            "predictions": {"own": trace(wall), "other": trace(path), "base": trace(path)}}
    data = {"format": "cs2.clone.review.v1", "split": "dev", "map": "de_mirage",
            "interval_seconds": .25, "cases": [case]}
    data.update(changes)
    out = tmp_path / "review.json"
    out.write_text(json.dumps(data))
    return out, data


def test_check_file_has_the_agreed_format(tmp_path):
    path, _ = review_file(tmp_path)
    _, check, details = map_review.run_checks(path, synthetic_map(), "synthetic")
    assert set(check) == {"format", "review_sha256", "map", "mesh", "thresholds", "note", "cases"}
    assert check["format"] == "cs2.clone.review-check.v1" and check["map"] == "de_mirage"
    assert check["review_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert "person must still review" in check["note"]
    case = check["cases"][0]
    assert (case["case"], case["player"], case["match_id"], case["round_id"]) == (0, "donk", "2393237", 4)
    assert set(case["traces"]) == {"actual", "own", "other", "base"}
    assert case["traces"]["actual"] == {"auto_check_passed": True, "reasons": []}
    assert case["traces"]["own"]["auto_check_passed"] is False
    assert case["traces"]["own"]["reasons"] == ["wall crossing at step 3 (t=1.0 s)"]
    assert details["calibration_on_actual"]["actual_traces_failed"] == 0


@pytest.mark.parametrize("changes", [
    {"format": "cs2.clone.review.v2"},
    {"split": "test"},
    {"map": "de_dust2"},
    {"interval_seconds": .5},
    {"cases": []},
])
def test_wrong_format_files_are_rejected(tmp_path, changes):
    path, _ = review_file(tmp_path, **changes)
    with pytest.raises(ValueError):
        map_review.validate_review(json.loads(path.read_text()))


def test_malformed_cases_are_rejected(tmp_path):
    _, data = review_file(tmp_path)
    bad = []
    for mutate in (lambda c: c.update(match_id="2393242"),             # held-out match
                   lambda c: c.update(start_position=[0, 0]),
                   lambda c: c["predictions"].pop("base"),
                   lambda c: c["actual"]["path"][3].__setitem__(0, 9.0),  # wrong timestamp
                   lambda c: c["actual"]["path"][2].__setitem__(1, float("nan")),
                   lambda c: c["actual"]["path"].__setitem__(1, [0.5, 1, 2])):
        copy = json.loads(json.dumps(data))
        mutate(copy["cases"][0])
        bad.append(copy)
    for item in bad:
        with pytest.raises(ValueError):
            map_review.validate_review(item)


def test_non_json_file_is_rejected(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{not json")
    with pytest.raises(ValueError):
        map_review.run_checks(path, None, "none")
