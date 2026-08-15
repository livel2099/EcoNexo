import { defineConfig, devices } from "@playwright/test";

/**
 * Configuración de pruebas E2E de humo (smoke) para EcoNexo web.
 *
 * Corre contra el modo demo (autónomo, sin backend), así los flujos
 * principales se validan sin depender de la API ni de la base de datos.
 * Playwright levanta `dev:demo` automáticamente y reutiliza el servidor si ya
 * está corriendo.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: {
    command: "npm run dev:demo",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
