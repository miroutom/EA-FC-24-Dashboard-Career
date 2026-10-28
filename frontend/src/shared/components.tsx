import { Activity, ArrowUpRight, Database, Info } from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { History, Metric } from "./api";
import { fmt } from "./api";

export function Empty({
  title = "Пока нет данных",
  children,
}: {
  title?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="empty">
      <Database size={30} />
      <h3>{title}</h3>
      <p>
        {children ||
          "Импортируйте исторический Excel или настройте сбор снимков в разделе синхронизации."}
      </p>
    </div>
  );
}
export function Feedback({
  loading,
  error,
}: {
  loading?: boolean;
  error?: Error | null;
}) {
  return loading ? (
    <div className="loading" role="status">
      <Activity size={20} /> Загружаем статистику…
    </div>
  ) : error ? (
    <div className="alert" role="alert">
      {error.message}
    </div>
  ) : null;
}
export function Quality({ warnings = [] }: { warnings?: string[] }) {
  return (
    <div className="quality">
      <Info size={15} />
      <span>
        Частичная история · только учтённые показатели источника.
        {warnings.length > 0 && (
          <details>
            <summary>Сведения об источниках ({warnings.length})</summary>
            {warnings.map((w) => (
              <p key={w}>{w}</p>
            ))}
          </details>
        )}
      </span>
    </div>
  );
}
export function Kpi({
  label,
  value,
  detail,
}: {
  label: string;
  value: Metric | undefined;
  detail?: string;
}) {
  return (
    <div className="kpi">
      <div className="kpi-label">
        {label}
        <ArrowUpRight size={16} />
      </div>
      <strong>{fmt(value)}</strong>
      <span>{detail || "По выбранным фильтрам"}</span>
    </div>
  );
}
export function Trend({ data }: { data: Partial<History>[] }) {
  return (
    <div
      className="chart"
      role="img"
      aria-label="Динамика голов и ассистов по учтённым сезонам"
    >
      <ResponsiveContainer width="100%" height={260}>
        <AreaChart data={data} margin={{ left: -20, top: 15, right: 12 }}>
          <defs>
            <linearGradient id="goalsFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#5086ff" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#5086ff" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#ffffff09" vertical={false} />
          <XAxis
            dataKey="season"
            stroke="#8590a7"
            tickLine={false}
            axisLine={false}
            fontSize={12}
          />
          <YAxis
            stroke="#8590a7"
            tickLine={false}
            axisLine={false}
            fontSize={12}
          />
          <Tooltip
            contentStyle={{
              background: "#1e2432",
              borderColor: "#333e55",
              borderRadius: 8,
            }}
            labelStyle={{ color: "#fff" }}
          />
          <Area
            isAnimationActive={false}
            type="monotone"
            dataKey="goals"
            name="Голы"
            stroke="#5086ff"
            fill="url(#goalsFill)"
            strokeWidth={3}
            connectNulls={false}
          />
          <Area
            isAnimationActive={false}
            type="monotone"
            dataKey="assists"
            name="Ассисты"
            stroke="#3cd8b1"
            fill="transparent"
            strokeWidth={2}
            connectNulls={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
