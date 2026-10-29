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
export type LivePlayer = {
  yellow: Metric;
  two_yellow: Metric;
  red: Metric;
  saves: Metric;
  goals_conceded: Metric;
  motm: Metric;
  avg_raw: Metric;
  injury_id: Metric;
  injury_date_raw: Metric;
  injury_duration_days: Metric;
  last_match_minutes: Metric;
  last_match_overall: Metric;
  last_match_fact: Metric;
  last_match_position: Metric;
  latest_match_rating_raw: Metric;
  latest_match_rating_minutes: Metric;
  latest_match_rating_date_raw: Metric;
  observed_at: string | null;
  data_quality: string;
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
  live: LivePlayer | null;
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
  team_matches: {
    matches: number;
    wins: number;
    draws: number;
    losses: number;
    goals_for: number;
    goals_against: number;
    points: number;
    points_per_game: number;
    avg_xg: Metric;
    avg_xga: Metric;
    avg_possession: Metric;
    recent_results: {
      result: "W" | "D" | "L";
      played_at: string | null;
      opponent: string | null;
      club_goals: Metric;
      opponent_goals: Metric;
    }[];
    coverage: string;
  } | null;
  xg: Metric;
  team_form: {
    season_id: number;
    records: {
      league_id: number;
      matches_played: Metric;
      wins: Metric;
      draws: Metric;
      losses: Metric;
      goals_for: Metric;
      goals_against: Metric;
      points: Metric;
      table_position: Metric;
      observed_at: string | null;
    }[];
    recent_results: {
      result: "W" | "D" | "L";
      league_id: number;
      observed_at: string | null;
      source: string;
    }[];
    warnings: string[];
    coverage: string;
    data_quality: string;
  } | null;
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

export type MatchTeamStats = {
  possession: Metric;
  xg: Metric;
  shots: Metric;
  shots_on_target: Metric;
  shots_off_target: Metric;
  blocked_shots: Metric;
  shot_accuracy: Metric;
  passes: Metric;
  completed_passes: Metric;
  pass_accuracy: Metric;
  tackles: Metric;
  tackles_won: Metric;
  interceptions: Metric;
  saves: Metric;
  fouls: Metric;
  offsides: Metric;
  dribbles: Metric;
  successful_dribbles: Metric;
  dribble_success: Metric;
  ball_recovery_seconds: Metric;
  penalties: Metric;
  yellow_cards: Metric;
  red_cards: Metric;
  injuries: Metric;
};
export type MatchEvent = {
  minute: number;
  kind: "goal" | "substitution" | "yellow" | "red" | "injury";
  team: "club" | "opponent";
  player: string;
  secondary_player: string | null;
  detail: string | null;
};
export type MatchPlayer = {
  external_player_id: number | null;
  name: string;
  position: string | null;
  overall: Metric;
  rating: Metric;
  goals: Metric;
  assists: Metric;
  started: boolean | null;
  substitute: boolean | null;
  motm: boolean | null;
};
export type MatchEvidence = {
  id: number;
  career_save_id: number;
  season_id: number;
  source_external_match_id: string | null;
  played_at: string | null;
  home_goals: Metric;
  away_goals: Metric;
  verified_source: string;
  external_compobjid: number | null;
  competition_name: string | null;
  club_team_external_id: number | null;
  opponent_name: string | null;
  club_was_home: boolean | null;
  club_goals: Metric;
  opponent_goals: Metric;
  duration_minutes: Metric;
  result: "W" | "D" | "L" | null;
  team_stats: MatchTeamStats;
  opponent_stats: MatchTeamStats;
  timeline: MatchEvent[];
  player_performances: MatchPlayer[];
  screenshot_paths: string[];
  screenshot_urls: string[];
  evidence: { note?: string; sources?: string[] };
};
export type MatchDraft = {
  draft_version: number;
  id: string;
  status: "NEEDS_REVIEW";
  source: string;
  classification_counts: Record<string, number>;
  confidence: {
    score: string;
    team_stats: string;
    players: string;
    player_roster_match_min: number | null;
    timeline: string;
  };
  warnings: string[];
  match: MatchEvidence;
  screenshot_urls: string[];
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
