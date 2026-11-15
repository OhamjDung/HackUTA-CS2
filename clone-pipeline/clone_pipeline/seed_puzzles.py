"""Cut replay puzzles out of a pro match recording (SPEC.md, replay puzzles).

A puzzle is the last N seconds before one player dies: where all ten players were (4 samples a second),
what the hero held, who shot, who killed whom. Built on demoparser2 and the round finder in parse.py.

    uv run python -m clone_pipeline.seed_puzzles <match.dem> <out_dir> --hero donk --count 1

The recordings are git-ignored; the small JSON puzzles this writes are what gets committed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from demoparser2 import DemoParser

from .parse import TEAM_SIDE, TICKRATE, _build_rounds

SAMPLE_EVERY = 16  # ticks: 4 samples a second
PROPS = ["X", "Y", "Z", "yaw", "pitch", "health", "armor_value", "balance", "has_helmet", "active_weapon_name",
         "team_num", "inventory"]
GRENADES = {"flashbang", "smokegrenade", "hegrenade", "molotov", "incgrenade", "decoy"}


# demoparser2 gives display names for the inventory and the active weapon. Puzzles use the game's item
# names without the "weapon_" prefix (what CounterStrikeSharp's GiveNamedItem and the death event use).
WEAPON_NAMES = {
    "AK-47": "ak47", "M4A1-S": "m4a1_silencer", "M4A4": "m4a1", "AWP": "awp", "Galil AR": "galilar",
    "FAMAS": "famas", "MP9": "mp9", "MAC-10": "mac10", "MP7": "mp7", "MP5-SD": "mp5sd", "UMP-45": "ump45",
    "P90": "p90", "PP-Bizon": "bizon", "Tec-9": "tec9", "USP-S": "usp_silencer", "P2000": "hkp2000",
    "Glock-18": "glock", "Desert Eagle": "deagle", "Five-SeveN": "fiveseven", "CZ75-Auto": "cz75a",
    "P250": "p250", "Dual Berettas": "elite", "R8 Revolver": "revolver", "SSG 08": "ssg08",
    "SCAR-20": "scar20", "G3SG1": "g3sg1", "SG 553": "sg556", "AUG": "aug", "Nova": "nova", "XM1014": "xm1014",
    "MAG-7": "mag7", "Sawed-Off": "sawedoff", "M249": "m249", "Negev": "negev", "Flashbang": "flashbang",
    "Smoke Grenade": "smokegrenade", "High Explosive Grenade": "hegrenade", "Molotov": "molotov",
    "Incendiary Grenade": "incgrenade", "Decoy Grenade": "decoy", "Zeus x27": "taser", "C4 Explosive": "c4",
}


def clean_weapon(name) -> str:
    """The game's item name for a weapon, '' for none. Every knife skin becomes 'knife'."""
    text = str(name if name is not None else "").strip()
    if text in ("", "nan", "None"):
        return ""
    if text in WEAPON_NAMES:
        return WEAPON_NAMES[text]
    if any(w in text.lower() for w in ("knife", "bayonet", "karambit", "daggers")):
        return "knife"
    return text.replace("weapon_", "").lower()


def moments(parser: DemoParser, rounds, hero_id: int, window_s: float):
    """Deaths of the hero that happen inside a live round, with the hero's kills in the window before."""
    deaths = parser.parse_event("player_death")
    out = []
    for row in deaths.itertuples():
        if int(getattr(row, "user_steamid")) != hero_id:
            continue
        tick = int(row.tick)
        rnd = rounds[(rounds.freeze_end < tick) & (rounds.end >= tick)]
        if rnd.empty:
            continue
        start = max(int(rnd.iloc[0].freeze_end), tick - int(window_s * TICKRATE))
        if tick - start < 5 * TICKRATE:
            continue  # died too early in the round for a useful window
        kills = deaths[(deaths["tick"] > start) & (deaths["tick"] < tick)
                       & (deaths["attacker_steamid"].astype(str) == str(hero_id))]
        out.append({"tick": tick, "start": start, "round": int(rnd.iloc[0]["round"]), "kills": len(kills),
                    "killer": row.attacker_name, "weapon": row.weapon})
    return out


def build_puzzle(parser: DemoParser, match_id: str, map_name: str, m: dict, hero_id: int, tags: list[str],
                 title: str) -> dict:
    ticks = list(range(m["start"], m["tick"] + 1, SAMPLE_EVERY))
    if ticks[-1] != m["tick"]:
        ticks.append(m["tick"])
    frame = parser.parse_ticks(PROPS, ticks=ticks)
    fires = parser.parse_event("weapon_fire")
    fires = fires[(fires["tick"] >= m["start"]) & (fires["tick"] <= m["tick"])]
    deaths = parser.parse_event("player_death")
    deaths = deaths[(deaths["tick"] >= m["start"]) & (deaths["tick"] <= m["tick"])]
    throws = fires[fires["weapon"].map(clean_weapon).isin(GRENADES)]

    players = []
    for i, (sid, g) in enumerate(sorted(frame.groupby("steamid"), key=lambda kv: str(kv[1].iloc[0]["name"]))):
        g = g.sort_values("tick")
        first = g.iloc[0]
        name = str(first["name"])
        mine = fires[fires["user_steamid"].astype(str) == str(sid)]["tick"].tolist()

        def firing(tick: int) -> bool:
            return any(tick - SAMPLE_EVERY < f <= tick for f in mine)

        track = [{"t": round((int(r.tick) - m["start"]) / TICKRATE, 2), "x": round(float(r.X), 1),
                  "y": round(float(r.Y), 1), "z": round(float(r.Z), 1), "yaw": round(float(r.yaw), 1),
                  "pitch": round(float(r.pitch), 1), "hp": int(r.health), "weapon": clean_weapon(r.active_weapon_name),
                  "fire": firing(int(r.tick))} for r in g.itertuples()]
        inventory = [clean_weapon(w) for w in (first["inventory"] if first["inventory"] is not None else [])]
        players.append({
            "slot": i + 1, "name": name, "side": TEAM_SIDE.get(int(first["team_num"]), "T"),
            "hero": int(sid) == hero_id,
            "start": {"health": int(first["health"]), "armor": int(first["armor_value"]),
                      "helmet": bool(first["has_helmet"]), "money": int(first["balance"]),
                      "weapons": inventory},
            "track": track,
        })
    events = [{"t": round((int(r.tick) - m["start"]) / TICKRATE, 2), "type": "kill", "attacker": r.attacker_name,
               "victim": r.user_name, "weapon": clean_weapon(r.weapon)} for r in deaths.itertuples()
              if r.attacker_name and r.user_name]
    names = {p["slot"]: p["name"] for p in players}
    for r in throws.itertuples():
        events.append({"t": round((int(r.tick) - m["start"]) / TICKRATE, 2), "type": "throw",
                       "attacker": next((p["name"] for p in players
                                         if str(r.user_steamid) and p["name"] == r.user_name), r.user_name),
                       "victim": None, "weapon": clean_weapon(r.weapon)})
    events.sort(key=lambda e: e["t"])
    hero = next(p for p in players if p["hero"])
    return {"id": f"pro_{match_id}_r{m['round']}_{hero['name']}", "title": title, "map": map_name, "source": "pro",
            "source_info": {"match": match_id, "round": m["round"], "hero_died_tick": m["tick"],
                            "demo_license": "see SPEC.md section 7.1"},
            "window_seconds": round((m["tick"] - m["start"]) / TICKRATE, 1), "players": players, "events": events,
            "original": {"kills": m["kills"], "died": True, "killer": m["killer"], "weapon": clean_weapon(m["weapon"])},
            "tags": tags, "rating": 1500 + 100 * m["kills"], "notes": ""}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("demo")
    ap.add_argument("out_dir")
    ap.add_argument("--hero", required=True, help="player name, as in the recording")
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--window", type=float, default=10.0)
    ap.add_argument("--min-kills", type=int, default=1, help="only deaths where the hero first got this many kills")
    ap.add_argument("--tags", default="entry,rifle,mirage")
    args = ap.parse_args()

    parser = DemoParser(args.demo)
    info = parser.parse_player_info()
    found = info[info["name"].str.lower() == args.hero.lower()]
    if len(found) != 1:
        raise SystemExit(f"Need exactly one player named {args.hero!r}; found {len(found)}")
    hero_id = int(found.iloc[0]["steamid"])
    rounds = _build_rounds(parser)
    options = [m for m in moments(parser, rounds, hero_id, args.window) if m["kills"] >= args.min_kills]
    options.sort(key=lambda m: -m["kills"])
    if not options:
        raise SystemExit("No matching deaths in this recording")
    header = parser.parse_header()
    match_id = Path(args.demo).name.split("_")[0]
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for m in options[: args.count]:
        title = f"{args.hero}: {m['kills']} kill{'s' if m['kills'] != 1 else ''}, then dead (round {m['round']})"
        puzzle = build_puzzle(parser, match_id, header.get("map_name", "de_mirage"), m, hero_id,
                              [t for t in args.tags.split(",") if t], title)
        path = out / f"{puzzle['id']}.json"
        path.write_text(json.dumps(puzzle, indent=1), encoding="utf-8")
        print(f"wrote {path} ({len(puzzle['players'])} players, window {puzzle['window_seconds']} s, "
              f"{m['kills']} original kills)")


if __name__ == "__main__":
    main()
