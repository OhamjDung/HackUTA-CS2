"""Replay puzzle routes (SPEC.md, replay puzzles). Not in the Interface specs doc.

`add_puzzle_routes` is called from create_app; it mounts the routes on the app and returns the store.
"""

import asyncio
import json
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from .core import Settings
from .feedback import feedback_for
from .puzzles import ID_RE, MAX_VIDEO_BYTES, NotFound, PuzzleStore, is_solved, needed_kills, new_id, validate_puzzle


class ResultBody(BaseModel):
    player: str | None = Field(default=None, max_length=40)
    survived: bool
    kills: int = Field(ge=0, le=30)


class VoteBody(BaseModel):
    player: str = Field(min_length=1, max_length=40)
    value: int


class StartBody(BaseModel):
    player: str = Field(default="guest", min_length=1, max_length=40)


class SaveDeathBody(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    tags: list[str] = []


class DraftBody(BaseModel):
    title: str = Field(default="Untitled", max_length=120)
    map: str = "de_mirage"
    slots: list[dict]


def add_puzzle_routes(app: FastAPI, settings: Settings, backend) -> PuzzleStore:
    store = PuzzleStore(settings.puzzle_dir, settings.puzzle_seed_dir)
    active_attempt: dict = {}  # one CS2 instance can play one attempt at a time
    attempt_timeout = 120.0
    completed_attempts: dict = {}

    def clear_attempt():
        path = active_attempt.get("path")
        active_attempt.clear()
        if path:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass  # a leftover copy cannot be used to submit a result

    def expire_attempt():
        now = time.monotonic()
        if active_attempt and now >= active_attempt["deadline"]:
            clear_attempt()
        for run_id in [key for key, value in completed_attempts.items() if value["expires"] <= now]:
            del completed_attempts[run_id]

    def puzzle_or_404(puzzle_id: str):
        try:
            return store.load(puzzle_id)
        except NotFound:
            raise HTTPException(404, f"No puzzle {puzzle_id}")
        except ValueError as exc:
            raise HTTPException(422, f"Puzzle {puzzle_id} is invalid: {exc}")

    def read_death(death_id: str):
        path = settings.death_dir / f"{death_id}.json"
        if not ID_RE.match(death_id) or not path.is_file():
            raise HTTPException(404, f"No death {death_id}")
        try:
            return validate_puzzle(json.loads(path.read_text(encoding="utf-8")))
        except (ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(422, f"Death {death_id} is invalid: {exc}")

    @app.get("/puzzles")
    async def list_puzzles(tag: str | None = None, map: str | None = None, source: str | None = None,
                           min_rating: float | None = None, max_rating: float | None = None,
                           sort: str = "rating"):
        try:
            return store.list(tag=tag, map_=map, source=source, min_rating=min_rating,
                              max_rating=max_rating, sort=sort)
        except ValueError as exc:
            raise HTTPException(422, str(exc))

    @app.get("/puzzles/tags")
    async def puzzle_tags():
        return store.tags()

    @app.get("/puzzles/daily")
    async def puzzle_daily():
        daily = store.daily()
        if not daily:
            raise HTTPException(404, "There are no puzzles yet")
        return daily

    @app.get("/puzzles/next")
    async def puzzle_next(player: str = "guest"):
        nxt = store.next_for(player[:40])
        if not nxt:
            raise HTTPException(404, "There are no puzzles yet")
        return nxt

    @app.get("/puzzles/drafts")
    async def list_drafts():
        return store.drafts()

    @app.post("/puzzles/drafts", status_code=201)
    async def create_draft(body: DraftBody):
        try:
            return store.create_draft(body.title, body.map, body.slots)
        except ValueError as exc:
            raise HTTPException(422, str(exc))

    @app.get("/puzzles/drafts/{draft_id}")
    async def get_draft(draft_id: str):
        try:
            return store.draft(draft_id)
        except NotFound:
            raise HTTPException(404, f"No draft {draft_id}")

    @app.put("/puzzles/drafts/{draft_id}/pov/{slot}")
    async def upload_pov(draft_id: str, slot: int, request: Request, ext: str = ".mp4"):
        """Raw video bytes as the body (no form). The footage is stored; no game state is derived from it."""
        ext = ext if ext.startswith(".") else "." + ext
        try:
            path = store.footage_path(draft_id, slot, ext)
        except NotFound:
            raise HTTPException(404, f"No draft {draft_id} or slot {slot}")
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        size = 0
        tmp = path.with_suffix(path.suffix + ".part")
        try:
            with tmp.open("wb") as out:
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > MAX_VIDEO_BYTES:
                        raise HTTPException(413, f"Video is over {MAX_VIDEO_BYTES // 2**20} MB")
                    out.write(chunk)
            if size == 0:
                raise HTTPException(422, "Empty upload")
            tmp.replace(path)
        finally:
            tmp.unlink(missing_ok=True)
        return store.footage_saved(draft_id, slot, path, size)

    @app.post("/puzzles", status_code=201)
    async def create_puzzle(body: dict):
        """Save a puzzle from a full puzzle document (the same format a death file has)."""
        body = {**body, "id": body.get("id") or new_id()}
        try:
            return store.summary(store.add(validate_puzzle(body)))
        except ValueError as exc:
            raise HTTPException(422, str(exc))

    @app.get("/puzzles/{puzzle_id}")
    async def get_puzzle(puzzle_id: str):
        puzzle = puzzle_or_404(puzzle_id)
        return {**store.summary(puzzle), "puzzle": puzzle.model_dump(),
                "feedback": feedback_for(puzzle.model_dump())}

    @app.delete("/puzzles/{puzzle_id}")
    async def delete_puzzle(puzzle_id: str):
        try:
            store.delete(puzzle_id)
        except NotFound:
            raise HTTPException(404, f"No saved puzzle {puzzle_id} (the seed puzzles cannot be deleted)")
        return {"deleted": puzzle_id}

    @app.post("/puzzles/{puzzle_id}/result")
    async def puzzle_result(puzzle_id: str, body: ResultBody):
        expire_attempt()
        if active_attempt and active_attempt["run_id"] == puzzle_id:
            attempt = dict(active_attempt)
            puzzle = attempt["puzzle"]
            if attempt.get("scene"):
                result = {"finished": True}
            elif attempt["library"]:
                result = store.record_attempt(puzzle.id, attempt["player"], body.survived, body.kills)
            else:
                result = {"solved": is_solved(puzzle, body.survived, body.kills),
                          "survived": body.survived, "kills": body.kills,
                          "need_kills": needed_kills(puzzle.original.kills)}
            completed_attempts[puzzle_id] = {"result": result, "expires": time.monotonic() + 300}
            clear_attempt()
            return result
        # Explicit manual results remain available for saved library puzzles.
        puzzle_or_404(puzzle_id)
        return store.record_attempt(puzzle_id, body.player or "guest", body.survived, body.kills)

    @app.get("/puzzle-attempts/{attempt_id}")
    async def attempt_status(attempt_id: str):
        expire_attempt()
        if active_attempt and active_attempt["run_id"] == attempt_id:
            return {"state": "pending"}
        if attempt_id in completed_attempts:
            return {"state": "finished", "result": completed_attempts[attempt_id]["result"]}
        raise HTTPException(404, "Puzzle attempt expired or was not found")

    @app.post("/puzzles/{puzzle_id}/vote")
    async def puzzle_vote(puzzle_id: str, body: VoteBody):
        puzzle_or_404(puzzle_id)
        try:
            return store.vote(puzzle_id, body.player, body.value)
        except ValueError as exc:
            raise HTTPException(422, str(exc))

    async def launch(puzzle, player: str, *, library: bool = True, scene: bool = False) -> dict:
        """Reserve the game and use a unique copied id to correlate its callback."""
        if backend.name != "cs2" or not hasattr(backend, "plugin_command"):
            raise HTTPException(409, "Practice in CS2 needs MATCH_BACKEND=cs2 with CloneDirector. "
                                     "The page's map replay works without it.")
        if not settings.game_puzzle_dir:
            raise HTTPException(409, "PUZZLE_GAME_DIR is not set: the service does not know where "
                                     "CloneDirector reads puzzles from")
        if scene and backend.busy():
            raise HTTPException(409, "A match is running. Stop it before watching a scene.")
        expire_attempt()
        if active_attempt:
            raise HTTPException(409, "Another puzzle attempt is still running. Wait for it to finish or time out.")
        run_id = "run_" + uuid.uuid4().hex
        path = settings.game_puzzle_dir / f"{run_id}.json"
        active_attempt.update({"run_id": run_id, "puzzle": puzzle, "player": player,
                               "library": library, "scene": scene, "path": path,
                               "deadline": time.monotonic() + attempt_timeout})
        try:
            settings.game_puzzle_dir.mkdir(parents=True, exist_ok=True)
            copy = puzzle.model_dump()
            copy["id"] = run_id
            path.write_text(json.dumps(copy), encoding="utf-8")
            if hasattr(backend, "prepare_puzzle"):
                await backend.prepare_puzzle(puzzle.map, puzzle.hero().side)
            reply = await backend.plugin_command(f"{'scene_load' if scene else 'puzzle_load'} {run_id}")
        except (RuntimeError, OSError, asyncio.TimeoutError) as exc:
            if active_attempt.get("run_id") == run_id:
                clear_attempt()
            raise HTTPException(409, f"Could not start the puzzle in CS2: {exc}")
        return {"started": True, "puzzle_id": puzzle.id, "reply": reply, "attempt_id": run_id}

    @app.post("/puzzles/{puzzle_id}/start")
    async def puzzle_start(puzzle_id: str, body: StartBody):
        """Play the puzzle in CS2."""
        return await launch(puzzle_or_404(puzzle_id), body.player)

    @app.get("/scenes")
    async def list_scenes():
        ids = ("pro_2393226_r9_donk", "pro_2393024_r19_broky", "pro_2393226_r7_donk", "pro_2393024_r4_broky")
        scenes = []
        for scene_id in ids:
            try:
                p = store.load(scene_id)
            except (NotFound, ValueError):
                continue
            scenes.append({"id": p.id, "title": p.title, "map": p.map, "duration": p.window_seconds,
                           "players": [player.name for player in p.players],
                           "kills": sum(e.type == "kill" for e in p.events)})
        return scenes

    @app.post("/scenes/{scene_id}/start")
    async def start_scene(scene_id: str):
        return await launch(puzzle_or_404(scene_id), "spectator", library=False, scene=True)

    @app.get("/players/{player}")
    async def get_player(player: str):
        return store.player(player[:40])

    @app.get("/players/{player}/history")
    async def player_history(player: str, limit: int = 50):
        return store.history(player[:40], min(max(limit, 1), 200))

    # Deaths: the last 10 seconds before a human died in CS2, saved by CloneDirector.
    async def death_list() -> list[dict]:
        out: list[dict] = []
        folder: Path = settings.death_dir
        if folder.is_dir():
            for path in sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:50]:
                try:
                    d = validate_puzzle(json.loads(path.read_text(encoding="utf-8")))
                except (ValueError, json.JSONDecodeError):
                    continue
                out.append({"id": d.id, "title": d.title, "map": d.map, "hero": d.hero().name,
                            "created": d.created, "killer": d.original.killer, "weapon": d.original.weapon})
        return out

    @app.get("/deaths")
    async def list_deaths():
        return await death_list()

    @app.get("/deaths/latest")
    async def latest_death():
        items = await death_list()
        if not items:
            raise HTTPException(404, "No deaths saved yet")
        d = read_death(items[0]["id"])
        return {"id": d.id, "puzzle": d.model_dump(), "feedback": feedback_for(d.model_dump())}

    @app.get("/deaths/{death_id}")
    async def get_death(death_id: str):
        d = read_death(death_id)
        return {"id": d.id, "puzzle": d.model_dump(), "feedback": feedback_for(d.model_dump())}

    @app.post("/deaths/{death_id}/start")
    async def start_death(death_id: str, body: StartBody):
        """Retry the last 10 seconds before a death in CS2, without saving it to the library."""
        return await launch(read_death(death_id), body.player, library=False)

    @app.post("/deaths/{death_id}/save", status_code=201)
    async def save_death(death_id: str, body: SaveDeathBody):
        """Turn a death into a library puzzle ("Save as puzzle")."""
        d = read_death(death_id)
        d.id, d.title, d.tags, d.source = new_id(), body.title, body.tags[:8], "user"
        try:
            return store.summary(store.add(d))
        except ValueError as exc:
            raise HTTPException(422, str(exc))

    return store
