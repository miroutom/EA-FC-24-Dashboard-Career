import {
  fireEvent,
  render,
  screen,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, expect, it, vi } from "vitest";
import { Careers } from "./Careers";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
it("only commits a conflict replacement after the user explicitly checks the replacement box", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        preview_token: "token",
        rows_count: 1,
        rows: [],
        errors: [],
        conflicts: [
          {
            player: "Synthetic",
            season: "2027/28",
            existing: { goals: 3 },
            incoming: { goals: 4 },
          },
        ],
        duplicate: false,
        coverage: "PARTIAL_SCREENSHOT",
      }),
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ duplicate: false }),
    });
  vi.stubGlobal("fetch", fetch);
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <Careers
        careers={[{ id: 1, name: "Test", game_version: "EA FC 24" }]}
        current={1}
        onSelect={vi.fn()}
      />
    </QueryClientProvider>,
  );
  fireEvent.change(screen.getByLabelText("Исторический Excel или CSV"), {
    target: { files: [new File(["fixture"], "test.csv")] },
  });
  const commit = await screen.findByRole("button", {
    name: "Подтвердить импорт",
  });
  expect(commit).toBeDisabled();
  expect(fetch).toHaveBeenCalledTimes(1);
  fireEvent.click(
    screen.getByLabelText("Подтверждаю замену перечисленных строк"),
  );
  expect(commit).toBeEnabled();
  fireEvent.click(commit);
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({
    preview_token: "token",
    strategy: "replace",
  });
});
