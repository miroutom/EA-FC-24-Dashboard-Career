import type { Player } from "../../shared/api";

export type ChartPlayer = Pick<
  Player,
  "id" | "name" | "position" | "goals" | "assists" | "appearances"
>;
export const ROLE_COLORS: Record<string, string> = {
  Атака: "#6094ff",
  Полузащита: "#38d8af",
  Защита: "#b394fa",
  Вратари: "#edbc67",
  "Без позиции": "#8292ad",
};

export function role(position: string | null) {
  if (
    ["ФРВ", "ЛФА", "ПФА", "ЦФ", "ЦФД", "ST", "CF", "LW", "RW"].includes(
      position || "",
    )
  )
    return "Атака";
  if (
    ["ЦАП", "ЦП", "ЦОП", "ЛП", "ПП", "CAM", "CM", "CDM", "LM", "RM"].includes(
      position || "",
    )
  )
    return "Полузащита";
  if (
    ["ЦЗ", "ЛЗ", "ПЗ", "ЛФЗ", "ПФЗ", "CB", "LB", "RB", "LWB", "RWB"].includes(
      position || "",
    )
  )
    return "Защита";
  if (["ВРТ", "GK"].includes(position || "")) return "Вратари";
  return "Без позиции";
}

export function attackLeaders(players: ChartPlayer[]) {
  return players
    .filter((p) => p.goals != null && p.assists != null)
    .map((p) => ({
      ...p,
      contributions: p.goals! + p.assists!,
      label: p.name.length > 19 ? `${p.name.slice(0, 18)}…` : p.name,
    }))
    .sort(
      (a, b) =>
        b.contributions - a.contributions || a.name.localeCompare(b.name),
    )
    .slice(0, 8);
}

export function goalDistribution(players: ChartPlayer[]) {
  const groups = new Map<string, number>();
  for (const p of players) {
    if (p.goals == null) continue;
    const group = role(p.position);
    groups.set(group, (groups.get(group) || 0) + p.goals);
  }
  const knownGoals = [...groups.values()].reduce((a, b) => a + b, 0);
  return {
    knownGoals,
    excluded: players.filter((p) => p.goals == null).length,
    items: [...groups]
      .filter(([, value]) => value > 0)
      .map(([name, value]) => ({
        name,
        value,
        share: value / knownGoals,
        fill: ROLE_COLORS[name],
      }))
      .sort((a, b) => b.value - a.value),
  };
}

export function productivity(players: ChartPlayer[]) {
  return players
    .filter(
      (p) =>
        p.appearances != null &&
        p.appearances > 0 &&
        p.goals != null &&
        p.assists != null,
    )
    .map((p) => ({
      ...p,
      contributions: p.goals! + p.assists!,
      rate: (p.goals! + p.assists!) / p.appearances!,
      role: role(p.position),
      fill: ROLE_COLORS[role(p.position)],
    }));
}
