"""Read one match recording (.dem) into tables for one player.

Built on demoparser2 (https://github.com/LaihoE/demoparser). A "tick" is one step of the game
simulation; CS2 runs 64 per second.
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from demoparser2 import DemoParser

TICKRATE = 64
TEAM_SIDE = {2: "T", 3: "CT"}

# Per-tick values read for the cloned player. Names are demoparser2's.
TICK_PROPS = [
    "X", "Y", "Z", "velocity_X", "velocity_Y", "velocity_Z", "pitch", "yaw",
    "last_place_name", "is_alive", "team_num", "buttons", "FORWARD", "BACK", "LEFT", "RIGHT",
    "duck_amount", "ducked", "ducking", "item_def_idx", "move_type",
    "balance", "current_equip_value", "total_rounds_played", "inventory",
]

# Weapons that do not count as "meeting an enemy" when fired.
NON_COMBAT_WEAPON_WORDS = ("knife", "bayonet", "karambit", "grenade", "flashbang", "molotov", "decoy", "c4")


@dataclass
class Match:
    """Everything the pipeline needs from one recording, for one player."""

    match_id: str            # taken from the file name, e.g. "2393226"
    file_name: str
    map_name: str
    player_name: str
    steam_id: str
    rounds: pd.DataFrame     # one row per round: round, freeze_end, end, winner, side
    ticks: pd.DataFrame      # one row per tick of the cloned player, with a "round" column
    purchases: pd.DataFrame  # the player's purchases: tick, item_name, round
    shots: pd.DataFrame      # the player's shots: tick, weapon, round
    hurts: pd.DataFrame      # damage the player dealt or took: tick, round
    deaths: pd.DataFrame     # every death in the match: tick, round, attacker, victim (Steam IDs)
    grenades: pd.DataFrame   # the player's grenade throws: tick, weapon, round, X, Y, Z, pitch, yaw


def is_combat_weapon(weapon: str) -> bool:
    name = str(weapon).lower()
    return not any(word in name for word in NON_COMBAT_WEAPON_WORDS)


def _build_rounds(parser: DemoParser) -> pd.DataFrame:
    """Pair each "round goes live" tick with the round end that follows it."""
    freeze_ends = sorted(parser.parse_event("round_freeze_end")["tick"].astype(int))
    ends = parser.parse_event("round_end")
    ends = ends[ends["winner"].notna()].sort_values("tick")
    rows = []
    for _, end in ends.iterrows():
        end_tick = int(end["tick"])
        before = [t for t in freeze_ends if t < end_tick]
        if not before:
            continue
        # A restart or timeout can add extra "live" ticks. The last one before the end is the real one.
        rows.append({"freeze_end": before[-1], "end": end_tick, "winner": str(end["winner"])})
    rounds = pd.DataFrame(rows).drop_duplicates("freeze_end", keep="last").reset_index(drop=True)
    rounds.insert(0, "round", range(1, len(rounds) + 1))
    return rounds


def _assign_round(ticks: pd.Series, rounds: pd.DataFrame, lead_ticks: int = 0) -> pd.Series:
    """Round number for each tick, or 0 if the tick is outside every round.

    lead_ticks widens each round backwards, so that purchases made before the round goes live
    count for that round.
    """
    out = pd.Series(0, index=ticks.index, dtype="int64")
    previous_end = 0
    for row in rounds.itertuples():
        start = max(previous_end, row.freeze_end - lead_ticks)
        out[(ticks > start) & (ticks <= row.end)] = row.round
        previous_end = row.end
    return out


# Verified targets, not weapon-role rules. Other players may be selected by exact Steam ID.
CANONICAL_IDS = {"donk": "76561198386265483", "broky": "76561198201620490"}


def resolve_player(info: pd.DataFrame, player: str) -> tuple[str, str]:
    """Resolve one identity; never merge same-name accounts or guess an alternate account."""
    expected = CANONICAL_IDS.get(player.lower(), player if player.isdigit() else None)
    if expected is not None:
        found = info[info["steamid"].astype(str) == expected]
    else:
        found = info[info["name"].str.lower() == player.lower()]
    if len(found) != 1 or found["steamid"].astype(str).nunique() != 1:
        raise ValueError(f"Missing or ambiguous player {player!r}; select one exact Steam ID.")
    return str(found.iloc[0]["steamid"]), str(found.iloc[0]["name"])


def load_match(path: str | Path, player_name: str) -> Match:
    """Parse one recording for the named player. Raises ValueError if the player is not in it."""
    path = Path(path)
    parser = DemoParser(str(path))
    header = parser.parse_header()

    info = parser.parse_player_info()
    steam_id, name = resolve_player(info, player_name)

    rounds = _build_rounds(parser)

    ticks = parser.parse_ticks(TICK_PROPS, players=[int(steam_id)])
    ticks = ticks.sort_values("tick").reset_index(drop=True)
    ticks["round"] = _assign_round(ticks["tick"], rounds)
    ticks = ticks[ticks["round"] > 0].reset_index(drop=True)

    # The player's side in each round is the side at the tick the round goes live.
    live = ticks.drop_duplicates("round", keep="first").set_index("round")
    rounds["side"] = rounds["round"].map(live["team_num"].map(TEAM_SIDE))
    rounds["equip_value"] = rounds["round"].map(live["current_equip_value"])

    def mine(event: str, id_column: str) -> pd.DataFrame:
        df = parser.parse_event(event)
        return df[df[id_column].astype(str) == steam_id].copy()

    purchases = mine("item_purchase", "steamid")
    purchases = purchases[~purchases["was_sold"].astype(bool)][["tick", "item_name"]]
    # Players buy during the freeze before the round goes live: allow 60 seconds of lead.
    purchases["round"] = _assign_round(purchases["tick"], rounds, lead_ticks=60 * TICKRATE)

    shots = mine("weapon_fire", "user_steamid")[["tick", "weapon"]]
    shots["round"] = _assign_round(shots["tick"], rounds)

    hurt_all = parser.parse_event("player_hurt")
    hurts = hurt_all[
        (hurt_all["user_steamid"].astype(str) == steam_id)
        | (hurt_all["attacker_steamid"].astype(str) == steam_id)
    ][["tick"]].copy()
    hurts["round"] = _assign_round(hurts["tick"], rounds)

    death_all = parser.parse_event("player_death")
    deaths = pd.DataFrame({
        "tick": death_all["tick"].astype(int),
        "attacker": death_all["attacker_steamid"].astype(str),
        "victim": death_all["user_steamid"].astype(str),
    })
    deaths["round"] = _assign_round(deaths["tick"], rounds)

    grenades = shots[~shots["weapon"].map(is_combat_weapon) & shots["weapon"].str.contains(
        "grenade|flashbang|molotov|decoy", case=False)].copy()
    grenades = grenades.merge(ticks[["tick", "X", "Y", "Z", "pitch", "yaw", "last_place_name"]], on="tick", how="left")

    return Match(
        match_id=path.name.split("_")[0],
        file_name=path.name,
        map_name=str(header.get("map_name", "")),
        player_name=name,
        steam_id=steam_id,
        rounds=rounds,
        ticks=ticks,
        purchases=purchases[purchases["round"] > 0].reset_index(drop=True),
        shots=shots[shots["round"] > 0].reset_index(drop=True),
        hurts=hurts[hurts["round"] > 0].reset_index(drop=True),
        deaths=deaths[deaths["round"] > 0].reset_index(drop=True),
        grenades=grenades[grenades["round"] > 0].reset_index(drop=True),
    )
