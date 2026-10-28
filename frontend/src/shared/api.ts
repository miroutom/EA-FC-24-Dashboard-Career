export type Metric = number | null;
export type Season = {
  id: number;
  start_year: number;
  end_year: number;
  source_policy: string;
};
export type Career = { id: number; name: string; game_version: string };
export type History = {
  season_id: number;
  season: string;
  appearances: Metric;
  goals: Metric;
  assists: Metric;
  clean_sheets: Metric;
  source: string;
  coverage: string;
  source_scope: string;
};
export type Player = {
  id: number;
  name: string;
  position: string | null;
  appearances: Metric;
  goals: Metric;
  assists: Metric;
  clean_sheets: Metric;
  goal_contributions: Metric;
  goals_per_appearance: Metric;
  contributions_per_appearance: Metric;
  seasons_count: number;
  first_season: string;
  last_season: string;
  history: History[];
  sources: string[];
  data_quality: string[];
  rating: Metric;
  overall: Metric;
  potential: Metric;
  observed_goals_share: Metric;
  competition_history: {
    season: string;
    competition: string;
    compobjid: number;
    appearances: Metric;
    goals: Metric;
    assists: Metric;
    source: string;
    coverage: string;
  }[];
};
export type Players = {
  items: Player[];
  total?: number;
  warnings: string[];
  data_quality: string[];
  last_synced_at: string | null;
  source_scope: string[];
};
export type Dashboard = Players & {
  kpis: Record<string, Metric>;
  players_count: number;
  seasons_count: number;
  chart: History[];
  leaders: Player[];
  coverage: string;
};
export type Save = {
  id: number;
  instance_key: string;
  status: string;
  active_branch_no: number;
  verified_live: boolean;
};
export type Sync = {
  collector: string;
  connected: boolean;
  stale: boolean;
  saves: Save[];
  last_synced_at: string | null;
  counts: Record<string, number>;
  unassigned_count: number;
  unassigned_counts: Record<string, number>;
  unassigned_errors: {
    id: number;
    action: string;
    message: string;
    time: string;
  }[];
  watcher: { enabled: boolean; last_scan: string | null; error: string | null };
  capabilities: Record<string, string>;
};
export type Delta = {
  id: number;
  player_id: number;
  confidence: string;
  interval_label: string;
  next_snapshot_id: number;
  previous_snapshot_id: number;
  values: Record<string, Metric>;
};
export type Preview = {
  preview_token: string | null;
  rows_count: number;
  rows: Record<string, unknown>[];
  errors: { row: number; message: string }[];
  conflicts: {
    player: string;
    season: string;
    existing: Record<string, Metric>;
    incoming: Record<string, Metric>;
  }[];
  duplicate: boolean;
  coverage: string;
};
export type Filters = {
  season_id?: number;
  competition_id?: number;
  save_id?: number;
  as_of?: string;
};

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      ...init?.headers,
    },
  });
  const data = await response.json();
  if (!response.ok)
    throw new Error(data.error?.message || `Ошибка ${response.status}`);
  return data as T;
}
export const post = <T>(path: string, body: unknown) =>
  api<T>(path, { method: "POST", body: JSON.stringify(body) });

export async function fetchPlayers(
  careerId: number,
  filters: Filters = {},
): Promise<Players> {
  const first = await api<Players>(
    `/careers/${careerId}/players?size=200&page=1&${params(filters)}`,
  );
  const items = [...first.items];
  for (let page = 2; items.length < (first.total || 0); page++) {
    const next = await api<Players>(
      `/careers/${careerId}/players?size=200&page=${page}&${params(filters)}`,
    );
    if (!next.items.length) break;
    items.push(...next.items);
  }
  return { ...first, items };
}
export const params = (filters: Filters) => {
  const p = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== "") p.set(k, String(v));
  });
  return p.toString();
};
export const fmt = (value: Metric | undefined, digits = 0) =>
  value == null
    ? "—"
    : value.toLocaleString("ru-RU", { maximumFractionDigits: digits });
export const date = (value: string | null | undefined) =>
  value ? new Date(value).toLocaleString("ru-RU") : "Ещё не было";
