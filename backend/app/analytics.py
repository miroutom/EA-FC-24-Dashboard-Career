from collections import defaultdict

from sqlalchemy import select

from .ingestion import latest_rows
from .models import (
    CareerSave,
    Competition,
    HistoricalStat,
    Match,
    Player,
    PlayerSeasonMetadata,
    PlayerStateSnapshot,
    Season,
    Snapshot,
    SnapshotRow,
    TeamStateSnapshot,
)
from .services import Problem, career

METRICS = ("appearances", "goals", "assists", "clean_sheets")
LIVE_COUNTERS = ("yellow", "two_yellow", "red", "saves", "goals_conceded", "motm")
TEAM_FORM_WARNING = (
    "FC 24: leagueteamlinks не содержит согласованную live-таблицу; W/D/L скрыты"
)


def total(values):
    values = list(values)
    return sum(values) if values and all(v is not None for v in values) else None


def live_context(session, career_id, season_id=None, save_id=None, as_of=None):
    saves = session.scalars(select(CareerSave).where(CareerSave.career_id == career_id)).all()
    if save_id is not None:
        saves = [save for save in saves if save.id == save_id]
    if len(saves) != 1:
        return None, None
    chosen = saves[0]
    if season_id is not None:
        selected_season = session.get(Season, season_id)
        if not selected_season or selected_season.career_id != career_id:
            return chosen, None
        return chosen, selected_season
    query = select(Snapshot.season_id).where(
        Snapshot.career_save_id == chosen.id,
        Snapshot.branch_no == chosen.active_branch_no,
    )
    if as_of:
        query = query.where(Snapshot.captured_at <= as_of)
    latest_season_id = session.scalar(
        query.order_by(Snapshot.captured_at.desc(), Snapshot.id.desc()).limit(1)
    )
    return chosen, session.get(Season, latest_season_id) if latest_season_id else None


def live_player_observations(
    session,
    career_id,
    season_id=None,
    competition_id=None,
    as_of=None,
    save_id=None,
):
    chosen, selected_season = live_context(session, career_id, season_id, save_id, as_of)
    if not chosen or not selected_season:
        return {}
    external_comp = None
    if competition_id is not None:
        competition = session.get(Competition, competition_id)
        if competition:
            external_comp = competition.external_compobjid

    grouped = defaultdict(list)
    for row, snap in latest_rows(
        session, chosen.id, chosen.active_branch_no, selected_season.id, as_of
    ).values():
        if external_comp is None or row.compobjid == external_comp:
            grouped[row.player_id].append((row, snap))

    result = {}
    for player_id, pairs in grouped.items():
        complete = all(snap.completeness == "COMPLETE" for _, snap in pairs)
        allowed_total = external_comp is not None or (complete and chosen.verified_live)
        latest_pair = max(pairs, key=lambda pair: (pair[1].captured_at, pair[1].id))
        result[player_id] = {
            **{
                metric: total(getattr(row, metric) for row, _ in pairs) if allowed_total else None
                for metric in LIVE_COUNTERS
            },
            "avg_raw": latest_pair[0].avg_raw if len(pairs) == 1 else None,
            "observed_at": latest_pair[1].in_game_date or latest_pair[1].captured_at,
            "data_quality": "experimental_live",
        }

    query = (
        select(PlayerStateSnapshot, Snapshot)
        .join(Snapshot, PlayerStateSnapshot.snapshot_id == Snapshot.id)
        .where(
            Snapshot.career_save_id == chosen.id,
            Snapshot.branch_no == chosen.active_branch_no,
            Snapshot.season_id == selected_season.id,
        )
    )
    if as_of:
        query = query.where(Snapshot.captured_at <= as_of)
    for state, snap in session.execute(query.order_by(Snapshot.captured_at, Snapshot.id)):
        current = result.setdefault(
            state.player_id,
            {
                **{metric: None for metric in LIVE_COUNTERS},
                "avg_raw": None,
                "data_quality": "experimental_live",
            },
        )
        current.update(
            {
                "injury_id": state.injury_id,
                "injury_date_raw": state.injury_date_raw,
                "injury_duration_days": state.injury_duration_days,
                "last_match_minutes": state.last_match_minutes,
                "last_match_overall": state.last_match_overall,
                "last_match_fact": state.last_match_fact,
                "last_match_position": state.last_match_position,
                "latest_match_rating_raw": state.latest_match_rating_raw,
                "latest_match_rating_minutes": state.latest_match_rating_minutes,
                "latest_match_rating_date_raw": state.latest_match_rating_date_raw,
                "observed_at": snap.in_game_date or snap.captured_at,
            }
        )
    return result


def _combined(row, home_field, away_field):
    home, away = getattr(row, home_field), getattr(row, away_field)
    return home + away if home is not None and away is not None else None


def team_form(session, career_id, season_id=None, as_of=None, save_id=None, **_filters):
    chosen, selected_season = live_context(session, career_id, season_id, save_id, as_of)
    if not chosen or not selected_season:
        return None
    query = (
        select(TeamStateSnapshot, Snapshot)
        .join(Snapshot, TeamStateSnapshot.snapshot_id == Snapshot.id)
        .where(
            Snapshot.career_save_id == chosen.id,
            Snapshot.branch_no == chosen.active_branch_no,
            Snapshot.season_id == selected_season.id,
        )
    )
    if as_of:
        query = query.where(Snapshot.captured_at <= as_of)
    observations = session.execute(query.order_by(Snapshot.captured_at, Snapshot.id)).all()
    if not observations:
        return None

    latest_by_league = {}
    previous_by_league = {}
    inferred = []
    warnings = []
    for state, snap in observations:
        league_id = state.league_external_id
        current_counts = (
            _combined(state, "home_wins", "away_wins"),
            _combined(state, "home_draws", "away_draws"),
            _combined(state, "home_losses", "away_losses"),
        )
        consistent = (
            state.matches_played is not None
            and all(value is not None for value in current_counts)
            and sum(current_counts) == state.matches_played
        )
        if not consistent:
            previous_by_league.pop(league_id, None)
            if TEAM_FORM_WARNING not in warnings:
                warnings.append(TEAM_FORM_WARNING)
            continue
        previous = previous_by_league.get(league_id)
        if (
            previous
            and state.matches_played is not None
            and previous[0] is not None
            and state.matches_played == previous[0] + 1
            and all(value is not None for value in (*current_counts, *previous[1]))
        ):
            deltas = tuple(current - old for current, old in zip(current_counts, previous[1]))
            if deltas.count(1) == 1 and deltas.count(0) == 2:
                inferred.append(
                    {
                        "result": ("W", "D", "L")[deltas.index(1)],
                        "league_id": league_id,
                        "observed_at": snap.in_game_date or snap.captured_at,
                        "source": "aggregate_delta",
                    }
                )
        previous_by_league[league_id] = (state.matches_played, current_counts)
        latest_by_league[league_id] = (state, snap)

    records = []
    for league_id, (state, snap) in latest_by_league.items():
        records.append(
            {
                "league_id": league_id,
                "matches_played": state.matches_played,
                "wins": _combined(state, "home_wins", "away_wins"),
                "draws": _combined(state, "home_draws", "away_draws"),
                "losses": _combined(state, "home_losses", "away_losses"),
                "goals_for": _combined(state, "home_goals_for", "away_goals_for"),
                "goals_against": _combined(state, "home_goals_against", "away_goals_against"),
                "points": state.points,
                "table_position": state.table_position,
                "observed_at": snap.in_game_date or snap.captured_at,
            }
        )
    records.sort(
        key=lambda row: (row["matches_played"] is not None, row["matches_played"] or -1), reverse=True
    )
    return {
        "season_id": selected_season.id,
        "records": records,
        "recent_results": inferred[-10:],
        "warnings": warnings,
        "coverage": "LEAGUE_AGGREGATES",
        "data_quality": "experimental_live",
    }


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
    live_by_player = live_player_observations(
        session,
        career_id,
        season_id=filters.get("season_id"),
        competition_id=filters.get("competition_id"),
        as_of=filters.get("as_of"),
        save_id=filters.get("save_id"),
    )
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
                "live": live_by_player.get(player_id),
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
    form = team_form(session, career_id, **filters)
    match_summary = verified_match_summary(session, career_id, **filters)
    if form and form["warnings"]:
        data["warnings"] = list(dict.fromkeys([*data["warnings"], *form["warnings"]]))
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
        "team_matches": match_summary,
        "xg": match_summary["avg_xg"] if match_summary else None,
        "team_form": form,
        "coverage": "ДЕМО: все показатели вымышленные"
        if filters.get("demo_mode")
        else "Неполная история: только учтённые строки источника",
    }


def verified_match_summary(session, career_id, **filters):
    query = select(Match).join(CareerSave).where(CareerSave.career_id == career_id)
    if filters.get("season_id") is not None:
        query = query.where(Match.season_id == filters["season_id"])
    if filters.get("save_id") is not None:
        query = query.where(Match.career_save_id == filters["save_id"])
    if filters.get("competition_id") is not None:
        competition = session.get(Competition, filters["competition_id"])
        if competition:
            query = query.where(Match.external_compobjid == competition.external_compobjid)
        else:
            return None
    if filters.get("as_of"):
        query = query.where(Match.played_at <= filters["as_of"][:10])
    rows = session.scalars(query.order_by(Match.played_at, Match.id)).all()
    if not rows:
        return None

    def average(key, side="team_stats"):
        values = [getattr(row, side).get(key) for row in rows]
        values = [value for value in values if value is not None]
        return sum(values) / len(values) if values else None

    wins = sum(row.result == "W" for row in rows)
    draws = sum(row.result == "D" for row in rows)
    losses = sum(row.result == "L" for row in rows)
    points = wins * 3 + draws
    return {
        "matches": len(rows),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": sum(row.club_goals or 0 for row in rows),
        "goals_against": sum(row.opponent_goals or 0 for row in rows),
        "points": points,
        "points_per_game": points / len(rows),
        "avg_xg": average("xg"),
        "avg_xga": average("xg", "opponent_stats"),
        "avg_possession": average("possession"),
        "recent_results": [
            {
                "result": row.result,
                "played_at": row.played_at,
                "opponent": row.opponent_name,
                "club_goals": row.club_goals,
                "opponent_goals": row.opponent_goals,
            }
            for row in rows[-8:]
        ],
        "coverage": "SCREENSHOT_VERIFIED_MANUAL",
    }
