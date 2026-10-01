import { expect, test } from "@playwright/test";
import { collaborator, dailyRecord } from "./presenze-operations.fixtures";

test("manual voucher and background INAZ correction survive refresh without double count", async ({ page }) => {
  let record = { ...dailyRecord, work_date: "2026-08-26", meal_voucher_manual: false, meal_voucher_automatic: true, meal_voucher_count: 1, meal_voucher_sources: ["automatic"], effective_extra_minutes: 120, operational_status: "blocking", operational_missing_minutes: 60, detail_anomalies: [{ anomaliagiornata: "OREM-Ore mancanti" }] };
  let job: Record<string, unknown> | null = null;
  let queued = 0;
  let saved = 0;
  await page.addInitScript(() => window.localStorage.setItem("gaia.access_token", "synthetic-test-session"));
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname.replace(/^\/api/, "");
    let body: unknown = {};
    if (path === "/auth/me") body = { id: 12, role: "admin", username: "test-admin", is_active: true, module_presenze: true, module_accessi: true, enabled_modules: ["presenze", "accessi"] };
    else if (path === "/auth/my-permissions") body = { sections: [], granted_keys: ["presenze.giornaliere", "presenze.giornaliera-individuale"] };
    else if (path === "/presenze/access-context") body = { can_view_all_data: true, can_view_all_credentials: true, can_manage_supervisors: true, is_supervisor: false, assigned_collaborators_count: 1 };
    else if (path === "/presenze/collaborators") body = { items: [collaborator], total: 1, page: 1, page_size: 200 };
    else if (path === "/presenze/credentials") body = [{ id: 7, active: true, label: "Test credential" }];
    else if (path === "/presenze/sync/config") body = { credential_id: 7, job_enabled: false };
    else if (path === "/presenze/sync/jobs") {
      if (route.request().method() === "POST") {
        const payload = route.request().postDataJSON();
        expect(payload.collaborator_limit).toBeNull();
        expect(payload.employee_codes).toBeNull();
        queued += 1;
        job = { id: "test-job", status: "pending", credential_id: 7, period_start: "2026-08-01", period_end: "2026-08-31", records_errors: 0, params_json: {}, finished_at: null };
        body = job;
      } else {
        if (job) {
          job = { ...job, status: "completed", finished_at: "2026-10-01T09:00:00Z" };
          record = { ...record, operational_status: "ok", operational_missing_minutes: 0, detail_anomalies: [] };
        }
        body = { items: job ? [job] : [], total: job ? 1 : 0 };
      }
    } else if (path === "/presenze/giornaliere/matrix" || path === "/presenze/giornaliere") body = { items: [record], total: 1, page: 1, page_size: 5000 };
    else if (path === "/presenze/giornaliere/" + record.id) {
      if (route.request().method() === "PATCH") {
        saved += 1;
        record = { ...record, meal_voucher_manual: route.request().postDataJSON().meal_voucher_manual, meal_voucher_sources: ["automatic", "manual"] };
      }
      body = record;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });
  await page.goto("/presenze/giornaliere");
  await page.getByLabel("Mese operativo").fill("2026-08");
  await page.getByTitle(/2026-08-26 · GAIA:/).click();
  await page.getByLabel("Buono pasto manuale").click();
  await expect(page.getByLabel("Buono pasto manuale")).toBeChecked();
  await expect(page.getByText(/Buono pasto: 1/)).toBeVisible();
  expect(saved).toBe(1);
  await page.getByRole("button", { name: "Chiudi ✕", exact: true }).click();
  await page.getByRole("button", { name: "Sincronizza da INAZ", exact: true }).click();
  await expect(page.getByRole("button", { name: "Sincronizzazione in corso" })).toBeDisabled();
  await expect(page.getByText("Sincronizzazione completata")).toBeVisible();
  expect(queued).toBe(1);
  await page.getByTitle(/2026-08-26 · GAIA:/).click();
  await expect(page.getByText("GAIA bloccante", { exact: true })).toHaveCount(0);
  await expect(page.getByLabel("Buono pasto manuale")).toBeChecked();
  await page.reload();
  await page.getByLabel("Mese operativo").fill("2026-08");
  await expect(page.getByText("Sincronizzazione completata")).toBeVisible();
  await page.getByTitle(/2026-08-26 · GAIA:/).click();
  await expect(page.getByLabel("Buono pasto manuale")).toBeChecked();
  await expect(page.getByText(/Buono pasto: 1/)).toBeVisible();
});
