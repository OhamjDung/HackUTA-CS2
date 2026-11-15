"""Tests for the quirk rules and the "who is it?" test. They use made-up numbers, no recording."""

import json
from pathlib import Path

import pandas as pd
import pytest

from clone_pipeline import quirks


def rows() -> pd.DataFrame:
    """Four players, two matches each. "hopper" jumps far more than the others and stays with the team."""
    data = []
    for player, jumps, alone in (("hopper", 6.0, 0.10), ("a", 1.0, 0.40), ("b", 1.5, 0.45), ("c", 2.0, 0.35)):
        for match, wobble in (("1", 0.0), ("2", 0.2)):
            row = {q: 1.0 for q in quirks.QUIRKS}
            row.update(player=player, steamid=player, match=match, rounds=20,
                       jumps_per_min=jumps + wobble, alone_share=alone + wobble / 10)
            data.append(row)
    return pd.DataFrame(data)


def test_fit_marks_only_stable_large_differences_as_distinctive():
    rules = quirks.fit_quirks(rows(), "hopper")
    assert rules["jumps_per_min"]["distinctive"] and rules["jumps_per_min"]["z"] > 1
    assert rules["alone_share"]["distinctive"] and rules["alone_share"]["z"] < -1
    assert "mean_speed" not in rules          # no spread in the population: no rule can be fitted


def test_fit_needs_the_player_and_enough_others():
    with pytest.raises(ValueError):
        quirks.fit_quirks(rows(), "nobody")


def test_a_quirk_passes_when_at_least_half_the_gap_is_covered():
    rules = quirks.fit_quirks(rows(), "hopper")
    mean, mine = rules["jumps_per_min"]["population_mean"], rules["jumps_per_min"]["player"]
    alone = rules["alone_share"]["player"]
    half = mean + 0.5 * (mine - mean)
    good = quirks.check_quirks(rules, {"jumps_per_min": half + 0.01, "alone_share": alone})
    assert good["checks"]["jumps_per_min"]["pass"] and good["pass"]
    weak = quirks.check_quirks(rules, {"jumps_per_min": half - 0.3, "alone_share": alone})
    assert not weak["checks"]["jumps_per_min"]["pass"]
    assert not weak["pass"]                   # 1 of 2 distinctive quirks is under the 60% rule
    wrong_side = quirks.check_quirks(rules, {"jumps_per_min": mean - 1, "alone_share": alone})
    assert wrong_side["checks"]["jumps_per_min"]["share_of_gap_covered"] < 0


def test_who_is_it_ranks_the_nearest_player_first():
    reference, population = quirks.reference_block(rows())
    measured = {q: 1.0 for q in quirks.QUIRKS} | {"jumps_per_min": 5.5, "alone_share": 0.12}
    ranking = quirks.who_is_it(reference, population, measured)
    assert ranking[0][0] == "hopper"
    assert len(ranking) == 4 and ranking[0][1] < ranking[1][1]


def test_controls_map_quirks_to_bot_settings():
    controls = quirks.controls_from_quirks(quirks.fit_quirks(rows(), "hopper"))
    assert controls["jumps_per_min"]["value"] == pytest.approx(6.1)
    assert controls["teamwork"]["value"] > 75          # stays with the team more than the others
    assert 0 <= controls["teamwork"]["value"] <= 100


def test_committed_learned_profiles_keep_the_fields_other_code_reads():
    clones = Path(__file__).resolve().parents[2] / "clones"
    for clone_id, base in (("donkL", "donk_v1"), ("brokyL", "broky_v1")):
        profile = json.loads((clones / f"{clone_id}.json").read_text(encoding="utf-8"))
        assert profile["clone_id"] == clone_id and profile["display_name"] == clone_id
        assert profile["stand_in_bot"] and profile["learned"]["based_on"] == base
        assert profile["learned"]["neural_model"] is None
        assert profile["quirk_controls"]["jumps_per_min"]["value"] > 0
        held = set(profile["learned"]["held_back_matches"])
        assert held and not held & set(profile["learned"]["building_matches"])
        assert profile["routes"]["T"] and profile["buy_plan"]["T"]
