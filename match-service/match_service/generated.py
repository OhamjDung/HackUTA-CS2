"""Generated movement paths for the replay page: offline review files from the model.

`clone-model/review.py` (Arjun's) writes `cs2.clone.review.v1` files: development rounds where
the model predicted the next few seconds of a player's movement with the player's own identity,
the other player's identity and no identity (the base model), next to the real path. This module
reads those files from `REVIEW_DIR` for drawing. It never changes them and never makes them
playable.

The identity test for this model failed (SPEC.md 8.6), so a file is only shown if it says it is a
development file that is not deployed, and none of its cases come from a held-out match.

A sidecar `cs2.clone.review-check.v1` file can add an automated geometry check per trace. It is
used only when its `review_sha256` is the SHA-256 of the review file's bytes.

Written from zero: no existing tool reads this format for a web view.
"""

import hashlib
import json
import math
import re
from pathlib import Path

REVIEW_FORMAT = "cs2.clone.review.v1"
CHECK_FORMAT = "cs2.clone.review-check.v1"
# Each player's held-out match (clone-model/common.py HOLDOUTS). They must never be shown here.
HOLDOUT_MATCHES = {"donk": "2393242", "broky": "2393024"}
TRACES = ("actual", "own", "other", "base")
PREDICTIONS = ("own", "other", "base")
MAX_BYTES = 20 * 1024 * 1024
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\.json")


class ReviewNotFound(Exception):
    pass


class ReviewInvalid(Exception):
    pass


class ReviewLibrary:
    def __init__(self, folder: Path):
        self.dir = folder

    # --- Files ----------------------------------------------------------------------------------

    def _path(self, name: str) -> Path:
        """The file `name` in the folder. Refuses anything that could point outside it."""
        if not NAME.fullmatch(name) or ".." in name:
            raise ReviewNotFound(f"Not a review file name: {name!r}")
        folder = self.dir.resolve()
        path = (folder / name).resolve()
        if path.parent != folder or not path.is_file():
            raise ReviewNotFound(f"No review file {name}")
        return path

    def _names(self) -> list[str]:
        if not self.dir.is_dir():
            return []
        return sorted(p.name for p in self.dir.glob("*.json") if NAME.fullmatch(p.name))

    def _load(self, name: str) -> tuple[dict, str]:
        """(parsed JSON, sha256 of the bytes). Raises ReviewInvalid for unreadable files."""
        path = self._path(name)
        if path.stat().st_size > MAX_BYTES:
            raise ReviewInvalid(f"{name} is larger than {MAX_BYTES // (1024 * 1024)} MB")
        return _read(path)

    # --- Listing --------------------------------------------------------------------------------

    def scan(self) -> dict:
        """Every review file with its cases, the check files that match one, and what was ignored."""
        reviews, checks, ignored = {}, [], []
        for name in self._names():
            try:
                data, digest = self._load(name)
                fmt = data.get("format") if isinstance(data, dict) else None
                if fmt == REVIEW_FORMAT:
                    validate_review(data)
                    reviews[name] = (data, digest)
                elif fmt == CHECK_FORMAT:
                    checks.append((name, data))
                else:
                    ignored.append({"file": name, "reason": f"format is {fmt!r}, not {REVIEW_FORMAT!r}"})
            except (ReviewInvalid, ReviewNotFound) as exc:
                ignored.append({"file": name, "reason": str(exc)})

        matched: dict[str, tuple[str, dict]] = {}
        by_digest = {digest: name for name, (_, digest) in reviews.items()}
        for name, data in checks:
            review = by_digest.get(data.get("review_sha256"))
            if review is None:
                ignored.append({"file": name, "reason": "review_sha256 matches no review file here"})
                continue
            try:
                matched[review] = (name, validate_check(data, reviews[review][0]))
            except ReviewInvalid as exc:
                ignored.append({"file": name, "reason": str(exc)})
        return {"reviews": reviews, "checks": matched, "ignored": ignored}

    def listing(self) -> dict:
        found = self.scan()
        files = []
        for name, (data, digest) in found["reviews"].items():
            check = found["checks"].get(name)
            cases = []
            for i, c in enumerate(data["cases"]):
                cases.append({
                    "case": i, "player": c["player"], "steam_id": c.get("steam_id"),
                    "match_id": str(c["match_id"]), "round_id": c["round_id"], "side": c.get("side"),
                    "seconds_into_round": c.get("seconds_into_round"), "context_tick": c.get("context_tick"),
                    "seconds": _seconds(c), "selected_step": data.get("selected_step"),
                    "identity_quality": data.get("identity_quality"),
                    "auto_check": _case_check_summary(check[1].get(i)) if check else None})
            files.append({**_file_meta(name, data, digest), "check_file": check[0] if check else None,
                          "cases": cases})
        return {"folder": str(self.dir.resolve()), "files": files, "ignored": found["ignored"]}

    # --- One case -------------------------------------------------------------------------------

    def case(self, name: str, index: int) -> dict:
        data, digest = self._load(name)
        if not isinstance(data, dict) or data.get("format") != REVIEW_FORMAT:
            raise ReviewInvalid(f"{name} is not a {REVIEW_FORMAT} file")
        validate_review(data)
        if not 0 <= index < len(data["cases"]):
            raise ReviewNotFound(f"{name} has no case {index} (it has {len(data['cases'])})")
        c = data["cases"][index]
        found = self.scan()
        check = found["checks"].get(name)
        check_entry = check[1].get(index) if check else None

        sx, sy = float(c["start_position"][0]), float(c["start_position"][1])
        raw = {"actual": c.get("actual")} | {k: (c.get("predictions") or {}).get(k) for k in PREDICTIONS}
        paths = {k: _xy(t["path"], sx, sy) if t else None for k, t in raw.items()}
        traces = {}
        for key in TRACES:
            t = raw[key]
            if not t:
                traces[key] = None
                continue
            same = [o for o in TRACES if o != key and raw[o] and raw[o]["path"] == t["path"]]
            traces[key] = {
                "identity_id": t.get("identity_id"),
                "path": paths[key],  # [[seconds after the start, x, y], ...], starting at the shared start
                "seconds": paths[key][-1][0],
                "end_stopped_at": t.get("end_stopped_at"),
                "channels": [ch for ch in ("yaw_degrees", "pitch_degrees", "alive_values", "firing_values")
                             if isinstance(t.get(ch), list)],
                "same_path_as": same,
                "distance_to_actual": _distance(paths[key], paths["actual"]) if key != "actual" else None,
                "auto_check": (check_entry or {}).get(key),
            }
        return {
            **_file_meta(name, data, digest),
            "case": index, "player": c["player"], "steam_id": c.get("steam_id"),
            "match_id": str(c["match_id"]), "round_id": c["round_id"], "side": c.get("side"),
            "context_tick": c.get("context_tick"), "seconds_into_round": c.get("seconds_into_round"),
            "start_position": c["start_position"], "traces": traces,
            "check": {"file": check[0], "note": check[1].note} if check else None,
        }


# --- Validation -----------------------------------------------------------------------------------

def validate_review(data: dict) -> None:
    """Raise ReviewInvalid unless this is a development, undeployed review with no held-out match."""
    if data.get("format") != REVIEW_FORMAT:
        raise ReviewInvalid(f"format must be {REVIEW_FORMAT!r}")
    if data.get("split") != "dev":
        raise ReviewInvalid(f"split must be 'dev', not {data.get('split')!r}")
    if data.get("deployed") is not False:
        raise ReviewInvalid("deployed must be false")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ReviewInvalid("no cases")
    held_out = set(HOLDOUT_MATCHES.values())
    for i, c in enumerate(cases):
        if not isinstance(c, dict):
            raise ReviewInvalid(f"case {i} is not an object")
        if str(c.get("match_id")) in held_out:
            raise ReviewInvalid(f"case {i} is from held-out match {c.get('match_id')}; the file is not shown")
        if not isinstance(c.get("player"), str) or c.get("match_id") is None or not isinstance(c.get("round_id"), int):
            raise ReviewInvalid(f"case {i} needs player, match_id and round_id")
        start = c.get("start_position")
        if not (isinstance(start, list) and len(start) >= 2 and all(_finite(v) for v in start)):
            raise ReviewInvalid(f"case {i}: start_position must be [x, y, z]")
        if not isinstance(c.get("actual"), dict):
            raise ReviewInvalid(f"case {i} has no actual path")
        preds = c.get("predictions")
        if not isinstance(preds, dict) or not any(isinstance(preds.get(k), dict) for k in PREDICTIONS):
            raise ReviewInvalid(f"case {i} has no own, other or base prediction")
        for key in TRACES:
            t = c["actual"] if key == "actual" else preds.get(key)
            if t is None:
                continue
            if not isinstance(t, dict):
                raise ReviewInvalid(f"case {i} {key}: not an object")
            path = t.get("path")
            if not isinstance(path, list) or not path:
                raise ReviewInvalid(f"case {i} {key}: path is missing or empty")
            last = 0.0
            for pt in path:
                if not (isinstance(pt, list) and len(pt) >= 3 and all(_finite(v) for v in pt)):
                    raise ReviewInvalid(f"case {i} {key}: each point must be [seconds, x, y, z]")
                if pt[0] <= last:
                    raise ReviewInvalid(f"case {i} {key}: times must increase from above 0")
                last = pt[0]


class CheckResults(dict):
    """{case index: {trace: {"auto_check_passed", "reasons"} or None}}, plus the file's note."""
    note: str | None = None


def validate_check(data: dict, review: dict) -> CheckResults:
    """Raise ReviewInvalid if an entry names a case the review doesn't have, or a different round."""
    entries = data.get("cases")
    if not isinstance(entries, list):
        raise ReviewInvalid("check file has no cases")
    out: dict[int, dict] = {}
    for e in entries:
        i = e.get("case") if isinstance(e, dict) else None
        if not isinstance(i, int) or not 0 <= i < len(review["cases"]):
            raise ReviewInvalid(f"check entry for case {i!r} is not a case in the review")
        c = review["cases"][i]
        for key, want in (("player", c["player"]), ("match_id", str(c["match_id"])), ("round_id", c["round_id"])):
            if key in e and (str(e[key]) if key == "match_id" else e[key]) != want:
                raise ReviewInvalid(f"check entry for case {i} has {key} {e[key]!r}; the review has {want!r}")
        traces = {}
        for key in TRACES:
            r = (e.get("traces") or {}).get(key)
            if isinstance(r, dict) and isinstance(r.get("auto_check_passed"), bool):
                traces[key] = {"auto_check_passed": r["auto_check_passed"],
                               "reasons": [str(x) for x in r.get("reasons") or []]}
            else:
                traces[key] = None  # not checked
        out[i] = traces
    results = CheckResults(out)
    results.note = str(data["note"]) if data.get("note") else None
    return results


# --- Helpers --------------------------------------------------------------------------------------

def _read(path: Path) -> tuple[dict, str]:
    # Read on every request (files are small, about 140 KB for eight cases), so a replaced file
    # and its check file are always seen together.
    raw = path.read_bytes()
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ReviewInvalid(f"{path.name} is not JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ReviewInvalid(f"{path.name} is not a JSON object")
    return data, hashlib.sha256(raw).hexdigest()


def _file_meta(name: str, data: dict, digest: str) -> dict:
    return {"file": name, "sha256": digest, "split": data["split"], "deployed": data["deployed"],
            "manual_review_required": data.get("manual_review_required"),
            "identity_quality": data.get("identity_quality"), "selected_step": data.get("selected_step"),
            "map": data.get("map"), "interval_seconds": data.get("interval_seconds"),
            "interpretation": data.get("interpretation")}


def _finite(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _xy(path: list, sx: float, sy: float) -> list[list[float]]:
    """[[t, x, y, z], ...] after the context, as [[t, x, y], ...] starting at the shared start (t=0)."""
    return [[0.0, round(sx, 1), round(sy, 1)]] + [[round(p[0], 3), round(p[1], 1), round(p[2], 1)] for p in path]


def _seconds(case: dict) -> float:
    ends = [t["path"][-1][0] for t in [case["actual"], *(case["predictions"].get(k) for k in PREDICTIONS)] if t]
    return max(ends)


def _distance(path: list, actual: list | None) -> dict | None:
    """Mean and final x/y distance from the real path at the same times (this example only)."""
    if not actual:
        return None
    real = {round(t, 3): (x, y) for t, x, y in actual}
    pairs = [(math.dist((x, y), real[round(t, 3)])) for t, x, y in path if round(t, 3) in real and t > 0]
    if not pairs:
        return None
    return {"mean": round(sum(pairs) / len(pairs), 1), "final": round(pairs[-1], 1), "points": len(pairs)}


def _case_check_summary(entry: dict | None) -> dict | None:
    if entry is None:
        return None
    return {k: (None if v is None else v["auto_check_passed"]) for k, v in entry.items()}
