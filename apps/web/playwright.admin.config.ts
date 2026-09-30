import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/admin",
  fullyParallel: true,
  workers: 2,
  use: { baseURL: "http://localhost:3107", channel: process.env.PLAYWRIGHT_CHANNEL, screenshot: "only-on-failure", trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npx cross-env NEXT_PUBLIC_DEMO_MODE=false NEXT_PUBLIC_API_URL=http://localhost:3108 NEXT_PUBLIC_WS_URL=ws://localhost:3108 next dev -p 3107 -H 127.0.0.1",
    url: "http://localhost:3107",
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
