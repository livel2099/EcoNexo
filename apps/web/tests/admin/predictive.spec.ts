import { test, expect, type Page } from "@playwright/test";

const session = { access_token: "predictive-test", org_id: "00000000-0000-4000-8000-000000000001", role: "admin", name: "Operaciones", email: "owner@example.com", account_type: "institutional", platform_admin: false };
const node = { id: "00000000-0000-4000-8000-000000000002", name: "Nodo Norte", lat: -26.92, lon: -54.78, tags: [], status: "online", latest_readings: {}, telemetry_mode: "open_meteo", pipeline_enabled: true };

async function mockPrediction(page: Page, role = "admin") {
  const enabled = new Set<string>();
  const changes: { path: string; body: Record<string, unknown> }[] = [];
  await page.addInitScript((value) => sessionStorage.setItem("econexo_session", JSON.stringify(value)), { ...session, role });
  await page.route("https://**", (route) => route.abort());
  await page.route("http://localhost:3108/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    const method = route.request().method();
    const headers = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Methods": "*" };
    if (method === "OPTIONS") return route.fulfill({ status: 204, headers });
    let data: unknown = [];
    if (path === "/auth/me") data = { ...session, role };
    if (path === "/orgs/me") data = { id: session.org_id, name: "Territorio de prueba", vertical: "forestal", primary_color: "#2E7D5B" };
    if (path === "/devices") data = [node];
    if (path === "/kpis") data = { global_status: "normal", active_alerts: 0, model_precision: null, valid_reports_rate: null, detection_time_s: null, response_time_reduction: null };
    if (path === "/predictions/settings") data = [...enabled].map((hazard) => ({ hazard, horizon_hours: 24, enabled: true, active_model_id: null }));
    if (path === "/predictions/evaluation") data = { generated_at: "2026-10-06T12:00:00Z", labels_policy: "Sin cobertura verificada no hay resultado negativo.", models: [], metrics: [{ model_version: "fire-weather-index-v1", scope_start: "2026-10-01T00:00:00Z", evaluated: 0, pending_labels: 1, precision: null, recall: null, event_recall: 0, fp: 0, independent_events: 1, events_missed: 1, median_lead_hours: null, brier: null, calibration: [] }] };
    if (path === "/predictions") data = [{ id: "prediction-1", device_id: node.id, device_name: node.name, horizon_hours: 24, issued_at: "2026-10-06T12:00:00Z", valid_from: "2026-10-06T13:00:00Z", valid_to: "2026-10-07T13:00:00Z", model_version: "fire-weather-index-v1", risk_index: 0.8, probability: null, warning: true, explanation: ["Máxima prevista: 35 °C"], action: "Preparar vigilancia y verificar condiciones locales." }];
    if (method === "POST") {
      const body = route.request().postDataJSON();
      changes.push({ path, body });
      if (path === "/predictions/models/deploy") body.enabled ? enabled.add(body.hazard) : enabled.delete(body.hazard);
      if (path === "/predictions/models/train") return route.fulfill({ status: 409, json: { detail: "Se necesitan al menos 120 pronósticos maduros" }, headers });
      data = { message: path === "/predictions/observations" ? "Resultado independiente registrado." : "Pronósticos archivados" };
    }
    await route.fulfill({ json: data, headers });
  });
  await page.goto("/dashboard");
  const cookies = page.getByRole("button", { name: "Solo esenciales", exact: true });
  if (await cookies.count()) await cookies.click();
  await page.getByRole("button", { name: "Predicción", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Predicción de incendios", exact: true })).toBeVisible();
  return changes;
}

test("fuente requiere consentimiento explícito y el índice no se presenta como probabilidad", async ({ page }) => {
  const changes = await mockPrediction(page);
  const enable = page.getByRole("button", { name: "Habilitar fuente", exact: true });
  await expect(enable).toBeDisabled();
  await page.getByRole("checkbox", { name: /Autorizo consultar Open-Meteo/ }).check();
  await enable.click();
  await expect(page.getByRole("heading", { name: "Pronósticos habilitados · 24 h" })).toBeVisible();
  expect(changes[0]).toEqual({ path: "/predictions/models/deploy", body: { hazard: "fire", horizon_hours: 24, enabled: true, external_weather_consent: true } });
  await expect(page.getByText("Índice meteorológico 80/100", { exact: true })).toBeVisible();
  await page.getByText("Fuentes y explicación", { exact: true }).click();
  await expect(page.getByText("Este índice no es una probabilidad de incidente.")).toBeVisible();
});

test("entrenamiento sin evidencia suficiente muestra bloqueo y métricas sin inventar precisión", async ({ page }) => {
  await mockPrediction(page);
  await page.getByRole("button", { name: "Entrenar candidato", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "120 pronósticos maduros" })).toBeVisible();
  await expect(page.getByText("No aplica al índice", { exact: true })).toBeVisible();
  await expect(page.getByText("1 / 1", { exact: true })).toBeVisible();
});

test("evidencia independiente se registra con hora, fuente y cobertura verificadas", async ({ page }) => {
  const changes = await mockPrediction(page);
  await page.getByLabel("Inicio del incidente", { exact: true }).fill("2026-10-01T10:00");
  await page.getByLabel("Referencia única", { exact: true }).fill("Incidente-2026-001");
  await page.getByLabel("Evidencia y cobertura", { exact: true }).fill("Incendio verificado en campo por equipo de guardia.");
  const save = page.getByRole("button", { name: "Guardar resultado verificado", exact: true });
  await expect(save).toBeDisabled();
  await page.getByRole("checkbox", { name: /Verifiqué el resultado/ }).check();
  await save.click();
  await expect(page.getByRole("status").filter({ hasText: "Resultado independiente registrado" })).toBeVisible();
  expect(changes[0].body.coverage_verified).toBe(true);
  expect(changes[0].body.start_at).toBe(changes[0].body.end_at);
  expect(changes[0].body.source).toBe("field_report");
});

test("visualizador ve pronósticos en móvil sin controles administrativos", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockPrediction(page, "visualizador");
  await expect(page.getByRole("button", { name: "Habilitar fuente", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Entrenar candidato", exact: true })).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.screenshot({ path: "../../output/predictive-mobile.png", fullPage: true });
});

test("hídrico y sanitario tienen consentimiento y entrenamiento independientes", async ({ page }) => {
  const changes = await mockPrediction(page);
  const select = page.getByRole("combobox", { name: "Riesgo predictivo", exact: true });
  await select.selectOption("hydric");
  await expect(page.getByRole("heading", { name: "Predicción de riesgo hídrico por lluvias", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Actualizar", exact: true })).toBeEnabled();
  await expect(page.getByRole("button", { name: "Habilitar fuente", exact: true })).toBeDisabled();
  await page.getByRole("checkbox", { name: /Autorizo consultar/ }).check();
  await page.getByRole("button", { name: "Habilitar fuente", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Pronósticos habilitados · 24 h" })).toBeVisible();
  expect(changes[0].body.hazard).toBe("hydric");
  await select.selectOption("health_air");
  await expect(page.getByRole("button", { name: "Actualizar", exact: true })).toBeEnabled();
  await expect(page.getByRole("heading", { name: "Predicción de riesgo sanitario por PM2.5", exact: true })).toBeVisible();
  await expect(page.getByRole("checkbox", { name: /Calidad del Aire/ })).not.toBeChecked();
  await expect(page.getByRole("button", { name: "Emitir pronósticos", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "Entrenar candidato", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "120 pronósticos maduros" })).toBeVisible();
  expect(changes[1].body.hazard).toBe("health_air");
  await select.selectOption("health_heat");
  await expect(page.getByRole("button", { name: "Actualizar", exact: true })).toBeEnabled();
  await expect(page.getByRole("heading", { name: "Predicción de riesgo sanitario por calor", exact: true })).toBeVisible();
  await expect(page.getByRole("option", { name: "Incidente sanitario asociado al calor verificado", exact: true })).toHaveCount(1);
});
