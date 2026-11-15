"""Turn one model-generated path into a CANDIDATE CS2-Bot-Controller playback file.

    uv run python -m clone_pipeline.generated --review review.json --check review-check.json \\
        --case 3 --trace own

Input: a `cs2.clone.review.v1` file from `clone-model/review.py` (4 points per second) and the
automated geometry check file for it (`cs2.clone.review-check.v1`). Output, only under the
git-ignored `data/generated-candidates/<player>/`:
    generated_<trace>_<player>_<side>_<match>_round<round_id>_case<case>.json.br
    generated_<trace>_<player>_<side>_<match>_round<round_id>_case<case>.provenance.json

This follows SPEC section 8.5 steps 5-7 up to a file for review. The output is NOT a playable
clone file: the identity test failed (SPEC 8.6), so a generated path is not the player's style, and
no person has reviewed the path yet. Nothing here writes into `clones/`. Promotion is a separate,
manual step that this module does not do.

Gates (each refuses with a ValueError naming the reason):
  - review `format` is cs2.clone.review.v1, `split` is "dev", `deployed` is false;
  - the check file is cs2.clone.review-check.v1, its `review_sha256` is the SHA-256 of the review
    file's bytes, its entry for this case names the same player/match/round, and the chosen trace
    has `auto_check_passed: true` (a missing entry counts as not passed);
  - the trace is "own", "other" or "base" ("actual" is real recorded data, not a generated path);
  - the case is not from a held-out match (donk 2393242, broky 2393024);
  - the path is non-empty, finite, its channels have equal length, and its times are 0.25, 0.5, ...;
  - the output folder is a `data/generated-candidates` folder and not inside any `clones` folder.

The file itself is written by `recording.write_recording`, the same writer used for recorded routes.
That writer's own field guesses (EntityFlags, Subticks, Fields, MouseDx/Dy, Buttons1/2, DuckSpeed)
apply unchanged; see its docstring. The values this module has to guess, on top of those:
  - Times: start_position is placed at t=0 and path point i at t=0.25*(i+1). The tick table has
    64*duration + 1 rows (t=0 to t=duration inclusive); the written recording has 64*duration
    ticks, because each recording tick is the move from one row to the next.
  - Length: the path is never extended. It is cut to `end_stopped_at` points when that is a
    non-negative number (the model's native early stop; -1 or null means it ran the full horizon),
    and cut before the first point whose alive value is below 0.5.
  - Positions: straight lines between the 0.25 s points, so every tick stays on the segments the
    geometry check looked at. Knot rows (every 16th) equal the input points exactly.
  - Velocity: the slope of those lines, constant within each 0.25 s step; the last row repeats the
    last step's velocity. It is a derivative of interpolated positions, not a measured velocity.
    Any height change gives a vertical velocity, which recording.py turns into "not on ground".
  - View angles: CS-NET's angles are 5-degree tokens, and the review stores "the heading used for
    the step", not the camera after the step. So angle i is placed at the START of step i
    (t=0.25*i) and the final row holds the last angle. Yaw is interpolated the short way round
    (across +/-180) and written in [-180, 180); pitch is interpolated linearly.
  - Movement keys: from each tick's velocity relative to that tick's yaw. Forward/back/left/right
    is pressed when the speed along that axis is more than cos(67.5 deg) = 38% of the horizontal
    speed (8-way keys), and no key is pressed below 8 units/s (half of one 4-unit token per
    0.25 s). Bits: FORWARD 8, BACK 16, MOVELEFT 512, MOVERIGHT 1024, the CS2 values in the
    pipeline's recorded routes (checked on all 159 route files in clones/: on every one of 187,170
    commands these bits agree with ForwardMove/LeftMove).
  - The geometry check is assumed to have judged the straight segments between start_position and
    the 0.25 s points; linear interpolation adds no point off those segments.
  - Not modeled, so always off: ducking, jumping, walking (shift), use, reload, and firing. The
    model's firing flag is not turned into the attack button: it is a 0.25 s token aimed at 5
    degrees, and CloneDirector hands fights to the bot base anyway. The count is in the provenance.
  - Weapon: the review does not record the held item. WeaponDefIndex defaults to the stock knife
    (CT 42, T 59), which every player owns; override with --weapon-def-index.
  - move_type 2 (walk) on every tick, the same default recording.py uses.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .recording import TICKRATE, read_recording, write_recording

REVIEW_FORMAT = "cs2.clone.review.v1"
CHECK_FORMAT = "cs2.clone.review-check.v1"
PROVENANCE_FORMAT = "cs2.clone.generated-candidate.v1"
STEP_SECONDS = 0.25
TICKS_PER_STEP = round(STEP_SECONDS * TICKRATE)  # 16
GENERATED_TRACES = ("own", "other", "base")
HELD_OUT = {"donk": "2393242", "broky": "2393024"}

IN_FORWARD, IN_BACK, IN_MOVELEFT, IN_MOVERIGHT = 8, 16, 512, 1024
KEY_SHARE = math.cos(math.radians(67.5))
MIN_KEY_SPEED = 8.0
ALIVE_THRESHOLD = 0.5
MOVETYPE_WALK = 2
STOCK_KNIFE = {"CT": 42, "T": 59}
CS2_RUN_SPEED = 250.0  # fastest normal ground speed (knife); faster steps get a warning

TRACE_MEANING = {
    "own": "Generated with the case player's own identity vector.",
    "other": "Generated with the other player's identity vector, on this player's context.",
    "base": "Generated with identity row 0: the unadapted CS-NET v4 base model, no player identity.",
}
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = REPO_ROOT / "data" / "generated-candidates"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def wrap_degrees(angle: np.ndarray | float) -> np.ndarray:
    """Angle in [-180, 180)."""
    return (np.asarray(angle, dtype=float) + 180.0) % 360.0 - 180.0


# ---------------------------------------------------------------- gates


def check_review(review: dict) -> None:
    if review.get("format") != REVIEW_FORMAT:
        raise ValueError(f"Review format is {review.get('format')!r}, expected {REVIEW_FORMAT!r}.")
    if review.get("split") != "dev":
        raise ValueError(f"Review split is {review.get('split')!r}; only 'dev' reviews can be converted.")
    if review.get("deployed") is not False:
        raise ValueError("Review 'deployed' must be false; refusing a review that claims deployment.")
    if not isinstance(review.get("cases"), list) or not review["cases"]:
        raise ValueError("Review has no cases.")


def check_trace_name(trace: str) -> None:
    if trace == "actual":
        raise ValueError("'actual' is the real recorded path, not a generated one; convert recorded "
                         "routes with clone_pipeline.build instead.")
    if trace not in GENERATED_TRACES:
        raise ValueError(f"Trace must be one of {GENERATED_TRACES}, not {trace!r}.")


def check_not_held_out(case: dict) -> None:
    match_id = str(case.get("match_id"))
    if match_id in HELD_OUT.values():
        raise ValueError(f"Case is from held-out match {match_id}; held-out matches are never converted.")


def check_geometry(check: dict, review_bytes: bytes, case_index: int, case: dict, trace: str) -> dict:
    """Return the check entry for this trace, or refuse."""
    if check.get("format") != CHECK_FORMAT:
        raise ValueError(f"Check file format is {check.get('format')!r}, expected {CHECK_FORMAT!r}.")
    if check.get("review_sha256") != sha256_bytes(review_bytes):
        raise ValueError("Check file's review_sha256 does not match this review file; it checked a different file.")
    entries = [c for c in check.get("cases", []) if c.get("case") == case_index]
    if len(entries) != 1:
        raise ValueError(f"Check file has {len(entries)} entries for case {case_index}; need exactly one.")
    entry = entries[0]
    for key in ("player", "match_id", "round_id"):
        if key in entry and str(entry[key]) != str(case.get(key)):
            raise ValueError(f"Check entry {key}={entry[key]!r} differs from the review case ({case.get(key)!r}).")
    result = (entry.get("traces") or {}).get(trace) or {}
    if result.get("auto_check_passed") is not True:
        reasons = result.get("reasons") or ["no check result for this trace"]
        raise ValueError(f"Trace {trace!r} of case {case_index} did not pass the geometry check: {reasons}")
    return result


def check_output_root(root: Path) -> Path:
    root = Path(root).resolve()
    if "clones" in root.parts:
        raise ValueError(f"Refusing to write inside a clones folder ({root}); candidates are not playable clones.")
    if root.parts[-2:] != ("data", "generated-candidates"):
        raise ValueError(f"Output root must be a data/generated-candidates folder (git-ignored), not {root}.")
    return root


# ---------------------------------------------------------------- conversion


def usable_points(trace: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray, str]:
    """The path points, yaw and pitch that may be used, and why the path ends there."""
    path = trace.get("path") or []
    if not path:
        raise ValueError("Trace path is empty.")
    channels = {name: trace.get(name) for name in ("yaw_degrees", "pitch_degrees", "alive_values")}
    for name, values in channels.items():
        if not isinstance(values, list) or len(values) != len(path):
            raise ValueError(f"Trace channel {name} does not have one value per path point.")
    pts = np.asarray(path, dtype=float)
    if pts.ndim != 2 or pts.shape[1] != 4:
        raise ValueError("Each path point must be [seconds, x, y, z].")
    arrays = [pts] + [np.asarray(v, dtype=float) for v in channels.values()]
    if not all(np.isfinite(a).all() for a in arrays):
        raise ValueError("Trace has a non-finite value.")
    expected = STEP_SECONDS * np.arange(1, len(pts) + 1)
    if not np.allclose(pts[:, 0], expected, atol=1e-6):
        raise ValueError("Path times must be 0.25, 0.5, 0.75, ... seconds after the context.")

    n, reason = len(pts), "full horizon"
    stop = trace.get("end_stopped_at")
    if stop is not None and not isinstance(stop, (int, float)):
        raise ValueError(f"end_stopped_at must be a number or null, not {stop!r}.")
    if stop is not None and stop >= 0 and int(stop) < n:
        n, reason = int(stop), f"model early stop after {int(stop)} points"
    alive = np.asarray(channels["alive_values"], dtype=float)
    dead = np.flatnonzero(alive[:n] < ALIVE_THRESHOLD)
    if dead.size:
        n, reason = int(dead[0]), f"cut before first non-alive point (index {int(dead[0])})"
    if n == 0:
        raise ValueError(f"Nothing left to convert ({reason}).")
    yaw = np.asarray(channels["yaw_degrees"], dtype=float)[:n]
    pitch = np.asarray(channels["pitch_degrees"], dtype=float)[:n]
    return pts[:n, 1:], yaw, pitch, reason


def interpolate_ticks(start: np.ndarray, points: np.ndarray, yaw: np.ndarray, pitch: np.ndarray) -> pd.DataFrame:
    """64 rows per second from t=0 to the last point, inclusive (64*duration + 1 rows)."""
    knots = np.vstack([start, points])           # position knot k at t = 0.25*k
    angle_yaw = np.append(yaw, yaw[-1])          # angle i at the start of step i; last held
    angle_pitch = np.append(pitch, pitch[-1])
    steps = len(points)
    rows = steps * TICKS_PER_STEP + 1
    frac = (np.arange(rows) % TICKS_PER_STEP) / TICKS_PER_STEP
    seg = np.minimum(np.arange(rows) // TICKS_PER_STEP, steps)
    seg_next = np.minimum(seg + 1, steps)

    pos = knots[seg] + (knots[seg_next] - knots[seg]) * frac[:, None]
    step_velocity = np.diff(knots, axis=0) / STEP_SECONDS
    velocity = step_velocity[np.minimum(seg, steps - 1)]

    yaw_delta = wrap_degrees(angle_yaw[seg_next] - angle_yaw[seg])
    yaw_ticks = wrap_degrees(angle_yaw[seg] + yaw_delta * frac)
    pitch_ticks = angle_pitch[seg] + (angle_pitch[seg_next] - angle_pitch[seg]) * frac

    keys = movement_keys(velocity[:, :2], yaw_ticks)
    return pd.DataFrame({
        "tick": np.arange(rows), "seconds": np.arange(rows) / TICKRATE,
        "X": pos[:, 0], "Y": pos[:, 1], "Z": pos[:, 2],
        "velocity_X": velocity[:, 0], "velocity_Y": velocity[:, 1], "velocity_Z": velocity[:, 2],
        "pitch": pitch_ticks, "yaw": yaw_ticks, **keys,
    })


def movement_keys(velocity_xy: np.ndarray, yaw_degrees: np.ndarray) -> dict:
    """8-way movement keys and the button bits for them."""
    rad = np.radians(yaw_degrees)
    forward = velocity_xy[:, 0] * np.cos(rad) + velocity_xy[:, 1] * np.sin(rad)
    left = -velocity_xy[:, 0] * np.sin(rad) + velocity_xy[:, 1] * np.cos(rad)
    speed = np.hypot(velocity_xy[:, 0], velocity_xy[:, 1])
    moving = speed >= MIN_KEY_SPEED
    limit = KEY_SHARE * speed
    keys = {
        "FORWARD": moving & (forward > limit), "BACK": moving & (forward < -limit),
        "LEFT": moving & (left > limit), "RIGHT": moving & (left < -limit),
    }
    buttons = (keys["FORWARD"] * IN_FORWARD + keys["BACK"] * IN_BACK
               + keys["LEFT"] * IN_MOVELEFT + keys["RIGHT"] * IN_MOVERIGHT)
    return {**keys, "buttons": buttons.astype(int)}


def tick_table(case: dict, trace: dict, weapon_def_index: int) -> tuple[pd.DataFrame, str]:
    start = np.asarray(case.get("start_position"), dtype=float)
    if start.shape != (3,) or not np.isfinite(start).all():
        raise ValueError("Case start_position must be three finite numbers.")
    points, yaw, pitch, reason = usable_points(trace)
    ticks = interpolate_ticks(start, points, yaw, pitch)
    ticks["duck_amount"] = 0.0
    ticks["ducked"] = False
    ticks["ducking"] = False
    ticks["item_def_idx"] = float(weapon_def_index)
    ticks["move_type"] = MOVETYPE_WALK
    return ticks, reason


# ---------------------------------------------------------------- output


def candidate_name(case: dict, case_index: int, trace: str) -> str:
    return (f"generated_{trace}_{case['player']}_{str(case['side']).lower()}_{case['match_id']}"
            f"_round{case['round_id']}_case{case_index}")


def convert(review_path: str | Path, check_path: str | Path, case_index: int, trace_name: str,
            root: str | Path = DEFAULT_ROOT, weapon_def_index: int | None = None,
            overwrite: bool = False) -> dict:
    """Run every gate, write the candidate and its provenance. Returns the provenance."""
    check_trace_name(trace_name)
    root = check_output_root(Path(root))
    review_bytes = Path(review_path).read_bytes()
    check_bytes = Path(check_path).read_bytes()
    review, check = json.loads(review_bytes), json.loads(check_bytes)
    check_review(review)
    if not 0 <= case_index < len(review["cases"]):
        raise ValueError(f"Case {case_index} is out of range (review has {len(review['cases'])} cases).")
    case = review["cases"][case_index]
    check_not_held_out(case)
    side = str(case.get("side"))
    if side not in STOCK_KNIFE:
        raise ValueError(f"Case side must be T or CT, not {side!r}.")
    if str(case.get("player")) not in HELD_OUT:
        raise ValueError(f"Unknown player {case.get('player')!r}; only donk and broky have known held-out matches.")
    check_result = check_geometry(check, review_bytes, case_index, case, trace_name)
    trace = (case.get("predictions") or {}).get(trace_name)
    if not trace:
        raise ValueError(f"Case {case_index} has no {trace_name!r} prediction.")

    weapon = STOCK_KNIFE[side] if weapon_def_index is None else int(weapon_def_index)
    ticks, end_reason = tick_table(case, trace, weapon)

    out_dir = root / str(case["player"])
    name = candidate_name(case, case_index, trace_name)
    playback, sidecar = out_dir / f"{name}.json.br", out_dir / f"{name}.provenance.json"
    if not overwrite and (playback.exists() or sidecar.exists()):
        raise ValueError(f"{playback} already exists; pass --overwrite to replace it.")
    recording_ticks = write_recording(ticks, playback)

    speed = np.hypot(ticks["velocity_X"], ticks["velocity_Y"])
    used_steps = len(ticks) // TICKS_PER_STEP
    firing = trace.get("firing_values") or []
    warnings = []
    if speed.max() > CS2_RUN_SPEED:
        warnings.append(f"Peak horizontal speed {speed.max():.1f} u/s is above CS2's {CS2_RUN_SPEED:.0f} u/s run speed.")
    provenance = {
        "format": PROVENANCE_FORMAT,
        "source": "generated",
        "identity_quality": "not_established",
        "identity_test": "failed (SPEC 8.6, first A100 run)",
        "style_claim": "None. The identity test failed, so this path is not evidence of the player's style.",
        "manual_review_required": True,
        "promoted": False,
        "playback_file": playback.name,
        "playback_sha256": sha256_bytes(playback.read_bytes()),
        "trace": trace_name,
        "trace_meaning": TRACE_MEANING[trace_name],
        "identity_id": trace.get("identity_id"),
        "review": {
            "file": Path(review_path).name, "sha256": sha256_bytes(review_bytes),
            "format": review.get("format"), "split": review.get("split"), "deployed": review.get("deployed"),
            "identity_quality": review.get("identity_quality"), "selected_step": review.get("selected_step"),
            "source": review.get("source"), "interpretation": review.get("interpretation"),
        },
        "geometry_check": {
            "file": Path(check_path).name, "sha256": sha256_bytes(check_bytes), "format": check.get("format"),
            "note": check.get("note"), "auto_check_passed": True, "reasons": check_result.get("reasons", []),
        },
        "case": {
            "index": case_index, "player": case.get("player"), "steam_id": case.get("steam_id"),
            "match_id": str(case.get("match_id")), "round_id_zero_based": case.get("round_id"),
            "side": side, "context_tick": case.get("context_tick"),
            "seconds_into_round": case.get("seconds_into_round"), "start_position": case.get("start_position"),
        },
        "conversion": {
            "converter": "clone_pipeline.generated -> clone_pipeline.recording.write_recording",
            "input_points_used": used_steps, "input_points_in_trace": len(trace["path"]),
            "end_reason": end_reason, "end_stopped_at": trace.get("end_stopped_at"),
            "duration_seconds": used_steps * STEP_SECONDS,
            "tick_table_rows": len(ticks), "recording_ticks": recording_ticks,
            "tickrate": TICKRATE,
            "positions": "linear between start_position (t=0) and the 0.25 s points; knot rows exact",
            "velocity": "slope of the linear segments; last row repeats the last step",
            "yaw": "shortest-arc linear; angle i placed at the start of step i, last held; 5-degree model tokens",
            "pitch": "linear; angle i placed at the start of step i, last held; 5-degree model tokens",
            "movement_keys": f"8-way from velocity vs yaw: share > {KEY_SHARE:.3f} of speed, none below {MIN_KEY_SPEED} u/s",
            "button_bits": {"FORWARD": IN_FORWARD, "BACK": IN_BACK, "MOVELEFT": IN_MOVELEFT, "MOVERIGHT": IN_MOVERIGHT},
            "not_modeled": ["duck", "jump", "walk", "fire", "use", "reload", "weapon switch"],
            "firing_steps_ignored": int(sum(1 for v in firing[:used_steps] if v >= 0.5)),
            "weapon_def_index": weapon,
            "weapon_def_index_reason": "given" if weapon_def_index is not None else f"stock {side} knife; review has no item",
            "max_horizontal_speed": round(float(speed.max()), 3),
            "rows_with_vertical_speed": int((ticks["velocity_Z"].abs() >= 1.0).sum()),
            "recording_py_guesses": "unchanged; see clone_pipeline/recording.py",
        },
        "warnings": warnings,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    sidecar.write_text(json.dumps(provenance, indent=1) + "\n", encoding="utf-8")
    return provenance


def summarize(path: str | Path) -> dict:
    """Numbers to eyeball a written candidate: tick count, first/last position, peak speed."""
    rec = read_recording(path)
    pre = [t["Pre"] for t in rec["Ticks"]]
    last = rec["Ticks"][-1]["Post"]
    speeds = [math.hypot(p["VelX"], p["VelY"]) for p in pre]
    return {
        "ticks": len(rec["Ticks"]), "commands": len(rec["Commands"]), "tickrate": rec["Tickrate"],
        "first": [pre[0]["OriginX"], pre[0]["OriginY"], pre[0]["OriginZ"]],
        "last": [last["OriginX"], last["OriginY"], last["OriginZ"]],
        "max_horizontal_speed": max(speeds),
        "keys_pressed_ticks": sum(1 for c in rec["Commands"] if c["ForwardMove"] or c["LeftMove"]),
        "not_on_ground_ticks": sum(1 for p in pre if not p["EntityFlags"] & 1),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Make a generated playback CANDIDATE for human review.")
    parser.add_argument("--review", required=True, type=Path, help="cs2.clone.review.v1 file")
    parser.add_argument("--check", required=True, type=Path, help="cs2.clone.review-check.v1 file for that review")
    parser.add_argument("--case", required=True, type=int, help="zero-based case index in the review")
    parser.add_argument("--trace", required=True, help="own, other or base")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="a data/generated-candidates folder")
    parser.add_argument("--weapon-def-index", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    provenance = convert(args.review, args.check, args.case, args.trace, args.root,
                         args.weapon_def_index, args.overwrite)
    out = Path(args.root).resolve() / provenance["case"]["player"] / provenance["playback_file"]
    print(json.dumps({"written": str(out), **summarize(out), "warnings": provenance["warnings"]}, indent=1))


if __name__ == "__main__":
    main()
