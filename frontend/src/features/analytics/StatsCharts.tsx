import { BarChart3, Crosshair, PieChart as PieIcon } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { fmt, type Player } from "../../shared/api";
import { Empty } from "../../shared/components";
import { attackLeaders, goalDistribution, productivity } from "./chart-data";

const tooltipStyle = {
  background: "#202a3c",
  border: "1px solid #42516d",
  borderRadius: 10,
  color: "#e5edff",
  boxShadow: "0 10px 30px #0005",
};
const axis = { fill: "#8b9fbe", fontSize: 10 };

function PlayerTip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: readonly {
    payload?: {
      name?: string;
      appearances?: number;
      contributions?: number;
      rate?: number;
    };
  }[];
}) {
  const point = payload?.[0]?.payload;
  if (!active || !point) return null;
  return (
    <div className="scatter-tooltip">
      <strong>{point.name}</strong>
      <p>Выступления: {fmt(point.appearances)}</p>
      <p>Голы + ассисты: {fmt(point.contributions)}</p>
      <p>Г+П / выступление: {fmt(point.rate, 2)}</p>
    </div>
  );
}

export function StatsCharts({ players }: { players: Player[] }) {
  const leaders = attackLeaders(players);
  const distribution = goalDistribution(players);
  const points = productivity(players);
  const best = [...points].sort((a, b) => b.rate - a.rate)[0];
  const average = points.length
    ? points.reduce((sum, p) => sum + p.contributions, 0) / points.length
    : 0;
  const excluded = players.length - points.length;
  return (
    <div className="analytics-grid">
      <section className="panel attack-panel">
        <div className="panel-heading">
          <div>
            <h2>
              <BarChart3 size={17} />
              Лидеры атаки
            </h2>
            <p>Голы + ассисты · восемь лидеров выбранного периода</p>
          </div>
          <span className="chart-badge">Г+П</span>
        </div>
        {leaders.length ? (
          <div
            className="attack-chart"
            role="img"
            aria-label="Лидеры по голам и ассистам"
          >
            <ResponsiveContainer width="100%" height={330}>
              <BarChart
                data={leaders}
                layout="vertical"
                margin={{ left: 0, right: 20, top: 6, bottom: 5 }}
                barSize={14}
              >
                <CartesianGrid stroke="#ffffff08" horizontal={false} />
                <XAxis
                  type="number"
                  tick={axis}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="label"
                  width={133}
                  tick={axis}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  cursor={{ fill: "#ffffff04" }}
                  contentStyle={tooltipStyle}
                  labelStyle={{ color: "#fff" }}
                  labelFormatter={(_, p) => p?.[0]?.payload?.name || "Игрок"}
                />
                <Bar
                  isAnimationActive={false}
                  dataKey="goals"
                  name="Голы"
                  stackId="attack"
                  fill="#6194ff"
                />
                <Bar
                  isAnimationActive={false}
                  dataKey="assists"
                  name="Ассисты"
                  stackId="attack"
                  fill="#3dd6b3"
                  radius={[0, 5, 5, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <Empty title="Недостаточно показателей" />
        )}
        <div className="chart-caption">
          <span>
            <i className="blue-dot" />
            Голы
          </span>
          <span>
            <i className="green-dot" />
            Ассисты
          </span>
          <small>Игроки с известными обоими счётчиками</small>
        </div>
      </section>
      <section className="panel distribution-panel">
        <div className="panel-heading">
          <div>
            <h2>
              <PieIcon size={17} />
              Откуда приходят голы
            </h2>
            <p>По позиции в последнем учтённом сезоне</p>
          </div>
        </div>
        {distribution.items.length ? (
          <>
            <div
              className="donut-wrap"
              role="img"
              aria-label="Распределение голов по позициям"
            >
              <ResponsiveContainer width="100%" height={255}>
                <PieChart>
                  <Pie
                    isAnimationActive={false}
                    data={distribution.items}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={76}
                    outerRadius={107}
                    paddingAngle={4}
                    stroke="none"
                    cornerRadius={4}
                  >
                    {distribution.items.map((d) => (
                      <Cell key={d.name} fill={d.fill} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
              <div className="donut-center">
                <strong>{fmt(distribution.knownGoals)}</strong>
                <span>голов в выборке</span>
              </div>
            </div>
            <div className="role-legend">
              {distribution.items.map((d) => (
                <div key={d.name}>
                  <span className="role-dot" style={{ background: d.fill }} />
                  <span>{d.name}</span>
                  <strong>{fmt(d.value)}</strong>
                  <small>{fmt(d.share * 100, 1)}%</small>
                </div>
              ))}
            </div>
          </>
        ) : (
          <Empty title="Нет голов для распределения" />
        )}
        {distribution.excluded > 0 && (
          <p className="chart-footnote">
            Игроков без показателей: {distribution.excluded}. Они не включены в
            доли.
          </p>
        )}
      </section>
      <section className="panel productivity-panel">
        <div className="panel-heading">
          <div>
            <h2>
              <Crosshair size={17} />
              Результативность и нагрузка
            </h2>
            <p>Каждая точка — игрок. Размер точки отражает Г+П.</p>
          </div>
          <span className="chart-badge">{points.length} игроков</span>
        </div>
        {points.length ? (
          <div className="productivity-layout">
            <div
              className="scatter-plot"
              role="img"
              aria-label="Связь выступлений и голевых действий игроков"
            >
              <ResponsiveContainer width="100%" height={290}>
                <ScatterChart
                  margin={{ top: 20, right: 25, bottom: 22, left: 0 }}
                >
                  <CartesianGrid stroke="#ffffff09" strokeDasharray="3 5" />
                  <XAxis
                    type="number"
                    dataKey="appearances"
                    name="Выступления"
                    tick={axis}
                    axisLine={false}
                    tickLine={false}
                    label={{
                      value: "Выступления",
                      position: "insideBottom",
                      offset: -16,
                      fill: "#778ba9",
                      fontSize: 10,
                    }}
                  />
                  <YAxis
                    type="number"
                    dataKey="contributions"
                    name="Г+П"
                    tick={axis}
                    axisLine={false}
                    tickLine={false}
                    width={43}
                  />
                  <ZAxis
                    type="number"
                    dataKey="contributions"
                    range={[65, 350]}
                  />
                  <ReferenceLine
                    y={average}
                    stroke="#617597"
                    strokeDasharray="4 5"
                  />
                  <Tooltip
                    cursor={{ strokeDasharray: "3 3", stroke: "#6781ab" }}
                    content={<PlayerTip />}
                  />
                  <Scatter
                    isAnimationActive={false}
                    data={points}
                    fillOpacity={0.82}
                  >
                    {points.map((p) => (
                      <Cell
                        key={p.id}
                        fill={p.fill}
                        stroke={p.fill}
                        strokeWidth={1}
                      />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
            </div>
            <aside className="efficiency-card">
              <span>ЛУЧШИЙ Г+П / ВЫСТУПЛЕНИЕ</span>
              <strong>{fmt(best.rate, 2)}</strong>
              <h3>{best.name}</h3>
              <p>
                {fmt(best.contributions)} голевых действий
                <br />
                за {fmt(best.appearances)} выступлений
              </p>
              <small>
                Среди игроков с известными показателями и хотя бы одним
                выступлением.
              </small>
            </aside>
          </div>
        ) : (
          <Empty title="Недостаточно данных для сравнения" />
        )}
        <p className="chart-footnote">
          Пунктир — средний Г+П по выборке.{" "}
          {excluded > 0 &&
            `Не включены ${excluded} игроков с нулём выступлений или неизвестными показателями.`}
        </p>
      </section>
    </div>
  );
}
