import argparse
from pathlib import Path

from alembic.config import Config
from sqlalchemy import select

from alembic import command

from .core import ROOT, Settings, make_engine, session_factory
from .importer import commit, preview
from .models import Career
from .services import season


def main():
    parser = argparse.ArgumentParser(description="Local database maintenance; no game data fabricated")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("migrate")
    seed = commands.add_parser("seed")
    seed.add_argument("--workbook", type=Path, default=ROOT / "leicester_rebuilt_with_career_totals.xlsx")
    seed.add_argument("--name", default="Leicester City")
    args = parser.parse_args()
    command.upgrade(Config(str(ROOT / "backend" / "alembic.ini")), "head")
    if args.command == "seed":
        factory = session_factory(make_engine(Settings().data_dir))
        with factory.begin() as session:
            career = session.scalar(select(Career).where(Career.name == args.name))
            if not career:
                career = Career(name=args.name, game_version="EA FC 24")
                session.add(career)
                session.flush()
                season(session, career.id, 2023)
            result = preview(session, career.id, args.workbook.name, args.workbook.read_bytes())
            if result["errors"] or result["conflicts"]:
                raise RuntimeError("Source validation/conflict requires the UI preview workflow")
            print(commit(session, career.id, result["preview_token"], "reject"))


if __name__ == "__main__":
    main()
