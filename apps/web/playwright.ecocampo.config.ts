import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/ecocampo", workers: 1, timeout: 60000,
  use: { baseURL: "http://localhost:3101", ...devices["Desktop Chrome"], channel: process.env.E2E_BROWSER_CHANNEL, screenshot: "only-on-failure" },
  webServer: {
    command: "npx cross-env NEXT_PUBLIC_DEMO_MODE=false NEXT_PUBLIC_API_URL=http://127.0.0.1:9 NEXT_PUBLIC_WS_URL=ws://127.0.0.1:9 next dev -p 3101",
    url: "http://localhost:3101", reuseExistingServer: false, timeout: 120000,
  },
});