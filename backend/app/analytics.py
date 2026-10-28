from collections import defaultdict

from sqlalchemy import select

from .ingestion import latest_rows
from .models import (
    CareerSave,
    Competition,
    HistoricalStat,
    Player,
    PlayerSeasonMetadata,
    Season,
    Snapshot,
    SnapshotRow,
)
from .services import Problem, career

METRICS = ("appearances", "goals", "assists", "clean_sheets")


def total(values):
    values = list(values)
    return sum(values) if values and all(v is not None for v in values) else None


def records(
    session, career_id, season_id=None, competition_id=None, as_of=None, save_id=None, demo_mode=False
):
    career(session, career_id)
    seasons = session.scalars(
        select(Season).where(Season.career_id == career_id).order_by(Season.start_year)
    ).all()
    if season_id is not None:
        seasons = [s for s in seasons if s.id == season_id]
        if not seasons:
            raise Problem(404, "SEASON_NOT_FOUND", "Сезон не найден в этой карьере")
    saves = session.scalars(select(CareerSave).where(CareerSave.career_id == career_id)).all()
    if save_id is not None:
        saves = [s for s in saves if s.id == save_id]
        if not saves:
            raise Problem(404, "SAVE_NOT_FOUND", "Сохранение не найдено в этой карьере")
    chosen = saves[0] if len(saves) == 1 else None
    warnings = []
    if len(saves) > 1:
        warnings.append("Выберите сохранение: Live-данные разных saves не объединяются")
    external_comp = None
    if competition_id:
        comp = session.get(Competition, competition_id)
        observed = (
            session.scalar(
                select(SnapshotRow.id)
                .join(Snapshot)
                .join(CareerSave)
                .where(CareerSave.career_id == career_id, SnapshotRow.compobjid == comp.external_compobjid)
                .limit(1)
            )
            if comp
            else None
        )
        if not comp or observed is None:
            raise Problem(404, "COMPETITION_NOT_FOUND", "Турнир не найден")
        external_comp = comp.external_compobjid
    out = []
    last_synced = None
    for ss in seasons:
        historical = session.scalars(
            select(HistoricalStat).where(
                HistoricalStat.career_id == career_id, HistoricalStat.season_id == ss.id
            )
        ).all()
        use_history = bool(historical) and ss.source_policy != "live" and not competition_id
        if use_history:
            if as_of:
                warnings.append(
                    "Excel содержит сезонные итоги без внутрисезонных дат; as_of применяется только к Live"
                )
            for stat in historical:
                out.append(
                    {
                        "player_id": stat.player_id,
                        "season_id": ss.id,
                        "season": f"{ss.start_year}/{str(ss.end_year)[2:]}",
                        **{m: getattr(stat, m) for m in METRICS},
                        "source": "demo" if stat.coverage == "DEMO_SYNTHETIC" else "historical",
                        "data_quality": "demo" if stat.coverage == "DEMO_SYNTHETIC" else "historical_partial",
                        "coverage": stat.coverage,
                        "source_scope": stat.scope,
                    }
                )
            if chosen:
                warnings.append(f"{ss.start_year}: исторический TOTAL имеет приоритет; Live не прибавляется")
            continue
        if not chosen:
            continue
        live = latest_rows(session, chosen.id, chosen.active_branch_no, ss.id, as_of)
        grouped = defaultdict(list)
        for row, snap in live.values():
            if external_comp is None or row.compobjid == external_comp:
                grouped[row.player_id].append((row, snap))
        for player_id, pairs in grouped.items():
            complete = all(snap.completeness == "COMPLETE" for _, snap in pairs)
            # Synthetic totals are permitted only in the explicitly isolated demo application.
            allowed_total = external_comp is not None or (complete and (chosen.verified_live or demo_mode))
            if not allowed_total:
                warnings.append("Состав турниров не подтверждён: выберите турнир для Live-показателей")
            out.append(
                {
                    "player_id": player_id,
                    "season_id": ss.id,
                    "season": f"{ss.start_year}/{str(ss.end_year)[2:]}",
                    **{
                        m: total(getattr(row, m) for row, _ in pairs) if allowed_total else None
                        for m in METRICS
                    },
                    "source": "demo" if demo_mode else "live",
                    "data_quality": "demo"
                    if demo_mode
                    else "verified_live"
                    if chosen.verified_live
                    else "unknown",
                    "coverage": "DEMO_SYNTHETIC"
                    if demo_mode
                    else "COMPLETE"
                    if allowed_total and complete
                    else "PARTIAL_LIVE",
                    "source_scope": "COMPETITION"
                    if external_comp is not None
                    else "ALL_COMPETITIONS"
                    if allowed_total
                    else "UNKNOWN",
                    "observed_competitions": sorted({r.compobjid for r, _ in pairs}),
                }
            )
            last_synced = max([last_synced or "", *[snap.imported_at for _, snap in pairs]])
    return out, list(dict.fromkeys(warnings)), last_synced


def players(session, career_id, **filters):
    rows, warnings, synced = records(session, career_id, **filters)
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["player_id"]].append(row)
    result = []
    for player_id, history in grouped.items():
        player = session.get(Player, player_id)
        last = max(history, key=lambda x: x["season"])
        meta = session.scalar(
            select(PlayerSeasonMetadata).where(
                PlayerSeasonMetadata.player_id == player_id,
                PlayerSeasonMetadata.season_id == last["season_id"],
            )
        )
        sums = {m: total(h[m] for h in history) for m in METRICS}
        ga = (
            sums["goals"] + sums["assists"]
            if sums["goals"] is not None and sums["assists"] is not None
            else None
        )
        apps = sums["appearances"]
        result.append(
            {
                "id": player_id,
                "name": player.display_name,
                "position": meta.position if meta else None,
                **sums,
                "goal_contributions": ga,
                "goals_per_appearance": sums["goals"] / apps if apps and sums["goals"] is not None else None,
                "contributions_per_appearance": ga / apps if apps and ga is not None else None,
                "seasons_count": len({h["season_id"] for h in history}),
                "first_season": min(h["season"] for h in history),
                "last_season": max(h["season"] for h in history),
                "history": history,
                "rating": None,
                "overall": None,
                "potential": None,
                "sources": sorted({h["source"] for h in history}),
                "data_quality": sorted({h["data_quality"] for h in history}),
            }
        )
    observed_goals = total(p["goals"] for p in result)
    for player in result:
        player["observed_goals_share"] = (
            player["goals"] / observed_goals if observed_goals and player["goals"] is not None else None
        )
    return {
        "items": result,
        "warnings": warnings,
        "last_synced_at": synced,
        "source_scope": sorted({r["source_scope"] for r in rows}),
        "data_quality": sorted({r["data_quality"] for r in rows}),
    }


def competition_history(
    session,
    career_id,
    player_id,
    season_id=None,
    competition_id=None,
    as_of=None,
    save_id=None,
    demo_mode=False,
):
    query = select(CareerSave).where(CareerSave.career_id == career_id)
    if save_id is not None:
        query = query.where(CareerSave.id == save_id)
    saves = session.scalars(query).all()
    if len(saves) != 1:
        return []
    save = saves[0]
    query = select(Season).where(Season.career_id == career_id)
    if season_id is not None:
        query = query.where(Season.id == season_id)
    selected_comp = session.get(Competition, competition_id) if competition_id else None
    result = []
    for ss in session.scalars(query.order_by(Season.start_year)):
        for row, snap in latest_rows(session, save.id, save.active_branch_no, ss.id, as_of).values():
            if row.player_id != player_id or (
                selected_comp and row.compobjid != selected_comp.external_compobjid
            ):
                continue
            comp = session.scalar(
                select(Competition).where(
                    Competition.game_version == "EA FC 24", Competition.external_compobjid == row.compobjid
                )
            )
            result.append(
                {
                    "season": f"{ss.start_year}/{str(ss.end_year)[2:]}",
                    "competition": comp.name,
                    "compobjid": row.compobjid,
                    **{m: getattr(row, m) for m in METRICS},
                    "source": "demo" if demo_mode else "live",
                    "coverage": "DEMO_SYNTHETIC" if demo_mode else snap.completeness,
                }
            )
    return result


def dashboard(session, career_id, **filters):
    data = players(session, career_id, **filters)
    by_season = defaultdict(list)
    for player in data["items"]:
        for row in player["history"]:
            by_season[row["season"]].append(row)
    chart = [
        {"season": label, **{m: total(r[m] for r in rows) for m in METRICS}}
        for label, rows in sorted(by_season.items())
    ]
    return {
        **data,
        "kpis": {m: total(p[m] for p in data["items"]) for m in METRICS},
        "players_count": len(data["items"]),
        "seasons_count": len(chart),
        "chart": chart,
        "leaders": sorted(
            data["items"], key=lambda p: (p["goals"] is not None, p["goals"] or 0), reverse=True
        )[:5],
        "team_matches": None,
        "xg": None,
        "coverage": "ДЕМО: все показатели вымышленные"
        if filters.get("demo_mode")
        else "Неполная история: только учтённые строки источника",
    }
