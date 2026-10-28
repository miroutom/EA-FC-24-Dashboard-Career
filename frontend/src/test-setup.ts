import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";
import { createElement } from "react";
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverMock;
Object.defineProperty(HTMLElement.prototype, "clientWidth", {
  configurable: true,
  value: 900,
});
Object.defineProperty(HTMLElement.prototype, "clientHeight", {
  configurable: true,
  value: 400,
});
vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) =>
      createElement("div", null, children),
  };
});
