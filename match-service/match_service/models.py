"""Request and response shapes for the Server API (see the Interface specs doc, section 2)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

Team = Literal["T", "CT"]
Mode = Literal["competitive", "wingman"]
Status = Literal["starting", "ready", "live", "ended", "failed"]

TEAM_SIZE: dict[str, int] = {"competitive": 5, "wingman": 2}
ROUNDS_TO_WIN: dict[str, int] = {"competitive": 13, "wingman": 9}


class Clone(BaseModel):
    # Goes into `clone_add <clone_id>`, so only plain ids are allowed.
    clone_id: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,64}$")
    display_name: str
    source: Literal["user", "pro"]
    # Built-in CS2-Bot-Improver bot that plays this clone until CloneDirector works (SPEC.md 5.4).
    # It goes into a console command, so only plain names are allowed (no quotes, spaces, `;`).
    stand_in_bot: str | None = Field(None, pattern=r"^[A-Za-z0-9_.-]{1,32}$")
    # The learned model for this clone (SPEC.md 5.4), or null. Shown to the demo pages; when it is set
    # and CS2_CLONE_ROUTES=generated, CloneDirector plays the model's generated routes (drivers.py).
    model: str | dict | None = None


class CloneInfo(Clone):
    """A clone as GET /clones lists it: the profile plus how it would be played right now."""
    driver: str                # mock, stand_in or clone_director
    label: str                 # for display
    playable: bool = True      # False: starting a match with it would be rejected
    reason: str | None = None  # why it is not playable


class PlayerIn(BaseModel):
    # 64-bit Steam IDs are 17 digits and start with 7656119.
    steam_id: str = Field(pattern=r"^7656119\d{10}$")
    team: Team


class CloneIn(BaseModel):
    clone_id: str
    team: Team


class MatchCreate(BaseModel):
    map: str = Field(pattern=r"^[a-z]{2}_[a-z0-9_]+$", examples=["de_mirage"])
    mode: Mode = "competitive"
    players: list[PlayerIn] = []
    clones: list[CloneIn] = []
    callback_url: HttpUrl | None = None
    # Mock only: makes the server "fail to start" so callers can test the failed path.
    mock_fail: bool = False


class Server(BaseModel):
    ip: str
    port: int


class Score(BaseModel):
    CT: int = 0
    T: int = 0


class MatchPlayer(BaseModel):
    team: Team
    is_clone: bool
    steam_id: str | None = None
    clone_id: str | None = None
    display_name: str


class Event(BaseModel):
    match_id: str
    event: Literal["match.ready", "match.live", "round.ended", "match.ended", "match.failed"]
    data: dict
    sent_at: datetime


class Match(BaseModel):
    match_id: str
    status: Status
    map: str
    mode: Mode
    server: Server | None = None
    join_link: str | None = None
    score: Score = Score()
    round: int = 0
    players: list[MatchPlayer]
    demo_url: str | None = None
    error: str | None = None
    created_at: datetime
