import { afterEach, expect, it, vi } from "vitest";
import { api, fmt, params, fetchPlayers } from "./api";

afterEach(() => vi.unstubAllGlobals());
it("fetches remaining player pages instead of truncating long careers", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ items: [{ id: 1 }], total: 2 }),
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ items: [{ id: 2 }], total: 2 }),
    });
  vi.stubGlobal("fetch", fetch);
  const data = await fetchPlayers(3, { season_id: 8 });
  expect(data.items.map((p) => p.id)).toEqual([1, 2]);
  expect(fetch.mock.calls[1][0]).toContain("page=2&season_id=8");
});
it("preserves unknown values and zero as distinct display states", () => {
  expect(fmt(null)).toBe("—");
  expect(fmt(undefined)).toBe("—");
  expect(fmt(0)).toBe("0");
});
it("preserves career filter context and UTC timestamp encoding", () => {
  const value = new URLSearchParams(
    params({ season_id: 4, as_of: "2026-10-28T12:00:00Z" }),
  );
  expect(value.get("season_id")).toBe("4");
  expect(value.get("as_of")).toBe("2026-10-28T12:00:00Z");
  expect(value.has("save_id")).toBe(false);
});
it("surfaces structured API failures rather than treating an error as empty data", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ error: { message: "Конфликт импорта" } }),
    }),
  );
  await expect(api("/careers/1/imports/commit")).rejects.toThrow(
    "Конфликт импорта",
  );
});
