from datetime import date, datetime
from pathlib import PurePosixPath
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
    two_yellow: Counter | None = None
    red: Counter | None = None
    clean_sheets: Counter | None = None
    saves: Counter | None = None
    goals_conceded: Counter | None = None
    motm: Counter | None = None
    avg: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    display_name: str | None = Field(default=None, max_length=150)


class TeamStateInput(Input):
    teamid: Identifier
    leagueid: Identifier
    nummatchesplayed: Counter | None = None
    homewins: Counter | None = None
    homedraws: Counter | None = None
    homelosses: Counter | None = None
    awaywins: Counter | None = None
    awaydraws: Counter | None = None
    awaylosses: Counter | None = None
    homegf: Counter | None = None
    homega: Counter | None = None
    awaygf: Counter | None = None
    awayga: Counter | None = None
    points: Counter | None = None
    currenttableposition: Counter | None = None
    lastgameresult: StrictInt | None = Field(default=None, ge=-1, le=2)
    teamform: Counter | None = None
    teamshortform: Counter | None = None
    teamlongform: Counter | None = None


class PlayerStateInput(Input):
    playerid: Identifier
    teamid: Identifier
    display_name: str | None = Field(default=None, max_length=150)
    injury_id: StrictInt | None = Field(default=None, ge=0, le=35)
    injury_date_raw: Counter | None = None
    injury_duration_days: Counter | None = None
    last_match_minutes: StrictInt | None = Field(default=None, ge=0, le=150)
    last_match_overall: StrictInt | None = Field(default=None, ge=-1, le=100)
    last_match_fact: StrictInt | None = Field(default=None, ge=-1, le=15)
    last_match_position: StrictInt | None = Field(default=None, ge=-1, le=50)
    latest_match_rating_raw: StrictInt | None = Field(default=None, ge=-1, le=100)
    latest_match_rating_minutes: StrictInt | None = Field(default=None, ge=-1, le=140)
    latest_match_rating_date_raw: StrictInt | None = Field(default=None, ge=0, le=99991231)


class SnapshotInput(Input):
    schema_version: Literal[1]
    producer: Literal["fc24-live-editor-lua", "lca-demo-simulator"]
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
    team_states: list[TeamStateInput] = Field(default_factory=list, max_length=100)
    player_states: list[PlayerStateInput] = Field(default_factory=list, max_length=500)

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
        team_keys = [(r.teamid, r.leagueid) for r in self.team_states]
        if len(team_keys) != len(set(team_keys)):
            raise ValueError("Duplicate team/league state rows")
        player_keys = [(r.playerid, r.teamid) for r in self.player_states]
        if len(player_keys) != len(set(player_keys)):
            raise ValueError("Duplicate player/team state rows")
        if self.user_team_id is not None and any(
            r.teamid != self.user_team_id for r in [*self.team_states, *self.player_states]
        ):
            raise ValueError("State rows must belong to user_team_id")
        return self


class CommitInput(Input):
    preview_token: str
    strategy: Literal["reject", "replace"] = "reject"


class NoteInput(Input):
    text: str = Field(min_length=1, max_length=5000)
    interval_id: int | None = None
    match_id: int | None = None


class MatchTeamStatsInput(Input):
    possession: float | None = Field(default=None, ge=0, le=100)
    xg: float | None = Field(default=None, ge=0, le=100)
    shots: Counter | None = None
    shots_on_target: Counter | None = None
    shots_off_target: Counter | None = None
    blocked_shots: Counter | None = None
    shot_accuracy: float | None = Field(default=None, ge=0, le=100)
    passes: Counter | None = None
    completed_passes: Counter | None = None
    pass_accuracy: float | None = Field(default=None, ge=0, le=100)
    tackles: Counter | None = None
    tackles_won: Counter | None = None
    interceptions: Counter | None = None
    saves: Counter | None = None
    fouls: Counter | None = None
    offsides: Counter | None = None
    dribbles: Counter | None = None
    successful_dribbles: Counter | None = None
    dribble_success: float | None = Field(default=None, ge=0, le=100)
    ball_recovery_seconds: float | None = Field(default=None, ge=0, le=300)
    penalties: Counter | None = None
    yellow_cards: Counter | None = None
    red_cards: Counter | None = None
    injuries: Counter | None = None


class MatchEventInput(Input):
    minute: int = Field(ge=0, le=130)
    kind: Literal["goal", "substitution", "yellow", "red", "injury"]
    team: Literal["club", "opponent"]
    player: str = Field(min_length=1, max_length=150)
    secondary_player: str | None = Field(default=None, max_length=150)
    detail: str | None = Field(default=None, max_length=300)


class MatchPlayerInput(Input):
    external_player_id: Identifier | None = None
    name: str = Field(min_length=1, max_length=150)
    position: str | None = Field(default=None, max_length=20)
    overall: int | None = Field(default=None, ge=0, le=100)
    rating: float | None = Field(default=None, ge=0, le=10)
    goals: Counter | None = None
    assists: Counter | None = None
    started: bool | None = None
    substitute: bool | None = None
    motm: bool | None = None


class MatchEvidenceInput(Input):
    career_save_id: Identifier
    season_id: Identifier
    source_external_match_id: str = Field(min_length=8, max_length=200)
    played_at: date
    external_compobjid: Identifier | None = None
    competition_name: str | None = Field(default=None, max_length=150)
    club_team_external_id: Identifier
    opponent_name: str = Field(min_length=1, max_length=150)
    club_was_home: bool
    club_goals: Counter
    opponent_goals: Counter
    duration_minutes: float | None = Field(default=None, ge=0, le=150)
    team_stats: MatchTeamStatsInput
    opponent_stats: MatchTeamStatsInput
    timeline: list[MatchEventInput] = Field(default_factory=list, max_length=300)
    player_performances: list[MatchPlayerInput] = Field(default_factory=list, max_length=100)
    screenshot_paths: list[str] = Field(default_factory=list, max_length=100)
    evidence_note: str = Field(min_length=1, max_length=3000)

    @field_validator("screenshot_paths")
    @classmethod
    def safe_relative_screenshot_paths(cls, values):
        for value in values:
            path = PurePosixPath(value)
            if (
                path.is_absolute()
                or ".." in path.parts
                or "\\" in value
                or ":" in value
                or path.suffix.lower() not in {".jpg", ".jpeg", ".png"}
            ):
                raise ValueError("Screenshot paths must be safe relative image paths")
        return values


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
