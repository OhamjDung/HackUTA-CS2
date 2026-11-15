"""Tests for the human-limits measurements. Made-up motion; no recording needed."""

import numpy as np
import pandas as pd

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
