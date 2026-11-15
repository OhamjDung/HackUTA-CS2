"""Human limits: how fast, how often and how soon elite players move, turn and shoot.

Measures, at the game's full 64 ticks per second, the movement and aim numbers that make a bot look
human or not (SPEC.md section 8.10). Run it on professional recordings to set the limits, and on a
recorded bot match to check a clone against them:

    uv run python -m clone_pipeline.limits measure --out limits.csv <recording.dem> [more .dem]
    uv run python -m clone_pipeline.limits summary limits_ticks.npz
    uv run python -m clone_pipeline.limits calibrate --out references/human_limits.json limits.csv
    uv run python -m clone_pipeline.limits check --name donkL [--like donk] <bot match.dem>

"calibrate" turns the per-player rows of real pros into pass/fail thresholds: each threshold sits 5%
beyond the most extreme real player-match, so every measured pro passes. "check" measures a recording
and fails a player who goes beyond what any measured elite pro did. With --like, it also shows the
real player's own range (the envelope), which is information, not a pass rule.

"measure" writes one row per player per match (rates and percentiles) and, next to it, a .npz file
with the pooled per-tick and per-event samples, so population percentiles are exact.

Definitions (all angles in degrees, distances in game units):
- moving: planar speed of at least 60 units/s, measured over 4 ticks (1/16 s).
- backwards: moving, and the direction of motion is more than 135 degrees from where the player
  looks (yaw). Sideways: between 45 and 135.
- turn speed: change of view direction per tick, times 64. Yaw and pitch are combined.
- flick: the view change in the 0.25 s before the first shot of a burst (a burst starts after a gap
  of more than 0.25 s between gun shots).
- flick time: from the moment the view has turned 10% of the way to the moment of the shot, for
  flicks of at least 15 degrees.
- response time: from taking damage, when the player had not fired for 1 s, to the player's next
  gun shot, if within 2 s. It includes turning and is a stand-in for reaction time.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from demoparser2 import DemoParser

TICK = 64
MOVING = 60.0
NADE_WORDS = ("knife", "bayonet", "karambit", "grenade", "flashbang", "molotov", "decoy", "c4", "taser")
RIFLES = {"weapon_ak47", "weapon_m4a1", "weapon_m4a1_silencer", "weapon_galilar", "weapon_famas",
          "weapon_aug", "weapon_sg556"}
PROPS = ["X", "Y", "Z", "pitch", "yaw", "is_alive", "team_num"]


def _is_gun(weapon) -> bool:
    return not any(word in str(weapon) for word in NADE_WORDS)


def _wrap(angle):
    return (np.asarray(angle) + 180.0) % 360.0 - 180.0


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


def player_series(t: pd.DataFrame):
    """Per-tick motion and view arrays for one player's alive, in-round ticks (sorted by tick)."""
    tick = t["tick"].to_numpy()
    x, y = t["X"].to_numpy(float), t["Y"].to_numpy(float)
    yaw, pitch = t["yaw"].to_numpy(float), t["pitch"].to_numpy(float)
    joined = np.diff(tick, prepend=tick[0] - 2) == 1
    # Motion over 4 ticks, only where all 4 steps are consecutive.
    ok4 = np.zeros(len(t), dtype=bool)
    if len(t) > 4:
        run = pd.Series(joined.astype(int)).rolling(4).sum().to_numpy() == 4
        ok4[4:] = run[4:]
    dx = np.full(len(t), np.nan); dy = np.full(len(t), np.nan)
    dx[4:], dy[4:] = x[4:] - x[:-4], y[4:] - y[:-4]
    speed = np.where(ok4, np.hypot(dx, dy) * TICK / 4, np.nan)
    move_dir = np.degrees(np.arctan2(dy, dx))
    rel = np.abs(_wrap(move_dir - yaw))
    dyaw = np.where(joined, _wrap(np.diff(yaw, prepend=yaw[0])), np.nan)
    dpitch = np.where(joined, np.diff(pitch, prepend=pitch[0]), np.nan)
    turn = np.hypot(dyaw, dpitch) * TICK                      # degrees per second
    accel = np.where(joined, np.abs(np.diff(np.nan_to_num(turn), prepend=0)) * TICK, np.nan)
    # Turn speed sustained over 4 ticks (mean of the last 4), only where all 4 are consecutive.
    turn4 = np.where(ok4, pd.Series(turn).rolling(4).mean().to_numpy(), np.nan)
    # The model's resolution: one sample every 16 ticks (4 per second).
    on_grid = (tick % 16 == 0)
    gi = np.flatnonzero(on_grid)
    step_ok = np.zeros(len(gi), dtype=bool)
    if len(gi) > 1:
        step_ok[1:] = (np.diff(tick[gi]) == 16) & np.array(
            [joined[a + 1:b + 1].all() for a, b in zip(gi[:-1], gi[1:])])
    gx, gy = x[gi], y[gi]
    mx, my = np.diff(gx, prepend=np.nan), np.diff(gy, prepend=np.nan)
    step_yaw = np.where(step_ok, np.abs(_wrap(np.diff(yaw[gi], prepend=np.nan))), np.nan)
    step_pitch = np.where(step_ok, np.abs(np.diff(pitch[gi], prepend=np.nan)), np.nan)
    step_move = np.where(step_ok, np.hypot(mx, my), np.nan)
    ok2 = step_ok & np.roll(step_ok, 1)
    step_dmove = np.where(ok2, np.hypot(mx - np.roll(mx, 1), my - np.roll(my, 1)), np.nan)
    return dict(tick=tick, speed=speed, rel=rel, turn=turn, turn4=turn4, turn_accel=accel, yaw=yaw,
                pitch=pitch, joined=joined, step_yaw=step_yaw, step_pitch=step_pitch,
                step_move=step_move, step_dmove=step_dmove)


def longest_runs(mask: np.ndarray, joined: np.ndarray) -> np.ndarray:
    """Lengths, in ticks, of every unbroken run of True (a gap in ticks breaks a run)."""
    runs, n = [], 0
    for m, j in zip(mask, joined):
        if m and (j or n == 0):
            n += 1
        else:
            if n:
                runs.append(n)
            n = 1 if m else 0
    if n:
        runs.append(n)
    return np.asarray(runs, dtype=float)


def measure(path: Path) -> tuple[pd.DataFrame, dict]:
    parser = DemoParser(str(path))
    rounds = _rounds(parser)
    ticks = parser.parse_ticks(PROPS)
    ticks = ticks[ticks["team_num"].isin([2, 3])].sort_values(["steamid", "tick"])
    tk = ticks["tick"].to_numpy()
    live = np.zeros(len(ticks), dtype=bool)
    for a, b in rounds:
        live |= (tk >= a) & (tk <= b)
    ticks = ticks[live & ticks["is_alive"].astype(bool).to_numpy()]

    shots = parser.parse_event("weapon_fire")
    shots = shots[shots["weapon"].map(_is_gun)]
    hurts = parser.parse_event("player_hurt")
    match = path.name.split("_")[0]

    rows, pools = [], {k: [] for k in ("speed", "back_run_s", "turn", "turn_accel", "flick_deg",
                                       "flick_peak", "flick_time_s", "response_s", "rifle_shot_speed")}
    for sid, g in ticks.groupby("steamid"):
        s = player_series(g)
        moving = s["speed"] >= MOVING
        back = moving & (s["rel"] > 135)
        side = moving & (s["rel"] > 45) & (s["rel"] <= 135)
        back_runs = longest_runs(back, s["joined"]) / TICK
        turn = s["turn"][np.isfinite(s["turn"])]
        index = pd.Series(np.arange(len(s["tick"])), index=s["tick"])
        index = index[~index.index.duplicated()]

        mine = shots[shots["user_steamid"].astype(str) == str(sid)].sort_values("tick")
        st = mine["tick"].to_numpy()
        starts = mine[np.diff(st, prepend=-10**9) > 16]
        flick_deg, flick_peak, flick_time, rifle_speed = [], [], [], []
        for row in starts.itertuples():
            i = index.get(row.tick)
            if i is None or i < 32 or not s["joined"][i - 31:i + 1].all():
                continue
            yaw_w, pitch_w = s["yaw"][i - 16:i + 1], s["pitch"][i - 16:i + 1]
            total = float(np.hypot(_wrap(yaw_w[-1] - yaw_w[0]), pitch_w[-1] - pitch_w[0]))
            flick_deg.append(total)
            flick_peak.append(float(np.nanmax(s["turn"][i - 15:i + 1])))
            if total >= 15:
                path_turn = np.cumsum(np.nan_to_num(s["turn"][i - 31:i + 1]) / TICK)
                start = int(np.argmax(path_turn >= 0.1 * path_turn[-1]))
                flick_time.append((31 - start) / TICK)
            if row.weapon in RIFLES and np.isfinite(s["speed"][i]):
                rifle_speed.append(float(s["speed"][i]))

        response = []
        taken = hurts[hurts["user_steamid"].astype(str) == str(sid)]["tick"].to_numpy()
        for t0 in taken:
            if ((st > t0 - TICK) & (st <= t0)).any():
                continue
            nxt = st[(st > t0) & (st <= t0 + 2 * TICK)]
            if len(nxt):
                response.append((nxt[0] - t0) / TICK)

        alive_s = len(g) / TICK

        def q(values, p):
            values = np.asarray(values, dtype=float)
            values = values[np.isfinite(values)]
            return float(np.percentile(values, p)) if len(values) else np.nan

        rows.append({
            "player": str(g["name"].iloc[0]).lower(), "steamid": str(sid), "match": match,
            "alive_minutes": round(alive_s / 60, 2),
            "moving_share": float(np.nanmean(moving)),
            "backwards_share_of_moving": float(back.sum() / max(1, moving.sum())),
            "sideways_share_of_moving": float(side.sum() / max(1, moving.sum())),
            "backwards_seconds_per_minute": float(back.sum() / TICK / (alive_s / 60)),
            "backwards_run_p95_s": q(back_runs, 95), "backwards_run_max_s": q(back_runs, 100),
            "speed_p99": q(s["speed"], 99), "speed_max": q(s["speed"], 100),
            "turn_p50": q(turn, 50), "turn_p99": q(turn, 99), "turn_p999": q(turn, 99.9), "turn_max": q(turn, 100),
            "turn_accel_p999": q(s["turn_accel"], 99.9),
            "turn4_p999": q(s["turn4"], 99.9),
            "backwards_run_p99_s": q(back_runs, 99),
            "step_yaw_p999": q(s["step_yaw"], 99.9), "step_pitch_p999": q(s["step_pitch"], 99.9),
            "step_move_p999": q(s["step_move"], 99.9), "step_dmove_p999": q(s["step_dmove"], 99.9),
            "bursts": len(starts), "flicks_15deg": len(flick_time),
            "flick_deg_p50": q(flick_deg, 50), "flick_deg_p95": q(flick_deg, 95),
            "flick_peak_p99": q(flick_peak, 99),
            "flick_time_p05_s": q(flick_time, 5), "flick_time_p50_s": q(flick_time, 50),
            "response_n": len(response), "response_p05_s": q(response, 5), "response_p50_s": q(response, 50),
            "rifle_shot_speed_p50": q(rifle_speed, 50), "rifle_shot_speed_p95": q(rifle_speed, 95),
        })
        pools["speed"].append(s["speed"][np.isfinite(s["speed"])])
        pools["back_run_s"].append(back_runs)
        pools["turn"].append(turn)
        pools["turn_accel"].append(s["turn_accel"][np.isfinite(s["turn_accel"])])
        for key, values in (("flick_deg", flick_deg), ("flick_peak", flick_peak), ("flick_time_s", flick_time),
                            ("response_s", response), ("rifle_shot_speed", rifle_speed)):
            pools[key].append(np.asarray(values, dtype=float))
    return pd.DataFrame(rows), {k: np.concatenate(v) if v else np.array([]) for k, v in pools.items()}


# Checked per player per match. "max": the value must not exceed the threshold; "min": must not be below.
# "needs": a column and the minimum count of samples the check requires.
CHECKS = {
    "turn4_p999": ("max", "sustained turn speed over 4 ticks, 99.9th percentile (deg/s)", None),
    "turn_p999": ("max", "turn speed, 99.9th percentile (deg/s)", None),
    "turn_accel_p999": ("max", "turn acceleration, 99.9th percentile (deg/s^2)", None),
    "backwards_share_of_moving": ("max", "share of moving time walking backwards", None),
    "backwards_run_p99_s": ("max", "unbroken backwards walking, 99th percentile (s)", None),
    "flick_time_p05_s": ("min", "flick time for flicks of 15 deg or more, 5th percentile (s)", ("flicks_15deg", 5)),
    "step_pitch_p999": ("max", "pitch change per 0.25 s step, 99.9th percentile (deg)", None),
    "step_move_p999": ("max", "distance per 0.25 s step, 99.9th percentile (units)", None),
    "step_dmove_p999": ("max", "change of step movement, 99.9th percentile (units)", None),
}
MARGIN = 0.05


def calibrate(rows: pd.DataFrame) -> dict:
    """Thresholds 5% beyond the most extreme real player-match, so that every row passes."""
    out = {}
    for column, (kind, meaning, needs) in CHECKS.items():
        values = rows if not needs else rows[rows[needs[0]] >= needs[1]]
        values = values[column].dropna()
        if values.empty:
            continue
        extreme = values.max() if kind == "max" else values.min()
        limit = extreme * (1 + MARGIN) if kind == "max" else extreme * (1 - MARGIN)
        out[column] = {"kind": kind, "limit": round(float(limit), 4), "meaning": meaning,
                       "needs": list(needs) if needs else None, "pros_extreme": round(float(extreme), 4)}
    return {"source": "elite pro player-matches", "player_matches": int(len(rows)),
            "players": int(rows["player"].nunique()), "margin": MARGIN, "checks": out}


def check_row(row: dict, limits: dict) -> dict:
    """Pass or fail each check for one measured player-match. Missing data is reported, not passed."""
    results = {}
    for column, rule in limits["checks"].items():
        value = row.get(column)
        needs = rule.get("needs")
        if needs and (row.get(needs[0]) is None or row.get(needs[0]) < needs[1]):
            results[column] = {"status": "not enough samples", "value": value, "limit": rule["limit"]}
            continue
        if value is None or not np.isfinite(value):
            results[column] = {"status": "no data", "value": None, "limit": rule["limit"]}
            continue
        ok = value <= rule["limit"] if rule["kind"] == "max" else value >= rule["limit"]
        results[column] = {"status": "pass" if ok else "FAIL", "value": round(float(value), 4),
                           "limit": rule["limit"], "kind": rule["kind"]}
    failed = [c for c, r in results.items() if r["status"] == "FAIL"]
    return {"pass": not failed, "failed": failed, "results": results}


def summarise(pools: dict) -> pd.DataFrame:
    out = []
    for key, values in pools.items():
        values = values[np.isfinite(values)]
        if not len(values):
            continue
        out.append({"measure": key, "n": len(values),
                    **{f"p{p}": float(np.percentile(values, p)) for p in (1, 5, 50, 95, 99, 99.9)},
                    "max": float(values.max())})
    return pd.DataFrame(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    m = sub.add_parser("measure")
    m.add_argument("--out", type=Path, required=True)
    m.add_argument("demos", nargs="+", type=Path)
    s = sub.add_parser("summary")
    s.add_argument("pools", type=Path)
    c = sub.add_parser("calibrate")
    c.add_argument("--out", type=Path, required=True)
    c.add_argument("rows", type=Path, help="per-player CSV written by measure, from real pros")
    k = sub.add_parser("check")
    k.add_argument("--limits", type=Path,
                   default=Path(__file__).resolve().parents[1] / "references" / "human_limits.json")
    k.add_argument("--name", required=True, help="the bot's or player's name in the recording")
    k.add_argument("--like", help="also show this real player's own range, from --reference")
    k.add_argument("--reference", type=Path,
                   default=Path(__file__).resolve().parents[2] / "clone-model" / "results" / "human-limits.csv")
    k.add_argument("demo", type=Path)
    args = ap.parse_args()
    pd.set_option("display.width", 220)
    if args.command == "measure":
        frames, pools = [], {}
        for demo in args.demos:
            rows, p = measure(demo)
            frames.append(rows)
            for k, v in p.items():
                pools.setdefault(k, []).append(v)
            print(f"{demo.name}: {len(rows)} players", file=sys.stderr, flush=True)
        pd.concat(frames).to_csv(args.out, index=False)
        merged = {k: np.concatenate(v) for k, v in pools.items()}
        np.savez_compressed(args.out.with_name(args.out.stem + "_ticks.npz"), **merged)
        print(summarise(merged).to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    elif args.command == "calibrate":
        import json
        rows = pd.read_csv(args.rows)
        limits = calibrate(rows)
        if not all(check_row(r, limits)["pass"] for r in rows.to_dict("records")):
            raise SystemExit("A real pro fails a limit; the calibration is wrong.")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(limits, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.out}: {len(limits['checks'])} checks from {limits['player_matches']} player-matches; all pass")
    elif args.command == "check":
        import json
        limits = json.loads(args.limits.read_text(encoding="utf-8"))
        rows, _ = measure(args.demo)
        found = rows[rows["player"] == args.name.lower()]
        if found.empty:
            raise SystemExit(f"{args.name!r} is not in the recording. Names: {sorted(rows['player'])}")
        row = found.iloc[0].to_dict()
        result = check_row(row, limits)
        like = None
        if args.like:
            ref = pd.read_csv(args.reference)
            like = ref[ref["player"] == args.like.lower()]
        verdict = "PASS" if result["pass"] else "FAIL"
        print(f"{args.name} in {args.demo.name}: {row['alive_minutes']} alive minutes, {verdict} "
              f"({len(result['failed'])} of {len(result['results'])} checks failed)")
        for column, r in result["results"].items():
            extra = ""
            if like is not None and len(like) and column in like:
                extra = f"   {args.like}: {like[column].min():.3f} to {like[column].max():.3f}"
            print(f"  {r['status']:>18}  {column:28s} value {r['value']}  limit {r.get('kind', '')} {r['limit']}{extra}")
        sys.exit(0 if result["pass"] else 1)
    else:
        with np.load(args.pools) as saved:
            print(summarise({k: saved[k] for k in saved.files}).to_string(index=False, float_format=lambda v: f"{v:.3f}"))


if __name__ == "__main__":
    main()
