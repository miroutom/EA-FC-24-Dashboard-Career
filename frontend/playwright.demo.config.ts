import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./demo-tests",
  use: {
    baseURL: "http://127.0.0.1:8001",
    viewport: { width: 1440, height: 1100 },
  },
  workers: 1,
});
