import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, fmt, params, fetchPlayers, type Players } from "../shared/api";
import { Empty, Feedback, Quality } from "../shared/components";
import { useScope } from "../shared/context";

export function Compare() {
  const { career, filters } = useScope();
  const [ids, setIds] = useState<number[]>([]);
  const players = useQuery({
    queryKey: ["players", career.id, filters],
    queryFn: () => fetchPlayers(career.id, filters),
  });
  const compare = useQuery({
    queryKey: ["compare", career.id, ids, filters],
    queryFn: () =>
      api<Players>(
        `/careers/${career.id}/compare?player_ids=${ids.join(",")}&${params(filters)}`,
      ),
    enabled: ids.length >= 2,
  });
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">SIDE BY SIDE</div>
          <h1>Сравнение игроков</h1>
          <p>
            От двух до четырёх игроков. Единые фильтры, одинаковый контекст.
          </p>
        </div>
      </div>
      <Feedback loading={players.isLoading} error={players.error} />
      <section className="panel">
        <label className="field">
          Добавить игрока
          <select
            aria-label="Добавить игрока для сравнения"
            value=""
            disabled={ids.length >= 4}
            onChange={(e) => setIds([...ids, Number(e.target.value)])}
          >
            <option value="">Выберите игрока</option>
            {players.data?.items
              .filter((p) => !ids.includes(p.id))
              .map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
          </select>
        </label>
        <div className="selected-players">
          {ids.map((id) => (
            <button
              key={id}
              onClick={() => setIds(ids.filter((x) => x !== id))}
            >
              {players.data?.items.find((p) => p.id === id)?.name} ×
            </button>
          ))}
        </div>
      </section>
      <Feedback
        loading={compare.isFetching && ids.length >= 2}
        error={compare.error}
      />
      {ids.length < 2 ? (
        <Empty title="Выберите минимум двух игроков">
          Сравнение использует реальные показатели из выбранной карьеры.
        </Empty>
      ) : (
        compare.data && (
          <>
            <Quality
              demo={compare.data.items.every((p) =>
                p.data_quality?.includes("demo"),
              )}
            />
            <section className="panel">
              <div
                className="chart"
                role="img"
                aria-label="Сравнение голов и ассистов"
              >
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={compare.data.items}>
                    <CartesianGrid stroke="#ffffff0a" vertical={false} />
                    <XAxis dataKey="name" stroke="#8e9ab0" />
                    <YAxis stroke="#8e9ab0" />
                    <Tooltip
                      contentStyle={{
                        background: "#1e2432",
                        border: "1px solid #333e55",
                      }}
                    />
                    <Legend />
                    <Bar
                      isAnimationActive={false}
                      dataKey="goals"
                      name="Голы"
                      fill="#5086ff"
                      radius={[4, 4, 0, 0]}
                    />
                    <Bar
                      isAnimationActive={false}
                      dataKey="assists"
                      name="Ассисты"
                      fill="#3cd8b1"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Показатель</th>
                      {compare.data.items.map((p) => (
                        <th key={p.id}>{p.name}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(
                      [
                        ["appearances", "Выступления"],
                        ["goals", "Голы"],
                        ["assists", "Ассисты"],
                        ["goal_contributions", "Г+П"],
                        ["seasons_count", "Учтённые сезоны"],
                        ["goals_per_appearance", "Голы / выступление"],
                      ] as const
                    ).map(([key, title]) => (
                      <tr key={key}>
                        <td>{title}</td>
                        {compare.data!.items.map((p) => (
                          <td key={p.id}>{fmt(p[key], 2)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )
      )}
    </>
  );
}
