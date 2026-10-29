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


class MatchDTO(Output):
    id: int
    career_save_id: int
    season_id: int
    source_external_match_id: str | None
    played_at: str | None
    home_goals: int | None
    away_goals: int | None
    verified_source: str
    external_compobjid: int | None
    competition_name: str | None
    club_team_external_id: int | None
    opponent_name: str | None
    club_was_home: bool | None
    club_goals: int | None
    opponent_goals: int | None
    duration_minutes: float | None
    result: str | None
    team_stats: dict
    opponent_stats: dict
    timeline: list[dict]
    player_performances: list[dict]
    screenshot_paths: list[str]
    screenshot_urls: list[str]
    evidence: dict


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


class LivePlayerDTO(Output):
    yellow: int | None = None
    two_yellow: int | None = None
    red: int | None = None
    saves: int | None = None
    goals_conceded: int | None = None
    motm: int | None = None
    avg_raw: float | None = None
    injury_id: int | None = None
    injury_date_raw: int | None = None
    injury_duration_days: int | None = None
    last_match_minutes: int | None = None
    last_match_overall: int | None = None
    last_match_fact: int | None = None
    last_match_position: int | None = None
    latest_match_rating_raw: int | None = None
    latest_match_rating_minutes: int | None = None
    latest_match_rating_date_raw: int | None = None
    observed_at: str | None = None
    data_quality: str = "experimental_live"


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
    live: LivePlayerDTO | None = None


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


class TeamRecordDTO(Output):
    league_id: int
    matches_played: int | None = None
    wins: int | None = None
    draws: int | None = None
    losses: int | None = None
    goals_for: int | None = None
    goals_against: int | None = None
    points: int | None = None
    table_position: int | None = None
    observed_at: str | None = None


class ObservedResultDTO(Output):
    result: str
    league_id: int
    observed_at: str | None = None
    source: str = "aggregate_delta"


class TeamFormDTO(Output):
    season_id: int
    records: list[TeamRecordDTO] = Field(default_factory=list)
    recent_results: list[ObservedResultDTO] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    coverage: str = "LEAGUE_AGGREGATES"
    data_quality: str = "experimental_live"


class MatchResultDTO(Output):
    result: str
    played_at: str | None = None
    opponent: str | None = None
    club_goals: int | None = None
    opponent_goals: int | None = None


class TeamMatchesDTO(Output):
    matches: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    points: int
    points_per_game: float
    avg_xg: float | None = None
    avg_xga: float | None = None
    avg_possession: float | None = None
    recent_results: list[MatchResultDTO] = Field(default_factory=list)
    coverage: str


class DashboardDTO(AnalyticsDTO):
    kpis: MetricsDTO
    players_count: int
    seasons_count: int
    chart: list[ChartPointDTO]
    leaders: list[PlayerDTO]
    team_matches: TeamMatchesDTO | None = None
    xg: float | None = None
    team_form: TeamFormDTO | None = None
    coverage: str


class CompareDTO(Output):
    items: list[PlayerDTO]
