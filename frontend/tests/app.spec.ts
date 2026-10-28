import { test, expect } from "@playwright/test";

test("real historical dashboard, filters, drawer, compare and sync", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Вся карьера. В деталях." }),
  ).toBeVisible();
  await expect(page.getByText("Collector: not verified")).toBeVisible();
  const season = page.getByLabel("Сезон", { exact: true });
  await expect(season.locator("option")).toHaveCount(6);
  await season.selectOption({ label: "2023/24" });
  await expect(page.locator(".kpi").filter({ hasText: "Голы игроков" }).locator("strong")).toHaveText("146");
  await season.selectOption("");
  await expect(page.locator(".kpi").filter({ hasText: "Голы игроков" }).locator("strong")).toHaveText("601");
  await page.screenshot({ path: "test-results/dashboard.png", fullPage: true });
  await page.getByRole("link", { name: "Состав и история" }).click();
  await page.getByLabel("Поиск игрока").fill("Vardy");
  const player = page.getByRole("button", { name: /Vardy/ });
  await expect(player).toBeVisible();
  await player.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByLabel("Поиск игрока")).toHaveValue("Vardy");
  await page.getByRole("link", { name: "Сравнение", exact: true }).click();
  const select = page.getByLabel("Добавить игрока для сравнения");
  await expect(select.locator("option").nth(1)).toBeAttached();
  const options = await select
    .locator("option")
    .evaluateAll((options) =>
      options.slice(1, 3).map((o) => (o as HTMLOptionElement).value),
    );
  await select.selectOption(options[0]);
  await select.selectOption(options[1]);
  await expect(
    page.getByRole("cell", { name: "Учтённые сезоны" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Синхронизация" }).click();
  await expect(
    page.getByRole("heading", { name: "Связь с вашей карьерой" }),
  ).toBeVisible();
  await expect(page.getByText("Снимков ещё нет")).toBeVisible();
  await page.setViewportSize({ width: 768, height: 1100 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Вся карьера. В деталях." }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/dashboard-768.png",
    fullPage: true,
  });
});
