"""Measure one player's habits from parsed matches.

Every function takes a list of Match objects, so that one match or many use the same code.
"""

from collections import Counter
import warnings
import math

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


def purchase_order(items: list[str]) -> list[str]:
    """Put the main gun and armor before utility so a limited budget reaches the gun first.

    CS2-Bot-Controller's src/features/buy/BuyController.cpp issues each buy in list order.
    Frequency still decides membership; this only changes execution order.
    """
    return sorted(items, key=lambda item: 0 if item in PRIMARY_GUNS else 1 if item in ARMOR else 2)


# Inventory names come directly from demoparser2, not CS-NET's per-file weapon IDs.
# Prices are conservative purchase-policy constraints, not a simulation of the bot's current money.
PRIMARY_PRICES = {
    "AK-47": 2700, "M4A4": 2900, "M4A1-S": 2900, "AWP": 4750, "Galil AR": 1800,
    "FAMAS": 1950, "SSG 08": 1700, "AUG": 3300, "SG 553": 3000, "MAC-10": 1050,
    "MP9": 1250, "MP7": 1500, "MP5-SD": 1500, "UMP-45": 1200, "P90": 2350,
    "PP-Bizon": 1400, "Nova": 1050, "XM1014": 2000, "MAG-7": 1300,
    "Sawed-Off": 1100, "Negev": 1700, "M249": 5200,
}
T_ONLY = {"AK-47", "Galil AR", "SG 553", "MAC-10", "Sawed-Off", "Glock-18", "Tec-9", "Molotov"}
CT_ONLY = {"M4A4", "M4A1-S", "FAMAS", "AUG", "MP9", "MAG-7", "USP-S", "P2000",
           "Five-SeveN", "Incendiary Grenade", "Defuse Kit"}


def _legal(item: str, side: str) -> bool:
    return item not in (CT_ONLY if side == "T" else T_ONLY)


def opening_inventory(match: Match, round_number: int) -> set[str] | None:
    """Inventory at the first observed live tick (within one tick of freeze end).

    None means unavailable, not an observed absence. An empty list is a known empty inventory.
    Drops/pickups later in the round cannot change this purchase-policy observation.
    """
    if "inventory" not in match.ticks:
        return None
    ticks = match.ticks[match.ticks["round"] == round_number].sort_values("tick")
    live = match.rounds[match.rounds["round"] == round_number]
    if ticks.empty or live.empty or ticks.iloc[0]["tick"] - live.iloc[0]["freeze_end"] > 1:
        return None
    row = ticks.iloc[0]
    if pd.isna(row["is_alive"]) or not bool(row["is_alive"]):
        return None
    inventory = row["inventory"]
    if not isinstance(inventory, (list, tuple)):
        return None
    if any(not isinstance(item, str) for item in inventory):
        return None
    return set(inventory)


def weapon_preferences(matches: list[Match], top: int = 6) -> list[str]:
    """Rank primaries by rounds carried at the live opening, then other guns by shots.

    This counts retained rifles even while a knife is active. Missing inventory falls back
    explicitly to shot ranking; no missing inventory is counted as zero possession.
    """
    carried: Counter[str] = Counter()
    fired: Counter[str] = Counter()
    missing = 0
    for match in matches:
        for r in match.rounds.itertuples():
            inv = opening_inventory(match, r.round)
            if inv is None:
                missing += 1
            else:
                carried.update(inv & PRIMARY_GUNS)
        shots = match.shots.loc[match.shots["weapon"].map(is_combat_weapon).astype(bool)]
        fired.update(shots["weapon"].astype(str).str.removeprefix("weapon_").value_counts().to_dict())
    if missing:
        warnings.warn(f"Opening inventory missing in {missing} rounds; possession counts cover observed rounds only. "
                      "Shot ranking is a fallback for weapons without possession evidence.", RuntimeWarning)
    primary = [BUY_ALIAS[item] for item, _ in sorted(carried.items(), key=lambda kv: (-kv[1], kv[0]))]
    fallback = [weapon for weapon, _ in sorted(fired.items(), key=lambda kv: (-kv[1], kv[0])) if weapon not in primary]
    return (primary + fallback)[:top]


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
    """Retain one side-legal primary from opening possession, with purchase fallback.

    Full plans choose the modal carried primary; force/eco primaries are capped at $2,000/
    $1,000 (Director's bucket floors), and pistol rounds never buy a primary. The full AWP
    plan requires $4,750 before armor: the existing Director's $4,000 full floor does NOT
    guarantee affordability. Static plans cannot express a money-dependent fallback.
    Other items retain the existing >=50% purchase rule and existing public output keys.
    """
    item_rounds: dict[tuple[str, str], Counter[str]] = {}
    carried: dict[tuple[str, str], Counter[str]] = {}
    observed: Counter[tuple[str, str]] = Counter()
    missing: Counter[tuple[str, str]] = Counter()
    round_counts: Counter[tuple[str, str]] = Counter()
    for match in matches:
        for row in match.rounds.itertuples():
            if row.side not in ("T", "CT"):
                continue
            if not math.isfinite(float(row.equip_value)):
                warnings.warn(f"Skipping unknown equipment category: {match.match_id} round {row.round}", RuntimeWarning)
                continue
            key = (row.side, buy_type(int(row.round), float(row.equip_value)))
            round_counts[key] += 1
            items = set(match.purchases[match.purchases["round"] == row.round]["item_name"].astype(str))
            item_rounds.setdefault(key, Counter()).update(items)
            inv = opening_inventory(match, row.round)
            if inv is None:
                missing[key] += 1
            else:
                observed[key] += 1
                carried.setdefault(key, Counter()).update(inv & PRIMARY_GUNS)
    out: dict[str, dict[str, dict]] = {}
    for key in sorted(round_counts):
        side, kind = key
        total = round_counts[key]
        counts = sorted(item_rounds.get(key, Counter()).items(), key=lambda kv: (-kv[1], kv[0]))
        share = {item: n / total for item, n in counts}
        usual = [item for item, value in share.items() if value >= 0.5 and item not in PRIMARY_GUNS and _legal(item, side)]
        cap = {"pistol": 0, "eco": 1000, "force": 2000, "full": float("inf")}[kind]
        def eligible(item):
            return item in PRIMARY_GUNS and _legal(item, side) and PRIMARY_PRICES[item] <= cap
        evidence = carried.get(key, Counter())
        candidates = [item for item, _ in sorted(evidence.items(), key=lambda kv: (-kv[1], kv[0])) if eligible(item)]
        # Observed no-primary inventories are real evidence: do not replace them with a dropped
        # gun someone bought for a teammate. Purchase fallback is only for missing inventory.
        if not observed[key] or (evidence and not candidates):
            # A retained unaffordable gun is not a buy recommendation for a low-money bot.
            # Use an affordable purchase observed in this bucket when one exists.
            candidates = [item for item in share if eligible(item)]
        if missing[key]:
            warnings.warn(f"{side}/{kind}: opening inventory missing in {missing[key]}/{total} rounds; "
                          + ("using purchase-frequency primary fallback." if not observed[key]
                             else "primary selected only from observed opening inventories."), RuntimeWarning)
        usual = candidates[:1] + usual
        if kind in ("force", "full") and not any(item in ARMOR for item in usual):
            usual += [item for item in share if item in ARMOR][:1]
        # Never issue competing armor aliases either.
        armor = next((item for item in usual if item in ARMOR), None)
        usual = [item for item in usual if item not in ARMOR or item == armor]
        usual = purchase_order(usual)
        out.setdefault(side, {})[kind] = {
            "items": usual,
            "aliases": [BUY_ALIAS[i] for i in usual if i in BUY_ALIAS],
            "unmapped_items": [i for i in usual if i not in BUY_ALIAS],
            "rounds_of_this_type": total,
            "share_of_rounds_bought": {item: round(value, 2) for item, value in share.items()},
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
