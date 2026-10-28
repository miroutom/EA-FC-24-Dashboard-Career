"""Explicit synthetic sandbox. Never invoked by the normal application startup."""

import csv
import hashlib
import io
import json
import re
import threading
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from . import importer
from .core import ROOT
from .models import (
    Career,
    CareerSave,
    Competition,
    HistoricalStat,
    ImportBatch,
    Note,
    Player,
    PlayerSeasonMetadata,
    SaveBranch,
    Snapshot,
)
from .services import normalize, season

PLAYERS = (
    ("Alex Mercer", "ФРВ"),
    ("Jamie Blake", "ФРВ"),
    ("Noah Turner", "ЛФА"),
    ("Leo Carter", "ПФА"),
    ("Oscar Bennett", "ЦАП"),
    ("Ethan Brooks", "ЦП"),
    ("Lucas Reid", "ЦП"),
    ("Theo Walker", "ЦОП"),
    ("Finn Hughes", "ЛЗ"),
    ("Mason Clarke", "ПЗ"),
    ("Oliver Shaw", "ЦЗ"),
    ("Jack Wilson", "ЦЗ"),
    ("Adam Parker", "ВРТ"),
    ("Harry Evans", "ВРТ"),
    ("Max Foster", "ЦП"),
    ("Sam Cooper", "ФРВ"),
    ("Ben Morgan", "ЦЗ"),
    ("Arthur Hayes", "ЦОП"),
    ("João Demo", "ПФА"),
    ("Adam Hložek Demo", "ЦАП"),
    ("Deniz Yılmaz Demo", "ЛЗ"),
    ("Nico Sørensen Demo", "ПЗ"),
)
DEMO_MARKER = "leicester-analytics-synthetic-sandbox-v1\n"


def prepare_demo_directory(settings):
    """Refuse any existing unmarked database, including the real default DATA_DIR."""
    directory = settings.data_dir.resolve()
    if directory == (ROOT / "data").resolve():
        raise ValueError("Demo mode cannot use the real data/ directory")
    marker = directory / ".demo-mode"
    if (directory / "analytics.sqlite3").exists() and not marker.exists():
        raise ValueError("Existing database is not a demo sandbox; choose a new demo directory")
    if marker.exists() and marker.read_text(encoding="utf-8") != DEMO_MARKER:
        raise ValueError("Unknown demo marker")
    directory.mkdir(parents=True, exist_ok=True)
    if not marker.exists():
        marker.write_text(DEMO_MARKER, encoding="utf-8")


def _historical_csv(players, years):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Сезон", "Игрок", "Позиция", "Матчи", "Голы", "Ассисты", "Сухие матчи", "Г+П"])
    for year in years:
        for i, (name, position) in enumerate(players):
            appearances = 24 + (i * 7 + year) % 24
            goals = (
                0
                if position == "ВРТ"
                else (20 if position in ("ФРВ", "ЛФА", "ПФА") else 8) - i % 6 + year % 3
            )
            assists = 0 if position == "ВРТ" else 2 + (i * 3 + year) % 14
            sheets = 4 + (i + year) % 12
            scale = {2020: 0.55, 2021: 0.82, 2022: 1.18}.get(year, 1)
            goals, assists = round(goals * scale), round(assists * scale)
            writer.writerow(
                [
                    f"{year}/{str(year + 1)[2:]}",
                    name,
                    position,
                    appearances,
                    goals,
                    assists,
                    sheets,
                    goals + assists,
                ]
            )
    return buffer.getvalue().encode("utf-8")


def seed_demo(factory):
    """Idempotent fixtures in a directory already guarded by prepare_demo_directory."""
    with factory.begin() as session:
        primary = session.scalar(select(Career).where(Career.name == "ДЕМО · Leicester City"))
        if primary:
            _extend_history(session, primary.id)
            return primary.id
        careers = [
            ("ДЕМО · Leicester City", PLAYERS, range(2023, 2027)),
            ("ДЕМО · Вторая карьера", PLAYERS[:12], range(2025, 2027)),
        ]
        for name, squad, years in careers:
            cc = Career(name=name, game_version="EA FC 24", primary_team_id=95)
            session.add(cc)
            session.flush()
            content = _historical_csv(squad, years)
            result = importer.preview(session, cc.id, "DEMO_GENERATED.csv", content)
            importer.commit(session, cc.id, result["preview_token"], "reject")
            for stat in session.scalars(select(HistoricalStat).where(HistoricalStat.career_id == cc.id)):
                stat.coverage = "DEMO_SYNTHETIC"
            session.add(
                Note(
                    career_id=cc.id,
                    text="ДЕМО: вымышленные игроки и показатели для знакомства с приложением. Данные не получены из EA FC 24.",
                )
            )
            if name == "ДЕМО · Leicester City":
                primary = cc
                ss = season(session, cc.id, 2027)
                for i, (display_name, position) in enumerate(PLAYERS):
                    player = session.scalar(
                        select(Player).where(
                            Player.career_id == cc.id, Player.normalized_name == normalize(display_name)
                        )
                    )
                    player.external_player_id = 900000 + i
                    session.add(PlayerSeasonMetadata(season_id=ss.id, player_id=player.id, position=position))
                save = CareerSave(
                    career_id=cc.id, instance_key="demo-leicester-save", verified_live=False, evidence=None
                )
                session.add(save)
                session.flush()
                session.add(SaveBranch(save_id=save.id, branch_no=0, status="ACTIVE"))
        _extend_history(session, primary.id)
        return primary.id


def _extend_history(session, career_id):
    """Add three earlier synthetic seasons once, including to an existing demo sandbox."""
    content = _historical_csv(PLAYERS, range(2020, 2023))
    sha = hashlib.sha256(content).hexdigest()
    if session.scalar(
        select(ImportBatch.id).where(ImportBatch.career_id == career_id, ImportBatch.sha256 == sha)
    ):
        return
    result = importer.preview(session, career_id, "DEMO_EXTENDED_HISTORY.csv", content)
    if result["errors"] or result["conflicts"]:
        return  # Preserve any explicit edits to the sandbox rather than silently replacing them.
    batch = importer.commit(session, career_id, result["preview_token"], "reject")
    for stat in session.scalars(
        select(HistoricalStat).where(HistoricalStat.source_batch_id == batch["batch_id"])
    ):
        stat.coverage = "DEMO_SYNTHETIC"


class DemoSimulator:
    """Produces labelled synthetic snapshots through the same local ingestion pipeline."""

    def __init__(self, ingestor, career_id):
        self.ingestor, self.career_id = ingestor, career_id
        self.lock = threading.Lock()
        with ingestor.factory() as session:
            events = session.scalars(select(Snapshot.event_name)).all()
        steps = [int(m[1]) for value in events if (m := re.fullmatch(r"demo_interval_(\d+)", value or ""))]
        steps.extend(
            int(m[1])
            for path in (ingestor.settings.data_dir / "spool").glob("demo-*.json")
            if (m := re.match(r"demo-(\d+)-", path.name))
        )
        self.step = max(steps, default=0)

    def _payload(self):
        self.step += 1
        rows = []
        for i, (name, position) in enumerate(PLAYERS):
            for comp, base in ((99001, 12), (99002, 4), (99003, 2)):
                progress = self.step if comp == 99001 else self.step // 2
                goals = (
                    0
                    if position == "ВРТ"
                    else max(0, 8 - i // 3) + (progress if i % 4 == 0 else progress // 3)
                )
                rows.append(
                    {
                        "playerid": 900000 + i,
                        "teamid": 95,
                        "compobjid": comp,
                        "display_name": name,
                        "app": base + progress,
                        "goals": goals,
                        "assists": 0 if position == "ВРТ" else i % 4 + progress // 2,
                        "yellow": i % 3,
                        "red": 0,
                        "clean_sheets": 1 + progress // 3,
                    }
                )
        return {
            "schema_version": 1,
            "producer": "lca-demo-simulator",
            "collector_version": "demo-1",
            "game_version": "EA FC 24",
            "captured_at_utc": datetime.now(UTC).isoformat(),
            "event": f"demo_interval_{self.step}",
            "save_uid": None,
            "instance_key": "demo-leicester-save",
            "user_team_id": 95,
            "season_start_year": 2027,
            "in_game_date": (date(2027, 8, 1) + timedelta(days=7 * self.step)).isoformat(),
            "completeness": "COMPLETE",
            "rows": rows,
        }

    def seed_snapshots(self):
        if self.step:
            return
        for _ in range(3):
            self.ingestor.ingest_bytes(json.dumps(self._payload(), ensure_ascii=False).encode())
        with self.ingestor.factory.begin() as session:
            for external_id, name in (
                (99001, "ДЕМО · Лига"),
                (99002, "ДЕМО · Кубок"),
                (99003, "ДЕМО · Европа"),
            ):
                comp = session.scalar(
                    select(Competition).where(Competition.external_compobjid == external_id)
                )
                comp.name = name

    def advance(self):
        with self.lock:
            payload = self._payload()
            path = self.ingestor.settings.data_dir / "spool" / f"demo-{self.step:05d}-{uuid.uuid4().hex}.json"
            temp = path.with_suffix(".tmp")
            temp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            temp.replace(path)
            return {"status": "QUEUED", "demo": True, "step": self.step, "career_id": self.career_id}
