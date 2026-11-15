"""Generated-path candidate converter, on small synthetic review and check files."""

import copy
import hashlib
import json
import math

import pytest

from clone_pipeline import generated
from clone_pipeline.recording import read_recording

START = [100.0, 200.0, -160.0]


def trace(points, yaw=None, pitch=None, alive=None, firing=None, end_stopped_at=-1, identity_id=2):
    n = len(points)
    return {
        "identity_id": identity_id,
        "path": [[round(0.25 * (i + 1), 3), *p] for i, p in enumerate(points)],
        "yaw_degrees": yaw if yaw is not None else [0.0] * n,
        "pitch_degrees": pitch if pitch is not None else [5.0] * n,
        "alive_values": alive if alive is not None else [1.0] * n,
        "firing_values": firing if firing is not None else [0.0] * n,
        "end_stopped_at": end_stopped_at,
    }


def straight(n, step=40.0):
    """n points moving +X from START, `step` units per 0.25 s (160 u/s)."""
    return [[START[0] + step * (i + 1), START[1], START[2]] for i in range(n)]


def review(match_id="2393237", own=None):
    case = {
        "player": "donk", "steam_id": "76561198386265483", "match_id": match_id, "round_id": 4,
        "side": "CT", "context_tick": 159, "seconds_into_round": 40.25, "start_position": START,
        "actual": trace(straight(8), identity_id=None),
        "predictions": {"own": own or trace(straight(8)), "other": trace(straight(8), identity_id=1),
                        "base": trace(straight(8), identity_id=0)},
    }
    return {"format": "cs2.clone.review.v1", "split": "dev", "deployed": False,
            "identity_quality": "not_established", "selected_step": 400,
            "source": {"adapter_sha256": "a" * 64, "base_checkpoint_sha256": "b" * 64}, "cases": [case]}


def write_files(tmp_path, rev, passed=("own",), sha=None, traces=None):
    review_path = tmp_path / "review.json"
    review_path.write_text(json.dumps(rev))
    digest = sha or hashlib.sha256(review_path.read_bytes()).hexdigest()
    result = traces if traces is not None else {
        name: {"auto_check_passed": name in passed, "reasons": [] if name in passed else ["crosses wall"]}
        for name in ("actual", "own", "other", "base")}
    check = {"format": "cs2.clone.review-check.v1", "review_sha256": digest, "note": "synthetic",
             "cases": [{"case": 0, "player": "donk", "match_id": rev["cases"][0]["match_id"], "round_id": 4,
                        "traces": result}]}
    check_path = tmp_path / "check.json"
    check_path.write_text(json.dumps(check))
    return review_path, check_path


@pytest.fixture
def root(tmp_path):
    return tmp_path / "data" / "generated-candidates"


def ticks_for(own):
    return generated.tick_table(review(own=own)["cases"][0], own, 42)[0]


def test_tick_count_is_64_per_second_plus_the_start_row(tmp_path, root):
    review_path, check_path = write_files(tmp_path, review())
    prov = generated.convert(review_path, check_path, 0, "own", root)
    # 8 points = 2.0 s. The table has 64*2 + 1 rows (t=0 included); the file has 64*2 ticks.
    assert prov["conversion"]["duration_seconds"] == 2.0
    assert prov["conversion"]["tick_table_rows"] == 129
    assert prov["conversion"]["recording_ticks"] == 128
    rec = read_recording(root / "donk" / prov["playback_file"])
    assert len(rec["Ticks"]) == len(rec["Commands"]) == 128 and rec["Tickrate"] == 64


def test_knot_rows_land_exactly_on_the_inputs():
    pts = [[130.5, 211.25, -160.0], [171.125, 190.0, -158.0], [171.125, 150.5, -150.0]]
    ticks = ticks_for(trace(pts, yaw=[10.0, 20.0, 30.0], pitch=[1.0, 2.0, 3.0]))
    knots = [START] + pts
    for k, knot in enumerate(knots):
        row = ticks.iloc[16 * k]
        assert [row["X"], row["Y"], row["Z"]] == knot
    # Angle i is the heading used for step i, so it sits at the start of that step; last is held.
    assert list(ticks["yaw"].iloc[[0, 16, 32, 48]]) == pytest.approx([10.0, 20.0, 30.0, 30.0])
    assert list(ticks["pitch"].iloc[[0, 16, 32, 48]]) == pytest.approx([1.0, 2.0, 3.0, 3.0])
    # Halfway through a step the position is halfway along the straight segment.
    assert ticks.iloc[8]["X"] == pytest.approx((START[0] + 130.5) / 2)


def test_yaw_turns_the_short_way_across_180():
    ticks = ticks_for(trace(straight(2), yaw=[170.0, -170.0]))
    first_step = ticks["yaw"].iloc[:17]
    assert ticks["yaw"].iloc[4] == pytest.approx(175.0)
    assert ticks["yaw"].iloc[8] == pytest.approx(-180.0)
    assert ticks["yaw"].iloc[12] == pytest.approx(-175.0)
    assert all(abs(y) >= 170.0 - 1e-9 for y in first_step)
    assert all(-180.0 <= y < 180.0 for y in ticks["yaw"])


def test_velocity_and_movement_keys_follow_the_path_relative_to_yaw():
    ahead = ticks_for(trace(straight(2), yaw=[0.0, 0.0]))
    assert ahead["velocity_X"].iloc[0] == pytest.approx(160.0)
    assert ahead["FORWARD"].all() and not ahead[["BACK", "LEFT", "RIGHT"]].any().any()
    assert set(ahead["buttons"]) == {8}
    # Facing +Y (yaw 90) while moving +X is a strafe to the right.
    strafe = ticks_for(trace(straight(2), yaw=[90.0, 90.0]))
    assert strafe["RIGHT"].all() and not strafe[["FORWARD", "BACK", "LEFT"]].any().any()
    assert set(strafe["buttons"]) == {1024}
    # Diagonal: forward and left together. Standing still: no keys.
    diag = ticks_for(trace([[START[0] + 30, START[1] + 30, START[2]]], yaw=[0.0]))
    assert set(diag["buttons"].iloc[:16]) == {8 | 512}
    still = ticks_for(trace([START, START], yaw=[0.0, 0.0]))
    assert set(still["buttons"]) == {0}


def test_path_is_cut_at_early_stop_and_before_the_first_dead_point():
    ticks, reason = generated.tick_table(review()["cases"][0], trace(straight(8), end_stopped_at=3), 42)
    assert len(ticks) == 3 * 16 + 1 and "early stop" in reason
    ticks, reason = generated.tick_table(review()["cases"][0], trace(straight(8), alive=[1, 1, 1, 1, 0, 0, 0, 0]), 42)
    assert len(ticks) == 4 * 16 + 1 and "non-alive" in reason
    assert ticks.iloc[-1]["X"] == straight(8)[3][0]


def test_file_round_trips_and_provenance_is_honest(tmp_path, root):
    review_path, check_path = write_files(tmp_path, review())
    prov = generated.convert(review_path, check_path, 0, "own", root)
    name = "generated_own_donk_ct_2393237_round4_case0"
    assert prov["playback_file"] == f"{name}.json.br"
    playback = root / "donk" / f"{name}.json.br"
    rec = read_recording(playback)
    assert rec["Ticks"][0]["Pre"]["OriginX"] == START[0]
    assert rec["Ticks"][16]["Pre"]["OriginX"] == straight(8)[0][0]
    assert rec["Ticks"][-1]["Post"]["OriginX"] == straight(8)[-1][0]
    assert rec["Commands"][0]["ForwardMove"] == 1.0 and rec["Ticks"][0]["WeaponDefIndex"] == 42
    summary = generated.summarize(playback)
    assert summary["ticks"] == 128 and summary["max_horizontal_speed"] == pytest.approx(160.0)

    saved = json.loads((root / "donk" / f"{name}.provenance.json").read_text())
    assert saved == prov
    assert saved["source"] == "generated" and saved["identity_quality"] == "not_established"
    assert saved["identity_test"] == "failed (SPEC 8.6, first A100 run)"
    assert saved["manual_review_required"] is True and saved["promoted"] is False
    assert saved["trace"] == "own" and saved["review"]["selected_step"] == 400
    assert saved["review"]["sha256"] == hashlib.sha256(review_path.read_bytes()).hexdigest()
    assert saved["geometry_check"]["sha256"] == hashlib.sha256(check_path.read_bytes()).hexdigest()
    assert saved["review"]["source"]["adapter_sha256"] == "a" * 64
    assert saved["case"]["match_id"] == "2393237" and saved["case"]["round_id_zero_based"] == 4
    assert saved["playback_sha256"] == hashlib.sha256(playback.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="already exists"):
        generated.convert(review_path, check_path, 0, "own", root)


def test_a_fast_step_gets_a_warning(tmp_path, root):
    review_path, check_path = write_files(tmp_path, review(own=trace(straight(4, step=80.0))))
    prov = generated.convert(review_path, check_path, 0, "own", root)
    assert prov["warnings"] and "320.0" in prov["warnings"][0]


@pytest.mark.parametrize("change, message", [
    (("format", "cs2.clone.review.v0"), "format"),
    (("split", "test"), "split"),
    (("deployed", True), "deployed"),
])
def test_review_gates_refuse(tmp_path, root, change, message):
    rev = review()
    rev[change[0]] = change[1]
    review_path, check_path = write_files(tmp_path, rev)
    with pytest.raises(ValueError, match=message):
        generated.convert(review_path, check_path, 0, "own", root)


def test_check_file_gates_refuse(tmp_path, root):
    review_path, check_path = write_files(tmp_path, review(), sha="0" * 64)
    with pytest.raises(ValueError, match="review_sha256"):
        generated.convert(review_path, check_path, 0, "own", root)
    review_path, check_path = write_files(tmp_path, review(), passed=("actual",))
    with pytest.raises(ValueError, match="did not pass"):
        generated.convert(review_path, check_path, 0, "own", root)
    review_path, check_path = write_files(tmp_path, review(), traces={"other": {"auto_check_passed": True}})
    with pytest.raises(ValueError, match="no check result"):
        generated.convert(review_path, check_path, 0, "own", root)
    review_path, check_path = write_files(tmp_path, review(), traces={"own": {"auto_check_passed": "yes"}})
    with pytest.raises(ValueError, match="did not pass"):
        generated.convert(review_path, check_path, 0, "own", root)
    with pytest.raises(FileNotFoundError):
        generated.convert(review_path, tmp_path / "missing-check.json", 0, "own", root)
    assert not root.exists()


def test_actual_trace_held_out_match_and_bad_paths_are_refused(tmp_path, root):
    review_path, check_path = write_files(tmp_path, review(), passed=("actual", "own"))
    with pytest.raises(ValueError, match="real recorded path"):
        generated.convert(review_path, check_path, 0, "actual", root)
    with pytest.raises(ValueError, match="one of"):
        generated.convert(review_path, check_path, 0, "best", root)
    for held in ("2393242", "2393024"):
        review_path, check_path = write_files(tmp_path, review(match_id=held))
        with pytest.raises(ValueError, match="held-out"):
            generated.convert(review_path, check_path, 0, "own", root)
    bad_traces = {
        "empty": trace([]),
        "non-finite": trace([[math.nan, 0.0, 0.0]]),
        "one value per": dict(trace(straight(2)), yaw_degrees=[0.0]),
        "times": dict(trace(straight(2)), path=[[0.5, 1.0, 2.0, 3.0], [0.75, 1.0, 2.0, 3.0]]),
        "Nothing left": trace(straight(2), alive=[0.0, 1.0]),
    }
    for message, bad in bad_traces.items():
        review_path, check_path = write_files(tmp_path, review(own=copy.deepcopy(bad)))
        with pytest.raises(ValueError, match=message):
            generated.convert(review_path, check_path, 0, "own", root)
    assert not root.exists()


def test_output_must_not_be_inside_clones(tmp_path):
    review_path, check_path = write_files(tmp_path, review())
    with pytest.raises(ValueError, match="clones"):
        generated.convert(review_path, check_path, 0, "own", tmp_path / "clones" / "data" / "generated-candidates")
    with pytest.raises(ValueError, match="clones"):
        generated.convert(review_path, check_path, 0, "own", generated.REPO_ROOT / "clones" / "donk_v1")
    with pytest.raises(ValueError, match="generated-candidates"):
        generated.convert(review_path, check_path, 0, "own", tmp_path / "somewhere")
