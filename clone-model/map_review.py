"""Automated de_mirage geometry check for a `cs2.clone.review.v1` file. No approval is implied.

Reused from CS-NET v4 (MIT, revision 268dd2193c8a3d6e330c07dde5a851196c94eeaa):
- `scripts/training_data/map_loader.py` (`MapGeometry`): the mesh is read with
  `open3d.io.read_triangle_mesh`, converted with `o3d.t.geometry.TriangleMesh.from_legacy` and
  added to one `o3d.t.geometry.RaycastingScene`; rays are `[origin, direction]` rows in OBJ space
  and `t_hit` (inf for a miss) is divided by the scale to give game units, as in
  `player_raycast_batch`. This module also keeps `primitive_normals` from the same call.
- `scripts/training_data/config.py`: `SCALE = 0.0254`, `game_to_obj` (game x, y, z to OBJ
  y*S, z*S, x*S, Y up) and `DEPTH_EYE_HEIGHT = 64.0`, the origin height CS-NET adds to the player
  position for its 64 wall-distance rays. 64 is the top body ray height here.
The code is copied in reduced form rather than imported, so the tests run without a CS-NET
checkout; see `third_party/CSNET_LICENSE`. One change: the tensor mesh is built from vertex and
triangle arrays (the same data `from_legacy` copies), so tests can pass a synthetic mesh. The checks themselves (body-height segment rays, floor
rays, speed, stops) are new: CS-NET only measures wall distances and never tests a path.

Steps are zero-based: step i moves from the point at t=0.25*i (step 0 starts at start_position,
t=0) to the point at t=0.25*(i+1); a step reason gives that end time. Point k is at t=0.25*k.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

import numpy as np

FORMAT_IN = "cs2.clone.review.v1"
FORMAT_OUT = "cs2.clone.review-check.v1"
CSNET_REVISION = "268dd2193c8a3d6e330c07dde5a851196c94eeaa"
MESH_REL = "maps/optimized_obj_files/de_mirage.obj"
TRACES = ("actual", "own", "other", "base")
HOLDOUTS = {"2393242", "2393024"}
NOTE = "Automated geometry check only; a person must still review paths before use."

SCALE = 0.0254             # CS-NET config.SCALE: OBJ units per game unit
DEPTH_EYE_HEIGHT = 64.0    # CS-NET config.DEPTH_EYE_HEIGHT

THRESHOLDS = {
    "step_seconds": 0.25,
    "body_ray_heights_units": [20.0, 36.0, DEPTH_EYE_HEIGHT],
    "ray_hit_tolerance_units": 0.5,
    "wall_crossing": "segment ray blocked at both 36 and 64 units above the feet",
    "low_obstacle_crossing": "blocked at 20 or 36 but not a wall, with both end points within "
                             "18 units of a floor (no jump or fall)",
    "step_height_units": 18.0,
    "floor_ray_origin_above_feet_units": 24.0,
    "max_floor_surface_above_feet_units": 18.0,
    "max_floor_gap_units": 72.0,
    "falling_exemption_min_drop_units": 8.0,
    "buried_check_max_units": 64.0,
    "min_headroom_units": 32.0,
    "headroom": "a downward-facing surface 18 to 32 units above the feet fails; surfaces within "
                "18 units (stair and step geometry) are tolerated; the crouch hull is 54",
    "max_horizontal_units_per_step": 80.0,
    "near_limit_horizontal_units_per_step": 62.5,
    "near_limit_floor_gap_units": 36.0,
    "stop_max_horizontal_units_per_step": 4.0,
    "long_stop_min_steps": 8,
    "calibration": "Limits set so every actual (real player) step and point passes; "
                   "80 units/step is sv_maxspeed 320 u/s, 62.5 is the 250 u/s knife run speed",
}


def _game_to_obj(p):
    p = np.asarray(p, dtype=float)
    return np.stack([p[..., 1], p[..., 2], p[..., 0]], -1) * SCALE


def _game_dir_to_obj(d):
    d = np.asarray(d, dtype=float)
    return np.stack([d[..., 1], d[..., 2], d[..., 0]], -1)


class MapGeometry:
    """CS-NET's Open3D raycasting scene, with game-space rays and hit normals."""

    def __init__(self, obj_vertices, triangles, name="mesh"):
        import open3d as o3d
        self._o3d = o3d
        self.vertices = np.asarray(obj_vertices, dtype=np.float32)
        self.triangles = np.asarray(triangles, dtype=np.int32)
        if self.triangles.ndim != 2 or len(self.triangles) == 0:
            raise ValueError(f"Map mesh has no triangles: {name}")
        mesh = o3d.t.geometry.TriangleMesh()
        mesh.vertex.positions = o3d.core.Tensor(self.vertices)
        mesh.triangle.indices = o3d.core.Tensor(self.triangles)
        self._scene = o3d.t.geometry.RaycastingScene()
        self._scene.add_triangles(mesh)
        self.name = name

    @classmethod
    def from_obj(cls, path: Path):
        import open3d as o3d
        mesh = o3d.io.read_triangle_mesh(str(path))
        if len(mesh.triangles) == 0:
            raise ValueError(f"Map OBJ is empty or invalid: {path}")
        return cls(np.asarray(mesh.vertices), np.asarray(mesh.triangles), Path(path).stem)

    @classmethod
    def from_game_triangles(cls, game_vertices, triangles, name="synthetic"):
        return cls(_game_to_obj(game_vertices), triangles, name)

    def game_vertices(self):
        v = self.vertices.astype(float) / SCALE
        return np.stack([v[:, 2], v[:, 0], v[:, 1]], 1)

    def cast(self, origins, directions):
        """Game-space rays; returns (distance in game units, inf on miss; hit normal z)."""
        origins = np.asarray(origins, dtype=float).reshape(-1, 3)
        directions = np.asarray(directions, dtype=float).reshape(-1, 3)
        if len(origins) == 0:
            return np.zeros(0), np.zeros(0)
        rays = np.concatenate([_game_to_obj(origins), _game_dir_to_obj(directions)], 1)
        ans = self._scene.cast_rays(self._o3d.core.Tensor(rays.astype(np.float32)))
        t = ans["t_hit"].numpy().astype(float)
        normal_z = ans["primitive_normals"].numpy()[:, 1].astype(float)
        return np.where(np.isfinite(t), t / SCALE, np.inf), normal_z


def _finite_list(value, length=None):
    return (isinstance(value, list) and (length is None or len(value) == length)
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
                    for v in value))


def validate_review(data):
    """Reject anything that is not a well-formed development review file."""
    if not isinstance(data, dict) or data.get("format") != FORMAT_IN:
        raise ValueError(f"Expected format {FORMAT_IN}")
    if data.get("split") != "dev":
        raise ValueError("Only development review files are checked")
    if data.get("map") != "de_mirage":
        raise ValueError("Only de_mirage review files are supported")
    step = data.get("interval_seconds")
    if step != THRESHOLDS["step_seconds"]:
        raise ValueError("Expected interval_seconds 0.25")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Review file has no cases")
    for i, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"Case {i} is not an object")
        if str(case.get("match_id")) in HOLDOUTS:
            raise ValueError(f"Case {i} uses a held-out match")
        if not _finite_list(case.get("start_position"), 3):
            raise ValueError(f"Case {i} has no valid start_position")
        preds = case.get("predictions")
        if not isinstance(preds, dict) or not all(k in preds for k in TRACES[1:]):
            raise ValueError(f"Case {i} lacks own/other/base predictions")
        for name in TRACES:
            trace = case.get("actual") if name == "actual" else preds[name]
            path = trace.get("path") if isinstance(trace, dict) else None
            if not isinstance(path, list):
                raise ValueError(f"Case {i} {name} has no path")
            for k, point in enumerate(path):
                if not _finite_list(point, 4) or abs(point[0] - step * (k + 1)) > 1e-6:
                    raise ValueError(f"Case {i} {name} point {k} is not [t, x, y, z] at 0.25 s steps")
    return cases


def trace_points(case, name):
    trace = case["actual"] if name == "actual" else case["predictions"][name]
    pts = np.asarray([case["start_position"]] + [p[1:] for p in trace["path"]], dtype=float)
    return pts, trace


def check_trace(geom: MapGeometry, points, trace=None, th=THRESHOLDS):
    """Check one path (point 0 = start). Returns failing reasons, notes and raw measurements."""
    points = np.asarray(points, dtype=float).reshape(-1, 3)
    dt = th["step_seconds"]
    n = len(points)
    reasons, notes = [], []
    down = np.tile([0.0, 0.0, -1.0], (n, 1))
    up = np.tile([0.0, 0.0, 1.0], (n, 1))
    lift = th["floor_ray_origin_above_feet_units"]
    t_down, _ = geom.cast(points + [0, 0, lift], down)
    surface_above = lift - t_down                    # floor height relative to the feet
    gap = np.where(np.isfinite(t_down), np.maximum(-surface_above, 0.0), np.inf)
    t_up, nz_up = geom.cast(points + [0, 0, 1.0], up)
    # Feet under a slab's underside (a downward-facing surface within step height): the +24 ray
    # may land on that slab's top, so measure the floor from just above the feet instead.
    under_slab = np.isfinite(t_up) & (nz_up < -0.5) & (t_up + 1.0 <= th["step_height_units"])
    if under_slab.any():
        t_low, _ = geom.cast(points[under_slab] + [0, 0, 1.0], down[under_slab])
        gap[under_slab] = np.where(np.isfinite(t_low), np.maximum(t_low - 1.0, 0.0), np.inf)
    buried = np.isfinite(t_up) & (nz_up > 0.5) & (t_up + 1.0 > th["step_height_units"]) & (
        t_up + 1.0 <= th["buried_check_max_units"])
    dz = np.diff(points[:, 2])
    falling = np.zeros(n, dtype=bool)
    drop = th["falling_exemption_min_drop_units"]
    falling[1:] |= dz <= -drop
    falling[:-1] |= dz <= -drop
    low_ceiling = np.isfinite(t_up) & (nz_up < -0.5) & (t_up + 1.0 > th["step_height_units"]) & (
        t_up + 1.0 <= th["min_headroom_units"])
    grounded = gap <= th["step_height_units"]
    for k in range(n):
        t = round(k * dt, 3)
        if not np.isfinite(t_down[k]):
            reasons.append(f"no floor below point {k} (t={t} s): outside the map or inside solid geometry")
        elif low_ceiling[k]:
            reasons.append(f"no headroom at point {k} (t={t} s): ceiling {t_up[k] + 1:.0f} units above feet")
        elif surface_above[k] > th["max_floor_surface_above_feet_units"]:
            reasons.append(f"below floor at point {k} (t={t} s): surface {surface_above[k]:.0f} units above feet")
        elif buried[k]:
            reasons.append(f"below floor at point {k} (t={t} s): upward-facing surface {t_up[k] + 1:.0f} units above feet")
        elif gap[k] > th["max_floor_gap_units"] and not falling[k]:
            reasons.append(f"floating at point {k} (t={t} s): {gap[k]:.0f} units above floor")
        elif gap[k] > th["max_floor_gap_units"]:
            notes.append(f"falling at point {k} (t={t} s): {gap[k]:.0f} units above floor")

    heights = th["body_ray_heights_units"]
    a, b = points[:-1], points[1:]
    seg = b - a
    length = np.linalg.norm(seg, axis=1)
    moving = length > 1e-6
    blocked = np.zeros((len(seg), len(heights)), dtype=bool)
    if moving.any():
        dirs = seg[moving] / length[moving, None]
        for j, h in enumerate(heights):
            t_hit, _ = geom.cast(a[moving] + [0, 0, h], dirs)
            blocked[moving, j] = t_hit < length[moving] - th["ray_hit_tolerance_units"]
    horiz = np.linalg.norm(seg[:, :2], axis=1)
    near_speed = 0
    for i in range(len(seg)):
        t = round((i + 1) * dt, 3)
        knee, waist, eye = blocked[i]
        if waist and eye:
            reasons.append(f"wall crossing at step {i} (t={t} s)")
        elif knee or waist:
            if grounded[i] and grounded[i + 1]:
                reasons.append(f"low-obstacle crossing at step {i} (t={t} s) without a jump")
            else:
                notes.append(f"low obstacle under an airborne step {i} (t={t} s)")
        elif eye:
            notes.append(f"low ceiling at eye height on step {i} (t={t} s)")
        if horiz[i] > th["max_horizontal_units_per_step"]:
            reasons.append(f"impossible speed at step {i} (t={t} s): {horiz[i] / dt:.0f} units/s")
        elif horiz[i] > th["near_limit_horizontal_units_per_step"]:
            near_speed += 1
    stop = horiz < th["stop_max_horizontal_units_per_step"]
    run_start = None
    for i, s in enumerate(list(stop) + [False]):
        if s and run_start is None:
            run_start = i
        elif not s and run_start is not None:
            if i - run_start >= th["long_stop_min_steps"]:
                notes.append(f"long stop over steps {run_start}-{i - 1} "
                             f"(t={run_start * dt:g}-{i * dt:g} s, {(i - run_start) * dt:g} s)")
            run_start = None
    native = trace.get("end_stopped_at") if trace else None
    if native not in (None, -1):
        notes.append(f"native early stop at model step {native}; path has {n - 1} points")
    stats = dict(
        points=n, steps=len(seg),
        max_horizontal_units_per_step=round(float(horiz.max()), 2) if len(horiz) else 0.0,
        steps_near_speed_limit=near_speed,
        max_floor_gap_units=round(float(np.max(gap)), 2) if np.isfinite(gap).all() else None,
        points_near_floor_gap_limit=int(np.sum(np.isfinite(gap) & (gap > th["near_limit_floor_gap_units"]))),
        max_floor_surface_above_feet_units=round(float(np.max(np.where(np.isfinite(t_down), surface_above, -np.inf))), 2),
        points_with_surface_above_feet=int(np.sum(np.isfinite(t_down) & (surface_above > 1.0))),
        steps_blocked_at_height={str(h): int(blocked[:, j].sum()) for j, h in enumerate(heights)},
        min_ceiling_above_18_units=_round_min(np.where((nz_up < -0.5) & (t_up + 1.0 > th["step_height_units"]),
                                                       t_up + 1.0, np.inf)),
        stopped_steps=int(stop.sum()))
    return reasons, notes, stats


def _round_min(values):
    m = float(np.min(values)) if len(values) else math.inf
    return round(m, 2) if math.isfinite(m) else None


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_checks(review_path: Path, geom: MapGeometry, mesh_label: str):
    raw = Path(review_path).read_bytes()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"Review file is not JSON: {error}") from error
    cases = validate_review(data)
    out_cases, detail_cases = [], []
    for index, case in enumerate(cases):
        traces, details = {}, {}
        for name in TRACES:
            pts, trace = trace_points(case, name)
            reasons, notes, stats = check_trace(geom, pts, trace)
            traces[name] = {"auto_check_passed": not reasons, "reasons": reasons}
            details[name] = {"notes": notes, "stats": stats}
        out_cases.append({"case": index, "player": case.get("player"), "match_id": str(case.get("match_id")),
                          "round_id": case.get("round_id"), "traces": traces})
        detail_cases.append({"case": index, "side": case.get("side"), "traces": details})
    check = {"format": FORMAT_OUT, "review_sha256": hashlib.sha256(raw).hexdigest(), "map": "de_mirage",
             "mesh": mesh_label, "thresholds": THRESHOLDS, "note": NOTE, "cases": out_cases}
    actual = [d["traces"]["actual"] for d in detail_cases]
    calibration = {
        "actual_traces_failed": sum(not c["traces"]["actual"]["auto_check_passed"] for c in out_cases),
        "actual_steps": sum(a["stats"]["steps"] for a in actual),
        "actual_points": sum(a["stats"]["points"] for a in actual),
        "actual_steps_near_speed_limit": sum(a["stats"]["steps_near_speed_limit"] for a in actual),
        "actual_max_horizontal_units_per_step": max(a["stats"]["max_horizontal_units_per_step"] for a in actual),
        "actual_points_near_floor_gap_limit": sum(a["stats"]["points_near_floor_gap_limit"] for a in actual),
        "actual_max_floor_gap_units": max((a["stats"]["max_floor_gap_units"] or 0) for a in actual),
        "actual_points_with_surface_above_feet": sum(a["stats"]["points_with_surface_above_feet"] for a in actual),
        "actual_max_floor_surface_above_feet_units": max(a["stats"]["max_floor_surface_above_feet_units"] for a in actual),
        "actual_steps_with_airborne_low_obstacle_note": sum(
            sum("low obstacle under an airborne" in n for n in a["notes"]) for a in actual),
        "actual_min_ceiling_above_18_units": min((a["stats"]["min_ceiling_above_18_units"] for a in actual
                                                  if a["stats"]["min_ceiling_above_18_units"] is not None), default=None),
        "actual_steps_with_low_ceiling_note": sum(sum("low ceiling" in n for n in a["notes"]) for a in actual),
    }
    details = {"format": "cs2.clone.review-check-details.v1", "review_sha256": check["review_sha256"],
               "note": NOTE, "calibration_on_actual": calibration, "cases": detail_cases}
    return data, check, details


def plot_case(geom: MapGeometry, case, index, check_case, out: Path, tri_cache=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    styles = [("actual", "Real player", "#111827", "-"), ("own", "Own identity", "#2563eb", "-"),
              ("other", "Other identity", "#ea580c", "--"), ("base", "Generic base", "#16a34a", ":")]
    paths = {name: trace_points(case, name)[0] for name in TRACES}
    allp = np.concatenate(list(paths.values()))
    lo, hi = allp[:, :2].min(0), allp[:, :2].max(0)
    centre, half = (lo + hi) / 2, max((hi - lo).max() / 2 + 250, 400)
    zlo, zhi = allp[:, 2].min() - 40, allp[:, 2].max() + 100
    gv, tris = tri_cache if tri_cache is not None else (geom.game_vertices(), geom.triangles)
    tv = gv[tris]
    inside = ((tv[:, :, 0].max(1) > centre[0] - half) & (tv[:, :, 0].min(1) < centre[0] + half) &
              (tv[:, :, 1].max(1) > centre[1] - half) & (tv[:, :, 1].min(1) < centre[1] + half) &
              (tv[:, :, 2].max(1) > zlo) & (tv[:, :, 2].min(1) < zhi))
    sel = tv[inside]
    normal = np.cross(sel[:, 1] - sel[:, 0], sel[:, 2] - sel[:, 0])
    nz = np.abs(normal[:, 2]) / np.maximum(np.linalg.norm(normal, axis=1), 1e-9)
    floor, wall = sel[nz >= 0.7], sel[nz < 0.7]
    wall = wall[(wall[:, :, 2].max(1) > allp[:, 2].min() + 18) & (wall[:, :, 2].min(1) < allp[:, 2].max() + 64)]
    fig, ax = plt.subplots(figsize=(8, 8), layout="constrained")
    ax.add_collection(PolyCollection(floor[:, :, :2], facecolor="#e5e7eb", edgecolor="#d1d5db", linewidth=.2))
    ax.add_collection(PolyCollection(wall[:, :, :2], facecolor="#6b7280", edgecolor="#4b5563", linewidth=.4, alpha=.9))
    for name, label, color, ls in styles:
        p = paths[name]
        ok = check_case["traces"][name]["auto_check_passed"]
        ax.plot(p[:, 0], p[:, 1], color=color, linestyle=ls, linewidth=2.2, alpha=.9,
                label=f"{label}: {'auto pass' if ok else 'auto FAIL'}")
        ax.scatter(*p[-1, :2], color=color, s=18, zorder=6)
        for reason in check_case["traces"][name]["reasons"]:
            for word, offset in (("step ", 1), ("point ", 0)):
                if word in reason:
                    k = int(reason.split(word, 1)[1].split()[0]) + offset
                    ax.scatter(*p[min(k, len(p) - 1), :2], marker="x", color="#dc2626", s=60, zorder=8)
                    break
    ax.scatter(*paths["actual"][0, :2], marker="o", facecolor="none", edgecolor="#111827", s=70, zorder=9)
    ax.set_xlim(centre[0] - half, centre[0] + half)
    ax.set_ylim(centre[1] - half, centre[1] + half)
    ax.set_aspect("equal")
    ax.set_xlabel("X (Source units)"); ax.set_ylabel("Y (Source units)")
    ax.set_title(f"Case {index}: {case.get('player')} {case.get('match_id')} r{case.get('round_id')} "
                 f"(zero-based), {case.get('side')}\nfloor (light) and wall (dark) triangles at "
                 f"z {zlo:.0f} to {zhi:.0f}; red x = failed step/point\n"
                 "Automated geometry check only; a person must still review paths", fontsize=9)
    ax.legend(loc="lower left", fontsize=8, framealpha=.9)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=140)
    plt.close(fig)


def _csnet_revision(root: Path):
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("review", type=Path, help="cs2.clone.review.v1 JSON file")
    parser.add_argument("--csnet", type=Path, required=True, help="CS-NET checkout at the pinned revision")
    parser.add_argument("--out-dir", type=Path, default=Path("data/map-review"))
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args(argv)
    revision = _csnet_revision(args.csnet)
    if revision != CSNET_REVISION:
        raise SystemExit(f"Expected CS-NET {CSNET_REVISION}, got {revision}")
    geom = MapGeometry.from_obj(args.csnet / MESH_REL)
    data, check, details = run_checks(args.review, geom, f"{MESH_REL} @ {CSNET_REVISION}")
    details["mesh_sha256"] = file_sha256(args.csnet / MESH_REL)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = args.review.stem
    (args.out_dir / f"{stem}.check.json").write_text(json.dumps(check, indent=2), encoding="utf-8")
    (args.out_dir / f"{stem}.check-details.json").write_text(json.dumps(details, indent=2), encoding="utf-8")
    if not args.no_figures:
        cache = (geom.game_vertices(), geom.triangles)
        for index, case in enumerate(data["cases"]):
            plot_case(geom, case, index, check["cases"][index], args.out_dir / f"{stem}.case-{index}.png", cache)
    for c in check["cases"]:
        print("CASE", c["case"], c["player"], c["match_id"], c["round_id"],
              " ".join(f"{k}={'pass' if v['auto_check_passed'] else 'FAIL'}" for k, v in c["traces"].items()))
        for k, v in c["traces"].items():
            for r in v["reasons"]:
                print("   ", k, r)
    print("CALIBRATION", json.dumps(details["calibration_on_actual"]))
    print("WROTE", args.out_dir / f"{stem}.check.json")


if __name__ == "__main__":
    main()
