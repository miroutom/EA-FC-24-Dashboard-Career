from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

Counter = Annotated[StrictInt, Field(ge=0, le=10_000_000)]
Identifier = Annotated[StrictInt, Field(ge=0, le=2**31 - 1)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CareerInput(Input):
    name: str = Field(min_length=1, max_length=120)
    game_version: Literal["EA FC 24"] = "EA FC 24"
    primary_team_id: Identifier | None = None
    start_year: int = Field(default=2023, ge=2000, le=2200)


class SaveInput(Input):
    instance_key: str = Field(min_length=8, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    external_save_uid: str | None = Field(default=None, max_length=200)
    verified_live: bool = False
    evidence: str | None = Field(default=None, max_length=3000)

    @model_validator(mode="after")
    def verification(self):
        if self.verified_live and not self.evidence:
            raise ValueError("Verification requires real-game version/scenario evidence")
        return self


class SnapshotRowInput(Input):
    playerid: Identifier
    teamid: Identifier
    compobjid: Identifier
    app: Counter | None = None
    goals: Counter | None = None
    assists: Counter | None = None
    yellow: Counter | None = None
    red: Counter | None = None
    clean_sheets: Counter | None = None
    avg: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    display_name: str | None = Field(default=None, max_length=150)


class SnapshotInput(Input):
    schema_version: Literal[1]
    producer: Literal["fc24-live-editor-lua"]
    collector_version: str = Field(min_length=1, max_length=40)
    game_version: Literal["EA FC 24"]
    captured_at_utc: datetime
    event: str | None = Field(default=None, max_length=150)
    save_uid: str | None = Field(default=None, max_length=200)
    instance_key: str | None = Field(default=None, max_length=100)
    in_game_date: date | None = None
    user_team_id: Identifier | None = None
    season_start_year: StrictInt | None = Field(default=None, ge=2000, le=2200)
    completeness: Literal["UNKNOWN", "PARTIAL", "COMPLETE"] = "UNKNOWN"
    rows: list[SnapshotRowInput] = Field(max_length=20000)

    @field_validator("captured_at_utc")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None or value.utcoffset().total_seconds() != 0:
            raise ValueError("UTC timestamp required")
        return value

    @model_validator(mode="after")
    def unique_keys(self):
        keys = [(r.playerid, r.teamid, r.compobjid) for r in self.rows]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate player/team/competition rows")
        if self.user_team_id is not None and any(r.teamid != self.user_team_id for r in self.rows):
            raise ValueError("Rows must belong to user_team_id")
        return self


class CommitInput(Input):
    preview_token: str
    strategy: Literal["reject", "replace"] = "reject"


class NoteInput(Input):
    text: str = Field(min_length=1, max_length=5000)
    interval_id: int | None = None
    match_id: int | None = None


class ResolveInput(Input):
    strategy: Literal["adopt", "reject"]


class PolicyInput(Input):
    source_policy: Literal["historical_first", "live"]
    acknowledged: Literal[True]


class IdentityInput(Input):
    external_player_id: Identifier
    confirmed: Literal[True]


class DTO(BaseModel):
    """Validate JSON serialization at the API boundary, including computed DTOs."""

    model_config = ConfigDict(extra="allow")
