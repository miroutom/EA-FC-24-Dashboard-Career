import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { Sheet } from "../components/ui/sheet";
import { api, fmt, params, type Player as PlayerDTO } from "../shared/api";
import { Empty, Feedback, Kpi, Trend } from "../shared/components";
import { useScope } from "../shared/context";

function PlayerContent({ player }: { player: PlayerDTO }) {
  return (
    <>
      {player.history.length ? (
        <>
          <div className="player-badges">
            <span className="pill">{player.position || "Позиция —"}</span>
            <span className="pill">
              {player.sources?.join(" + ") || "Источник неизвестен"}
            </span>
          </div>
          <div className="kpis player-kpis">
            <Kpi label="Выступления" value={player.appearances} />
            <Kpi label="Голы" value={player.goals} />
            <Kpi label="Ассисты" value={player.assists} />
            <Kpi label="Г+П" value={player.goal_contributions} />
          </div>
          {player.live && (
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h3>Live-состояние игрока</h3>
                  <p>
                    Экспериментальные поля FC 24; значения не пересчитываются
                    вручную
                  </p>
                </div>
                <span className="pill">experimental</span>
              </div>
              <div className="kpis player-kpis">
                <Kpi label="Жёлтые" value={player.live.yellow} />
                <Kpi label="2ЖК" value={player.live.two_yellow} />
                <Kpi label="Красные" value={player.live.red} />
                <Kpi label="Игрок матча" value={player.live.motm} />
                <Kpi label="Сейвы" value={player.live.saves} />
                <Kpi label="Пропущено" value={player.live.goals_conceded} />
              </div>
              <p className="muted">
                Последний матч: {fmt(player.live.last_match_minutes)} мин. ·
                OVR-снимок: {fmt(player.live.last_match_overall)} · оценка raw:{" "}
                {fmt(player.live.latest_match_rating_raw)} · минут в истории
                оценки: {fmt(player.live.latest_match_rating_minutes)}
              </p>
              <p className="muted">
                Травма raw ID: {fmt(player.live.injury_id)} · длительность:{" "}
                {fmt(player.live.injury_duration_days)} дн. · дата raw:{" "}
                {fmt(player.live.injury_date_raw)}
              </p>
            </section>
          )}
          <p className="muted">
            {player.seasons_count} учтённых сезонов · {player.first_season} —{" "}
            {player.last_season}
          </p>
          <Trend data={player.history} />
          <p className="muted">
            Доля голов среди учтённых игроков:{" "}
            {player.observed_goals_share == null
              ? "—"
              : `${fmt(player.observed_goals_share * 100, 1)}%`}
            . Это доля в доступных данных, не гарантированно полный вклад в голы
            клуба.
          </p>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Сезон</th>
                  <th>Выст.</th>
                  <th>Г</th>
                  <th>А</th>
                  <th>Источник</th>
                </tr>
              </thead>
              <tbody>
                {player.history.map((row) => (
                  <tr key={row.season_id}>
                    <td>{row.season}</td>
                    <td>{fmt(row.appearances)}</td>
                    <td>{fmt(row.goals)}</td>
                    <td>{fmt(row.assists)}</td>
                    <td>
                      <span className="pill">{row.source}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!!player.competition_history?.length && (
            <>
              <h3 className="mt-6 mb-3">Live: по турнирам</h3>
              <p className="muted">
                Отдельный источник; эти значения не добавляются к историческим
                итогам.
              </p>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Сезон</th>
                      <th>Турнир</th>
                      <th>Выст.</th>
                      <th>Г</th>
                      <th>А</th>
                    </tr>
                  </thead>
                  <tbody>
                    {player.competition_history.map((r) => (
                      <tr key={`${r.season}-${r.compobjid}`}>
                        <td>{r.season}</td>
                        <td>{r.competition}</td>
                        <td>{fmt(r.appearances)}</td>
                        <td>{fmt(r.goals)}</td>
                        <td>{fmt(r.assists)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
          <div className="unavailable">
            OVR: — · Потенциал: — · Оценка: —<br />
            Данные развития и индивидуальные оценки пока недоступны. История
            может быть неполной.
          </div>
        </>
      ) : (
        <Empty title="Нет показателей в выбранных фильтрах" />
      )}
    </>
  );
}
export function PlayerDrawer() {
  const { career, filters, selected, selectPlayer } = useScope();
  const query = useQuery({
    queryKey: ["player", career.id, selected, filters],
    queryFn: () =>
      api<PlayerDTO>(
        `/careers/${career.id}/players/${selected}?${params(filters)}`,
      ),
    enabled: selected !== null,
  });
  return (
    <Sheet
      open={selected !== null}
      onClose={() => selectPlayer(null)}
      title={query.data?.name || "Игрок"}
    >
      <Feedback loading={query.isLoading} error={query.error} />
      {query.data && (
        <>
          <PlayerContent player={query.data} />
          <Link
            className="profile-link"
            to={`/players/${query.data.id}`}
            onClick={() => selectPlayer(null)}
          >
            Открыть полный профиль →
          </Link>
        </>
      )}
    </Sheet>
  );
}
export function PlayerProfile() {
  const { id } = useParams();
  const { career, filters } = useScope();
  const query = useQuery({
    queryKey: ["player", career.id, id, filters],
    queryFn: () =>
      api<PlayerDTO>(`/careers/${career.id}/players/${id}?${params(filters)}`),
  });
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">PLAYER HISTORY</div>
          <h1>{query.data?.name || "Профиль игрока"}</h1>
        </div>
      </div>
      <Feedback loading={query.isLoading} error={query.error} />
      {query.data && (
        <section className="panel">
          <PlayerContent player={query.data} />
        </section>
      )}
    </>
  );
}
