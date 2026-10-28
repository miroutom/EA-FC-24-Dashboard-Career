import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, Check, Link2, RefreshCw, StickyNote } from "lucide-react";
import { useState } from "react";
import { Button } from "../components/ui/button";
import {
  api,
  fetchPlayers,
  date,
  post,
  type Delta,
  type Season,
  type Sync as SyncDTO,
} from "../shared/api";
import { Empty, Feedback } from "../shared/components";
import { useScope } from "../shared/context";

export function Sync() {
  const { career, filters } = useScope();
  const client = useQueryClient();
  const [key, setKey] = useState<string>(() => crypto.randomUUID());
  const [uid, setUid] = useState("");
  const [text, setText] = useState("");
  const [interval, setIntervalId] = useState("");
  const [policyAck, setPolicyAck] = useState(false);
  const [pid, setPid] = useState("");
  const [external, setExternal] = useState("");
  const [identityAck, setIdentityAck] = useState(false);
  const query = useQuery({
    queryKey: ["sync", career.id],
    queryFn: () => api<SyncDTO>(`/careers/${career.id}/sync/status`),
  });
  const events = useQuery({
    queryKey: ["events", career.id],
    queryFn: () =>
      api<
        {
          id: number;
          action: string;
          message: string;
          time: string;
          level: string;
        }[]
      >(`/careers/${career.id}/sync/events`),
  });
  const snapshots = useQuery({
    queryKey: ["snapshots", career.id],
    queryFn: () =>
      api<
        {
          id: number;
          branch_no: number;
          status: string;
          captured_at: string;
          source_version: string;
        }[]
      >(`/careers/${career.id}/snapshots`),
  });
  const changes = useQuery({
    queryKey: ["changes", career.id],
    queryFn: () => api<Delta[]>(`/careers/${career.id}/changes`),
  });
  const notes = useQuery({
    queryKey: ["notes", career.id],
    queryFn: () =>
      api<
        {
          id: number;
          text: string;
          created_at: string;
          interval_id: number | null;
        }[]
      >(`/careers/${career.id}/notes`),
  });
  const seasons = useQuery({
    queryKey: ["seasons", career.id],
    queryFn: () => api<Season[]>(`/careers/${career.id}/seasons`),
  });
  const players = useQuery({
    queryKey: ["identity-players", career.id],
    queryFn: () => fetchPlayers(career.id),
  });
  const invalidate = () => {
    void client.invalidateQueries();
  };
  const bind = useMutation({
    mutationFn: () =>
      post(`/careers/${career.id}/saves/bind`, {
        instance_key: key,
        external_save_uid: uid || null,
      }),
    onSuccess: invalidate,
  });
  const retry = useMutation({
    mutationFn: () => post(`/careers/${career.id}/sync/retry`, {}),
    onSuccess: invalidate,
  });
  const resolve = useMutation({
    mutationFn: ({ id, strategy }: { id: number; strategy: string }) =>
      post(`/careers/${career.id}/saves/${id}/resolve`, { strategy }),
    onSuccess: invalidate,
  });
  const note = useMutation({
    mutationFn: () =>
      post(`/careers/${career.id}/notes`, {
        text,
        interval_id: interval ? Number(interval) : null,
      }),
    onSuccess: () => {
      setText("");
      invalidate();
    },
  });
  const policy = useMutation({
    mutationFn: (value: string) =>
      post(`/careers/${career.id}/seasons/${filters.season_id}/policy`, {
        source_policy: value,
        acknowledged: true,
      }),
    onSuccess: () => {
      setPolicyAck(false);
      invalidate();
    },
  });
  const identity = useMutation({
    mutationFn: () =>
      post(`/careers/${career.id}/players/${pid}/identity`, {
        external_player_id: Number(external),
        confirmed: true,
      }),
    onSuccess: () => {
      setIdentityAck(false);
      invalidate();
    },
  });
  const d = query.data;
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">LOCAL DATA PIPELINE</div>
          <h1>Связь с вашей карьерой</h1>
          <p>Локальный сбор, прозрачные источники, сохранённая история.</p>
        </div>
        <Button
          variant="outline"
          onClick={() => retry.mutate()}
          disabled={retry.isPending}
        >
          <RefreshCw size={16} /> Повторить очередь
        </Button>
      </div>
      <Feedback loading={query.isLoading} error={query.error} />
      <Feedback
        error={
          bind.error ||
          retry.error ||
          resolve.error ||
          note.error ||
          policy.error ||
          identity.error
        }
      />
      {d && (
        <>
          <div className="sync-banner">
            <Activity size={24} />
            <div>
              <strong>Collector: {d.collector}</strong>
              <p>
                {d.connected
                  ? "Есть свежие локальные снимки"
                  : "Нет свежих снимков"}{" "}
                · Последняя синхронизация: {date(d.last_synced_at)}
              </p>
            </div>
            <span className={`pill ${d.connected ? "green" : "amber"}`}>
              {d.connected ? "Свежие данные" : "Ожидание"}
            </span>
          </div>
          <div className="two-columns">
            <section className="panel">
              <h2>
                <Link2 size={18} /> Привязка сохранения
              </h2>
              <p className="muted">
                Один раз свяжите конкретный save с карьерой. Перед переключением
                save меняйте его конфигурацию коллектора. Автоматических догадок
                нет.
              </p>
              {d.saves.map((s) => (
                <div className="save-card" key={s.id}>
                  <strong>
                    Save #{s.id} · ветка {s.active_branch_no}
                  </strong>
                  <code>{s.instance_key}</code>
                  <span className="pill">{s.status}</span>
                  {s.status === "CONFLICT" && (
                    <>
                      <p>
                        Счётчики уменьшились или нарушен порядок. Предыдущая
                        история сохранена. Выбор новой ветки заменит
                        Live-представление.
                      </p>
                      <Button
                        onClick={() =>
                          resolve.mutate({ id: s.id, strategy: "adopt" })
                        }
                      >
                        Принять новую ветку
                      </Button>{" "}
                      <Button
                        variant="outline"
                        onClick={() =>
                          resolve.mutate({ id: s.id, strategy: "reject" })
                        }
                      >
                        Сохранить прежнюю
                      </Button>
                    </>
                  )}
                </div>
              ))}
              <form
                className="form-stack"
                onSubmit={(e) => {
                  e.preventDefault();
                  bind.mutate();
                }}
              >
                <label className="field">
                  instance_key
                  <input
                    required
                    minLength={8}
                    pattern="[a-zA-Z0-9_-]+"
                    value={key}
                    onChange={(e) => setKey(e.target.value)}
                  />
                </label>
                <label className="field">
                  Save UID, только если подтверждён
                  <input
                    value={uid}
                    onChange={(e) => setUid(e.target.value)}
                    placeholder="Необязательно"
                  />
                </label>
                <Button disabled={bind.isPending}>Связать save</Button>
              </form>
            </section>
            <section className="panel">
              <h2>Диагностика синхронизации</h2>
              <dl className="diagnostics">
                <div>
                  <dt>Watcher</dt>
                  <dd>{d.watcher.enabled ? "Включён" : "Выключен"}</dd>
                </div>
                <div>
                  <dt>Последнее сканирование</dt>
                  <dd>{date(d.watcher.last_scan)}</dd>
                </div>
                <div>
                  <dt>Не назначены карьере</dt>
                  <dd>{d.unassigned_count}</dd>
                </div>
                {Object.entries(d.counts).map(([k, v]) => (
                  <div key={k}>
                    <dt>{k}</dt>
                    <dd>{v}</dd>
                  </div>
                ))}
                {Object.entries(d.unassigned_counts || {}).map(([k, v]) => (
                  <div key={`unassigned-${k}`}>
                    <dt>Без привязки: {k}</dt>
                    <dd>{v}</dd>
                  </div>
                ))}
                {Object.entries(d.capabilities).map(([k, v]) => (
                  <div key={k}>
                    <dt>{k}</dt>
                    <dd className="amber-text">{v}</dd>
                  </div>
                ))}
              </dl>
              {d.unassigned_errors?.map((e) => (
                <div className="alert" key={e.id}>
                  {e.action}: {e.message}
                </div>
              ))}
              {d.watcher.error && (
                <div className="alert">{d.watcher.error}</div>
              )}
              <div className="unavailable">
                P0/P2 требуют реальной проверки Windows + EA FC 24. Тестовые
                JSON подтверждают обработку файлов, но не проверку игры.
                Инструкция: docs/manual-game-validation.md
              </div>
            </section>
          </div>
          <section className="panel">
            <h2>История снимков</h2>
            {snapshots.data?.length ? (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Снимок</th>
                      <th>Время</th>
                      <th>Ветка</th>
                      <th>Статус</th>
                      <th>Коллектор</th>
                    </tr>
                  </thead>
                  <tbody>
                    {snapshots.data.map((s) => (
                      <tr key={s.id}>
                        <td>#{s.id}</td>
                        <td>{date(s.captured_at)}</td>
                        <td>{s.branch_no}</td>
                        <td>{s.status}</td>
                        <td>{s.source_version}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <Empty title="Снимков ещё нет">
                Watcher автоматически обработает snapshot_v1 JSON в
                DATA_DIR/spool.
              </Empty>
            )}
          </section>
          <div className="two-columns">
            <section className="panel">
              <h2>
                <StickyNote size={18} /> Заметки по желанию
              </h2>
              <form
                className="form-stack"
                onSubmit={(e) => {
                  e.preventDefault();
                  note.mutate();
                }}
              >
                <select
                  aria-label="Интервал заметки"
                  value={interval}
                  onChange={(e) => setIntervalId(e.target.value)}
                >
                  <option value="">Общая заметка о периоде</option>
                  {changes.data?.map((c) => (
                    <option value={c.id} key={c.id}>
                      Между #{c.previous_snapshot_id} и #{c.next_snapshot_id},
                      игрок #{c.player_id}
                    </option>
                  ))}
                </select>
                <textarea
                  aria-label="Текст заметки"
                  required
                  maxLength={5000}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="Что запомнилось в этой части карьеры?"
                />
                <Button disabled={note.isPending || !text.trim()}>
                  Сохранить заметку
                </Button>
              </form>
              {notes.data?.map((n) => (
                <article className="note" key={n.id}>
                  <small>
                    {date(n.created_at)}
                    {n.interval_id && ` · интервал #${n.interval_id}`}
                  </small>
                  <p>{n.text}</p>
                </article>
              ))}
            </section>
            <section className="panel">
              <h2>Журнал событий</h2>
              {events.data?.length ? (
                events.data.slice(0, 15).map((e) => (
                  <article className="event" key={e.id}>
                    <Check size={15} />
                    <div>
                      <strong>{e.action}</strong>
                      <p>{e.message}</p>
                      <small>{date(e.time)}</small>
                    </div>
                  </article>
                ))
              ) : (
                <p className="muted">События появятся после приёма файлов.</p>
              )}
            </section>
          </div>
          <section className="panel">
            <details>
              <summary>Сопоставление истории и Live-источника</summary>
              <p className="muted">
                Выбор Live вместо исторического TOTAL заменяет представление
                сезона, не складывает источники. Сначала проверьте полноту
                турниров и соответствие игроков.
              </p>
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={policyAck}
                  onChange={(e) => setPolicyAck(e.target.checked)}
                />
                Подтверждаю соответствие и проверку источников выбранного сезона
              </label>
              <p>
                Сезон:{" "}
                {seasons.data?.find((s) => s.id === filters.season_id)
                  ?.start_year || "Выберите один сезон вверху"}
              </p>
              <Button
                disabled={!policyAck || !filters.season_id}
                onClick={() => policy.mutate("live")}
              >
                Использовать Live
              </Button>{" "}
              <Button
                variant="outline"
                disabled={!policyAck || !filters.season_id}
                onClick={() => policy.mutate("historical_first")}
              >
                Использовать историю
              </Button>
              <h3>Явное сопоставление игрока</h3>
              <div className="form-stack">
                <select
                  aria-label="Исторический игрок"
                  value={pid}
                  onChange={(e) => setPid(e.target.value)}
                >
                  <option value="">Выберите исторического игрока</option>
                  {players.data?.items
                    .filter((p) => p.sources.includes("historical"))
                    .map((p) => (
                      <option value={p.id} key={p.id}>
                        {p.name}
                      </option>
                    ))}
                </select>
                <input
                  type="number"
                  min={0}
                  aria-label="ID игрока в игре"
                  placeholder="Фактический playerid из игры"
                  value={external}
                  onChange={(e) => setExternal(e.target.value)}
                />
                <label className="checkbox">
                  <input
                    type="checkbox"
                    checked={identityAck}
                    onChange={(e) => setIdentityAck(e.target.checked)}
                  />
                  Подтверждаю, что это один и тот же игрок
                </label>
                <Button
                  disabled={!identityAck || !pid || external === ""}
                  onClick={() => identity.mutate()}
                >
                  Связать ID игрока
                </Button>
              </div>
            </details>
          </section>
        </>
      )}
    </>
  );
}
