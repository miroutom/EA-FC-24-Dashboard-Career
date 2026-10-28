import { expect, it } from "vitest";
import {
  attackLeaders,
  goalDistribution,
  productivity,
  role,
  type ChartPlayer,
} from "./chart-data";

const player = (
  id: number,
  changes: Partial<ChartPlayer> = {},
): ChartPlayer => ({
  id,
  name: `Test ${id}`,
  position: "ФРВ",
  goals: 4,
  assists: 2,
  appearances: 10,
  ...changes,
});

it("ranks known goals and assists while retaining real zero counters", () => {
  const data = attackLeaders([
    player(1),
    player(2, { goals: null }),
    player(3, { goals: 0, assists: 0 }),
    player(4, { assists: 8 }),
  ]);
  expect(data.map((p) => p.id)).toEqual([4, 1, 3]);
  expect(data[0].contributions).toBe(12);
});
it("computes role shares only from known goal counts and labels unknown positions", () => {
  const data = goalDistribution([
    player(1, { goals: 6 }),
    player(2, { position: "ЦП", goals: 2 }),
    player(3, { position: null, goals: 2 }),
    player(4, { goals: null }),
  ]);
  expect(data.knownGoals).toBe(10);
  expect(data.excluded).toBe(1);
  expect(data.items.map((r) => r.share)).toEqual([0.6, 0.2, 0.2]);
  expect(role("new-unknown")).toBe("Без позиции");
});
it("does not invent ratios for zero appearances or incomplete counters", () => {
  const data = productivity([
    player(1),
    player(2, { appearances: 0 }),
    player(3, { assists: null }),
  ]);
  expect(data).toHaveLength(1);
  expect(data[0].rate).toBe(0.6);
});
it("keeps zero-goal and unavailable distributions empty without fabricated slices", () => {
  expect(goalDistribution([player(1, { goals: 0 })]).items).toEqual([]);
  expect(goalDistribution([player(1, { goals: null })]).excluded).toBe(1);
});
