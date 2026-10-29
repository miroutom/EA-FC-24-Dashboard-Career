import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Trophy } from "lucide-react";
import { Link } from "react-router-dom";
import { api, type Dashboard, fmt, params } from "../shared/api";
import { Empty, Feedback, Kpi, Quality, Trend } from "../shared/components";
import { useScope } from "../shared/context";
import { StatsCharts } from "../features/analytics/StatsCharts";

export function Summary() {
  const { career, filters, selectPlayer } = useScope();
  const query = useQuery({
    queryKey: ["dashboard", career.id, filters],
    queryFn: () =>
      api<Dashboard>(`/careers/${career.id}/dashboard?${params(filters)}`),
  });
  const d = query.data;
  const teamRecord = d?.team_form?.records[0];
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">CAREER INTELLIGENCE</div>
          <h1>Вся карьера. В деталях.</h1>
          <p>История игроков, результативность и движение вперёд.</p>
        </div>
        <span className="pill">EA SPORTS FC 24</span>
      </div>
      <Feedback loading={query.isLoading} error={query.error} />
      {d &&
        (d.items.length ? (
          <>
            <div className="kpis">
              <Kpi
                label="Учтённых игроков"
                value={d.players_count}
                detail={`${d.seasons_count} учтённых сезонов`}
              />
              <Kpi
                label="Голы игроков"
                value={d.kpis.goals}
                detail="Без гарантии учёта автоголов"
              />
              <Kpi label="Голевые передачи" value={d.kpis.assists} />
              <Kpi
                label="Выступления игроков"
                value={d.kpis.appearances}
                detail="Сумма выступлений, не матчей клуба"
              />
            </div>
            <Quality
              warnings={d.warnings}
              demo={d.data_quality.includes("demo")}
            />
            {d.team_matches && (
              <section className="panel">
                <div className="panel-heading">
                  <div>
                    <h2>Подтверждённая форма</h2>
                    <p>Только матчи с явной карточкой и сохранёнными доказательствами</p>
                  </div>
                  <span className="pill">{d.team_matches.coverage}</span>
                </div>
                <div className="kpis">
                  <Kpi label="Матчи" value={d.team_matches.matches} />
                  <Kpi label="Победы" value={d.team_matches.wins} />
                  <Kpi label="Ничьи" value={d.team_matches.draws} />
                  <Kpi label="Поражения" value={d.team_matches.losses} />
                </div>
                <div className="verified-form-row">
                  <div className="form-strip">
                    {d.team_matches.recent_results.map((result, index) => (
                      <span className={`form-${result.result.toLowerCase()}`} key={`${result.played_at}-${index}`} title={`${result.opponent}: ${fmt(result.club_goals)}–${fmt(result.opponent_goals)}`}>
                        {result.result}
                      </span>
                    ))}
                  </div>
                  <p className="muted">
                    Голы {d.team_matches.goals_for}–{d.team_matches.goals_against} · xG {fmt(d.team_matches.avg_xg, 1)} · владение {fmt(d.team_matches.avg_possession)}%
                  </p>
                  <Link to="/matches">Открыть матчи <ArrowRight size={15} /></Link>
                </div>
              </section>
            )}
            {teamRecord && (
              <section className="panel">
                <div className="panel-heading">
                  <div>
                    <h2>Форма команды</h2>
                    <p>
                      Экспериментальные агрегаты лиги · ID{" "}
                      {teamRecord.league_id}
                    </p>
                  </div>
                  <span className="pill">{d.team_form?.coverage}</span>
                </div>
                <div className="kpis">
                  <Kpi label="Матчи" value={teamRecord.matches_played} />
                  <Kpi label="Победы" value={teamRecord.wins} />
                  <Kpi label="Ничьи" value={teamRecord.draws} />
                  <Kpi label="Поражения" value={teamRecord.losses} />
                </div>
                <p className="muted">
                  Голы: {fmt(teamRecord.goals_for)}–
                  {fmt(teamRecord.goals_against)} · Очки:{" "}
                  {fmt(teamRecord.points)} · Место:{" "}
                  {fmt(teamRecord.table_position)}
                </p>
                {!!d.team_form?.recent_results.length && (
                  <div
                    className="player-badges"
                    aria-label="Последние подтверждённые результаты"
                  >
                    {d.team_form.recent_results.map((result, index) => (
                      <span
                        className="pill"
                        key={`${result.league_id}-${result.observed_at}-${index}`}
                        title="Выведено из изменения сезонных W/D/L между соседними снимками"
                      >
                        {result.result}
                      </span>
                    ))}
                  </div>
                )}
              </section>
            )}
            <div className="dashboard-grid">
              <section className="panel">
                <div className="panel-heading">
                  <div>
                    <h2>Сезонная динамика</h2>
                    <p>Результативность учтённых игроков</p>
                  </div>
                  <div className="legend">
                    <span className="blue-dot" />
                    Голы <span className="green-dot" />
                    Ассисты
                  </div>
                </div>
                <Trend data={d.chart} />
              </section>
              <section className="panel leaders">
                <div className="panel-heading">
                  <h2>
                    <Trophy size={17} /> Лидеры по голам
                  </h2>
                  <Link to="/squad" aria-label="Вся таблица">
                    <ArrowRight size={17} />
                  </Link>
                </div>
                {d.leaders.map((p, i) => (
                  <button
                    key={p.id}
                    className="leader"
                    onClick={() => selectPlayer(p.id)}
                  >
                    <span className="rank">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span className="avatar">
                      {p.name
                        .split(" ")
                        .filter(Boolean)
                        .map((n) => n[0])
                        .slice(-2)
                        .join("")}
                    </span>
                    <span className="leader-name">
                      {p.name}
                      <small>
                        {p.position || "Позиция неизвестна"} · {p.seasons_count}{" "}
                        сез.
                      </small>
                    </span>
                    <strong>{fmt(p.goals)}</strong>
                  </button>
                ))}
              </section>
            </div>
            <StatsCharts players={d.items} />
            <section className="panel">
              <div className="panel-heading">
                <h2>История по сезонам</h2>
                <span className="muted">Источники и охват сохранены</span>
              </div>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Сезон</th>
                      <th>Выступления игроков</th>
                      <th>Голы</th>
                      <th>Ассисты</th>
                    </tr>
                  </thead>
                  <tbody>
                    {d.chart.map((row) => (
                      <tr key={row.season}>
                        <td>
                          <span className="season-chip">{row.season}</span>
                        </td>
                        <td>{fmt(row.appearances)}</td>
                        <td>{fmt(row.goals)}</td>
                        <td>{fmt(row.assists)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
            <div className="unavailable">
              Подтверждённые результаты, xG, владение, события и оценки доступны в разделе <Link to="/matches">«Матчи»</Link>.
            </div>
            <div className="unavailable" style={{ display: "none" }}>
              Поматчевые данные недоступны. Результаты, соперники, xG и владение
              появятся только при наличии подтверждённого источника.
            </div>
          </>
        ) : (
          <Empty />
        ))}
    </>
  );
}
