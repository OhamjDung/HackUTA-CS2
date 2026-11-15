"""Replay puzzles: stored moments a player retries until solved (SPEC.md, replay puzzles).

Modelled on Lichess's puzzle database: each puzzle has a rating that moves with solves, a player has a
rating and a streak, there is a daily puzzle, themes (tags), votes and an attempt history.
Written from zero on the standard library (sqlite3) and pydantic; no existing CS2 tool stores these.

Files: a puzzle is one JSON file (`<id>.json`) in the seed folder (committed, read-only) or the user
folder (data/puzzles). SQLite (`puzzles.db` in the user folder) holds ratings, plays, votes, attempts
and drafts, and is rebuilt around the JSON files, so a puzzle file copied in shows up on the next list.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

START_RATING = 1500.0
K_PLAYER = 32.0
K_PUZZLE = 16.0
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
VIDEO_TYPES = {".mp4", ".webm", ".mov", ".mkv"}
MAX_VIDEO_BYTES = 500 * 1024 * 1024


class Sample(BaseModel):
    t: float = Field(ge=0)
    x: float
    y: float
    z: float = 0
    yaw: float = 0
    pitch: float = 0
    hp: int = 100
    weapon: str = ""
    fire: bool = False


class Start(BaseModel):
    health: int = 100
    armor: int = 0
    helmet: bool = False
    money: int = 0
    weapons: list[str] = []


class PuzzlePlayer(BaseModel):
    slot: int
    name: str = Field(min_length=1, max_length=40)
    side: Literal["CT", "T"]
    hero: bool = False
    start: Start = Start()
    track: list[Sample] = Field(min_length=1)


class PuzzleEvent(BaseModel):
    t: float = Field(ge=0)
    type: Literal["kill", "throw", "plant", "defuse"]
    attacker: str | None = None
    victim: str | None = None
    weapon: str | None = None


class Original(BaseModel):
    kills: int = Field(ge=0)
    died: bool
    killer: str | None = None
    weapon: str | None = None


class Puzzle(BaseModel):
    id: str
    title: str = Field(min_length=1, max_length=120)
    map: str = "de_mirage"
    source: Literal["user", "pro"] = "user"
    source_info: dict = {}
    created: str = ""
    window_seconds: float = Field(default=10.0, gt=0, le=30)
    players: list[PuzzlePlayer] = Field(min_length=2, max_length=10)
    events: list[PuzzleEvent] = []
    original: Original
    tags: list[str] = []
    rating: float = START_RATING  # difficulty seed; the live rating is in the database
    notes: str = ""

    def hero(self) -> PuzzlePlayer:
        heroes = [p for p in self.players if p.hero]
        if len(heroes) != 1:
            raise ValueError("A puzzle needs exactly one hero")
        return heroes[0]


def validate_puzzle(data: dict) -> Puzzle:
    """Parse and check a puzzle dict. Raises ValueError with a readable message."""
    try:
        puzzle = Puzzle.model_validate(data)
    except ValidationError as exc:
        raise ValueError("; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()[:5]))
    if not ID_RE.match(puzzle.id):
        raise ValueError("id must be letters, digits, '-' or '_' (max 64)")
    puzzle.hero()
    slots = [p.slot for p in puzzle.players]
    if len(slots) != len(set(slots)):
        raise ValueError("Two players share a slot")
    names = [p.name for p in puzzle.players]
    if len(names) != len(set(names)):
        raise ValueError("Two players share a name")
    for p in puzzle.players:
        times = [s.t for s in p.track]
        if times != sorted(times):
            raise ValueError(f"Samples for {p.name} are not in time order")
    return puzzle


# --- Rules ---------------------------------------------------------------------------------------

def needed_kills(original_kills: int) -> int:
    """More kills than the original clip, and at least one."""
    return max(1, original_kills + 1)


def is_solved(puzzle: Puzzle, survived: bool, kills: int) -> bool:
    return survived and kills >= needed_kills(puzzle.original.kills)


def expected_score(rating: float, opponent: float) -> float:
    return 1.0 / (1.0 + 10 ** ((opponent - rating) / 400.0))


def new_ratings(player: float, puzzle: float, solved: bool) -> tuple[float, float]:
    """Elo: a solve moves the player up and the puzzle down, by how unexpected it was."""
    exp_player = expected_score(player, puzzle)
    score = 1.0 if solved else 0.0
    return (player + K_PLAYER * (score - exp_player),
            puzzle + K_PUZZLE * ((1.0 - score) - (1.0 - exp_player)))


def daily_pick(ids: list[str], day: date) -> str | None:
    """The same puzzle for everyone on one date: a hash of the date picks from the sorted ids."""
    if not ids:
        return None
    ids = sorted(ids)
    digest = hashlib.sha256(day.isoformat().encode()).digest()
    return ids[int.from_bytes(digest[:4], "big") % len(ids)]


# --- Store ---------------------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS stats (puzzle_id TEXT PRIMARY KEY, rating REAL NOT NULL, plays INTEGER NOT NULL DEFAULT 0,
  solves INTEGER NOT NULL DEFAULT 0, up INTEGER NOT NULL DEFAULT 0, down INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS players (player TEXT PRIMARY KEY, rating REAL NOT NULL, streak INTEGER NOT NULL DEFAULT 0,
  best_streak INTEGER NOT NULL DEFAULT 0, solved INTEGER NOT NULL DEFAULT 0, attempts INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS attempts (id INTEGER PRIMARY KEY AUTOINCREMENT, puzzle_id TEXT NOT NULL, player TEXT NOT NULL,
  solved INTEGER NOT NULL, survived INTEGER NOT NULL, kills INTEGER NOT NULL, rating_before REAL NOT NULL,
  rating_after REAL NOT NULL, at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS votes (puzzle_id TEXT NOT NULL, player TEXT NOT NULL, value INTEGER NOT NULL,
  PRIMARY KEY (puzzle_id, player));
CREATE TABLE IF NOT EXISTS drafts (id TEXT PRIMARY KEY, title TEXT NOT NULL, map TEXT NOT NULL, created TEXT NOT NULL,
  status TEXT NOT NULL, message TEXT NOT NULL, slots TEXT NOT NULL);
"""


class NotFound(Exception):
    pass


class PuzzleStore:
    def __init__(self, user_dir: Path, seed_dir: Path | None = None):
        self.user_dir = user_dir
        self.seed_dir = seed_dir
        user_dir.mkdir(parents=True, exist_ok=True)
        (user_dir / "footage").mkdir(exist_ok=True)
        self.db = sqlite3.connect(user_dir / "puzzles.db", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    # -- files
    def _files(self) -> dict[str, Path]:
        out: dict[str, Path] = {}
        for folder in (self.seed_dir, self.user_dir):
            if folder and folder.is_dir():
                for path in sorted(folder.glob("*.json")):
                    out[path.stem] = path
        return out

    def load(self, puzzle_id: str) -> Puzzle:
        path = self._files().get(puzzle_id) if ID_RE.match(puzzle_id) else None
        if not path:
            raise NotFound(puzzle_id)
        return validate_puzzle(json.loads(path.read_text(encoding="utf-8")))

    def add(self, puzzle: Puzzle) -> Puzzle:
        """Save a new user puzzle. Refuses an id that already exists (seed or user)."""
        if puzzle.id in self._files():
            raise ValueError(f"A puzzle with id {puzzle.id} already exists")
        puzzle.created = puzzle.created or datetime.now(timezone.utc).isoformat(timespec="seconds")
        (self.user_dir / f"{puzzle.id}.json").write_text(puzzle.model_dump_json(indent=1), encoding="utf-8")
        self._stats(puzzle)
        return puzzle

    def delete(self, puzzle_id: str) -> None:
        path = self.user_dir / f"{puzzle_id}.json"
        if not ID_RE.match(puzzle_id) or not path.is_file():
            raise NotFound(puzzle_id)  # seed puzzles are not deletable
        path.unlink()
        self.db.execute("DELETE FROM stats WHERE puzzle_id=?", (puzzle_id,))
        self.db.commit()

    # -- stats
    def _stats(self, puzzle: Puzzle) -> sqlite3.Row:
        row = self.db.execute("SELECT * FROM stats WHERE puzzle_id=?", (puzzle.id,)).fetchone()
        if not row:
            self.db.execute("INSERT INTO stats (puzzle_id, rating) VALUES (?, ?)", (puzzle.id, puzzle.rating))
            self.db.commit()
            row = self.db.execute("SELECT * FROM stats WHERE puzzle_id=?", (puzzle.id,)).fetchone()
        return row

    def summary(self, puzzle: Puzzle) -> dict:
        s = self._stats(puzzle)
        hero = puzzle.hero()
        return {"id": puzzle.id, "title": puzzle.title, "map": puzzle.map, "source": puzzle.source,
                "side": hero.side, "hero": hero.name, "tags": puzzle.tags, "created": puzzle.created,
                "window_seconds": puzzle.window_seconds, "rating": round(s["rating"]), "plays": s["plays"],
                "solves": s["solves"], "up": s["up"], "down": s["down"],
                "need_kills": needed_kills(puzzle.original.kills), "original": puzzle.original.model_dump()}

    def list(self, *, tag: str | None = None, map_: str | None = None, source: str | None = None,
             min_rating: float | None = None, max_rating: float | None = None,
             sort: str = "rating") -> list[dict]:
        rows = []
        for pid in self._files():
            try:
                rows.append(self.summary(self.load(pid)))
            except (ValueError, json.JSONDecodeError):
                continue  # a bad file is skipped here; GET /puzzles/{id} reports why
        if tag:
            rows = [r for r in rows if tag in r["tags"]]
        if map_:
            rows = [r for r in rows if r["map"] == map_]
        if source:
            rows = [r for r in rows if r["source"] == source]
        if min_rating is not None:
            rows = [r for r in rows if r["rating"] >= min_rating]
        if max_rating is not None:
            rows = [r for r in rows if r["rating"] <= max_rating]
        key = {"rating": lambda r: r["rating"], "plays": lambda r: -r["plays"],
               "new": lambda r: r["created"], "votes": lambda r: -(r["up"] - r["down"])}.get(sort)
        if key is None:
            raise ValueError("sort must be rating, plays, new or votes")
        return sorted(rows, key=key, reverse=sort == "new")

    def tags(self) -> list[dict]:
        counts: dict[str, int] = {}
        for r in self.list():
            for t in r["tags"]:
                counts[t] = counts.get(t, 0) + 1
        return [{"tag": t, "count": n} for t, n in sorted(counts.items())]

    # -- players
    def player(self, name: str) -> dict:
        row = self.db.execute("SELECT * FROM players WHERE player=?", (name,)).fetchone()
        if not row:
            self.db.execute("INSERT INTO players (player, rating) VALUES (?, ?)", (name, START_RATING))
            self.db.commit()
            row = self.db.execute("SELECT * FROM players WHERE player=?", (name,)).fetchone()
        return {"player": row["player"], "rating": round(row["rating"]), "streak": row["streak"],
                "best_streak": row["best_streak"], "solved": row["solved"], "attempts": row["attempts"]}

    def record_attempt(self, puzzle_id: str, player: str, survived: bool, kills: int) -> dict:
        puzzle = self.load(puzzle_id)
        solved = is_solved(puzzle, survived, kills)
        p = self.db.execute("SELECT * FROM players WHERE player=?", (player,)).fetchone()
        if not p:
            self.player(player)
            p = self.db.execute("SELECT * FROM players WHERE player=?", (player,)).fetchone()
        s = self._stats(puzzle)
        before = p["rating"]
        after, puzzle_after = new_ratings(before, s["rating"], solved)
        streak = p["streak"] + 1 if solved else 0
        self.db.execute("UPDATE players SET rating=?, streak=?, best_streak=?, solved=solved+?, attempts=attempts+1 "
                        "WHERE player=?", (after, streak, max(p["best_streak"], streak), int(solved), player))
        self.db.execute("UPDATE stats SET rating=?, plays=plays+1, solves=solves+? WHERE puzzle_id=?",
                        (puzzle_after, int(solved), puzzle_id))
        self.db.execute("INSERT INTO attempts (puzzle_id, player, solved, survived, kills, rating_before, rating_after, at)"
                        " VALUES (?,?,?,?,?,?,?,?)", (puzzle_id, player, int(solved), int(survived), kills, before,
                                                       after, datetime.now(timezone.utc).isoformat(timespec="seconds")))
        self.db.commit()
        return {"solved": solved, "survived": survived, "kills": kills, "need_kills": needed_kills(puzzle.original.kills),
                "player": self.player(player), "rating_change": round(after - before, 1),
                "puzzle_rating": round(puzzle_after)}

    def history(self, player: str, limit: int = 50) -> list[dict]:
        rows = self.db.execute("SELECT * FROM attempts WHERE player=? ORDER BY id DESC LIMIT ?", (player, limit))
        return [dict(r) for r in rows]

    def vote(self, puzzle_id: str, player: str, value: int) -> dict:
        if value not in (-1, 0, 1):
            raise ValueError("value must be -1, 0 or 1")
        puzzle = self.load(puzzle_id)
        self._stats(puzzle)
        self.db.execute("INSERT INTO votes (puzzle_id, player, value) VALUES (?,?,?) "
                        "ON CONFLICT(puzzle_id, player) DO UPDATE SET value=excluded.value", (puzzle_id, player, value))
        up = self.db.execute("SELECT COUNT(*) FROM votes WHERE puzzle_id=? AND value=1", (puzzle_id,)).fetchone()[0]
        down = self.db.execute("SELECT COUNT(*) FROM votes WHERE puzzle_id=? AND value=-1", (puzzle_id,)).fetchone()[0]
        self.db.execute("UPDATE stats SET up=?, down=? WHERE puzzle_id=?", (up, down, puzzle_id))
        self.db.commit()
        return {"up": up, "down": down}

    # -- daily and streak
    def daily(self, day: date | None = None) -> dict | None:
        pid = daily_pick(list(self._files()), day or datetime.now(timezone.utc).date())
        return self.summary(self.load(pid)) if pid else None

    def next_for(self, player: str, exclude: list[str] | None = None) -> dict | None:
        """The unsolved puzzle closest to the player's rating (the Lichess 'next puzzle' rule)."""
        me = self.player(player)
        solved = {r["puzzle_id"] for r in self.db.execute(
            "SELECT DISTINCT puzzle_id FROM attempts WHERE player=? AND solved=1", (player,))}
        skip = solved | set(exclude or [])
        rows = [r for r in self.list() if r["id"] not in skip]
        if not rows:
            rows = [r for r in self.list() if r["id"] not in set(exclude or [])]  # all solved: allow repeats
        return min(rows, key=lambda r: abs(r["rating"] - me["rating"])) if rows else None

    # -- drafts (multi-POV creator). Footage is stored; deriving a game state from it is not built.
    def create_draft(self, title: str, map_: str, slots: list[dict]) -> dict:
        if not 2 <= len(slots) <= 10:
            raise ValueError("A draft needs 2 to 10 player slots")
        names = [s.get("name", "").strip() for s in slots]
        if not all(names) or len(names) != len(set(names)):
            raise ValueError("Every slot needs a different player name")
        for s in slots:
            if s.get("side") not in ("CT", "T"):
                raise ValueError("Every slot needs a side, CT or T")
        did = uuid.uuid4().hex[:12]
        clean = [{"slot": i, "name": s["name"].strip()[:40], "side": s["side"], "offset_seconds": float(s.get("offset_seconds") or 0),
                  "file": None, "bytes": 0} for i, s in enumerate(slots)]
        self.db.execute("INSERT INTO drafts (id,title,map,created,status,message,slots) VALUES (?,?,?,?,?,?,?)",
                        (did, title.strip()[:120] or "Untitled", map_, datetime.now(timezone.utc).isoformat(timespec="seconds"),
                         "awaiting_footage", "Upload each player's POV video.", json.dumps(clean)))
        self.db.commit()
        return self.draft(did)

    def draft(self, draft_id: str) -> dict:
        row = self.db.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone() if ID_RE.match(draft_id) else None
        if not row:
            raise NotFound(draft_id)
        out = dict(row)
        out["slots"] = json.loads(out["slots"])
        return out

    def drafts(self) -> list[dict]:
        ids = [r["id"] for r in self.db.execute("SELECT id FROM drafts ORDER BY created DESC")]
        return [self.draft(i) for i in ids]

    def footage_path(self, draft_id: str, slot: int, suffix: str) -> Path:
        if suffix.lower() not in VIDEO_TYPES:
            raise ValueError(f"Video type must be one of {', '.join(sorted(VIDEO_TYPES))}")
        draft = self.draft(draft_id)
        if not 0 <= slot < len(draft["slots"]):
            raise NotFound(f"slot {slot}")
        return self.user_dir / "footage" / f"{draft_id}-{slot}{suffix.lower()}"

    def footage_saved(self, draft_id: str, slot: int, path: Path, size: int) -> dict:
        draft = self.draft(draft_id)
        draft["slots"][slot]["file"] = path.name
        draft["slots"][slot]["bytes"] = size
        complete = all(s["file"] for s in draft["slots"])
        status = "needs_derivation" if complete else "awaiting_footage"
        message = ("All POVs are stored. Deriving a game state from footage is not built yet: the pipeline "
                   "that reads positions out of video is a placeholder." if complete
                   else f"{sum(1 for s in draft['slots'] if s['file'])} of {len(draft['slots'])} POVs uploaded.")
        self.db.execute("UPDATE drafts SET slots=?, status=?, message=? WHERE id=?",
                        (json.dumps(draft["slots"]), status, message, draft_id))
        self.db.commit()
        return self.draft(draft_id)


def new_id(prefix: str = "u") -> str:
    return f"{prefix}{int(time.time())}{uuid.uuid4().hex[:4]}"
