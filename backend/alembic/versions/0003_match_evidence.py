"""Store screenshot-verified match evidence."""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("matches") as batch:
        batch.add_column(sa.Column("external_compobjid", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("competition_name", sa.String(length=150), nullable=True))
        batch.add_column(sa.Column("club_team_external_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("opponent_name", sa.String(length=150), nullable=True))
        batch.add_column(sa.Column("club_was_home", sa.Boolean(), nullable=True))
        batch.add_column(sa.Column("club_goals", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("opponent_goals", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("duration_minutes", sa.Float(), nullable=True))
        batch.add_column(sa.Column("result", sa.String(length=1), nullable=True))
        batch.add_column(sa.Column("team_stats", sa.JSON(), nullable=False, server_default="{}"))
        batch.add_column(sa.Column("opponent_stats", sa.JSON(), nullable=False, server_default="{}"))
        batch.add_column(sa.Column("timeline", sa.JSON(), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("player_performances", sa.JSON(), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("screenshot_paths", sa.JSON(), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("evidence", sa.JSON(), nullable=False, server_default="{}"))
        batch.create_index("ux_match_source", ["career_save_id", "source_external_match_id"], unique=True)


def downgrade():
    with op.batch_alter_table("matches") as batch:
        batch.drop_index("ux_match_source")
        batch.drop_column("evidence")
        batch.drop_column("screenshot_paths")
        batch.drop_column("player_performances")
        batch.drop_column("timeline")
        batch.drop_column("opponent_stats")
        batch.drop_column("team_stats")
        batch.drop_column("result")
        batch.drop_column("duration_minutes")
        batch.drop_column("opponent_goals")
        batch.drop_column("club_goals")
        batch.drop_column("club_was_home")
        batch.drop_column("opponent_name")
        batch.drop_column("club_team_external_id")
        batch.drop_column("competition_name")
        batch.drop_column("external_compobjid")
