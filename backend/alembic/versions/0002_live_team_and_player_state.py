"""Add optional FC24 team form and player state observations."""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("collector_snapshot_rows") as batch:
        batch.add_column(sa.Column("two_yellow", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("saves", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("goals_conceded", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("motm", sa.Integer(), nullable=True))

    op.create_table(
        "team_state_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("team_external_id", sa.Integer(), nullable=False),
        sa.Column("league_external_id", sa.Integer(), nullable=False),
        sa.Column("matches_played", sa.Integer(), nullable=True),
        sa.Column("home_wins", sa.Integer(), nullable=True),
        sa.Column("home_draws", sa.Integer(), nullable=True),
        sa.Column("home_losses", sa.Integer(), nullable=True),
        sa.Column("away_wins", sa.Integer(), nullable=True),
        sa.Column("away_draws", sa.Integer(), nullable=True),
        sa.Column("away_losses", sa.Integer(), nullable=True),
        sa.Column("home_goals_for", sa.Integer(), nullable=True),
        sa.Column("home_goals_against", sa.Integer(), nullable=True),
        sa.Column("away_goals_for", sa.Integer(), nullable=True),
        sa.Column("away_goals_against", sa.Integer(), nullable=True),
        sa.Column("points", sa.Integer(), nullable=True),
        sa.Column("table_position", sa.Integer(), nullable=True),
        sa.Column("last_game_result_raw", sa.Integer(), nullable=True),
        sa.Column("form", sa.Integer(), nullable=True),
        sa.Column("short_form", sa.Integer(), nullable=True),
        sa.Column("long_form", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["snapshot_id"], ["collector_snapshots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_id", "team_external_id", "league_external_id"),
    )
    op.create_index(
        op.f("ix_team_state_snapshots_snapshot_id"),
        "team_state_snapshots",
        ["snapshot_id"],
        unique=False,
    )

    op.create_table(
        "player_state_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("player_external_id", sa.Integer(), nullable=False),
        sa.Column("team_external_id", sa.Integer(), nullable=False),
        sa.Column("injury_id", sa.Integer(), nullable=True),
        sa.Column("injury_date_raw", sa.Integer(), nullable=True),
        sa.Column("injury_duration_days", sa.Integer(), nullable=True),
        sa.Column("last_match_minutes", sa.Integer(), nullable=True),
        sa.Column("last_match_overall", sa.Integer(), nullable=True),
        sa.Column("last_match_fact", sa.Integer(), nullable=True),
        sa.Column("last_match_position", sa.Integer(), nullable=True),
        sa.Column("latest_match_rating_raw", sa.Integer(), nullable=True),
        sa.Column("latest_match_rating_minutes", sa.Integer(), nullable=True),
        sa.Column("latest_match_rating_date_raw", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.ForeignKeyConstraint(["snapshot_id"], ["collector_snapshots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_id", "player_external_id", "team_external_id"),
    )
    op.create_index(
        op.f("ix_player_state_snapshots_snapshot_id"),
        "player_state_snapshots",
        ["snapshot_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_player_state_snapshots_snapshot_id"), table_name="player_state_snapshots")
    op.drop_table("player_state_snapshots")
    op.drop_index(op.f("ix_team_state_snapshots_snapshot_id"), table_name="team_state_snapshots")
    op.drop_table("team_state_snapshots")
    with op.batch_alter_table("collector_snapshot_rows") as batch:
        batch.drop_column("motm")
        batch.drop_column("goals_conceded")
        batch.drop_column("saves")
        batch.drop_column("two_yellow")
