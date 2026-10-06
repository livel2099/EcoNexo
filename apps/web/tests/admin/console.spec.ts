import { test, expect, type Page } from "@playwright/test";

const orgId = "00000000-0000-4000-8000-000000000001";
const userId = "00000000-0000-4000-8000-000000000002";
const session = { access_token: "test-session", name: "Administración", email: "owner@example.com", role: "admin", org_id: orgId, platform_admin: true, account_type: "institutional", must_change_password: false };

async function mockConsole(page: Page) {
  const user = { id: userId, org_id: orgId, org_name: "Organización de prueba", name: "Responsable", email: "responsable@example.com", phone: "5493764000000", role: "admin", is_active: true, organization_active: false, auth_provider: "password", must_change_password: false, created_at: "2026-09-01T00:00:00Z", last_login_at: null };
  const org = { id: orgId, name: user.org_name, contact_name: user.name, contact_email: user.email, contact_phone: user.phone, is_active: false, access_status: "pending", municipality: "Posadas", province: "Misiones", vertical: "forestal", users_active: 1, users_total: 1, slug: "org-prueba", plan_name: "Municipal", subscription_status: "active" };
  const plan = { plan_key: "municipal", display_name: "Municipal", description: "Plan de prueba", entitlements: { included_modules: ["core"], max_users: 10 }, billing_period: "monthly", price_min_usd: 800 };
  let licenseStatus = "active";
  const changes: Array<{ url: string; body: Record<string, unknown> }> = [];
  await page.addInitScript((value) => { sessionStorage.setItem("econexo_session", JSON.stringify(value)); }, session);
  await page.route("http://localhost:3108/**", async (route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();
    if (method === "OPTIONS") return route.fulfill({ status: 204, headers: { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Methods": "*" } });
    let data: unknown = {};
    if (["PATCH", "POST"].includes(method)) {
      const body = route.request().postDataJSON() || {};
      changes.push({ url: url.pathname, body });
      if (url.pathname === `/platform/users/${userId}`) { Object.assign(user, body); org.contact_email = user.email; }
      if (url.pathname.endsWith("/cancel")) licenseStatus = "cancelled";
      if (url.pathname.endsWith("/reset-password")) user.must_change_password = true;
    }
    if (url.pathname === "/platform/summary") data = { organizations_active: 0, organizations_total: 1, users_total: 1, users_active: 1, platform_admins: 1, pending_license_requests: 0, logins_24h: 0 };
    if (url.pathname === "/platform/users") data = [user];
    if (url.pathname === "/platform/organizations") data = [org];
    if (url.pathname === "/platform/audit") data = [];
    if (url.pathname === "/platform/operations") data = {
      generated_at: "2026-10-06T12:00:00Z", stale_after_minutes: 30,
      metrics: { devices_total: 10, devices_stale: 3, latest_reading_at: null,
        alerts_pending: 2, alerts_confirmed: 5, alerts_discarded: 1,
        pipeline_degraded_24h: 1, latest_pipeline_at: null },
      integrations: [{ name: "MQTT", configured: true, detail: "Configuración sin prueba de disponibilidad." }],
      predictive_status: "not_validated", predictive_gaps: ["Validar anticipación con eventos independientes."],
    };
    if (url.pathname === "/subscriptions/me") data = { plan, entitlements: plan.entitlements, status: "active", available: true, usage: { users: 1, devices: 0, zones: 0, rules: 0, reports_this_month: 0 }, platform_admin: true, expiry_label: "sin vencimiento" };
    if (url.pathname === "/subscriptions/plans") data = [plan];
    if (url.pathname.includes("/requests")) data = [];
    if (url.pathname === "/subscriptions/platform/organizations") data = [{ org_id: orgId, org_name: user.org_name, municipality: "Posadas", plan_key: "municipal", display_name: "Municipal", status: licenseStatus, expires_at: null }];
    await route.fulfill({ json: data, headers: { "Access-Control-Allow-Origin": "*" } });
  });
  return changes;
}

test("diagnóstico operativo visible y sin desbordamiento en móvil", async ({ page }) => {
  await mockConsole(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/plataforma");
  await page.getByRole("button", { name: "Operación y predicción", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Predicción de incidentes pendiente de validación" })).toBeVisible();
  await expect(page.getByText("Validar anticipación con eventos independientes.")).toBeVisible();
  await expect(page.getByText("Configuración sin prueba de disponibilidad.")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
});

test("ingreso privado rechaza administrador de organización sin guardar sesión", async ({ page }) => {
  await page.route("http://localhost:3108/auth/login", (route) => route.fulfill({
    json: { ...session, platform_admin: false }, headers: { "Access-Control-Allow-Origin": "*" },
  }));
  await page.goto("/plataforma/ingreso");
  await page.getByLabel("Correo", { exact: true }).fill("admin@example.com");
  await page.getByLabel("Contraseña", { exact: true }).fill("TemporarySecure2026!");
  await page.getByRole("button", { name: "Ingresar", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Acceso reservado" })).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem("econexo_session"))).toBeNull();
});

test("ingreso privado exige cambiar la contraseña temporal", async ({ page }) => {
  await page.route("http://localhost:3108/auth/login", (route) => route.fulfill({
    json: { ...session, must_change_password: true }, headers: { "Access-Control-Allow-Origin": "*" },
  }));
  await page.goto("/plataforma/ingreso");
  await page.getByLabel("Correo", { exact: true }).fill(session.email);
  await page.getByLabel("Contraseña", { exact: true }).fill("TemporarySecure2026!");
  await page.getByRole("button", { name: "Ingresar", exact: true }).click();
  await expect(page).toHaveURL(/\/cambiar-contrasena$/);
});

test("portada pública, documentación y contacto en escritorio y móvil", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Conectamos datos");
  await expect(page.getByRole("link", { name: "Acceder", exact: true })).toHaveAttribute("href", "/login");
  await expect(page.getByRole("link", { name: /econexoargentina@gmail.com/ })).toHaveAttribute("href", "mailto:econexoargentina@gmail.com");
  await page.getByRole("button", { name: "Solo esenciales", exact: true }).click();
  await page.screenshot({ path: "../../output/landing-desktop.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole("link", { name: "Acceder", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.screenshot({ path: "../../output/landing-mobile.png", fullPage: true });
  await page.getByRole("link", { name: /GUÍA DE USO/ }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Documentación y primeros pasos");
});

test("corregir datos del contacto de una organización pendiente", async ({ page }) => {
  const changes = await mockConsole(page);
  await page.goto("/plataforma");
  await page.getByRole("button", { name: "Organizaciones", exact: true }).click();
  await page.getByRole("button", { name: "Editar contacto", exact: true }).click();
  await page.getByLabel("Nombre del usuario", { exact: true }).fill("Nombre corregido");
  await page.getByLabel("Correo de acceso", { exact: true }).fill("corregido@example.com");
  await page.getByLabel("Teléfono de contacto", { exact: true }).fill("5493764111111");
  await page.getByRole("button", { name: "Guardar cambios", exact: true }).click();
  await expect(page.getByText("Usuario actualizado en la auditoría global.")).toBeVisible();
  expect(changes[0]).toEqual({ url: `/platform/users/${userId}`, body: { name: "Nombre corregido", email: "corregido@example.com", phone: "5493764111111", role: "admin" } });
});

test("baja de licencia visible en móvil, con cancelación y confirmación", async ({ page }) => {
  const changes = await mockConsole(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/plataforma");
  await page.getByRole("button", { name: "Licencias", exact: true }).click();
  const cancel = page.getByRole("button", { name: "Dar de baja", exact: true });
  await expect(cancel).toBeVisible();
  page.once("dialog", (dialog) => dialog.dismiss());
  await cancel.click();
  expect(changes).toHaveLength(0);
  page.once("dialog", (dialog) => dialog.accept());
  await cancel.click();
  await expect(page.getByText("Licencia de Organización de prueba dada de baja.")).toBeVisible();
  await expect(cancel).toBeDisabled();
  expect(changes[0].url).toBe(`/subscriptions/platform/${orgId}/cancel`);
});

test("restablecer clave obliga al cambio de contraseña", async ({ page }) => {
  const changes = await mockConsole(page);
  await page.goto("/plataforma");
  await page.getByRole("button", { name: "Usuarios", exact: true }).click();
  page.on("dialog", (dialog) => dialog.accept(dialog.type() === "prompt" ? "TemporarySecure2026!" : undefined));
  await page.getByRole("button", { name: "Restablecer clave", exact: true }).click();
  await expect(page.getByText("Contraseña temporal asignada; el cambio será obligatorio.")).toBeVisible();
  expect(changes[0]).toEqual({ url: `/platform/users/${userId}/reset-password`, body: { temporary_password: "TemporarySecure2026!" } });
  await expect(page.getByText("cambio de clave pendiente")).toBeVisible();
});

test("el rol actualizado habilita Admin Core aun con licencia cancelada", async ({ page }) => {
  await mockConsole(page);
  await page.addInitScript((value) => { sessionStorage.setItem("econexo_session", JSON.stringify({ ...value, role: "visualizador", platform_admin: false })); }, session);
  await page.route("https://**", (route) => route.abort());
  await page.route("http://localhost:3108/auth/me", (route) => route.fulfill({ json: { ...session, platform_admin: false }, headers: { "Access-Control-Allow-Origin": "*" } }));
  for (const path of ["/alerts", "/devices", "/reports", "/zones", "/admin/users", "/admin/audit?limit=120", "/satellite/detections?hours=48", "/pipeline/runs?limit=1"]) {
    await page.route(`http://localhost:3108${path}`, (route) => route.fulfill({ json: [], headers: { "Access-Control-Allow-Origin": "*" } }));
  }
  await page.route("http://localhost:3108/kpis", (route) => route.fulfill({ status: 402, json: { detail: "La licencia no está activa. Revisá Admin Core → Suscripción" }, headers: { "Access-Control-Allow-Origin": "*" } }));
  await page.goto("/dashboard");
  await expect(page.getByRole("button", { name: "Admin Core", exact: true })).toBeVisible();
  await expect(page.getByRole("alert").filter({ hasText: "La licencia no está activa" })).toBeVisible();
  await page.getByRole("button", { name: "Abrir Admin Core", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Gobierno de la plataforma" })).toBeVisible();
  await page.getByRole("button", { name: "Suscripción", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Municipal", exact: true })).toBeVisible();
});
