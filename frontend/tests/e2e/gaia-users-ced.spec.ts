import { expect, test } from "@playwright/test";

test("CED opens user management without NAS and creates only standard accounts", async ({ page }) => {
  const createdPayloads: Record<string, unknown>[] = [];
  const ced = { id: 91, username: "ced-e2e", email: "ced@example.local", role: "ced", is_active: true, enabled_modules: [] };
  await page.addInitScript(() => localStorage.setItem("gaia.access_token", "synthetic-ced-session"));
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const request = route.request();
    if (path === "/api/admin/users" && request.method() === "POST") {
      const payload = request.postDataJSON() as Record<string, unknown>;
      createdPayloads.push(payload);
      await route.fulfill({ status: 201, json: {
        ...payload, id: 101, created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
        last_login_at: null, last_login_ip: null, login_count: 0, enabled_modules: [],
      } });
      return;
    }
    const json = path === "/api/auth/me" ? ced
      : path === "/api/auth/my-permissions" ? { sections: [], granted_keys: [] }
      : path === "/api/admin/users" ? { items: [], total: 0 }
      : path === "/api/sections" ? []
      : path.endsWith("/send-invite") ? { user_id: 101, email: "standard@example.local", email_sent: true }
      : path === "/api/auth/presence/summary" ? { window_minutes: 15, active_users: 0, visible_users: 0, items: [], by_module: [] }
      : { nas_users: 0, nas_groups: 0, shares: 0, reviews: 0, snapshots: 0, sync_runs: 0 };
    await route.fulfill({ json });
  });
  await page.goto("/gaia/users");
  await expect(page.getByText("Nuovo utente GAIA", { exact: true })).toBeVisible();
  const editor = page.locator("article").filter({ has: page.getByText("Nuovo utente GAIA", { exact: true }) });
  await expect(editor.getByText("NAS Control", { exact: true })).toHaveCount(0);
  await expect(editor.getByText("Rete", { exact: true })).toHaveCount(0);
  await expect(editor.getByRole("combobox", { name: /^Ruolo/ }).locator("option")).toHaveText(["Operatore", "Viewer", "Reviewer", "HR Manager"]);
  await editor.getByLabel("Username", { exact: true }).fill("ced-standard");
  await editor.getByLabel("Email", { exact: true }).fill("standard@example.local");
  await editor.getByRole("button", { name: "Crea e apri permessi sezione" }).click();
  await expect.poll(() => createdPayloads.length).toBe(1);
  expect(createdPayloads[0]).toMatchObject({ role: "viewer", module_accessi: false, module_rete: false });
  await expect(page.getByText("Utente ced-standard creato e mail di attivazione inviata.", { exact: true })).toBeVisible();
});

test("a standard viewer cannot open GAIA user management", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("gaia.access_token", "synthetic-viewer-session"));
  const managementRequests: string[] = [];
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.startsWith("/api/admin/users")) managementRequests.push(path);
    const json = path === "/api/auth/me"
      ? { id: 92, username: "viewer-e2e", role: "viewer", is_active: true, enabled_modules: [] }
      : path === "/api/auth/my-permissions" ? { sections: [], granted_keys: [] } : {};
    await route.fulfill({ json });
  });
  await page.goto("/gaia/users");
  await expect(page.getByText("Accesso non autorizzato", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Crea e apri permessi sezione" })).toHaveCount(0);
  expect(managementRequests).toEqual([]);
});
