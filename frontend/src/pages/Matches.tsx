import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Camera, Goal, ListOrdered, ScanText, ShieldCheck } from "lucide-react";
import { api, fmt, type MatchDraft, type MatchEvidence } from "../shared/api";
import { Empty, Feedback } from "../shared/components";
import { useScope } from "../shared/context";

const statRows = [
  ["xG", "xg", 1],
  ["Владение", "possession", 0, "%"],
  ["Удары", "shots", 0],
  ["В створ", "shots_on_target", 0],
  ["Точность ударов", "shot_accuracy", 0, "%"],
  ["Пасы", "passes", 0],
  ["Точность пасов", "pass_accuracy", 0, "%"],
  ["Отборы", "tackles", 0],
  ["Успешные отборы", "tackles_won", 0],
  ["Перехваты", "interceptions", 0],
  ["Сейвы", "saves", 0],
  ["Фолы", "fouls", 0],
  ["Офсайды", "offsides", 0],
] as const;

const eventLabel = {
  goal: "Гол",
  substitution: "Замена",
  yellow: "ЖК",
  red: "КК",
  injury: "Травма",
};

export function Matches() {
  const { career, filters } = useScope();
  const queryString = new URLSearchParams();
  if (filters.season_id) queryString.set("season_id", String(filters.season_id));
  if (filters.competition_id)
    queryString.set("competition_id", String(filters.competition_id));
  if (filters.save_id) queryString.set("save_id", String(filters.save_id));
  const query = useQuery({
    queryKey: ["matches", career.id, filters],
    queryFn: () =>
      api<MatchEvidence[]>(`/careers/${career.id}/matches?${queryString}`),
  });
  const draftsQuery = useQuery({
    queryKey: ["match-drafts", career.id],
    queryFn: () => api<MatchDraft[]>(`/careers/${career.id}/match-drafts`),
    refetchInterval: 10_000,
  });
  const matches = query.data || [];
  const drafts = draftsQuery.data || [];
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">MATCH CENTRE</div>
          <h1>Матчи и послематчевая аналитика</h1>
          <p>Только подтверждённые скриншотами показатели и дельты сезонных счётчиков.</p>
        </div>
        <div className="form-strip" aria-label="Последние результаты">
          {matches.slice(0, 8).reverse().map((match) => (
            <span className={`form-${match.result?.toLowerCase()}`} key={match.id}>
              {match.result}
            </span>
          ))}
        </div>
      </div>
      <Feedback loading={query.isLoading} error={query.error} />
      <Feedback loading={draftsQuery.isLoading} error={draftsQuery.error} />
      {!!drafts.length && (
        <section className="panel ocr-drafts">
          <div className="panel-heading">
            <div>
              <h2><ScanText size={17} /> Черновики Windows OCR</h2>
              <p>Они не входят в W/D/L и сезонную статистику, пока вы их не проверили.</p>
            </div>
            <span className="pill">{drafts.length} на проверке</span>
          </div>
          {drafts.map((draft) => (
            <article className="ocr-draft" key={draft.id}>
              <div className="ocr-draft-score">
                <span>{draft.match.opponent_name || "Соперник не распознан"}</span>
                <strong>{fmt(draft.match.opponent_goals)} : {fmt(draft.match.club_goals)}</strong>
                <span>RB Salzburg</span>
              </div>
              <div className="ocr-draft-meta">
                <span>xG <strong>{fmt(draft.match.team_stats.xg, 1)}</strong></span>
                <span>Владение <strong>{fmt(draft.match.team_stats.possession)}%</strong></span>
                <span>Удары <strong>{fmt(draft.match.team_stats.shots)}</strong></span>
                <span>Игроки <strong>{draft.match.player_performances.length}</strong></span>
                <span>Кадры <strong>{draft.screenshot_urls.length}</strong></span>
              </div>
              <div className="ocr-warning">
                <AlertTriangle size={15} />
                <span>{draft.warnings.join(" ")}</span>
              </div>
              <div className="screenshot-grid ocr-preview">
                {draft.screenshot_urls.slice(0, 4).map((url, index) => (
                  <a href={url} target="_blank" rel="noreferrer" key={url}>
                    <img src={url} loading="lazy" alt={`OCR-кадр ${index + 1}`} />
                  </a>
                ))}
              </div>
            </article>
          ))}
        </section>
      )}
      {!query.isLoading && !query.error && !matches.length && <Empty />}
      {matches.map((match) => (
        <article className="match-card" key={match.id}>
          <header className="match-scoreboard">
            <div>
              <span className="eyebrow">{match.competition_name || "Турнир не указан"}</span>
              <strong>{match.club_was_home ? "RB Salzburg" : match.opponent_name}</strong>
            </div>
            <div className="match-score">
              <span>{match.club_was_home ? fmt(match.club_goals) : fmt(match.opponent_goals)}</span>
              <small>:</small>
              <span>{match.club_was_home ? fmt(match.opponent_goals) : fmt(match.club_goals)}</span>
              <em>{match.result}</em>
            </div>
            <div className="match-away">
              <span>{match.played_at || "Дата не указана"}</span>
              <strong>{match.club_was_home ? match.opponent_name : "RB Salzburg"}</strong>
            </div>
          </header>

          <div className="match-layout">
            <section className="panel match-stats">
              <div className="panel-heading">
                <h2><ShieldCheck size={17} /> Командная статистика</h2>
                <span className="pill">{match.duration_minutes ? `${match.duration_minutes} мин` : "90 мин"}</span>
              </div>
              <div className="stat-comparison stat-comparison-head">
                <strong>{match.opponent_name}</strong><span>Показатель</span><strong>RB Salzburg</strong>
              </div>
              {statRows.map(([label, key, digits, suffix = ""]) => (
                <div className="stat-comparison" key={key}>
                  <strong>{fmt(match.opponent_stats[key], digits)}{match.opponent_stats[key] != null ? suffix : ""}</strong>
                  <span>{label}</span>
                  <strong>{fmt(match.team_stats[key], digits)}{match.team_stats[key] != null ? suffix : ""}</strong>
                </div>
              ))}
            </section>

            <section className="panel match-timeline">
              <div className="panel-heading">
                <h2><ListOrdered size={17} /> Ход матча</h2>
                <span className="pill">{match.timeline.length} событий</span>
              </div>
              <div className="timeline-list">
                {match.timeline.map((event, index) => (
                  <div className={`timeline-event ${event.team}`} key={`${event.minute}-${event.player}-${index}`}>
                    <time>{event.minute}′</time>
                    <span className={`event-kind event-${event.kind}`}>
                      {event.kind === "goal" && <Goal size={13} />}{eventLabel[event.kind]}
                    </span>
                    <strong>{event.player}</strong>
                    {event.secondary_player && <small>↔ {event.secondary_player}</small>}
                  </div>
                ))}
              </div>
            </section>
          </div>

          <section className="panel match-players">
            <div className="panel-heading">
              <div><h2>Оценки игроков</h2><p>Рейтинг восстановлен из точной дельты avg ×10 и проверен по скриншотам.</p></div>
            </div>
            <div className="table-scroll">
              <table>
                <thead><tr><th>Игрок</th><th>Поз.</th><th>ОБЩ</th><th>Оценка</th><th>Голы</th><th>Ассисты</th><th>Статус</th></tr></thead>
                <tbody>
                  {[...match.player_performances]
                    .sort((a, b) => (b.rating || 0) - (a.rating || 0))
                    .map((player) => (
                      <tr key={player.external_player_id || player.name}>
                        <td><strong>{player.name}</strong>{player.motm && <span className="motm">MOTM</span>}</td>
                        <td>{player.position || "—"}</td><td>{fmt(player.overall)}</td>
                        <td><span className={`rating rating-${(player.rating || 0) >= 8 ? "high" : "normal"}`}>{fmt(player.rating, 1)}</span></td>
                        <td>{fmt(player.goals)}</td><td>{fmt(player.assists)}</td>
                        <td>{player.substitute ? "Со скамейки" : "Старт"}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </section>

          {!!match.screenshot_urls.length && (
            <section className="panel match-gallery">
              <div className="panel-heading">
                <div><h2><Camera size={17} /> Доказательства</h2><p>{match.evidence.note}</p></div>
                <span className="pill">{match.screenshot_urls.length} скриншотов</span>
              </div>
              <div className="screenshot-grid">
                {match.screenshot_urls.map((url, index) => (
                  <a href={url} target="_blank" rel="noreferrer" key={url}>
                    <img src={url} loading="lazy" alt={`Скриншот матча ${index + 1}`} />
                  </a>
                ))}
              </div>
            </section>
          )}
        </article>
      ))}
    </>
  );
}
