import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from alembic.config import Config
from fastapi import Depends, FastAPI, File, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from alembic import command

from . import analytics, importer
from .core import ROOT, Settings, make_engine, session_factory
from .ingestion import Ingestor, Watcher
from .models import (
    Career,
    CareerSave,
    Competition,
    HistoricalStat,
    ImportBatch,
    InferredDelta,
    Match,
    Note,
    Player,
    PlayerAlias,
    QueueItem,
    SaveBranch,
    Season,
    Snapshot,
    SnapshotRow,
    SyncEvent,
)
from .responses import AnalyticsDTO, CareerDTO, CompareDTO, CompetitionDTO, DashboardDTO, PlayerDTO, SeasonDTO
from .schemas import (
    DTO,
    CareerInput,
    CommitInput,
    IdentityInput,
    NoteInput,
    PolicyInput,
    ResolveInput,
    SaveInput,
)
from .services import Problem, career, season


def row_dto(row):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def create_app(settings=None, migrate=True):
    settings = settings or Settings()
    engine = make_engine(settings.data_dir)
    if migrate:
        # Revision uses concrete DDL; tests and production follow the same upgrade path.
        cfg = Config(str(ROOT / "backend" / "alembic.ini"))
        cfg.attributes["connection"] = engine.connect()
        try:
            command.upgrade(cfg, "head")
        finally:
            cfg.attributes["connection"].close()
    factory = session_factory(engine)
    ingestor = Ingestor(factory, settings)
    watcher = Watcher(ingestor)

    @asynccontextmanager
    async def lifespan(app):
        if settings.watcher_enabled:
            watcher.start()
        yield
        watcher.stop()
        engine.dispose()

    app = FastAPI(title="Leicester City Analytics", version="0.2.0", lifespan=lifespan)
    app.state.factory, app.state.ingestor, app.state.watcher = factory, ingestor, watcher

    def db():
        with factory.begin() as session:
            yield session

    def filters(
        season_id: int | None = None,
        competition_id: int | None = None,
        as_of: datetime | None = None,
        save_id: int | None = None,
    ):
        if as_of and as_of.tzinfo is None:
            raise Problem(422, "UTC_REQUIRED", "as_of требует часовой пояс")
        return dict(
            season_id=season_id,
            competition_id=competition_id,
            as_of=as_of.astimezone(UTC).isoformat() if as_of else None,
            save_id=save_id,
        )

    @app.middleware("http")
    async def local_origin_guard(request: Request, call_next):
        host = request.headers.get("host", "").split(":")[0]
        origin = request.headers.get("origin")
        allowed = (
            "http://127.0.0.1:8000",
            "http://localhost:8000",
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        )
        if host not in ("127.0.0.1", "localhost", "testserver") or (origin and origin not in allowed):
            return JSONResponse(
                {"error": {"code": "LOCAL_ONLY", "message": "Только локальный доступ"}}, status_code=403
            )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(Problem)
    async def problem_handler(_, exc):
        return JSONResponse(
            {"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
            status_code=exc.status,
        )

    @app.exception_handler(IntegrityError)
    async def integrity_handler(_, exc):
        return JSONResponse(
            {"error": {"code": "CONSTRAINT_CONFLICT", "message": "Конфликт уникальности; обновите данные"}},
            status_code=409,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_, exc):
        return JSONResponse(
            {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Проверьте параметры запроса",
                    "details": [{"loc": list(e["loc"]), "message": e["msg"]} for e in exc.errors()],
                }
            },
            status_code=422,
        )

    base = "/api/v1"

    @app.get(base + "/health", response_model=DTO)
    def health():
        return {"status": "ok", "collector": "not verified", "version": "0.2.0"}

    @app.get(base + "/careers", response_model=list[CareerDTO])
    def get_careers(session=Depends(db)):
        return [row_dto(c) for c in session.scalars(select(Career).order_by(Career.id))]

    @app.post(base + "/careers", response_model=CareerDTO, status_code=201)
    def create_career(body: CareerInput, session=Depends(db)):
        result = Career(
            name=body.name.strip(), game_version=body.game_version, primary_team_id=body.primary_team_id
        )
        if not result.name:
            raise Problem(422, "EMPTY_NAME", "Введите название")
        session.add(result)
        session.flush()
        season(session, result.id, body.start_year)
        return row_dto(result)

    @app.get(base + "/careers/{career_id}/seasons", response_model=list[SeasonDTO])
    def get_seasons(career_id: int, session=Depends(db)):
        career(session, career_id)
        return [
            row_dto(s)
            for s in session.scalars(
                select(Season).where(Season.career_id == career_id).order_by(Season.start_year)
            )
        ]

    @app.get(base + "/careers/{career_id}/competitions", response_model=list[CompetitionDTO])
    def competitions(career_id: int, session=Depends(db)):
        career(session, career_id)
        ids = (
            select(SnapshotRow.compobjid)
            .join(Snapshot)
            .join(CareerSave)
            .where(CareerSave.career_id == career_id)
        )
        return [
            row_dto(c)
            for c in session.scalars(select(Competition).where(Competition.external_compobjid.in_(ids)))
        ]

    @app.get(base + "/careers/{career_id}/dashboard", response_model=DashboardDTO)
    def dashboard(career_id: int, f=Depends(filters), session=Depends(db)):
        return analytics.dashboard(session, career_id, **f)

    @app.get(base + "/careers/{career_id}/players", response_model=AnalyticsDTO)
    def players(
        career_id: int,
        search: str = Query("", max_length=150),
        sort: str = "goals",
        descending: bool = True,
        page: int = Query(1, ge=1),
        size: int = Query(50, ge=1, le=200),
        f=Depends(filters),
        session=Depends(db),
    ):
        if sort not in (
            "name",
            "goals",
            "assists",
            "appearances",
            "goal_contributions",
            "seasons_count",
            "goals_per_appearance",
        ):
            raise Problem(422, "SORT", "Неизвестная сортировка")
        data = analytics.players(session, career_id, **f)
        items = [p for p in data["items"] if search.casefold() in p["name"].casefold()]
        known = [p for p in items if p[sort] is not None]
        known.sort(key=lambda p: p[sort].casefold() if sort == "name" else p[sort], reverse=descending)
        items = known + [p for p in items if p[sort] is None]
        return {
            **data,
            "items": items[(page - 1) * size : page * size],
            "total": len(items),
            "page": page,
            "size": size,
        }

    def get_player(session, career_id, player_id, f):
        player = session.get(Player, player_id)
        if not player or player.career_id != career_id:
            raise Problem(404, "PLAYER_NOT_FOUND", "Игрок не найден в этой карьере")
        data = analytics.players(session, career_id, **f)
        result = next((p for p in data["items"] if p["id"] == player_id), None)
        if not result:
            return {"id": player.id, "name": player.display_name, "history": [], "data_quality": ["unknown"]}
        return {
            **result,
            "last_synced_at": data["last_synced_at"],
            "source_scope": data["source_scope"],
            "competition_history": analytics.competition_history(session, career_id, player_id, **f),
        }

    @app.get(base + "/careers/{career_id}/players/{player_id}", response_model=PlayerDTO)
    def player_detail(career_id: int, player_id: int, f=Depends(filters), session=Depends(db)):
        return get_player(session, career_id, player_id, f)

    @app.get(base + "/careers/{career_id}/compare", response_model=CompareDTO)
    def compare(
        career_id: int, player_ids: str = Query(max_length=100), f=Depends(filters), session=Depends(db)
    ):
        try:
            ids = [int(x) for x in player_ids.split(",")]
        except ValueError as exc:
            raise Problem(422, "PLAYER_IDS", "Нужны ID игроков через запятую") from exc
        if not 2 <= len(set(ids)) <= 4 or len(ids) != len(set(ids)):
            raise Problem(422, "PLAYER_COUNT", "Выберите от 2 до 4 разных игроков")
        return {"items": [get_player(session, career_id, pid, f) for pid in ids]}

    @app.post(base + "/careers/{career_id}/imports/preview", response_model=DTO)
    async def preview(career_id: int, file: UploadFile = File(...), session=Depends(db)):
        content = await file.read(settings.max_file_bytes + 1)
        if len(content) > settings.max_file_bytes:
            raise Problem(422, "FILE_LIMIT", "Файл превышает 5 MiB")
        return importer.preview(session, career_id, file.filename or "upload", content)

    @app.post(base + "/careers/{career_id}/imports/commit", response_model=DTO)
    def commit(career_id: int, body: CommitInput, session=Depends(db)):
        return importer.commit(session, career_id, body.preview_token, body.strategy)

    @app.get(base + "/careers/{career_id}/imports", response_model=list[DTO])
    def imports(career_id: int, session=Depends(db)):
        career(session, career_id)
        return [
            row_dto(b) for b in session.scalars(select(ImportBatch).where(ImportBatch.career_id == career_id))
        ]

    @app.post(base + "/careers/{career_id}/saves/bind", response_model=DTO)
    def bind(career_id: int, body: SaveInput, session=Depends(db)):
        career(session, career_id)
        save = CareerSave(career_id=career_id, **body.model_dump())
        session.add(save)
        session.flush()
        session.add(SaveBranch(save_id=save.id, branch_no=0, status="ACTIVE"))
        return row_dto(save)

    def owned_save(session, career_id, save_id):
        save = session.get(CareerSave, save_id)
        if not save or save.career_id != career_id:
            raise Problem(404, "SAVE_NOT_FOUND", "Сохранение не найдено в этой карьере")
        return save

    @app.post(base + "/careers/{career_id}/saves/{save_id}/resolve", response_model=DTO)
    def resolve(career_id: int, save_id: int, body: ResolveInput, session=Depends(db)):
        save = owned_save(session, career_id, save_id)
        pending = session.scalar(
            select(SaveBranch).where(SaveBranch.save_id == save.id, SaveBranch.status == "PENDING")
        )
        if not pending:
            raise Problem(409, "NO_CONFLICT", "Нет конфликтной ветки")
        if body.strategy == "adopt":
            active = session.scalar(
                select(SaveBranch).where(
                    SaveBranch.save_id == save.id, SaveBranch.branch_no == save.active_branch_no
                )
            )
            active.status = "ARCHIVED"
            pending.status = "ACTIVE"
            save.active_branch_no = pending.branch_no
        else:
            pending.status = "REJECTED"
        save.status = "ACTIVE"
        session.add(
            SyncEvent(
                save_id=save.id, action="RESOLVED", level="WARNING", message=f"Явное решение: {body.strategy}"
            )
        )
        return row_dto(save)

    @app.post(base + "/careers/{career_id}/seasons/{season_id}/policy", response_model=DTO)
    def policy(career_id: int, season_id: int, body: PolicyInput, session=Depends(db)):
        ss = session.get(Season, season_id)
        if not ss or ss.career_id != career_id:
            raise Problem(404, "SEASON_NOT_FOUND", "Сезон не найден")
        ss.source_policy = body.source_policy
        return row_dto(ss)

    @app.post(base + "/careers/{career_id}/players/{player_id}/identity", response_model=DTO)
    def link_identity(career_id: int, player_id: int, body: IdentityInput, session=Depends(db)):
        target = session.get(Player, player_id)
        if not target or target.career_id != career_id:
            raise Problem(404, "PLAYER_NOT_FOUND", "Игрок не найден")
        existing = session.scalar(
            select(Player).where(
                Player.career_id == career_id, Player.external_player_id == body.external_player_id
            )
        )
        if target.external_player_id is not None and target.external_player_id != body.external_player_id:
            raise Problem(409, "IDENTITY_CONFLICT", "Игрок уже связан с другим ID")
        if existing and existing.id != target.id:
            if session.scalar(select(HistoricalStat.id).where(HistoricalStat.player_id == existing.id)):
                raise Problem(
                    409, "IDENTITY_CONFLICT", "Оба игрока имеют историю; требуется отдельная проверка"
                )
            for model in (SnapshotRow, InferredDelta):
                session.execute(
                    update(model).where(model.player_id == existing.id).values(player_id=target.id)
                )
            for alias in session.scalars(select(PlayerAlias).where(PlayerAlias.player_id == existing.id)):
                alias.player_id = target.id
            session.delete(existing)
            session.flush()
        target.external_player_id = body.external_player_id
        return row_dto(target)

    @app.get(base + "/careers/{career_id}/sync/status", response_model=DTO)
    def sync_status(career_id: int, session=Depends(db)):
        career(session, career_id)
        saves = session.scalars(select(CareerSave).where(CareerSave.career_id == career_id)).all()
        ids = [s.id for s in saves]
        latest = session.scalar(
            select(Snapshot).where(Snapshot.career_save_id.in_(ids)).order_by(Snapshot.imported_at.desc())
        )
        successful = session.scalar(
            select(Snapshot)
            .where(Snapshot.career_save_id.in_(ids), Snapshot.status.in_(["IMPORTED", "NO_CHANGE"]))
            .order_by(Snapshot.imported_at.desc())
        )
        stale = (
            not successful
            or (datetime.now(UTC) - datetime.fromisoformat(successful.imported_at)).total_seconds()
            > settings.stale_seconds
        )
        counts = dict(
            session.execute(
                select(QueueItem.status, func.count())
                .where(QueueItem.save_id.in_(ids))
                .group_by(QueueItem.status)
            ).all()
        )
        queue = session.scalars(
            select(QueueItem).where(QueueItem.save_id.in_(ids)).order_by(QueueItem.id.desc()).limit(100)
        ).all()
        counts["IGNORED"] = session.scalar(
            select(func.count())
            .select_from(SyncEvent)
            .where(SyncEvent.save_id.in_(ids), SyncEvent.action == "IGNORED")
        )
        return {
            "collector": "verified by user evidence"
            if saves and all(s.verified_live for s in saves)
            else "not verified",
            "connected": bool(successful and not stale),
            "stale": stale,
            "saves": [row_dto(s) for s in saves],
            "last_snapshot": row_dto(latest) if latest else None,
            "last_synced_at": successful.imported_at if successful else None,
            "counts": counts,
            "queue": [row_dto(q) for q in queue],
            "unassigned_count": session.scalar(
                select(func.count()).select_from(QueueItem).where(QueueItem.save_id.is_(None))
            ),
            "unassigned_counts": dict(
                session.execute(
                    select(QueueItem.status, func.count())
                    .where(QueueItem.save_id.is_(None))
                    .group_by(QueueItem.status)
                ).all()
            ),
            "unassigned_errors": [
                row_dto(e)
                for e in session.scalars(
                    select(SyncEvent)
                    .where(SyncEvent.save_id.is_(None), SyncEvent.level == "ERROR")
                    .order_by(SyncEvent.id.desc())
                    .limit(10)
                )
            ],
            "watcher": {
                "enabled": settings.watcher_enabled,
                "last_scan": watcher.last_scan,
                "error": watcher.last_error,
            },
            "capabilities": {
                "match_details": "UNAVAILABLE",
                "ratings": "NOT_TESTED",
                "auto_capture": "NOT_TESTED",
            },
        }

    @app.get(base + "/careers/{career_id}/sync/events", response_model=list[DTO])
    def sync_events(career_id: int, session=Depends(db)):
        career(session, career_id)
        ids = select(CareerSave.id).where(CareerSave.career_id == career_id)
        return [
            row_dto(e)
            for e in session.scalars(
                select(SyncEvent).where(SyncEvent.save_id.in_(ids)).order_by(SyncEvent.id.desc()).limit(100)
            )
        ]

    @app.post(base + "/careers/{career_id}/sync/retry", response_model=DTO)
    def retry(career_id: int, session=Depends(db)):
        career(session, career_id)
        saves = session.scalars(select(CareerSave).where(CareerSave.career_id == career_id)).all()
        candidates = session.scalars(
            select(QueueItem).where(QueueItem.status.in_(["NEEDS_BINDING", "QUARANTINE"]))
        ).all()
        ids = []
        for item in candidates:
            try:
                doc = json.loads((settings.data_dir / item.raw_path).read_text(encoding="utf-8"))
            except (ValueError, OSError):
                continue
            if any(
                (doc.get("instance_key") == s.instance_key)
                or (s.external_save_uid and doc.get("save_uid") == s.external_save_uid)
                for s in saves
            ):
                ids.append(item.id)
        # Use independent ingestion transactions; release request read transaction first.
        session.commit()
        return {"results": [ingestor.retry(i) for i in ids]}

    @app.get(base + "/careers/{career_id}/snapshots", response_model=list[DTO])
    def snapshots(
        career_id: int, save_id: int | None = None, limit: int = Query(100, ge=1, le=500), session=Depends(db)
    ):
        career(session, career_id)
        if save_id:
            owned_save(session, career_id, save_id)
        ids = select(CareerSave.id).where(CareerSave.career_id == career_id)
        query = select(Snapshot).where(Snapshot.career_save_id.in_(ids))
        if save_id:
            query = query.where(Snapshot.career_save_id == save_id)
        return [row_dto(s) for s in session.scalars(query.order_by(Snapshot.id.desc()).limit(limit))]

    @app.get(base + "/careers/{career_id}/changes", response_model=list[DTO])
    def changes(
        career_id: int,
        player_id: int | None = None,
        season_id: int | None = None,
        confidence: str | None = None,
        session=Depends(db),
    ):
        career(session, career_id)
        query = (
            select(InferredDelta)
            .join(Snapshot, InferredDelta.next_snapshot_id == Snapshot.id)
            .join(CareerSave)
            .where(CareerSave.career_id == career_id)
        )
        if player_id:
            get_player(session, career_id, player_id, {})
            query = query.where(InferredDelta.player_id == player_id)
        if season_id:
            ss = session.get(Season, season_id)
            if not ss or ss.career_id != career_id:
                raise Problem(404, "SEASON_NOT_FOUND", "Сезон не найден")
            query = query.where(Snapshot.season_id == season_id)
        if confidence:
            query = query.where(InferredDelta.confidence == confidence)
        return [row_dto(d) for d in session.scalars(query.order_by(InferredDelta.id.desc()).limit(200))]

    @app.get(base + "/careers/{career_id}/notes", response_model=list[DTO])
    def notes(career_id: int, session=Depends(db)):
        career(session, career_id)
        return [
            row_dto(n)
            for n in session.scalars(
                select(Note).where(Note.career_id == career_id).order_by(Note.id.desc()).limit(200)
            )
        ]

    @app.post(base + "/careers/{career_id}/notes", response_model=DTO)
    def add_note(career_id: int, body: NoteInput, session=Depends(db)):
        career(session, career_id)
        if body.interval_id:
            owner = session.scalar(
                select(CareerSave.career_id)
                .join(Snapshot, Snapshot.career_save_id == CareerSave.id)
                .join(InferredDelta, InferredDelta.next_snapshot_id == Snapshot.id)
                .where(InferredDelta.id == body.interval_id)
            )
            if owner != career_id:
                raise Problem(404, "INTERVAL_NOT_FOUND", "Интервал не найден")
        if body.match_id:
            match = session.get(Match, body.match_id)
            if not match or session.get(CareerSave, match.career_save_id).career_id != career_id:
                raise Problem(404, "MATCH_NOT_FOUND", "Подтверждённый матч не найден")
        result = Note(career_id=career_id, **body.model_dump())
        session.add(result)
        session.flush()
        return row_dto(result)

    dist = ROOT / "frontend" / "dist"
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            if path.startswith("api/"):
                raise Problem(404, "NOT_FOUND", "Endpoint не найден")
            return FileResponse(dist / "index.html")

    return app


def main():
    import uvicorn

    uvicorn.run(create_app(), host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
