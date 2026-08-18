import { test, expect } from "@playwright/test";

/**
 * Pruebas de humo (smoke) de EcoNexo web en modo demo.
 * Verifican que los flujos críticos cargan y responden, sin backend.
 */

test.describe("EcoNexo · smoke", () => {
  test("la portada carga con la marca EcoNexo", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/EcoNexo/i);
  });

  test("el asistente EcoBot está disponible", async ({ page }) => {
    await page.goto("/");
    const fab = page.getByRole("button", { name: /asistente EcoBot/i });
    await expect(fab).toBeVisible();
    await fab.click();
    await expect(page.getByRole("dialog", { name: /EcoBot/i })).toBeVisible();
  });

  test("la pantalla de acceso muestra ingresar y crear organización", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("tab", { name: /ingresar/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /crear organización/i })).toBeVisible();
    await expect(page.getByLabel(/email/i)).toBeVisible();
  });

  test("el reporte ciudadano muestra el formulario", async ({ page }) => {
    await page.goto("/reportar");
    await expect(page.getByRole("heading", { name: /detectar un incidente ambiental/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /enviar reporte para validación/i })).toBeVisible();
  });

  test("login demo lleva al Centro de Comando", async ({ page }) => {
    await page.goto("/login");
    // Este flujo requiere modo demo (autónomo). En una config con API real
    // (p. ej. .env.local con NEXT_PUBLIC_DEMO_MODE=false) se omite en vez de
    // fallar, porque no hay backend que autentique.
    const demoActive = await page.getByText(/Demo autónoma activa/i).isVisible().catch(() => false);
    test.skip(!demoActive, "Requiere NEXT_PUBLIC_DEMO_MODE=true (sin backend real).");
    // En modo demo el email y la contraseña vienen precargados.
    const submit = page.getByRole("button", { name: /ingresar al centro de comando/i });
    await expect(submit).toBeEnabled();
    // Evitar la carrera de hidratación de SSR: reintentar el click hasta que
    // React tome el control y el formulario navegue al dashboard.
    await expect(async () => {
      await submit.click();
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 2000 });
    }).toPass({ timeout: 15_000 });
    await expect(page.getByRole("button", { name: /centro de comando/i })).toBeVisible();
  });
});
