import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/brazil',
  timeout: 60_000,
  use: { ...devices['Desktop Chrome'], channel: 'chrome', baseURL: 'http://localhost:3107' },
  webServer: {
    command: 'npm run dev:demo -- -p 3107',
    url: 'http://localhost:3107',
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
