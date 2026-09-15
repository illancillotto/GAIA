import { expect, test, type Page } from "@playwright/test";

const message = {
  id: "00000000-0000-0000-0000-000000000401",
  collaborator_id: "00000000-0000-0000-0000-000000000101",
  collaborator_name: "ROSSI MARIO",
  application_user_id: 7,
  user_label: "Mario Rossi",
  username: "mrossi",
  phone_e164: "+393331234567",
  text_body: "Ciao Mario, la timbratura risulta incompleta.",
  days: [{ work_date: "2026-09-14", problem: "missing_exit", detail: "uscita mancante" }],
  status: "READ",
  provider: "waha",
  provider_message_id: "wa-1",
  error_code: null,
  error_message: null,
  created_at: "2026-09-15T07:30:00Z",
  updated_at: "2026-09-15T07:35:00Z",
  delivered_at: "2026-09-15T07:31:00Z",
  read_at: "2026-09-15T07:35:00Z",
};

async function mockDashboard(page: Page): Promise<void> {
  await page.route("**/api/auth/login", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ access_token: "whatsapp-e2e", token_type: "bearer" }) }));
  await page.route("**/api/auth/me", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: 1, username: "admin", email: "admin@example.local", role: "admin", is_active: true, module_accessi: true, module_presenze: true, enabled_modules: ["accessi", "presenze"] }) }));
  await page.route("**/api/auth/my-permissions", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ sections: [], granted_keys: [] }) }));
  await page.route("**/api/dashboard/summary", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ nas_users: 0, nas_groups: 0, shares: 0, reviews: 0, snapshots: 0, sync_runs: 0 }) }));
  await page.route("**/api/presenze/whatsapp/dashboard", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ provider_enabled: true, provider: "dry_run", session_status: "dry_run", session_detail: "Nessun messaggio viene inviato", cron: "30 9 * * 1-5", next_run_at: "2026-09-16T07:30:00Z", send_window: "08:00-19:00", max_per_run: 40, sent_total: 12, delivered_total: 10, read_total: 8, failed_total: 1, uncertain_total: 1, opted_out_total: 1 }) }));
  await page.route("**/api/presenze/whatsapp/messages**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [message], total: 1, page: 1, page_size: 25 }) }));
  await page.route("**/api/presenze/whatsapp/opt-outs", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "[]" }));
  await page.route("**/api/presenze/whatsapp/preview", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ generated_at: "2026-09-15T08:00:00Z", ready: [{ collaborator_id: message.collaborator_id, collaborator_name: message.collaborator_name, application_user_id: 7, phone_e164: message.phone_e164, days: message.days, message_text: message.text_body, ready: true, reason: null }], skipped: [] }) }));
}

async function loginAndOpen(page: Page): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Username o email").fill("admin");
  await page.locator("input#password").fill("password");
  await page.getByRole("button", { name: "Accedi alla piattaforma" }).click();
  await page.waitForURL("**/");
  await page.goto("/presenze/whatsapp");
  await expect(page.getByRole("heading", { name: "Ogni messaggio, fino alla lettura." })).toBeVisible();
}

for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
  test(`dashboard WhatsApp intuitiva ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await mockDashboard(page);
    await loginAndOpen(page);
    const cards = page.locator(".metric-card");
    await expect(cards).toHaveCount(4);
    const heights = await cards.evaluateAll((items) => items.map((item) => Math.round(item.getBoundingClientRect().height)));
    expect(new Set(heights).size).toBe(1);
    await page.getByRole("button", { name: "Apri", exact: true }).click();
    const detail = page.getByRole("dialog", { name: "Mario Rossi" });
    await expect(detail).toBeVisible();
    const detailBox = await detail.locator("article").boundingBox();
    expect(detailBox?.height ?? 0).toBeGreaterThan(viewport.height * 0.8);
    await detail.getByRole("button", { name: "Chiudi", exact: true }).click();
    await page.getByRole("button", { name: "Apri anteprima" }).click();
    const preview = page.getByRole("dialog", { name: "Prossimi promemoria" });
    await expect(preview.getByText("ROSSI MARIO")).toBeVisible();
    const previewBox = await preview.locator(":scope > article").boundingBox();
    expect(previewBox?.width ?? 0).toBeGreaterThan(viewport.width * 0.85);
  });
}
