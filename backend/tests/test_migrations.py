from alembic.autogenerate import compare_metadata
from alembic.config import Config
from sqlalchemy import inspect

from alembic import command
from app.core import ROOT, Base, make_engine


def test_revision_roundtrip_matches_models_and_enables_sqlite_pragmas(tmp_path):
    engine = make_engine(tmp_path)
    config = Config(str(ROOT / "backend" / "alembic.ini"))
    with engine.connect() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        from alembic.migration import MigrationContext

        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
        assert connection.exec_driver_sql("PRAGMA journal_mode").scalar() == "wal"
        connection.commit()
        command.downgrade(config, "base")
        assert inspect(connection).get_table_names() == ["alembic_version"]
        connection.commit()
        command.upgrade(config, "head")
        assert "collector_snapshot_rows" in inspect(connection).get_table_names()
    engine.dispose()
