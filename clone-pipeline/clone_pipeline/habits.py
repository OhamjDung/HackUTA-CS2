"""Measure one player's habits from parsed matches.

Every function takes a list of Match objects, so that one match or many use the same code.
"""

from collections import Counter

import pandas as pd

from .parse import TICKRATE, Match, is_combat_weapon
from .routes import Segment, buy_type, first_contact_tick

# demoparser2 gives purchase names as shown in the game. The right column is the short name that
# CS2 buy commands use. NOT TESTED against CS2-Bot-Controller's "bc_buy" command; its accepted names
# must be checked on the game machine.
BUY_ALIAS = {
    "AK-47": "ak47", "M4A4": "m4a1", "M4A1-S": "m4a1_silencer", "AWP": "awp", "Galil AR": "galilar",
    "FAMAS": "famas", "SSG 08": "ssg08", "AUG": "aug", "SG 553": "sg556", "MAC-10": "mac10",
    "MP9": "mp9", "MP7": "mp7", "MP5-SD": "mp5sd", "UMP-45": "ump45", "P90": "p90", "PP-Bizon": "bizon",
    "Desert Eagle": "deagle", "P250": "p250", "Five-SeveN": "fiveseven", "Tec-9": "tec9",
    "CZ75-Auto": "cz75a", "Dual Berettas": "elite", "R8 Revolver": "revolver", "USP-S": "usp_silencer",
    "P2000": "hkp2000", "Glock-18": "glock", "Nova": "nova", "XM1014": "xm1014", "MAG-7": "mag7",
    "Sawed-Off": "sawedoff", "Negev": "negev", "M249": "m249",
    "Kevlar Vest": "vest", "Kevlar & Helmet": "vesthelm", "Defuse Kit": "defuser", "Zeus x27": "taser",
    "Smoke Grenade": "smokegrenade", "Flashbang": "flashbang", "High Explosive Grenade": "hegrenade",
    "Molotov": "molotov", "Incendiary Grenade": "incgrenade", "Decoy Grenade": "decoy",
}


ARMOR = {"Kevlar Vest", "Kevlar & Helmet"}
PRIMARY_GUNS = {
    "AK-47", "M4A4", "M4A1-S", "AWP", "Galil AR", "FAMAS", "SSG 08", "AUG", "SG 553", "MAC-10", "MP9",
    "MP7", "MP5-SD", "UMP-45", "P90", "PP-Bizon", "Nova", "XM1014", "MAG-7", "Sawed-Off", "Negev", "M249",
}


def weapon_preferences(matches: list[Match], top: int = 6) -> list[str]:
    """Guns ordered by the number of shots the player fired with them."""
    fired: Counter[str] = Counter()
    for match in matches:
        shots = match.shots[match.shots["weapon"].map(is_combat_weapon)]
        fired.update(shots["weapon"].astype(str).str.removeprefix("weapon_").value_counts().to_dict())
    return [weapon for weapon, _ in fired.most_common(top)]


def opening_duel_rates(matches: list[Match]) -> dict[str, float]:
    """For every player in these matches: the share of rounds where they were in the round's first kill,
    as the killer or the one killed. Keyed by Steam ID."""
    involved: Counter[str] = Counter()
    rounds_played: Counter[str] = Counter()
    for match in matches:
        everyone = set(match.deaths["attacker"]) | set(match.deaths["victim"])
        # A death with no killer (a fall, the bomb) has an empty attacker. Keep real Steam IDs only.
        everyone = {p for p in everyone if isinstance(p, str) and p.isdigit()}
        for player in everyone:
            rounds_played[player] += len(match.rounds)
        first = match.deaths.sort_values("tick").drop_duplicates("round", keep="first")
        for row in first.itertuples():
            for player in (row.attacker, row.victim):
                if player in everyone:
                    involved[player] += 1
    return {p: involved[p] / rounds_played[p] for p in rounds_played if rounds_played[p] > 0}


def aggression(matches: list[Match], steam_id: str) -> dict:
    """Aggression from 0 to 1: the share of the other players in the same matches who take the
    round's first fight less often than this player.

    This mapping is a design choice. It has not been validated against how a bot with that number plays.
    """
    rates = opening_duel_rates(matches)
    mine = rates.get(steam_id, 0.0)
    others = [rate for player, rate in rates.items() if player != steam_id]
    below = sum(1 for rate in others if rate < mine)
    return {
        "value": round(below / len(others), 3) if others else 0.5,
        "opening_duel_rate": round(mine, 3),
        "compared_with_players": len(others),
    }


def positions(matches: list[Match], top: int = 12) -> dict[str, dict[str, float]]:
    """Per side: the share of the player's alive time spent in each named map area."""
    out: dict[str, dict[str, float]] = {}
    for side in ("T", "CT"):
        counts: Counter[str] = Counter()
        for match in matches:
            side_rounds = set(match.rounds[match.rounds["side"] == side]["round"])
            ticks = match.ticks[match.ticks["round"].isin(side_rounds) & match.ticks["is_alive"].astype(bool)]
            counts.update(ticks["last_place_name"].dropna().astype(str).value_counts().to_dict())
        counts.pop("", None)
        total = sum(counts.values())
        if total:
            out[side] = {place: round(n / total, 4) for place, n in counts.most_common(top)}
    return out


def seconds_to_first_contact(matches: list[Match]) -> dict[str, list[float]]:
    """Per side: for each round with a fight, the seconds from "round goes live" to the player's first fight."""
    out: dict[str, list[float]] = {"T": [], "CT": []}
    for match in matches:
        for row in match.rounds.itertuples():
            contact = first_contact_tick(match, row.round)
            if contact is not None and row.side in out:
                out[row.side].append(round((contact - row.freeze_end) / TICKRATE, 2))
    return out


def buy_plan(matches: list[Match]) -> dict[str, dict[str, dict]]:
    """Per side and purchase type: the items the player bought in at least half of those rounds.

    Exact purchase lists rarely repeat, because players buy extra items to drop for teammates.
    So each item is judged on its own, and counted once per round.
    """
    item_rounds: dict[tuple[str, str], Counter[str]] = {}
    round_counts: Counter[tuple[str, str]] = Counter()
    for match in matches:
        for row in match.rounds.itertuples():
            if row.side not in ("T", "CT"):
                continue
            key = (row.side, buy_type(int(row.round), float(row.equip_value)))
            round_counts[key] += 1
            items = set(match.purchases[match.purchases["round"] == row.round]["item_name"].astype(str))
            item_rounds.setdefault(key, Counter()).update(items)
    out: dict[str, dict[str, dict]] = {}
    for key in sorted(round_counts):
        side, kind = key
        total = round_counts[key]
        counts = sorted(item_rounds.get(key, Counter()).items(), key=lambda kv: (-kv[1], kv[0]))
        share = {item: n / total for item, n in counts}  # most-bought first, ties by name
        usual = [item for item, s in share.items() if s >= 0.5]
        # A player who survives a round keeps their gun and armor and does not buy them again, so
        # both are under-counted. A bot buys from nothing each round, so a force or full buy always
        # gets the player's most-bought gun and armor of that round type.
        if kind in ("force", "full"):
            for group in (PRIMARY_GUNS, ARMOR):
                if not any(item in group for item in usual):
                    bought = [item for item in share if item in group]  # most-bought first
                    usual += bought[:1]
        out.setdefault(side, {})[kind] = {
            "items": usual,
            "aliases": [BUY_ALIAS[i] for i in usual if i in BUY_ALIAS],
            "unmapped_items": [i for i in usual if i not in BUY_ALIAS],
            "rounds_of_this_type": total,
            "share_of_rounds_bought": {item: round(s, 2) for item, s in share.items()},
        }
    return out


def grenade_throws(matches: list[Match]) -> list[dict]:
    """Every grenade the player threw: where they stood, where they looked, and when."""
    out = []
    for match in matches:
        live = match.rounds.set_index("round")
        for row in match.grenades.itertuples():
            if pd.isna(row.X):
                continue
            out.append({
                "match_id": match.match_id, "round": int(row.round), "side": live.loc[row.round, "side"],
                "type": str(row.weapon).removeprefix("weapon_"),
                "place": row.last_place_name,
                "seconds_into_round": round((row.tick - live.loc[row.round, "freeze_end"]) / TICKRATE, 2),
                "position": [round(float(row.X), 1), round(float(row.Y), 1), round(float(row.Z), 1)],
                "pitch": round(float(row.pitch), 2), "yaw": round(float(row.yaw), 2),
            })
    return out


def route_shares(segments: list[Segment]) -> dict[str, dict[str, float]]:
    """Per side: the share of rounds on which the player took each route."""
    out: dict[str, dict[str, float]] = {}
    for side in ("T", "CT"):
        counts = Counter(s.route_key for s in segments if s.side == side)
        total = sum(counts.values())
        if total:
            out[side] = {key: round(n / total, 4) for key, n in counts.most_common()}
    return out
