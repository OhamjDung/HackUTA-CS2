"""Tests that need no match recording. They build a small fake match in memory."""

import pandas as pd
import pytest

from clone_pipeline import habits
from clone_pipeline.parse import Match
from clone_pipeline.recording import read_recording, to_recording, write_recording
from clone_pipeline.routes import buy_type, cut_segments, first_contact_tick
from clone_pipeline.similarity import overlap

ME, ENEMY = "76561198000000001", "76561198000000002"


def fake_ticks(round_number: int, start: int, count: int, place_at) -> pd.DataFrame:
    rows = []
    for i in range(count):
        rows.append({
            "tick": start + i, "round": round_number, "X": float(i), "Y": 0.0, "Z": 0.0,
            "velocity_X": 64.0, "velocity_Y": 0.0, "velocity_Z": 0.0, "pitch": 0.0, "yaw": 90.0,
            "last_place_name": place_at(i), "is_alive": True, "team_num": 2, "buttons": 8,
            "FORWARD": True, "BACK": False, "LEFT": False, "RIGHT": False,
            "duck_amount": 0.0, "ducked": False, "ducking": False, "item_def_idx": 7.0, "move_type": 2,
            "balance": 800, "current_equip_value": 4500, "total_rounds_played": round_number - 1,
        })
    return pd.DataFrame(rows)


def fake_match(hurt_tick: int | None = None) -> Match:
    """One T-side round that goes live at tick 1000 and lasts 40 seconds."""
    ticks = fake_ticks(2, 1000, 40 * 64, lambda i: "TSpawn" if i < 320 else "TopofMid")
    rounds = pd.DataFrame([{"round": 2, "freeze_end": 1000, "end": 1000 + 40 * 64, "winner": "T",
                            "side": "T", "equip_value": 4500}])
    hurts = pd.DataFrame({"tick": [hurt_tick] if hurt_tick else [], "round": [2] if hurt_tick else []})
    return Match(
        match_id="1", file_name="1_fake.dem", map_name="de_mirage", player_name="me", steam_id=ME,
        rounds=rounds, ticks=ticks,
        purchases=pd.DataFrame({"tick": [900, 901], "item_name": ["AK-47", "Smoke Grenade"], "round": [2, 2]}),
        shots=pd.DataFrame({"tick": [1100], "weapon": ["weapon_ak47"], "round": [2]}),
        hurts=hurts,
        deaths=pd.DataFrame({"tick": [1500], "attacker": [ME], "victim": [ENEMY], "round": [2]}),
        grenades=pd.DataFrame(columns=["tick", "weapon", "round", "X", "Y", "Z", "pitch", "yaw", "last_place_name"]),
    )


def test_buy_type():
    assert buy_type(1, 800) == "pistol"
    assert buy_type(13, 800) == "pistol"
    assert buy_type(5, 900) == "eco"
    assert buy_type(5, 2500) == "force"
    assert buy_type(5, 5000) == "full"


def test_a_gunshot_alone_is_not_contact():
    assert first_contact_tick(fake_match(), 2) is None


def test_segment_stops_at_the_time_limit_when_there_is_no_fight():
    [seg] = cut_segments(fake_match())
    assert seg.end_reason == "time_limit"
    assert seg.seconds == 20.0
    assert seg.places == ["TSpawn", "TopofMid"]
    assert seg.route_key == "TopofMid"


def test_segment_stops_when_the_player_takes_damage():
    [seg] = cut_segments(fake_match(hurt_tick=1000 + 10 * 64))
    assert seg.end_reason == "contact"
    assert seg.seconds == 10.0


def test_a_segment_shorter_than_three_seconds_is_dropped():
    assert cut_segments(fake_match(hurt_tick=1000 + 64)) == []


def test_recording_has_the_fields_the_bot_plugin_requires(tmp_path):
    [seg] = cut_segments(fake_match())
    rec = to_recording(seg.ticks)
    assert rec["FormatVersion"] == 1 and rec["Tickrate"] == 64
    assert len(rec["Ticks"]) == len(rec["Commands"]) == len(seg.ticks) - 1
    # Field names copied from CS2-Bot-Controller's Types.cs. Its loader rejects a file missing any of them.
    assert set(rec["Ticks"][0]["Pre"]) == {
        "OriginX", "OriginY", "OriginZ", "VelX", "VelY", "VelZ", "Pitch", "Yaw", "Roll", "EntityFlags",
        "MoveType", "Buttons", "Buttons1", "Buttons2", "DuckAmount", "DuckSpeed", "LadderNormalX",
        "LadderNormalY", "LadderNormalZ", "Ducked", "Ducking", "DesiresDuck", "ActualMoveType"}
    assert set(rec["Commands"][0]) == {
        "ForwardMove", "LeftMove", "UpMove", "Pitch", "Yaw", "Roll", "Buttons", "Buttons1", "Buttons2",
        "MouseDx", "MouseDy", "WeaponSelect", "Fields", "LeftHandDesired"}
    assert rec["Commands"][0]["ForwardMove"] == 1.0
    assert rec["Ticks"][0]["Post"]["OriginX"] == rec["Ticks"][1]["Pre"]["OriginX"]

    path = tmp_path / "route.json.br"
    assert write_recording(seg.ticks, path) == len(rec["Ticks"])
    assert read_recording(path) == rec


def test_recording_file_name_must_end_in_json_br(tmp_path):
    [seg] = cut_segments(fake_match())
    with pytest.raises(ValueError):
        write_recording(seg.ticks, tmp_path / "route.json")


def test_overlap():
    assert overlap({"A": 1.0}, {"A": 1.0}) == 1.0
    assert overlap({"A": 1.0}, {"B": 1.0}) == 0.0
    assert overlap({}, {"A": 1.0}) is None


def test_habits_on_the_fake_match():
    match = fake_match()
    assert habits.weapon_preferences([match]) == ["ak47"]
    assert habits.opening_duel_rates([match]) == {ME: 1.0, ENEMY: 1.0}
    plan = habits.buy_plan([match])["T"]["full"]
    assert plan["aliases"] == ["ak47", "smokegrenade"]
    assert habits.positions([match])["T"] == {"TopofMid": 0.875, "TSpawn": 0.125}


def test_frequent_grenades_do_not_consume_the_main_weapon_budget_first():
    match = fake_match()
    second = match.rounds.iloc[0].copy()
    second["round"] = 3
    match.rounds = pd.concat([match.rounds, pd.DataFrame([second])], ignore_index=True)
    match.purchases = pd.DataFrame({
        "tick": [900, 901, 3500, 3501],
        "item_name": ["AK-47", "Smoke Grenade", "Smoke Grenade", "Kevlar Vest"],
        "round": [2, 2, 3, 3],
    })
    plan = habits.buy_plan([match])["T"]["full"]
    assert plan["aliases"] == ["ak47", "vest", "smokegrenade"]
    assert plan["share_of_rounds_bought"]["Smoke Grenade"] == 1.0
