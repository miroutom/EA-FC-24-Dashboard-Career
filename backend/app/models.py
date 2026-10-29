from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)

from .core import Base, now


class Career(Base):
    __tablename__ = "careers"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    game_version = Column(String(40), nullable=False, default="EA FC 24")
    primary_team_id = Column(Integer, nullable=True)
    created_at = Column(String, nullable=False, default=now)


class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True)
    game_version = Column(String, nullable=False)
    external_team_id = Column(Integer, nullable=True)
    name = Column(String, nullable=False)


class Season(Base):
    __tablename__ = "seasons"
    id = Column(Integer, primary_key=True)
    career_id = Column(ForeignKey("careers.id"), nullable=False, index=True)
    start_year = Column(Integer, nullable=False)
    end_year = Column(Integer, nullable=False)
    source_policy = Column(String, nullable=False, default="historical_first")
    __table_args__ = (
        UniqueConstraint("career_id", "start_year"),
        CheckConstraint("end_year = start_year + 1"),
    )


class Competition(Base):
    __tablename__ = "competitions"
    id = Column(Integer, primary_key=True)
    game_version = Column(String, nullable=False)
    external_compobjid = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    kind = Column(String, nullable=False, default="UNKNOWN")
    __table_args__ = (UniqueConstraint("game_version", "external_compobjid"),)


class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True)
    career_id = Column(ForeignKey("careers.id"), nullable=False, index=True)
    external_player_id = Column(Integer, nullable=True)
    display_name = Column(String(150), nullable=False)
    normalized_name = Column(String(150), nullable=False)
    __table_args__ = (
        Index(
            "ux_player_external",
            "career_id",
            "external_player_id",
            unique=True,
            sqlite_where=text("external_player_id IS NOT NULL"),
        ),
    )


class PlayerAlias(Base):
    __tablename__ = "player_aliases"
    id = Column(Integer, primary_key=True)
    career_id = Column(ForeignKey("careers.id"), nullable=False)
    player_id = Column(ForeignKey("players.id"), nullable=False)
    alias = Column(String, nullable=False)
    source = Column(String, nullable=False)
    __table_args__ = (UniqueConstraint("career_id", "alias"),)


class PlayerSeasonMetadata(Base):
    __tablename__ = "player_season_metadata"
    id = Column(Integer, primary_key=True)
    season_id = Column(ForeignKey("seasons.id"), nullable=False)
    player_id = Column(ForeignKey("players.id"), nullable=False)
    position = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    overall = Column(Integer, nullable=True)
    potential = Column(Integer, nullable=True)
    observed_at = Column(String, nullable=False, default=now)
    __table_args__ = (UniqueConstraint("season_id", "player_id"),)


class ImportBatch(Base):
    __tablename__ = "import_batches"
    id = Column(Integer, primary_key=True)
    career_id = Column(ForeignKey("careers.id"), nullable=False)
    filename = Column(String, nullable=False)
    sha256 = Column(String(64), nullable=False)
    status = Column(String, nullable=False)
    stats = Column(JSON, nullable=False, default=dict)
    created_at = Column(String, nullable=False, default=now)
    __table_args__ = (UniqueConstraint("career_id", "sha256"),)


class ImportPreview(Base):
    __tablename__ = "import_previews"
    token = Column(String, primary_key=True)
    career_id = Column(ForeignKey("careers.id"), nullable=False)
    filename = Column(String, nullable=False)
    sha256 = Column(String(64), nullable=False)
    rows = Column(JSON, nullable=False)
    baseline_digest = Column(String, nullable=False)
    created_at = Column(String, nullable=False, default=now)


class HistoricalStat(Base):
    __tablename__ = "historical_aggregate_stats"
    id = Column(Integer, primary_key=True)
    career_id = Column(ForeignKey("careers.id"), nullable=False)
    season_id = Column(ForeignKey("seasons.id"), nullable=False, index=True)
    player_id = Column(ForeignKey("players.id"), nullable=False)
    team_id = Column(Integer, nullable=True)
    scope = Column(String, nullable=False, default="ALL_COMPETITIONS")
    competition_id = Column(ForeignKey("competitions.id"), nullable=True)
    appearances = Column(Integer, nullable=True)
    goals = Column(Integer, nullable=True)
    assists = Column(Integer, nullable=True)
    clean_sheets = Column(Integer, nullable=True)
    source_batch_id = Column(ForeignKey("import_batches.id"), nullable=False)
    coverage = Column(String, nullable=False, default="PARTIAL_SCREENSHOT")
    __table_args__ = (
        CheckConstraint(
            "(scope = 'ALL_COMPETITIONS' AND competition_id IS NULL) OR (scope = 'COMPETITION' AND competition_id IS NOT NULL)"
        ),
        CheckConstraint("appearances IS NULL OR appearances >= 0"),
        CheckConstraint("goals IS NULL OR goals >= 0"),
        CheckConstraint("assists IS NULL OR assists >= 0"),
        Index(
            "ux_history_total",
            "career_id",
            "season_id",
            "player_id",
            unique=True,
            sqlite_where=text("scope = 'ALL_COMPETITIONS'"),
        ),
        Index(
            "ux_history_comp",
            "career_id",
            "season_id",
            "player_id",
            "competition_id",
            unique=True,
            sqlite_where=text("scope = 'COMPETITION'"),
        ),
    )


class CareerSave(Base):
    __tablename__ = "career_saves"
    id = Column(Integer, primary_key=True)
    career_id = Column(ForeignKey("careers.id"), nullable=False, index=True)
    external_save_uid = Column(String(200), nullable=True, unique=True)
    instance_key = Column(String(100), nullable=False, unique=True)
    active_branch_no = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False, default="ACTIVE")
    verified_live = Column(Boolean, nullable=False, default=False)
    evidence = Column(Text, nullable=True)
    bound_at = Column(String, nullable=False, default=now)


class SaveBranch(Base):
    __tablename__ = "save_branches"
    id = Column(Integer, primary_key=True)
    save_id = Column(ForeignKey("career_saves.id"), nullable=False)
    branch_no = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    reason = Column(String, nullable=True)
    __table_args__ = (UniqueConstraint("save_id", "branch_no"),)


class Snapshot(Base):
    __tablename__ = "collector_snapshots"
    id = Column(Integer, primary_key=True)
    career_save_id = Column(ForeignKey("career_saves.id"), nullable=False, index=True)
    branch_no = Column(Integer, nullable=False)
    season_id = Column(ForeignKey("seasons.id"), nullable=False)
    in_game_date = Column(String, nullable=True)
    captured_at = Column(String, nullable=False)
    event_name = Column(String, nullable=True)
    source_version = Column(String, nullable=False)
    payload_sha256 = Column(String(64), nullable=False)
    state_sha256 = Column(String(64), nullable=False)
    status = Column(String, nullable=False)
    completeness = Column(String, nullable=False)
    raw_path = Column(String, nullable=False)
    imported_at = Column(String, nullable=False, default=now)
    __table_args__ = (UniqueConstraint("career_save_id", "payload_sha256"),)


class SnapshotRow(Base):
    __tablename__ = "collector_snapshot_rows"
    id = Column(Integer, primary_key=True)
    snapshot_id = Column(ForeignKey("collector_snapshots.id"), nullable=False, index=True)
    player_id = Column(ForeignKey("players.id"), nullable=False)
    player_external_id = Column(Integer, nullable=False)
    team_external_id = Column(Integer, nullable=False)
    compobjid = Column(Integer, nullable=False)
    appearances = Column(Integer, nullable=True)
    goals = Column(Integer, nullable=True)
    assists = Column(Integer, nullable=True)
    yellow = Column(Integer, nullable=True)
    two_yellow = Column(Integer, nullable=True)
    red = Column(Integer, nullable=True)
    clean_sheets = Column(Integer, nullable=True)
    saves = Column(Integer, nullable=True)
    goals_conceded = Column(Integer, nullable=True)
    motm = Column(Integer, nullable=True)
    avg_raw = Column(Float, nullable=True)
    __table_args__ = (UniqueConstraint("snapshot_id", "player_external_id", "team_external_id", "compobjid"),)


class TeamStateSnapshot(Base):
    __tablename__ = "team_state_snapshots"
    id = Column(Integer, primary_key=True)
    snapshot_id = Column(ForeignKey("collector_snapshots.id"), nullable=False, index=True)
    team_external_id = Column(Integer, nullable=False)
    league_external_id = Column(Integer, nullable=False)
    matches_played = Column(Integer, nullable=True)
    home_wins = Column(Integer, nullable=True)
    home_draws = Column(Integer, nullable=True)
    home_losses = Column(Integer, nullable=True)
    away_wins = Column(Integer, nullable=True)
    away_draws = Column(Integer, nullable=True)
    away_losses = Column(Integer, nullable=True)
    home_goals_for = Column(Integer, nullable=True)
    home_goals_against = Column(Integer, nullable=True)
    away_goals_for = Column(Integer, nullable=True)
    away_goals_against = Column(Integer, nullable=True)
    points = Column(Integer, nullable=True)
    table_position = Column(Integer, nullable=True)
    last_game_result_raw = Column(Integer, nullable=True)
    form = Column(Integer, nullable=True)
    short_form = Column(Integer, nullable=True)
    long_form = Column(Integer, nullable=True)
    __table_args__ = (UniqueConstraint("snapshot_id", "team_external_id", "league_external_id"),)


class PlayerStateSnapshot(Base):
    __tablename__ = "player_state_snapshots"
    id = Column(Integer, primary_key=True)
    snapshot_id = Column(ForeignKey("collector_snapshots.id"), nullable=False, index=True)
    player_id = Column(ForeignKey("players.id"), nullable=False)
    player_external_id = Column(Integer, nullable=False)
    team_external_id = Column(Integer, nullable=False)
    injury_id = Column(Integer, nullable=True)
    injury_date_raw = Column(Integer, nullable=True)
    injury_duration_days = Column(Integer, nullable=True)
    last_match_minutes = Column(Integer, nullable=True)
    last_match_overall = Column(Integer, nullable=True)
    last_match_fact = Column(Integer, nullable=True)
    last_match_position = Column(Integer, nullable=True)
    latest_match_rating_raw = Column(Integer, nullable=True)
    latest_match_rating_minutes = Column(Integer, nullable=True)
    latest_match_rating_date_raw = Column(Integer, nullable=True)
    __table_args__ = (UniqueConstraint("snapshot_id", "player_external_id", "team_external_id"),)


class InferredDelta(Base):
    __tablename__ = "inferred_deltas"
    id = Column(Integer, primary_key=True)
    previous_snapshot_id = Column(ForeignKey("collector_snapshots.id"), nullable=False)
    next_snapshot_id = Column(ForeignKey("collector_snapshots.id"), nullable=False)
    player_id = Column(ForeignKey("players.id"), nullable=False)
    team_external_id = Column(Integer, nullable=False)
    compobjid = Column(Integer, nullable=False)
    values = Column(JSON, nullable=False)
    confidence = Column(String, nullable=False)
    interval_label = Column(String, nullable=False, default="Между снимками")


class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True)
    career_save_id = Column(ForeignKey("career_saves.id"), nullable=False)
    season_id = Column(ForeignKey("seasons.id"), nullable=False)
    source_external_match_id = Column(String, nullable=True)
    played_at = Column(String, nullable=True)
    opponent_id = Column(ForeignKey("teams.id"), nullable=True)
    home_goals = Column(Integer, nullable=True)
    away_goals = Column(Integer, nullable=True)
    verified_source = Column(String, nullable=False)
    external_compobjid = Column(Integer, nullable=True)
    competition_name = Column(String(150), nullable=True)
    club_team_external_id = Column(Integer, nullable=True)
    opponent_name = Column(String(150), nullable=True)
    club_was_home = Column(Boolean, nullable=True)
    club_goals = Column(Integer, nullable=True)
    opponent_goals = Column(Integer, nullable=True)
    duration_minutes = Column(Float, nullable=True)
    result = Column(String(1), nullable=True)
    team_stats = Column(JSON, nullable=False, default=dict)
    opponent_stats = Column(JSON, nullable=False, default=dict)
    timeline = Column(JSON, nullable=False, default=list)
    player_performances = Column(JSON, nullable=False, default=list)
    screenshot_paths = Column(JSON, nullable=False, default=list)
    evidence = Column(JSON, nullable=False, default=dict)
    __table_args__ = (
        Index("ux_match_source", "career_save_id", "source_external_match_id", unique=True),
    )


class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True)
    career_id = Column(ForeignKey("careers.id"), nullable=False)
    match_id = Column(ForeignKey("matches.id"), nullable=True)
    interval_id = Column(ForeignKey("inferred_deltas.id"), nullable=True)
    text = Column(Text, nullable=False)
    created_at = Column(String, nullable=False, default=now)


class SyncEvent(Base):
    __tablename__ = "sync_events"
    id = Column(Integer, primary_key=True)
    save_id = Column(ForeignKey("career_saves.id"), nullable=True, index=True)
    snapshot_id = Column(ForeignKey("collector_snapshots.id"), nullable=True)
    action = Column(String, nullable=False)
    level = Column(String, nullable=False)
    message = Column(String, nullable=False)
    time = Column(String, nullable=False, default=now)


class QueueItem(Base):
    __tablename__ = "queue_items"
    id = Column(Integer, primary_key=True)
    sha256 = Column(String(64), nullable=False, unique=True)
    status = Column(String, nullable=False)
    raw_path = Column(String, nullable=False)
    save_id = Column(ForeignKey("career_saves.id"), nullable=True)
    error = Column(String, nullable=True)
    updated_at = Column(String, nullable=False, default=now)
