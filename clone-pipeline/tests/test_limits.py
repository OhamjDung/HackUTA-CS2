"""Tests for the human-limits measurements. Made-up motion; no recording needed."""

import numpy as np
import pandas as pd
import pytest

from clone_pipeline.limits import _wrap, longest_runs, player_series


def series(xs, ys, yaws, pitches=None, start=1000):
    n = len(xs)
    return pd.DataFrame({"tick": np.arange(start, start + n), "X": xs, "Y": ys, "yaw": yaws,
                         "pitch": np.zeros(n) if pitches is None else pitches})


def test_wrap_keeps_angles_between_minus_180_and_180():
    assert np.allclose(_wrap([190, -190, 360, 45]), [-170, 170, 0, 45])


def test_walking_backwards_is_detected():
    n = 40
    xs = -np.arange(n) * 4.0             # moving towards -X at 256 units per second
    s = player_series(series(xs, np.zeros(n), np.zeros(n)))   # looking towards +X
    moving = s["speed"] >= 60
    assert moving[4:].all()
    assert (s["rel"][4:] > 135).all()   # motion is opposite to the view: backwards


def test_walking_forwards_and_sideways_are_not_backwards():
    n = 40
    forward = player_series(series(np.arange(n) * 4.0, np.zeros(n), np.zeros(n)))
    assert (forward["rel"][4:] < 45).all()
    sideways = player_series(series(np.zeros(n), np.arange(n) * 4.0, np.zeros(n)))
    assert np.allclose(sideways["rel"][4:], 90)


def test_turn_speed_is_degrees_per_second_and_a_gap_breaks_it():
    yaws = np.arange(20) * 2.0           # 2 degrees per tick = 128 degrees per second
    s = player_series(series(np.zeros(20), np.zeros(20), yaws))
    assert np.allclose(s["turn"][1:], 128)
    gap = series(np.zeros(20), np.zeros(20), yaws)
    gap.loc[10:, "tick"] += 100          # the player died or the round changed
    assert np.isnan(player_series(gap)["turn"][10])


def test_runs_are_counted_and_broken_by_gaps():
    mask = np.array([1, 1, 1, 0, 1, 1, 0, 0, 1], dtype=bool)
    joined = np.ones(9, dtype=bool)
    assert longest_runs(mask, joined).tolist() == [3, 2, 1]
    joined[1] = False                    # a gap in ticks between tick 0 and tick 1
    assert longest_runs(mask, joined).tolist() == [1, 2, 2, 1]


def test_calibrated_limits_pass_every_real_row_and_fail_an_inhuman_one():
    from clone_pipeline.limits import calibrate, check_row
    rows = pd.DataFrame([
        {"player": "a", "turn4_p999": 1000.0, "turn_p999": 1100.0, "turn_accel_p999": 20000.0,
         "backwards_share_of_moving": 0.07, "backwards_run_p99_s": 2.0, "flick_time_p05_s": 0.12,
         "flicks_15deg": 8, "step_pitch_p999": 40.0, "step_move_p999": 67.0, "step_dmove_p999": 66.0},
        {"player": "b", "turn4_p999": 1400.0, "turn_p999": 1500.0, "turn_accel_p999": 30000.0,
         "backwards_share_of_moving": 0.10, "backwards_run_p99_s": 4.0, "flick_time_p05_s": 0.09,
         "flicks_15deg": 6, "step_pitch_p999": 60.0, "step_move_p999": 72.0, "step_dmove_p999": 75.0},
    ])
    limits = calibrate(rows)
    assert all(check_row(r, limits)["pass"] for r in rows.to_dict("records"))
    assert limits["checks"]["turn_p999"]["limit"] == pytest.approx(1500.0 * 1.05)
    assert limits["checks"]["flick_time_p05_s"]["limit"] == pytest.approx(0.09 * 0.95)
    aimbot = dict(rows.iloc[0], turn_p999=4219.0, flick_time_p05_s=0.06, backwards_share_of_moving=0.25)
    result = check_row(aimbot, limits)
    assert not result["pass"]
    assert set(result["failed"]) == {"turn_p999", "flick_time_p05_s", "backwards_share_of_moving"}


def test_a_check_without_enough_samples_is_reported_not_passed_or_failed():
    from clone_pipeline.limits import check_row
    limits = {"checks": {"flick_time_p05_s": {"kind": "min", "limit": 0.09, "needs": ["flicks_15deg", 5]}}}
    result = check_row({"flick_time_p05_s": 0.01, "flicks_15deg": 2}, limits)
    assert result["pass"] and result["results"]["flick_time_p05_s"]["status"] == "not enough samples"
    assert check_row({"flick_time_p05_s": None, "flicks_15deg": 9}, limits)["results"]["flick_time_p05_s"]["status"] == "no data"
