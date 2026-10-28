import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { DemoBanner } from "./DemoBanner";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
it("labels synthetic data and queues a snapshot only on an explicit click", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue({
      ok: true,
      json: async () => ({ status: "QUEUED", demo: true }),
    });
  vi.stubGlobal("fetch", fetch);
  render(
    <QueryClientProvider client={new QueryClient()}>
      <DemoBanner />
    </QueryClientProvider>,
  );
  expect(screen.getByText("ДЕМО · вымышленные данные")).toBeVisible();
  expect(fetch).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Следующий демоснимок" }));
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
  expect(fetch.mock.calls[0][0]).toBe("/api/v1/demo/advance");
  expect(await screen.findByRole("status")).toHaveTextContent(
    "Демоснимок в очереди",
  );
});
