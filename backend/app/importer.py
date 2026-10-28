import csv
import hashlib
import io
import re
import uuid
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import openpyxl
from sqlalchemy import select

from .models import HistoricalStat, ImportBatch, ImportPreview, Player, PlayerSeasonMetadata, Season
from .services import Problem, career, digest, historical_player, normalize, season

HEADERS = {
    "Сезон": "season",
    "Игрок": "name",
    "Позиция": "position",
    "Матчи": "appearances",
    "Голы": "goals",
    "Ассисты": "assists",
    "Сухие матчи": "clean_sheets",
}
METRICS = ("appearances", "goals", "assists", "clean_sheets")


def parse(filename, content):
    suffix = Path(filename).suffix.lower()
    if suffix == ".xlsx":
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                if sum(x.file_size for x in archive.infolist()) > 30_000_000:
                    raise Problem(422, "EXPANDED_LIMIT", "Слишком большой распакованный Excel")
            workbook = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
            if "Все сезоны" not in workbook.sheetnames:
                raise Problem(422, "MISSING_SHEET", "Нужен лист «Все сезоны»")
            sheet = workbook["Все сезоны"]
            if (sheet.max_row or 0) > 20001 or (sheet.max_column or 0) > 50:
                raise Problem(422, "ROW_LIMIT", "Не более 20000 строк и 50 колонок")
            values = list(sheet.values)
            workbook.close()
        except (zipfile.BadZipFile, ValueError, KeyError) as exc:
            raise Problem(422, "INVALID_XLSX", "Некорректный Excel") from exc
    elif suffix == ".csv":
        try:
            text = content.decode("utf-8-sig")
            dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
            values = list(csv.reader(io.StringIO(text), dialect))
        except (UnicodeDecodeError, csv.Error) as exc:
            raise Problem(422, "INVALID_CSV", "Нужен CSV UTF-8 с заголовками") from exc
    else:
        raise Problem(422, "FILE_TYPE", "Допускаются XLSX и CSV")
    if not values or len(values) > 20001:
        raise Problem(422, "ROW_LIMIT", "Пустой файл или превышен лимит строк")
    header = [str(x).strip() for x in values[0]]
    if any(header.count(h) != 1 for h in HEADERS):
        raise Problem(422, "HEADERS", "Нужны уникальные колонки: " + ", ".join(HEADERS))
    rows, errors, seen = [], [], {}
    for number, cells in enumerate(values[1:], 2):
        if not any(v is not None and str(v).strip() for v in cells):
            continue
        record = {
            key: cells[header.index(h)] if header.index(h) < len(cells) else None
            for h, key in HEADERS.items()
        }
        try:
            match = re.fullmatch(r"(20\d{2})[/-](\d{2}|20\d{2})", str(record["season"]).strip())
            if not match or int(match[2]) % 100 != (int(match[1]) + 1) % 100:
                raise ValueError("некорректный сезон")
            record["year"] = int(match[1])
            record["name"] = str(record["name"] or "").strip()
            if not record["name"] or len(record["name"]) > 150:
                raise ValueError("пустое или слишком длинное имя")
            record["position"] = str(record["position"]).strip() if record["position"] else None
            for metric in METRICS:
                value = record[metric]
                if value is None or str(value).strip() in ("", "—", "-"):
                    record[metric] = None
                else:
                    if isinstance(value, bool) or not re.fullmatch(r"\d+(\.0+)?", str(value).strip()):
                        raise ValueError(f"{metric}: нужен неотрицательный целый счётчик")
                    record[metric] = int(float(value))
                    if record[metric] > 10_000_000:
                        raise ValueError("счётчик превышает лимит")
            key = (record["year"], normalize(record["name"]))
            if key in seen:
                if record != seen[key]:
                    raise ValueError("противоречащие друг другу строки одного игрока/сезона")
                continue
            seen[key] = record
            rows.append(record)
        except ValueError as exc:
            errors.append({"row": number, "message": str(exc)})
    return rows, errors


def baseline(session, career_id):
    stats = session.scalars(
        select(HistoricalStat).where(HistoricalStat.career_id == career_id).order_by(HistoricalStat.id)
    ).all()
    metadata = session.execute(
        select(PlayerSeasonMetadata.player_id, PlayerSeasonMetadata.season_id, PlayerSeasonMetadata.position)
        .join(Season)
        .where(Season.career_id == career_id)
        .order_by(PlayerSeasonMetadata.id)
    ).all()
    return digest(
        {
            "stats": [
                (s.id, s.season_id, s.player_id, *[getattr(s, k) for k in METRICS], s.source_batch_id)
                for s in stats
            ],
            "metadata": [tuple(m) for m in metadata],
        }
    )


def conflicts(session, career_id, rows):
    result = []
    for row in rows:
        player = session.scalar(
            select(Player).where(
                Player.career_id == career_id,
                Player.normalized_name == normalize(row["name"]),
                Player.external_player_id.is_(None),
            )
        )
        # Historical aliases provide the canonical exact-name mapping, even after linking an ID.
        from .models import PlayerAlias

        alias = session.scalar(
            select(PlayerAlias).where(
                PlayerAlias.career_id == career_id, PlayerAlias.alias == normalize(row["name"])
            )
        )
        if alias:
            player = session.get(Player, alias.player_id)
        ss = session.scalar(
            select(Season).where(Season.career_id == career_id, Season.start_year == row["year"])
        )
        old = (
            session.scalar(
                select(HistoricalStat).where(
                    HistoricalStat.player_id == player.id, HistoricalStat.season_id == ss.id
                )
            )
            if player and ss
            else None
        )
        meta = (
            session.scalar(
                select(PlayerSeasonMetadata).where(
                    PlayerSeasonMetadata.player_id == player.id, PlayerSeasonMetadata.season_id == ss.id
                )
            )
            if old
            else None
        )
        position_changed = bool(old) and (meta.position if meta else None) != row["position"]
        if old and (position_changed or any(getattr(old, metric) != row[metric] for metric in METRICS)):
            result.append(
                {
                    "player": row["name"],
                    "season": row["season"],
                    "existing": {
                        **{m: getattr(old, m) for m in METRICS},
                        "position": meta.position if meta else None,
                    },
                    "incoming": {**{m: row[m] for m in METRICS}, "position": row["position"]},
                }
            )
    return result


def preview(session, career_id, filename, content):
    career(session, career_id)
    rows, errors = parse(filename, content)
    sha = hashlib.sha256(content).hexdigest()
    token = str(uuid.uuid4())
    if not errors:
        session.add(
            ImportPreview(
                token=token,
                career_id=career_id,
                filename=Path(filename).name,
                sha256=sha,
                rows=rows,
                baseline_digest=baseline(session, career_id),
            )
        )
    duplicate = session.scalar(
        select(ImportBatch).where(ImportBatch.career_id == career_id, ImportBatch.sha256 == sha)
    )
    return {
        "preview_token": token if not errors else None,
        "rows_count": len(rows),
        "rows": rows[:200],
        "errors": errors,
        "conflicts": conflicts(session, career_id, rows),
        "duplicate": duplicate is not None,
        "coverage": "PARTIAL_SCREENSHOT",
        "sheet": "Все сезоны" if filename.lower().endswith(".xlsx") else "CSV",
    }


def commit(session, career_id, token, strategy):
    career(session, career_id)
    item = session.get(ImportPreview, token)
    if not item or item.career_id != career_id:
        raise Problem(404, "PREVIEW_NOT_FOUND", "Предпросмотр не найден в этой карьере")
    batch = session.scalar(
        select(ImportBatch).where(ImportBatch.career_id == career_id, ImportBatch.sha256 == item.sha256)
    )
    if batch:
        return {"batch_id": batch.id, "duplicate": True, "rows_count": 0}
    if datetime.fromisoformat(item.created_at) < datetime.now(UTC) - timedelta(hours=24):
        raise Problem(409, "PREVIEW_EXPIRED", "Повторите предпросмотр")
    if item.baseline_digest != baseline(session, career_id):
        raise Problem(409, "PREVIEW_STALE", "Данные изменились после предпросмотра; повторите его")
    collisions = conflicts(session, career_id, item.rows)
    if collisions and strategy != "replace":
        raise Problem(409, "IMPORT_CONFLICT", "Подтвердите замену конфликтующих строк", collisions)
    batch = ImportBatch(
        career_id=career_id,
        filename=item.filename,
        sha256=item.sha256,
        status="COMMITTED",
        stats={"rows": len(item.rows), "replaced": len(collisions)},
    )
    session.add(batch)
    session.flush()
    for row in item.rows:
        ss = season(session, career_id, row["year"])
        player = historical_player(session, career_id, row["name"])
        old = session.scalar(
            select(HistoricalStat).where(
                HistoricalStat.season_id == ss.id, HistoricalStat.player_id == player.id
            )
        )
        if not old:
            old = HistoricalStat(
                career_id=career_id, season_id=ss.id, player_id=player.id, source_batch_id=batch.id
            )
            session.add(old)
        for metric in METRICS:
            setattr(old, metric, row[metric])
        old.source_batch_id = batch.id
        meta = session.scalar(
            select(PlayerSeasonMetadata).where(
                PlayerSeasonMetadata.season_id == ss.id, PlayerSeasonMetadata.player_id == player.id
            )
        )
        if not meta:
            meta = PlayerSeasonMetadata(season_id=ss.id, player_id=player.id)
            session.add(meta)
        meta.position = row["position"]
    session.flush()
    return {"batch_id": batch.id, "duplicate": False, "rows_count": len(item.rows)}
