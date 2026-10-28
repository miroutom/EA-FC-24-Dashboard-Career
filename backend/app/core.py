from datetime import UTC, datetime
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    data_dir: Path = ROOT / "data"
    watcher_enabled: bool = True
    demo_mode: bool = False
    http_port: int = 8000
    stale_seconds: int = 300
    max_file_bytes: int = 5 * 1024 * 1024


class Base(DeclarativeBase):
    pass


def now():
    return datetime.now(UTC).isoformat()


def make_engine(data_dir: Path):
    data_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{data_dir / 'analytics.sqlite3'}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )

    @event.listens_for(engine, "connect")
    def configure(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=30000")

    return engine


def session_factory(engine):
    return sessionmaker(engine, expire_on_commit=False)
