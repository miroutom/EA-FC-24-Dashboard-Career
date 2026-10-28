import { useQuery } from "@tanstack/react-query";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from "@tanstack/react-table";
import { Search } from "lucide-react";
import { useMemo, useState } from "react";
import {
  api,
  fetchPlayers,
  type Delta,
  fmt,
  type Player,
  params,
} from "../shared/api";
import { Empty, Feedback, Quality, Trend } from "../shared/components";
import { useScope } from "../shared/context";

const helper = createColumnHelper<Player>();
export function Squad() {
  const { career, filters, selectPlayer } = useScope();
  const [tab, setTab] = useState("table");
  const [search, setSearch] = useState("");
  const [position, setPosition] = useState("");
  const [sorting, setSorting] = useState<SortingState>([
    { id: "goals", desc: true },
  ]);
  const query = useQuery({
    queryKey: ["players", career.id, filters],
    queryFn: () => fetchPlayers(career.id, filters),
  });
  const changes = useQuery({
    queryKey: ["changes", career.id, filters.season_id],
    queryFn: () =>
      api<Delta[]>(
        `/careers/${career.id}/changes?${params({ season_id: filters.season_id })}`,
      ),
    enabled: tab === "updates",
  });
  const columns = useMemo(
    () => [
      helper.accessor("name", {
        header: "Игрок",
        cell: (c) => (
          <button
            className="player-link"
            onClick={() => selectPlayer(c.row.original.id)}
          >
            <span className="avatar small">
              {c.getValue().split(" ").at(-1)?.slice(0, 2)}
            </span>
            {c.getValue()}
          </button>
        ),
      }),
      ...(
        [
          ["position", "Поз."],
          ["seasons_count", "Сезоны"],
          ["appearances", "Выступления"],
          ["goals", "Голы"],
          ["assists", "Ассисты"],
          ["goal_contributions", "Г+П"],
          ["clean_sheets", "Сухие"],
          ["goals_per_appearance", "Г/выст."],
          ["contributions_per_appearance", "Г+П/выст."],
        ] as const
      ).map(([key, title]) =>
        helper.accessor(key, {
          header: title,
          cell: (c) =>
            typeof c.getValue() === "string"
              ? c.getValue()
              : fmt(c.getValue() as number | null, 2),
          sortUndefined: "last",
        }),
      ),
    ],
    [selectPlayer],
  );
  const data = useMemo(
    () =>
      (query.data?.items || []).filter(
        (p) => !position || p.position === position,
      ),
    [query.data, position],
  );
  const table = useReactTable({
    data,
    columns,
    state: { globalFilter: search, sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">SQUAD ANALYTICS</div>
          <h1>Игроки делают историю.</h1>
          <p>Учтённые футболисты карьеры, включая покинувших клуб.</p>
        </div>
        <span className="pill">{query.data?.total || 0} игроков</span>
      </div>
      <div className="tabs">
        {[
          ["table", "Таблица"],
          ["overview", "Обзор"],
          ["updates", "Обновления"],
        ].map(([id, label]) => (
          <button
            key={id}
            className={tab === id ? "active" : ""}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>
      <Feedback loading={query.isLoading} error={query.error} />
      {tab === "updates" ? (
        <>
          <Feedback loading={changes.isLoading} error={changes.error} />
          {changes.data?.length ? (
            <section className="panel">
              <h2>Между снимками</h2>
              {changes.data.map((d) => (
                <div className="change-row" key={d.id}>
                  <span>
                    #{d.previous_snapshot_id} → #{d.next_snapshot_id} · игрок #
                    {d.player_id}
                  </span>
                  <span>
                    Голы: {fmt(d.values.goals)} · ассисты:{" "}
                    {fmt(d.values.assists)}
                  </span>
                  <span className="pill">{d.confidence}</span>
                </div>
              ))}
            </section>
          ) : (
            <Empty title="Сборщик ещё не передавал изменений">
              После подключения Live Editor здесь появятся изменения за период
              между снимками.
            </Empty>
          )}
        </>
      ) : query.data?.items.length ? (
        tab === "overview" ? (
          <div className="overview-cards">
            {(["goals", "assists", "appearances"] as const).map(
              (key, index) => (
                <section className="panel" key={key}>
                  <h2>{["Голы", "Ассисты", "Выступления"][index]}</h2>
                  {[...query.data!.items]
                    .sort((a, b) => (b[key] ?? -1) - (a[key] ?? -1))
                    .slice(0, 5)
                    .map((p) => (
                      <button
                        className="leader"
                        key={p.id}
                        onClick={() => selectPlayer(p.id)}
                      >
                        <span className="leader-name">{p.name}</span>
                        <strong>{fmt(p[key])}</strong>
                      </button>
                    ))}
                </section>
              ),
            )}
            <section className="panel wide">
              <h2>Динамика лидера по голам</h2>
              <Trend
                data={
                  [...query.data.items].sort(
                    (a, b) => (b.goals ?? -1) - (a.goals ?? -1),
                  )[0].history
                }
              />
            </section>
          </div>
        ) : (
          <section className="panel">
            <div className="table-toolbar">
              <label className="search">
                <Search size={17} />
                <input
                  aria-label="Поиск игрока"
                  placeholder="Найти игрока…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </label>
              <select
                aria-label="Позиция"
                value={position}
                onChange={(e) => setPosition(e.target.value)}
              >
                <option value="">Все позиции</option>
                {[
                  ...new Set(
                    query.data.items.map((p) => p.position).filter(Boolean),
                  ),
                ]
                  .sort()
                  .map((p) => (
                    <option key={p}>{p}</option>
                  ))}
              </select>
            </div>
            <div className="table-scroll">
              <table>
                <thead>
                  {table.getHeaderGroups().map((g) => (
                    <tr key={g.id}>
                      {g.headers.map((h) => (
                        <th key={h.id}>
                          <button onClick={h.column.getToggleSortingHandler()}>
                            {flexRender(
                              h.column.columnDef.header,
                              h.getContext(),
                            )}{" "}
                            {h.column.getIsSorted() === "desc"
                              ? "↓"
                              : h.column.getIsSorted() === "asc"
                                ? "↑"
                                : ""}
                          </button>
                        </th>
                      ))}
                    </tr>
                  ))}
                </thead>
                <tbody>
                  {table.getRowModel().rows.map((row) => (
                    <tr key={row.id}>
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id}>
                          {flexRender(
                            cell.column.columnDef.cell,
                            cell.getContext(),
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {!table.getRowModel().rows.length && (
                <Empty title="Игроки не найдены">
                  Измените поиск или фильтр позиции.
                </Empty>
              )}
            </div>
            <Quality warnings={query.data.warnings} />
          </section>
        )
      ) : (
        query.data && <Empty />
      )}
    </>
  );
}
