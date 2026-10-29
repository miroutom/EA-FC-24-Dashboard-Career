import hashlib
import logging
import shutil
import threading
from datetime import UTC

from pydantic import ValidationError
from sqlalchemy import func, select

from .core import now
from .models import (
    Career,
    CareerSave,
    Competition,
    InferredDelta,
    PlayerStateSnapshot,
    QueueItem,
    SaveBranch,
    Season,
    Snapshot,
    SnapshotRow,
    SyncEvent,
    TeamStateSnapshot,
)
from .schemas import SnapshotInput
from .services import digest, live_player, season

COUNTERS = ("appearances", "goals", "assists", "yellow", "red", "clean_sheets")
LOG = logging.getLogger(__name__)


def latest_rows(session, save_id, branch_no, season_id, as_of=None):
    query = (
        select(SnapshotRow, Snapshot)
        .join(Snapshot, SnapshotRow.snapshot_id == Snapshot.id)
        .where(
            Snapshot.career_save_id == save_id,
            Snapshot.branch_no == branch_no,
            Snapshot.season_id == season_id,
        )
    )
    if as_of:
        query = query.where(Snapshot.captured_at <= as_of)
    rows = session.execute(query.order_by(Snapshot.captured_at, Snapshot.id)).all()
    result = {}
    for row, snap in rows:
        result[(row.player_external_id, row.team_external_id, row.compobjid)] = (row, snap)
    return result


class Ingestor:
    def __init__(self, factory, settings):
        self.factory, self.settings = factory, settings
        self.lock = threading.Lock()
        for folder in ("spool", "raw", "quarantine", "processed"):
            (settings.data_dir / folder).mkdir(parents=True, exist_ok=True)

    def ingest_bytes(self, content: bytes):
        sha = hashlib.sha256(content).hexdigest()
        raw = self.settings.data_dir / "raw" / f"{sha}.json"
        if not raw.exists():
            try:
                with raw.open("xb") as handle:
                    handle.write(content)
            except FileExistsError:
                pass
        with self.lock, self.factory.begin() as session:
            item = session.scalar(select(QueueItem).where(QueueItem.sha256 == sha))
            if item and item.status in ("IMPORTED", "NO_CHANGE", "CONFLICT", "HELD"):
                bound = session.get(CareerSave, item.save_id)
                session.add(
                    SyncEvent(
                        save_id=item.save_id,
                        action="IGNORED",
                        level="INFO",
                        message="Повторная доставка: без изменений",
                    )
                )
                return {"status": "DUPLICATE", "save_id": bound.id if bound else None}
            if not item:
                item = QueueItem(sha256=sha, raw_path=f"raw/{sha}.json", status="RECEIVED")
                session.add(item)
            try:
                if len(content) > self.settings.max_file_bytes:
                    raise ValueError("FILE_TOO_LARGE")
                doc = SnapshotInput.model_validate_json(content)
                if (doc.producer == "lca-demo-simulator") != self.settings.demo_mode:
                    raise ValueError("Synthetic and real snapshot sources must stay isolated")
            except (ValidationError, ValueError):
                item.status, item.error, item.updated_at = (
                    "QUARANTINE",
                    "INVALID_SNAPSHOT: проверьте schema_version, типы и размер",
                    now(),
                )
                shutil.copyfile(raw, self.settings.data_dir / "quarantine" / f"{sha}.json")
                session.add(SyncEvent(action="QUARANTINE", level="ERROR", message=item.error))
                return {"status": item.status}
            by_uid = (
                session.scalar(select(CareerSave).where(CareerSave.external_save_uid == doc.save_uid))
                if doc.save_uid
                else None
            )
            by_key = (
                session.scalar(select(CareerSave).where(CareerSave.instance_key == doc.instance_key))
                if doc.instance_key
                else None
            )
            binding = by_uid or by_key
            if (by_uid and by_key and by_uid.id != by_key.id) or (
                by_key and doc.save_uid and by_key.external_save_uid != doc.save_uid
            ):
                binding = None
            if binding and doc.instance_key and binding.instance_key != doc.instance_key:
                binding = None
            if not binding or doc.season_start_year is None or doc.user_team_id is None:
                item.status, item.error, item.updated_at = (
                    "NEEDS_BINDING",
                    "Неизвестная привязка save, сезон или команда",
                    now(),
                )
                return {"status": item.status}
            cc = session.get(Career, binding.career_id)
            if cc.game_version != doc.game_version or (
                cc.primary_team_id is not None and cc.primary_team_id != doc.user_team_id
            ):
                item.status, item.error = "NEEDS_BINDING", "Игра или команда не соответствует карьере"
                return {"status": item.status}
            if cc.primary_team_id is None:
                cc.primary_team_id = doc.user_team_id
            item.save_id = binding.id
            ss = season(session, binding.career_id, doc.season_start_year)
            captured = doc.captured_at_utc.astimezone(UTC).isoformat()
            state = digest(
                {
                    "season": ss.start_year,
                    "team": doc.user_team_id,
                    "rows": sorted(
                        [r.model_dump() for r in doc.rows],
                        key=lambda r: (r["playerid"], r["teamid"], r["compobjid"]),
                    ),
                    "team_states": sorted(
                        [r.model_dump() for r in doc.team_states],
                        key=lambda r: (r["teamid"], r["leagueid"]),
                    ),
                    "player_states": sorted(
                        [r.model_dump() for r in doc.player_states],
                        key=lambda r: (r["playerid"], r["teamid"]),
                    ),
                }
            )
            branch = binding.active_branch_no
            previous = session.scalar(
                select(Snapshot)
                .where(Snapshot.career_save_id == binding.id, Snapshot.branch_no == branch)
                .order_by(Snapshot.captured_at.desc(), Snapshot.id.desc())
            )
            old_rows = latest_rows(session, binding.id, branch, ss.id)
            rollback_reason = None
            if previous:
                prior_season = session.get(Season, previous.season_id)
                if ss.start_year < prior_season.start_year:
                    rollback_reason = "SEASON_ROLLBACK"
                elif captured < previous.captured_at:
                    rollback_reason = "OUT_OF_ORDER"
                elif (
                    doc.in_game_date
                    and previous.in_game_date
                    and doc.in_game_date.isoformat() < previous.in_game_date
                ):
                    rollback_reason = "GAME_DATE_ROLLBACK"
            for incoming in doc.rows:
                old = old_rows.get((incoming.playerid, incoming.teamid, incoming.compobjid))
                if old:
                    for name in COUNTERS:
                        value = incoming.app if name == "appearances" else getattr(incoming, name)
                        before = getattr(old[0], name)
                        if value is not None and before is not None and value < before:
                            rollback_reason = "COUNTER_DECREASE"
            if binding.status == "CONFLICT":
                branch = session.scalar(
                    select(func.max(SaveBranch.branch_no)).where(SaveBranch.save_id == binding.id)
                )
                pending = session.scalar(
                    select(SaveBranch).where(SaveBranch.save_id == binding.id, SaveBranch.branch_no == branch)
                )
                status = "HELD"
                if pending.status != "PENDING":
                    raise RuntimeError("Missing pending conflict branch")
            elif rollback_reason:
                branch = 1 + (
                    session.scalar(
                        select(func.max(SaveBranch.branch_no)).where(SaveBranch.save_id == binding.id)
                    )
                    or 0
                )
                session.add(
                    SaveBranch(save_id=binding.id, branch_no=branch, status="PENDING", reason=rollback_reason)
                )
                binding.status, status = "CONFLICT", "CONFLICT"
            else:
                status = "NO_CHANGE" if previous and previous.state_sha256 == state else "IMPORTED"
            snap = Snapshot(
                career_save_id=binding.id,
                branch_no=branch,
                season_id=ss.id,
                in_game_date=doc.in_game_date.isoformat() if doc.in_game_date else None,
                captured_at=captured,
                event_name=doc.event,
                source_version=doc.collector_version,
                payload_sha256=sha,
                state_sha256=state,
                status=status,
                completeness=doc.completeness,
                raw_path=item.raw_path,
            )
            session.add(snap)
            session.flush()
            for incoming in doc.rows:
                player = live_player(session, binding.career_id, incoming.playerid, incoming.display_name)
                comp = session.scalar(
                    select(Competition).where(
                        Competition.game_version == doc.game_version,
                        Competition.external_compobjid == incoming.compobjid,
                    )
                )
                if not comp:
                    session.add(
                        Competition(
                            game_version=doc.game_version,
                            external_compobjid=incoming.compobjid,
                            name=f"Турнир #{incoming.compobjid}",
                        )
                    )
                row = SnapshotRow(
                    snapshot_id=snap.id,
                    player_id=player.id,
                    player_external_id=incoming.playerid,
                    team_external_id=incoming.teamid,
                    compobjid=incoming.compobjid,
                    appearances=incoming.app,
                    goals=incoming.goals,
                    assists=incoming.assists,
                    yellow=incoming.yellow,
                    two_yellow=incoming.two_yellow,
                    red=incoming.red,
                    clean_sheets=incoming.clean_sheets,
                    saves=incoming.saves,
                    goals_conceded=incoming.goals_conceded,
                    motm=incoming.motm,
                    avg_raw=incoming.avg,
                )
                session.add(row)
                old = old_rows.get((incoming.playerid, incoming.teamid, incoming.compobjid))
                if old and status == "IMPORTED":
                    delta = {
                        k: getattr(row, k) - getattr(old[0], k)
                        if getattr(row, k) is not None and getattr(old[0], k) is not None
                        else None
                        for k in COUNTERS
                    }
                    if any(v is not None and v != 0 for v in delta.values()):
                        inconsistent = delta["appearances"] == 0 and any(
                            (delta[k] or 0) > 0 for k in ("goals", "assists", "yellow", "red")
                        )
                        confidence = (
                            "INVALID"
                            if inconsistent
                            else "AMBIGUOUS"
                            if doc.completeness != "COMPLETE"
                            or any(v is None for v in delta.values())
                            or (delta["appearances"] or 0) > 1
                            else "INTERVAL"
                        )
                        session.add(
                            InferredDelta(
                                previous_snapshot_id=old[1].id,
                                next_snapshot_id=snap.id,
                                player_id=player.id,
                                team_external_id=incoming.teamid,
                                compobjid=incoming.compobjid,
                                values=delta,
                                confidence=confidence,
                            )
                        )
            for incoming in doc.team_states:
                session.add(
                    TeamStateSnapshot(
                        snapshot_id=snap.id,
                        team_external_id=incoming.teamid,
                        league_external_id=incoming.leagueid,
                        matches_played=incoming.nummatchesplayed,
                        home_wins=incoming.homewins,
                        home_draws=incoming.homedraws,
                        home_losses=incoming.homelosses,
                        away_wins=incoming.awaywins,
                        away_draws=incoming.awaydraws,
                        away_losses=incoming.awaylosses,
                        home_goals_for=incoming.homegf,
                        home_goals_against=incoming.homega,
                        away_goals_for=incoming.awaygf,
                        away_goals_against=incoming.awayga,
                        points=incoming.points,
                        table_position=incoming.currenttableposition,
                        last_game_result_raw=incoming.lastgameresult,
                        form=incoming.teamform,
                        short_form=incoming.teamshortform,
                        long_form=incoming.teamlongform,
                    )
                )
            for incoming in doc.player_states:
                player = live_player(session, binding.career_id, incoming.playerid, incoming.display_name)
                session.add(
                    PlayerStateSnapshot(
                        snapshot_id=snap.id,
                        player_id=player.id,
                        player_external_id=incoming.playerid,
                        team_external_id=incoming.teamid,
                        injury_id=incoming.injury_id,
                        injury_date_raw=incoming.injury_date_raw,
                        injury_duration_days=incoming.injury_duration_days,
                        last_match_minutes=incoming.last_match_minutes,
                        last_match_overall=incoming.last_match_overall,
                        last_match_fact=incoming.last_match_fact,
                        last_match_position=incoming.last_match_position,
                        latest_match_rating_raw=incoming.latest_match_rating_raw,
                        latest_match_rating_minutes=incoming.latest_match_rating_minutes,
                        latest_match_rating_date_raw=incoming.latest_match_rating_date_raw,
                    )
                )
            item.status, item.error, item.updated_at = status, rollback_reason, now()
            session.add(
                SyncEvent(
                    save_id=binding.id,
                    snapshot_id=snap.id,
                    action=status,
                    level="WARNING" if status in ("CONFLICT", "HELD") else "INFO",
                    message=rollback_reason
                    or (
                        "ДЕМО: принят синтетический снимок"
                        if self.settings.demo_mode
                        else "Снимок принят; экспериментальный источник"
                        if not binding.verified_live
                        else "Снимок принят"
                    ),
                )
            )
            return {"status": status, "snapshot_id": snap.id, "save_id": binding.id}

    def retry(self, item_id):
        with self.factory() as session:
            item = session.get(QueueItem, item_id)
            if not item:
                return None
            raw = self.settings.data_dir / item.raw_path
        return self.ingest_bytes(raw.read_bytes())


class Watcher:
    """Single local owner. Two unchanged size/mtime AND checksum observations before ingestion."""

    def __init__(self, ingestor):
        self.ingestor = ingestor
        self.stop_event = threading.Event()
        self.thread = None
        self.seen = {}
        self.last_scan = None
        self.last_error = None

    def scan(self):
        spool = self.ingestor.settings.data_dir / "spool"
        current = set()
        for path in sorted(spool.glob("*.json")):
            if path.is_symlink() or not path.is_file():
                continue
            current.add(path)
            stat = path.stat()
            # Oversized files do not enter memory; preserve original in quarantine.
            if stat.st_size > self.ingestor.settings.max_file_bytes:
                shutil.move(
                    str(path),
                    str(self.ingestor.settings.data_dir / "quarantine" / (path.name + ".oversized")),
                )
                with self.ingestor.factory.begin() as session:
                    session.add(SyncEvent(action="QUARANTINE", level="ERROR", message="FILE_TOO_LARGE"))
                continue
            content = path.read_bytes()
            fingerprint = (stat.st_size, stat.st_mtime_ns, hashlib.sha256(content).hexdigest())
            if self.seen.get(path) != fingerprint:
                self.seen[path] = fingerprint
                continue
            result = self.ingestor.ingest_bytes(content)
            folder = "quarantine" if result["status"] == "QUARANTINE" else "processed"
            destination = self.ingestor.settings.data_dir / folder / f"{fingerprint[2]}.json"
            # The raw archive already contains the original. Content-addressed destination is safe.
            if destination.exists():
                path.unlink()
            else:
                path.replace(destination)
            self.seen.pop(path, None)
        self.seen = {p: fp for p, fp in self.seen.items() if p in current and p.exists()}
        self.last_scan = now()
        self.last_error = None

    def start(self):
        def run():
            while not self.stop_event.wait(1):
                try:
                    self.scan()
                except Exception:
                    self.last_error = (
                        "WATCHER_ERROR: проверьте права на папку данных; операция будет повторена"
                    )
                    LOG.error("Watcher processing failed", exc_info=False)

        self.thread = threading.Thread(target=run, name="snapshot-watcher", daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
