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
    clone_id: str
    display_name: str
    source: Literal["user", "pro"]


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
