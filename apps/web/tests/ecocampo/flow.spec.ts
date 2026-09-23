import { test, expect, type Page } from "@playwright/test";

async function setup(page: Page, empty = false) {
  const history: unknown[] = [];
  await page.addInitScript(() => sessionStorage.setItem("econexo_session", JSON.stringify({ access_token: "test", role: "admin", name: "Prueba", account_type: "institutional" })));
  await page.route("http://127.0.0.1:9/**", async route => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown = [];
    if (path === "/ecocampo/lots" || path === "/agro/lots") body = empty ? [] : [{ id: "lot-1", name: "Lote de prueba", area_ha: 10, crop_key: "pastizal", crop_name: "Pastizal", is_active: true, advisories: [] }];
    if (path === "/kpis") body = {global_status: "normal"};
    if (path === "/agro/summary") body = {lots_total: 1, lots_active: 1, area_ha: 10, advisories_high: 0, advisories_medium: 0};
    if (path.endsWith("/assessments")) {
      if (route.request().method() === "POST") {
        const evidence = route.request().postDataJSON();
        const result = { status: "datos_insuficientes", vegetation: "sin_referencia", ndvi_delta: null, estimated_animals: evidence.dry_matter_kg_ha === 1000 ? 5 : null, limitations: "Prueba controlada", missing: ["Agua por verificar"], risks: [], sources: [] };
        const row = { id: `assessment-${history.length}`, evidence, result, created_at: new Date().toISOString() };
        history.unshift(row); body = row;
      } else body = history;
    }
    await route.fulfill({ json: body });
  });
  await page.goto("/dashboard");
  await page.getByRole("button", {name: "Solo esenciales", exact:true}).click();
  await expect(page.getByRole("button", { name: "EcoCampo", exact: true })).toBeVisible();
}

test("AG y EcoCampo separados; aptitud, presupuesto e historial visibles y utilizables", async ({page}) => {
  await setup(page);
  await page.getByRole("button", {name: "EcoNexo AG", exact: true}).click();
  await expect(page.getByRole("heading", {name: "Lotes y decisiones de campo"})).toBeVisible();
  await expect(page.getByRole("navigation", {name: "Herramientas EcoCampo"})).toHaveCount(0);
  await page.getByRole("button", {name: "EcoCampo", exact: true}).click();
  await expect(page.getByRole("heading", {name: "Procesar evaluación de aptitud"})).toBeVisible();
  await expect(page.getByLabel("Lote a evaluar")).toHaveValue("lot-1");
  await page.getByLabel("Fecha de observación").fill(new Date().toISOString().slice(0,10));
  await page.getByLabel("Fuente, sensor, período de referencia e informe de campo").fill("Informe de prueba");
  await page.getByRole("button", {name: "Procesar evaluación y guardar", exact: true}).click();
  await expect(page.getByRole("status").filter({hasText: "Evaluación procesada"})).toBeVisible();
  await page.getByRole("button", {name: "Presupuesto forrajero", exact: true}).click();
  await page.getByLabel("Materia seca aprovechable medida (kg/ha)", {exact:true}).fill("1000");
  await page.getByLabel("Fracción de aprovechamiento prevista (%)", {exact:true}).fill("50");
  await page.getByLabel("Demanda por animal (kg MS/día)", {exact:true}).fill("10");
  await page.getByLabel("Días de pastoreo previstos", {exact:true}).fill("100");
  await page.getByRole("combobox", {name: "Especies forrajeras y calidad verificadas", exact:true}).selectOption("true");
  await page.getByRole("button", {name: "Calcular y guardar presupuesto", exact:true}).click();
  await expect(page.getByRole("status").filter({hasText: "5 animales"})).toBeVisible();
  await page.getByRole("button", {name: "Historial", exact:true}).click();
  await expect(page.getByRole("heading", {name: "Historial de evaluaciones"})).toBeVisible();
  await expect(page.getByText("5 animales durante el período declarado", {exact:false})).toBeVisible();
  await page.getByRole("button", {name: "Monitoreo NDVI", exact:true}).click();
  await expect(page.getByRole("button", {name: "Consultar últimos 30 días"})).toBeVisible();
});

test("EcoCampo sin lotes muestra cómo comenzar", async ({page}) => {
  await setup(page, true);
  await page.getByRole("button", {name: "EcoCampo", exact:true}).click();
  await page.getByRole("button", {name: "Crear primer lote"}).click();
  await expect(page.getByLabel("Nombre del lote", {exact:true})).toBeVisible();
  await expect(page.getByRole("button", {name: "Crear lote", exact:true})).toBeVisible();
});

test("EcoCampo precarga NDVI satelital y sugerencias del Centro de Comando", async ({page}) => {
  await page.addInitScript(() => sessionStorage.setItem("econexo_session", JSON.stringify({ access_token: "test", role: "admin", name: "Prueba", account_type: "institutional" })));
  await page.route("http://127.0.0.1:9/**", async route => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown = [];
    if (path === "/ecocampo/lots" || path === "/agro/lots") body = [{ id: "lot-1", name: "Lote de prueba", area_ha: 10, crop_key: "pastizal", crop_name: "Pastizal", is_active: true, advisories: [] }];
    if (path === "/kpis") body = { global_status: "normal" };
    if (path === "/agro/summary") body = { lots_total: 1, lots_active: 1, area_ha: 10, advisories_high: 0, advisories_medium: 0 };
    if (path.endsWith("/assessments")) body = [];
    if (path.endsWith("/ndvi")) body = [{ polygon: { type: "Polygon", coordinates: [[[0, 0]]] }, result: { series: [{ day: "2026-09-20", ndvi: 0.62, valid_pixel_pct: 88 }], source: "Sentinel-2 (prueba)", note: "" } }];
    if (path.endsWith("/conditions")) body = { as_of: "2026-09-22", precipitation_7d_mm: 10, balance_14d_mm: 5, soil_moisture_pct: 42, soil_moisture_ts: "2026-09-23T00:00:00Z", soil_moisture_source: "Nodo Norte a 1.2 km del lote", water_hint: true, flooding_hint: true, note: "Sugerencia automática" };
    await route.fulfill({ json: body });
  });
  await page.goto("/dashboard");
  await page.getByRole("button", {name: "Solo esenciales", exact:true}).click();
  await page.getByRole("button", {name: "EcoCampo", exact: true}).click();
  await expect(page.getByRole("heading", {name: "Procesar evaluación de aptitud"})).toBeVisible();
  await expect(page.getByLabel("NDVI medio del lote", {exact:true})).toHaveValue("0.62");
  await expect(page.getByLabel("Píxeles válidos del lote (%)", {exact:true})).toHaveValue("88");
  await expect(page.getByLabel("Fecha de observación")).toHaveValue("2026-09-20");
  await expect(page.getByRole("combobox", {name: "Agua suficiente y de calidad adecuada", exact:true})).toHaveValue("true");
  await expect(page.getByRole("combobox", {name: "Presencia de anegamiento", exact:true})).toHaveValue("true");
  await expect(page.getByText(/nodo norte a 1\.2 km del lote/i)).toBeVisible();
});