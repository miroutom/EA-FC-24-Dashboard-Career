import { test, expect } from "@playwright/test";

test("Mac demo is labelled, isolated, populated and updates through the watcher", async ({
  page,
  request,
}) => {
  const externalRequests: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (
      ["http:", "https:"].includes(url.protocol) &&
      !["127.0.0.1", "localhost"].includes(url.hostname)
    )
      externalRequests.push(url.origin);
  });
  const health = await (await request.get("/api/v1/health")).json();
  expect(health.demo_mode).toBe(true);
  await page.goto("/");
  await expect(
    page.getByRole("region", { name: "Демонстрационный режим" }),
  ).toBeVisible();
  await expect(page.getByText("ДЕМО · вымышленные данные")).toBeVisible();
  const careers = await (await request.get("/api/v1/careers")).json();
  const cid = careers[0].id;
  const initial = await (
    await request.get(`/api/v1/careers/${cid}/dashboard`)
  ).json();
  expect(initial.players_count).toBe(22);
  expect(initial.seasons_count).toBe(8);
  expect(initial.data_quality).toEqual(["demo"]);
  await expect(
    page
      .locator(".kpi")
      .filter({ hasText: "Учтённых игроков" })
      .locator("strong"),
  ).toHaveText("22");
  const count = (
    await (await request.get(`/api/v1/careers/${cid}/snapshots`)).json()
  ).length;
  await page.getByRole("button", { name: "Следующий демоснимок" }).click();
  await expect
    .poll(
      async () =>
        (await (await request.get(`/api/v1/careers/${cid}/snapshots`)).json())
          .length,
      { timeout: 10000 },
    )
    .toBe(count + 1);
  await expect
    .poll(
      async () =>
        (await (await request.get(`/api/v1/careers/${cid}/dashboard`)).json())
          .kpis.goals,
    )
    .toBeGreaterThan(initial.kpis.goals);
  const updated = await (
    await request.get(`/api/v1/careers/${cid}/dashboard`)
  ).json();
  await expect(
    page.locator(".kpi").filter({ hasText: "Голы игроков" }).locator("strong"),
  ).toHaveText(updated.kpis.goals.toLocaleString("ru-RU"), { timeout: 10000 });
  await expect(
    page.getByRole("heading", { name: "Лидеры атаки" }),
  ).toBeVisible();
  await expect(
    page
      .getByRole("img", { name: "Лидеры по голам и ассистам" })
      .locator(".recharts-bar-rectangle"),
  ).toHaveCount(16);
  await expect(
    page
      .getByRole("img", { name: "Распределение голов по позициям" })
      .locator(".recharts-pie-sector"),
  ).toHaveCount(3);
  await expect(
    page
      .getByRole("img", {
        name: "Связь выступлений и голевых действий игроков",
      })
      .locator(".recharts-scatter-symbol"),
  ).toHaveCount(22);
  await page.screenshot({
    path: "test-results/demo-dashboard.png",
    fullPage: true,
  });
  await page
    .getByLabel("Карьера", { exact: true })
    .selectOption(String(careers[1].id));
  await expect(
    page
      .locator(".kpi")
      .filter({ hasText: "Учтённых игроков" })
      .locator("strong"),
  ).toHaveText("12");
  await page.getByLabel("Карьера", { exact: true }).selectOption(String(cid));
  await page.getByRole("link", { name: "Состав и история" }).click();
  await page.getByLabel("Поиск игрока").fill("Alex Mercer");
  await page.getByRole("button", { name: /Alex Mercer/ }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await page.getByRole("link", { name: "Синхронизация" }).click();
  await expect(
    page.getByText("Collector: demo simulator (synthetic)"),
  ).toBeVisible();
  await page.setViewportSize({ width: 768, height: 1100 });
  await page.goto("/");
  await expect(
    page.getByRole("region", { name: "Демонстрационный режим" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Лидеры атаки" }),
  ).toBeVisible();
  expect(externalRequests).toEqual([]);
});
