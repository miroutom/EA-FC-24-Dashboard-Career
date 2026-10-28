"""Typed public analytics DTOs, separate from persistence models."""

from pydantic import BaseModel, ConfigDict, Field


class Output(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CareerDTO(Output):
    id: int
    name: str
    game_version: str
    primary_team_id: int | None
    created_at: str


class SeasonDTO(Output):
    id: int
    career_id: int
    start_year: int
    end_year: int
    source_policy: str


class CompetitionDTO(Output):
    id: int
    game_version: str
    external_compobjid: int
    name: str
    kind: str


class MetricsDTO(Output):
    appearances: int | None = None
    goals: int | None = None
    assists: int | None = None
    clean_sheets: int | None = None


class HistoryDTO(MetricsDTO):
    player_id: int
    season_id: int
    season: str
    source: str
    data_quality: str
    coverage: str
    source_scope: str
    observed_competitions: list[int] | None = None


class PlayerDTO(MetricsDTO):
    id: int
    name: str
    position: str | None = None
    goal_contributions: int | None = None
    goals_per_appearance: float | None = None
    contributions_per_appearance: float | None = None
    seasons_count: int = 0
    first_season: str | None = None
    last_season: str | None = None
    history: list[HistoryDTO] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    data_quality: list[str] = Field(default_factory=list)
    rating: None = None
    overall: None = None
    potential: None = None
    observed_goals_share: float | None = None
    competition_history: list["CompetitionHistoryDTO"] = Field(default_factory=list)
    last_synced_at: str | None = None
    source_scope: list[str] = Field(default_factory=list)


class CompetitionHistoryDTO(MetricsDTO):
    season: str
    competition: str
    compobjid: int
    source: str
    coverage: str


class AnalyticsDTO(Output):
    items: list[PlayerDTO]
    warnings: list[str]
    data_quality: list[str]
    source_scope: list[str]
    last_synced_at: str | None
    total: int | None = None
    page: int | None = None
    size: int | None = None


class ChartPointDTO(MetricsDTO):
    season: str


class DashboardDTO(AnalyticsDTO):
    kpis: MetricsDTO
    players_count: int
    seasons_count: int
    chart: list[ChartPointDTO]
    leaders: list[PlayerDTO]
    team_matches: None = None
    xg: None = None
    coverage: str


class CompareDTO(Output):
    items: list[PlayerDTO]
