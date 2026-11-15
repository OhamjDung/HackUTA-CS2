"""Per-player quirks: measure them, fit one rule per quirk, and test "who is it?".

A quirk is one number per player per match, such as jumps per minute. It is measured at the
game's full 64 ticks per second, for every player in a recording, so that each player can be
compared with the others in the same matches (the "population").

Why this exists (SPEC.md section 8.8): the first learned model was judged on 4-second paths, where
identity is not visible. Measured over a whole match, simple rates identify a player well.

Three commands:

    # Build a learned-quirk clone ("<player>L") on top of an existing clone profile.
    uv run python -m clone_pipeline.quirks build --player donk --demos ../data/demos \
        --holdout 2393242 --base ../clones/donk_v1.json --clone-id donkL

    # Check the quirks on a real held-back match (the ceiling), or on a recorded bot match.
    uv run python -m clone_pipeline.quirks score --profile ../clones/donkL.json \
        --demo <recording.dem> --name <the name the player or bot has in that recording>

The pass rules below were fixed on 2026-11-14 BEFORE any bot match or held-back match was scored
with them. They are deliberately looser than the first identity test, which required the player's
own identity to beat every alternative outright. Do not tune them on held-back results.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from demoparser2 import DemoParser

TICK = 64

# ---- pass rules (fixed before scoring; see the module text) ---------------------------------
WHO_IS_IT_TOP_K = 2          # pass if the true player is among the 2 nearest candidates
DISTINCTIVE_Z = 1.0          # a quirk is "distinctive" at 1 standard deviation from the population
QUIRK_MIN_SHARE = 0.5        # a quirk passes if the measured value covers at least half the
                             # player's distance from the population mean, on the player's side
QUIRKS_PASS_SHARE = 0.6      # the quirk test passes if at least 60% of distinctive quirks pass

RIFLES = {"weapon_ak47", "weapon_m4a1", "weapon_m4a1_silencer", "weapon_galilar", "weapon_famas"}
PISTOLS = {"weapon_glock", "weapon_usp_silencer", "weapon_hkp2000", "weapon_deagle", "weapon_p250",
           "weapon_tec9", "weapon_fiveseven", "weapon_cz75a", "weapon_elite"}
NADES = {"weapon_smokegrenade": "smoke", "weapon_flashbang": "flash", "weapon_hegrenade": "he",
         "weapon_molotov": "fire", "weapon_incgrenade": "fire"}
IN_JUMP = 2
KNIFE_IDS = [42, 59, *range(500, 530)]
PROPS = ["X", "Y", "Z", "pitch", "yaw", "is_alive", "team_num", "duck_amount", "buttons",
         "item_def_idx", "LEFT", "RIGHT"]

# What each quirk means, in plain words. The order is the order of the measured vector.
QUIRKS = {
    "jumps_per_min": "jumps per minute alive",
    "still_share": "share of alive time standing still",
    "full_speed_share": "share of alive time at running speed",
    "slow_share": "share of alive time moving slowly (walking or crouching)",
    "mean_speed": "average speed, game units per second",
    "look_speed_deg_s": "typical turning speed while moving, degrees per second",
    "pitch_std": "how much the view moves up and down",
    "crouch_time_share": "share of alive time crouched",
    "knife_out_share": "share of alive time holding the knife",
    "rifle_speed_at_first_shot": "speed at the first rifle shot of a burst",
    "moving_first_shot_share": "share of rifle bursts started while still moving",
    "single_shot_burst_share": "share of bursts that are a single shot",
    "shots_per_burst": "shots per burst",
    "crouched_shot_share": "share of shots fired while crouched",
    "turn_before_shot_deg": "typical turn in the quarter second before a burst, degrees",
    "peek_left_share": "share of bursts started while strafing left",
    "shots_per_round": "gun shots per round",
    "awp_shot_share": "share of shots fired with the sniper rifle (AWP)",
    "pistol_shot_share": "share of shots fired with pistols",
    "nades_per_round": "grenades thrown per round",
    "smoke_share": "share of grenades that are smokes",
    "flash_share": "share of grenades that are flashbangs",
    "fire_share": "share of grenades that are fire grenades",
    "first_contact_sec": "typical seconds from round start to the first damage dealt or taken",
    "opening_duel_rate": "share of rounds where the player is in the first kill",
    "team_distance": "typical distance from the centre of the teammates, game units",
    "alone_share": "share of alive time more than 1200 units from the teammates' centre",
}


def _is_gun(weapon) -> bool:
    w = str(weapon)
    return not any(x in w for x in ("knife", "bayonet", "karambit", "grenade", "flashbang", "molotov", "decoy", "c4"))


def _rounds(parser: DemoParser) -> list[tuple[int, int]]:
    live = sorted(parser.parse_event("round_freeze_end")["tick"].astype(int))
    ends = parser.parse_event("round_end")
    ends = sorted(ends[ends["winner"].notna()]["tick"].astype(int))
    out = []
    for end in ends:
        before = [t for t in live if t < end]
        if before:
            out.append((before[-1], end))
    return sorted(set(out))


def measure_recording(path: str | Path) -> pd.DataFrame:
    """One row per player in the recording: the quirk vector, plus player, steamid, match, rounds."""
    path = Path(path)
    parser = DemoParser(str(path))
    rounds = _rounds(parser)
    if not rounds:
        raise ValueError(f"No complete rounds in {path.name}")
    n_rounds = len(rounds)

    t = parser.parse_ticks(PROPS)
    t = t[t["team_num"].isin([2, 3])].sort_values(["steamid", "tick"]).reset_index(drop=True)
    tick = t["tick"].to_numpy()
    rid = np.zeros(len(t), dtype=int)
    for i, (a, b) in enumerate(rounds, 1):
        rid[(tick >= a) & (tick <= b)] = i
    t = t[(rid > 0) & t["is_alive"].astype(bool).to_numpy()].reset_index(drop=True)

    shots = parser.parse_event("weapon_fire")
    hurts = parser.parse_event("player_hurt")
    deaths = parser.parse_event("player_death").sort_values("tick")
    deaths["round"] = [next((i for i, (a, b) in enumerate(rounds, 1) if a <= x <= b), 0) for x in deaths["tick"]]
    first_death = deaths[deaths["round"] > 0].drop_duplicates("round")

    # Distance from the centre of the other teammates, sampled twice a second.
    samp = t[t["tick"] % 32 == 0]
    grouped = samp.groupby(["tick", "team_num"])
    count = grouped["X"].transform("count")
    others_x = (grouped["X"].transform("sum") - samp["X"]) / (count - 1).clip(lower=1)
    others_y = (grouped["Y"].transform("sum") - samp["Y"]) / (count - 1).clip(lower=1)
    samp = samp.assign(team_dist=np.hypot(samp["X"] - others_x, samp["Y"] - others_y).where(count > 1))

    rows = []
    for sid, g in t.groupby("steamid"):
        x, y, tk = g["X"].to_numpy(), g["Y"].to_numpy(), g["tick"].to_numpy()
        joined = np.diff(tk, prepend=tk[0] - 1) == 1   # False where the player's ticks are not consecutive
        speed = np.where(joined, np.hypot(np.diff(x, prepend=x[0]), np.diff(y, prepend=y[0])) * TICK, np.nan)
        yaw = g["yaw"].to_numpy()
        turn = (np.diff(yaw, prepend=yaw[0]) + 180) % 360 - 180
        yaw_rate = np.where(joined, np.abs(turn) * TICK, np.nan)
        buttons = g["buttons"].fillna(0).astype(np.int64).to_numpy()
        jumping = (buttons & IN_JUMP) > 0
        jump_starts = jumping & ~np.roll(jumping, 1) & joined
        duck = g["duck_amount"].fillna(0).to_numpy()
        weapon_id = g["item_def_idx"].fillna(-1).astype(int).to_numpy()
        by_tick = pd.DataFrame({"speed": speed, "duck": duck, "yaw": yaw, "left": g["LEFT"].to_numpy(),
                                "right": g["RIGHT"].to_numpy()}, index=tk)
        by_tick = by_tick[~by_tick.index.duplicated()]

        def at(ticks, column, earlier=0):
            return by_tick[column].reindex(np.asarray(ticks) - earlier).to_numpy(dtype=float)

        mine = shots[shots["user_steamid"].astype(str) == str(sid)]
        guns = mine[mine["weapon"].map(_is_gun)].sort_values("tick")
        gun_ticks = guns["tick"].to_numpy()
        starts_burst = np.diff(gun_ticks, prepend=-10**9) > 16     # a gap of over a quarter second
        burst_ticks = gun_ticks[starts_burst]
        burst_len = np.diff(np.append(np.flatnonzero(starts_burst), len(gun_ticks))) if len(gun_ticks) else np.array([])
        rifle_bursts = guns[starts_burst & guns["weapon"].isin(RIFLES).to_numpy()]["tick"].to_numpy()
        rifle_speed = at(rifle_bursts, "speed")
        turned = np.abs((at(burst_ticks, "yaw") - at(burst_ticks, "yaw", 16) + 180) % 360 - 180)
        left, right = np.nansum(at(burst_ticks, "left", 10)), np.nansum(at(burst_ticks, "right", 10))
        nades = mine[mine["weapon"].isin(NADES)]["weapon"].map(NADES).value_counts()
        damage = pd.concat([hurts[hurts["attacker_steamid"].astype(str) == str(sid)]["tick"],
                            hurts[hurts["user_steamid"].astype(str) == str(sid)]["tick"]])
        contact = [(damage[(damage >= a) & (damage <= b)].min() - a) / TICK
                   for a, b in rounds if ((damage >= a) & (damage <= b)).any()]
        opening = ((first_death["attacker_steamid"].astype(str) == str(sid)) |
                   (first_death["user_steamid"].astype(str) == str(sid))).sum()
        team_dist = samp[samp["steamid"] == sid]["team_dist"]
        moving = speed > 5

        def safe(fn, values, default=np.nan):
            values = np.asarray(values, dtype=float)
            return float(fn(values)) if values.size and not np.all(np.isnan(values)) else default

        rows.append({
            "player": str(g["name"].iloc[0]).lower(), "steamid": str(sid),
            "match": path.name.split("_")[0], "rounds": n_rounds,
            "jumps_per_min": float(jump_starts.sum() / (len(g) / TICK / 60)),
            "still_share": safe(np.nanmean, speed < 5),
            "full_speed_share": safe(np.nanmean, speed > 200),
            "slow_share": safe(np.nanmean, (speed >= 5) & (speed < 140)),
            "mean_speed": safe(np.nanmean, speed),
            "look_speed_deg_s": safe(np.nanmedian, yaw_rate[moving]),
            "pitch_std": float(g["pitch"].std()),
            "crouch_time_share": float(np.mean(duck > 0.5)),
            "knife_out_share": float(np.mean(np.isin(weapon_id, KNIFE_IDS))),
            "rifle_speed_at_first_shot": safe(np.nanmedian, rifle_speed),
            "moving_first_shot_share": safe(np.nanmean, rifle_speed > 40),
            "single_shot_burst_share": safe(np.mean, burst_len == 1),
            "shots_per_burst": safe(np.mean, burst_len),
            "crouched_shot_share": safe(np.nanmean, at(gun_ticks, "duck") > 0.5),
            "turn_before_shot_deg": safe(np.nanmedian, turned),
            "peek_left_share": float(left / (left + right)) if left + right > 0 else np.nan,
            "shots_per_round": len(gun_ticks) / n_rounds,
            "awp_shot_share": float(np.mean(guns["weapon"] == "weapon_awp")) if len(guns) else 0.0,
            "pistol_shot_share": float(np.mean(guns["weapon"].isin(PISTOLS))) if len(guns) else np.nan,
            "nades_per_round": float(nades.sum() / n_rounds),
            "smoke_share": float(nades.get("smoke", 0) / max(1, nades.sum())),
            "flash_share": float(nades.get("flash", 0) / max(1, nades.sum())),
            "fire_share": float(nades.get("fire", 0) / max(1, nades.sum())),
            "first_contact_sec": safe(np.median, contact),
            "opening_duel_rate": float(opening / n_rounds),
            "team_distance": safe(np.nanmedian, team_dist),
            "alone_share": safe(np.nanmean, team_dist > 1200),
        })
    return pd.DataFrame(rows)


def fit_quirks(rows: pd.DataFrame, player: str) -> dict:
    """Fit one rule per quirk for `player` from building matches only.

    Each rule holds the player's value, the population's mean and spread, how far the player is from
    the population (z, in population standard deviations), and whether the quirk is distinctive:
    at least DISTINCTIVE_Z away, in the same direction in every building match.
    """
    player = player.lower()
    mine, others = rows[rows["player"] == player], rows[rows["player"] != player]
    if mine.empty or others["player"].nunique() < 3:
        raise ValueError("Need the player and at least 3 other players in the building matches.")
    out = {}
    for name in QUIRKS:
        mean, sd = others[name].mean(), others[name].std()
        values = mine[name].dropna()
        if values.empty or not np.isfinite(sd) or sd == 0:
            continue
        z_each = (values - mean) / sd
        z = float(z_each.mean())
        same_direction = bool((np.sign(z_each) == np.sign(z)).all())
        out[name] = {
            "meaning": QUIRKS[name],
            "player": round(float(values.mean()), 4),
            "population_mean": round(float(mean), 4),
            "population_sd": round(float(sd), 4),
            "z": round(z, 2),
            "matches": int(len(values)),
            "distinctive": bool(abs(z) >= DISTINCTIVE_Z and same_direction and len(values) >= 2),
        }
    return out


def check_quirks(rules: dict, measured: dict) -> dict:
    """Per distinctive quirk: is the measured value on the player's side of the population mean, and
    at least QUIRK_MIN_SHARE of the way from the population mean to the player's value?"""
    checks = {}
    for name, rule in rules.items():
        value = measured.get(name)
        if not rule["distinctive"] or value is None or not np.isfinite(value):
            continue
        gap = rule["player"] - rule["population_mean"]
        covered = (value - rule["population_mean"]) / gap if gap else 0.0
        checks[name] = {"player": rule["player"], "population_mean": rule["population_mean"],
                        "measured": round(float(value), 4), "share_of_gap_covered": round(float(covered), 2),
                        "pass": bool(covered >= QUIRK_MIN_SHARE)}
    passed = sum(c["pass"] for c in checks.values())
    return {"checks": checks, "passed": passed, "distinctive_quirks": len(checks),
            "pass": bool(checks) and passed / len(checks) >= QUIRKS_PASS_SHARE}


def who_is_it(reference: dict[str, dict], population: dict[str, dict], measured: dict) -> list[tuple[str, float]]:
    """Rank the reference players by distance to the measured quirk vector (nearest first).

    reference: player -> {quirk: value}. population: quirk -> {"mean":, "sd":}. Distance is the mean
    squared difference in population standard deviations, over the quirks both sides have.
    """
    ranking = []
    for player, vector in reference.items():
        diffs = [((measured[q] - vector[q]) / population[q]["sd"]) ** 2 for q in QUIRKS
                 if q in vector and q in measured and q in population and population[q]["sd"] > 0
                 and np.isfinite(measured[q]) and np.isfinite(vector[q])]
        if diffs:
            ranking.append((player, float(np.mean(diffs))))
    return sorted(ranking, key=lambda item: item[1])


def reference_block(rows: pd.DataFrame, min_matches: int = 2) -> tuple[dict, dict]:
    """Reference vectors for every player seen in at least `min_matches` building matches, and the
    population mean and spread per quirk."""
    counts = rows.groupby("player")["match"].nunique()
    keep = counts[counts >= min_matches].index
    means = rows[rows["player"].isin(keep)].groupby("player")[list(QUIRKS)].mean()
    reference = {p: {q: round(float(v), 4) for q, v in row.items() if np.isfinite(v)} for p, row in means.iterrows()}
    population = {q: {"mean": round(float(rows[q].mean()), 4), "sd": round(float(rows[q].std()), 4)} for q in QUIRKS}
    return reference, population


# Rules switched off until a recorded match shows they stay inside human limits
# (clone-model/ROUND3_DESIGN.md, section 6, step 1). CloneDirector only applies quirks listed in
# "quirk_controls", so leaving a quirk out of it switches the rule off.
DISABLED_CONTROLS = {
    "still_share": "suspected cause of donkL walking backwards (Arjun watched it, 2026-11-15): the "
                   "sidestep makes the bot base walk back to its spot while aiming at its angle",
    "crouched_shot_share": "holding crouch for 0.6 s at the start of a burst may look mechanical",
}


def disabled_controls(rules: dict) -> dict:
    """The switched-off rules, with the value they would use and why they are off."""
    return {name: {"value": rules[name]["player"], "why_off": why}
            for name, why in DISABLED_CONTROLS.items() if name in rules}


def controls_from_quirks(rules: dict) -> dict:
    """Turn fitted quirks into bot controls. Each entry says what drives it and whether anything
    applies it yet. The mappings are design choices and are NOT validated in the game."""
    def z(name):
        return rules.get(name, {}).get("z", 0.0)

    controls = {}
    if "jumps_per_min" in rules:
        controls["jumps_per_min"] = {
            "value": rules["jumps_per_min"]["player"],
            "applied_by": "CloneDirector: presses jump at this rate while the bot runs outside a fight",
            "status": "implemented in the plugin; not run in CS2",
        }
    # The personality file's Teamwork is 0..100. A player who stays near teammates gets a high value.
    # 75 is the middle; each population standard deviation of "alone" moves it by 15.
    if "alone_share" in rules:
        controls["teamwork"] = {
            "value": int(np.clip(round(75 - 15 * z("alone_share")), 0, 100)),
            "applied_by": "bot personality file (botprofile.db), field Teamwork",
            "status": "written to botprofile.txt; installing it is a manual step",
        }
    plugin = {
        "shots_per_burst": "CloneDirector: releases the trigger after a drawn number of shots",
        "single_shot_burst_share": "CloneDirector: share of bursts limited to one shot",
        "crouched_shot_share": "CloneDirector: crouches for this share of bursts",
        "still_share": "CloneDirector: sidesteps when the bot has stood still more than this share",
    }
    for name, how in plugin.items():
        if name in rules and name not in DISABLED_CONTROLS:
            controls[name] = {"value": rules[name]["player"], "applied_by": how,
                              "status": "implemented in the plugin; not run in CS2"}
    # Distinctive quirks that no bot control can drive today. Stored so the score can still check them.
    blocked = {
        "look_speed_deg_s": "the bot interface has no control over view direction",
        "moving_first_shot_share": "would need movement control during a fight, which belongs to the bot base",
        "nades_per_round": "grenade throws are not yet installed into the grenade system",
        "flash_share": "grenade throws are not yet installed into the grenade system",
        "first_contact_sec": "set by routes and the personality file's Aggression, not by a separate control",
        "opening_duel_rate": "set by routes and the personality file's Aggression, not by a separate control",
        "awp_shot_share": "set by the purchase plan, not by a separate control",
    }
    for name, why in blocked.items():
        if name in rules and rules[name]["distinctive"]:
            controls[name] = {"value": rules[name]["player"], "applied_by": "nothing", "status": f"measured only: {why}"}
    return controls


def _gather(demos: Path, skip: set[str]) -> pd.DataFrame:
    paths = sorted(demos.glob("*.dem")) if demos.is_dir() else [demos]
    frames = [measure_recording(p) for p in paths if p.name.split("_")[0] not in skip]
    if not frames:
        raise ValueError("No recordings to measure.")
    return pd.concat(frames, ignore_index=True)


def build(args) -> None:
    player = args.player.lower()
    rows = _gather(args.demos, set(args.holdout))
    rows = rows[rows["match"].isin(rows[rows["player"] == player]["match"])]   # only this player's matches
    rules = fit_quirks(rows, player)
    reference, population = reference_block(rows)
    controls = controls_from_quirks(rules)

    profile = json.loads(args.base.read_text(encoding="utf-8"))
    base_id = profile["clone_id"]
    profile.update({
        "clone_id": args.clone_id,
        "display_name": args.clone_id,
        # CloneDirector adds the bot by this name. Each clone has its own entry in the bot base's
        # profile file (clone-director/tools/add_clone_bot_entries.py), named after the clone id.
        "stand_in_bot": args.clone_id,
        "learned": {
            "kind": "per-quirk rules fitted from recordings (clone_pipeline/quirks.py)",
            "based_on": base_id,
            "neural_model": None,
            "building_matches": sorted(rows["match"].unique().tolist()),
            "held_back_matches": sorted(args.holdout),
            "pass_rules": {"who_is_it_top_k": WHO_IS_IT_TOP_K, "distinctive_z": DISTINCTIVE_Z,
                           "quirk_min_share_of_gap": QUIRK_MIN_SHARE, "quirks_pass_share": QUIRKS_PASS_SHARE},
        },
        "quirks": rules,
        "quirk_controls": controls,
        "quirk_controls_disabled": disabled_controls(rules),
        "quirk_reference": {"players": reference, "population": population},
    })
    if "teamwork" in controls:
        profile["teamwork"] = controls["teamwork"]["value"] / 100
    out = args.out / f"{args.clone_id}.json"
    out.write_text(json.dumps(profile, indent=2), encoding="utf-8")

    distinctive = {k: v for k, v in rules.items() if v["distinctive"]}
    print(f"Wrote {out.name}: {len(rules)} quirks fitted, {len(distinctive)} distinctive, "
          f"from matches {profile['learned']['building_matches']}")
    for name, rule in sorted(distinctive.items(), key=lambda kv: -abs(kv[1]["z"])):
        print(f"  {name:28s} player {rule['player']:>9.3f}   others {rule['population_mean']:>9.3f}   z {rule['z']:+.2f}")
    print("  controls:", {k: v["value"] for k, v in controls.items()})


def score(args) -> None:
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    rows = measure_recording(args.demo)
    found = rows[rows["player"] == args.name.lower()]
    if found.empty:
        raise SystemExit(f"{args.name!r} is not in the recording. Names: {sorted(rows['player'])}")
    measured = {q: float(found.iloc[0][q]) for q in QUIRKS}
    target = profile["learned"]["based_on"].split("_")[0] if not args.target else args.target.lower()
    ref = profile["quirk_reference"]
    ranking = who_is_it(ref["players"], ref["population"], measured)
    names = [p for p, _ in ranking]
    rank = names.index(target) + 1 if target in names else None
    quirk_result = check_quirks(profile["quirks"], measured)
    result = {
        "recording": Path(args.demo).name, "measured_player": args.name, "target": target,
        "rounds": int(found.iloc[0]["rounds"]),
        "who_is_it": {"ranking": [[p, round(d, 3)] for p, d in ranking], "target_rank": rank,
                      "candidates": len(ranking), "pass": bool(rank is not None and rank <= WHO_IS_IT_TOP_K)},
        "quirks": quirk_result,
    }
    print(json.dumps(result, indent=2))
    if args.out:
        args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Measure, fit and test per-player quirks.")
    sub = ap.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="write a learned-quirk clone profile")
    b.add_argument("--player", required=True)
    b.add_argument("--demos", required=True, type=Path)
    b.add_argument("--holdout", nargs="*", default=[])
    b.add_argument("--base", required=True, type=Path, help="an existing clone profile to build on")
    b.add_argument("--clone-id", required=True)
    b.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[2] / "clones")
    b.set_defaults(run=build)
    s = sub.add_parser("score", help="test one recording against a learned-quirk profile")
    s.add_argument("--profile", required=True, type=Path)
    s.add_argument("--demo", required=True, type=Path)
    s.add_argument("--name", required=True, help="the player's or bot's name in the recording")
    s.add_argument("--target", help="whose clone this is; default: taken from the profile")
    s.add_argument("--out", type=Path)
    s.set_defaults(run=score)
    args = ap.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
