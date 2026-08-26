import { expect, test, type Page } from "@playwright/test";

const collaborator = {
  id: "00000000-0000-0000-0000-000000000101",
  owner_user_id: 77,
  application_user_id: 77,
  kint: "10159",
  kkint: "{smoke}",
  employee_code: "1854",
  company_code: "53",
  company_label: "53 - CBO",
  name: "SUBORDINATO ORGANIGRAMMA",
  birth_date: "1980-01-01",
  contract_kind: "impiegato",
  operai_group: null,
  standard_daily_minutes: 420,
  is_active: true,
  last_seen_at: "2026-08-16T09:00:00Z",
  created_at: "2026-08-16T09:00:00Z",
  updated_at: "2026-08-16T09:00:00Z",
};

const dailyRecord = {
  id: "00000000-0000-0000-0000-000000000201",
  collaborator_id: collaborator.id,
  owner_user_id: 77,
  application_user_id: 77,
  work_date: "2026-08-16",
  schedule_code: "IMP1_STD",
  teo_minutes: 420,
  ordinary_minutes: 420,
  absence_minutes: 0,
  justified_minutes: 0,
  maggiorazione_minutes: 0,
  mpe_minutes: 0,
  straordinario_minutes: 0,
  km_value: null,
  trasferta_minutes: null,
  trasferta_montano: false,
  reperibilita_unit: "none",
  reperibilita_quantity: null,
  override_straordinario_minutes: null,
  override_mpe_minutes: null,
  manual_note: null,
  request_type: null,
  request_description: null,
  request_status: null,
  request_authorized_by: null,
  resolved_absence_cause: null,
  validation_status: "pending",
  validated_by_user_id: null,
  validated_at: null,
  validation_note: null,
  effective_straordinario_minutes: 0,
  effective_mpe_minutes: 0,
  effective_extra_minutes: 0,
  operational_status: "ok",
  operational_formula_code: "IMP1_STD",
  operational_expected_minutes: 420,
  operational_worked_minutes: 420,
  operational_missing_minutes: 0,
  operational_mpe_minutes: 0,
  operational_notes: [],
  stato: "Giornata regolare",
  evidenze: null,
  raw_weekday: "D",
  detail_title: null,
  detail_status: "Giornata regolare",
  detail_programmed_schedule: "IMP1_STD",
  detail_effective_schedule: null,
  detail_time_slots: "08:00 - 15:00",
  detail_schedule_type: null,
  detail_theoretical_hours: "07:00",
  detail_absence_hours: "00:00",
  detail_day_summary: {},
  detail_day_totals: {},
  detail_requests: [],
  detail_anomalies: [],
  detail_punch_rows: [],
  detail_text: null,
  detail_error: null,
  special_day: false,
  raw_payload_json: {},
  source_job_id: null,
  created_at: "2026-08-16T09:00:00Z",
  updated_at: "2026-08-16T09:00:00Z",
  punches: [],
};

async function openHierarchyDailyRecord(page: Page, canApprove: boolean) {
  await page.route("**/api/auth/login", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ access_token: "playwright-presenze-hierarchy", token_type: "bearer" }),
    });
  });
  await page.route("**/api/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: 12,
        username: canApprove ? "dirigente_smoke" : "caporeparto_read_smoke",
        email: "smoke@example.local",
        role: "viewer",
        is_active: true,
        module_accessi: true,
        module_rete: false,
        module_inventario: false,
        module_catasto: false,
        module_utenze: false,
        module_operazioni: false,
        module_riordino: false,
        module_ruolo: false,
        module_presenze: true,
        enabled_modules: ["accessi", "presenze"],
      }),
    });
  });
  await page.route("**/api/auth/my-permissions", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        sections: [
          {
            section_key: "presenze.giornaliere",
            section_label: "Giornaliere",
            module: "presenze",
            is_granted: true,
            source: "smoke",
          },
        ],
        granted_keys: ["presenze.giornaliere"],
      }),
    });
  });
  await page.route("**/api/presenze/access-context", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        can_view_all_data: false,
        can_view_all_credentials: false,
        can_manage_supervisors: false,
        is_supervisor: canApprove,
        assigned_collaborators_count: 1,
      }),
    });
  });
  await page.route("**/api/presenze/collaborators?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [collaborator], total: 1, page: 1, page_size: 200 }),
    });
  });
  await page.route("**/api/presenze/giornaliere/matrix?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [dailyRecord], total: 1, page: 1, page_size: 5000 }),
    });
  });
  await page.route(`**/api/presenze/giornaliere/${dailyRecord.id}`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(dailyRecord) });
  });

  const username = process.env.PLAYWRIGHT_ADMIN_USERNAME ?? "admin";
  const password = process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? "#0r1st4n3s1";
  await page.goto("/login");
  await page.getByLabel("Username o email").fill(username);
  await page.locator("input#password").fill(password);
  await page.getByRole("button", { name: "Accedi alla piattaforma" }).click();
  await page.waitForURL("**/");
  await page.goto("/presenze/giornaliere");
  await expect(page.getByText("SUBORDINATO ORGANIGRAMMA").first()).toBeVisible();
  await expect(page.getByText("PERSONALE NON ASSEGNATO")).toHaveCount(0);
  await page.getByTitle(/2026-08-16/).click();
  await expect(page.getByText(/2026-08-16 .* SUBORDINATO ORGANIGRAMMA/)).toBeVisible();
}

test("capo reparto read-only vede solo il subordinato senza azioni approve", async ({ page }) => {
  await openHierarchyDailyRecord(page, false);
  await expect(page.getByRole("button", { name: "Valida giornaliera" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Riapri validazione" })).toHaveCount(0);
});

test("dirigente con approve vede il subordinato e le azioni di validazione", async ({ page }) => {
  await openHierarchyDailyRecord(page, true);
  await expect(page.getByRole("button", { name: "Valida giornaliera" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Riapri validazione" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Salva rettifiche" })).toBeDisabled();
});
