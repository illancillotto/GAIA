import { test, expect, type Page } from "@playwright/test";

async function loginAsAdmin(page: Page) {
  const username = process.env.PLAYWRIGHT_ADMIN_USERNAME ?? "admin";
  const password = process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? "#0r1st4n3s1";

  await page.goto("/login");
  await page.getByLabel("Username o email").fill(username);
  await page.locator("input#password").fill(password);
  await page.getByRole("button", { name: "Accedi alla piattaforma" }).click();
  await page.waitForURL("**/");
}

test("admin opens catasto import detail page for a completed batch", async ({ page }) => {
  await loginAsAdmin(page);

  await page.route("**/api/catasto/import/summary**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        tipo: "capacitas_ruolo",
        totale_batch: 8,
        processing_batch: 1,
        completed_batch: 6,
        failed_batch: 1,
        replaced_batch: 0,
        ultimo_completed_at: "2026-04-21T09:46:00Z",
      }),
    });
  });

  await page.route("**/api/catasto/import/00000000-0000-0000-0000-000000000333/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "00000000-0000-0000-0000-000000000333",
        filename: "capacitas-detail.xlsx",
        tipo: "capacitas_ruolo",
        anno_campagna: 2025,
        hash_file: "mock-detail",
        righe_totali: 12,
        righe_importate: 12,
        righe_anomalie: 2,
        status: "completed",
        report_json: {
          anno_campagna: 2025,
          righe_totali: 12,
          righe_importate: 12,
          righe_con_anomalie: 2,
          anomalie: {
            "VAL-02-cf_invalido": { count: 1 },
            "VAL-04-comune_invalido": { count: 1 },
          },
          preview_anomalie: [
            { riga: 3, tipo: "VAL-02-cf_invalido", cf_raw: "BADCF" },
          ],
          distretti_rilevati: [10, 12],
          comuni_rilevati: ["Arborea", "Cabras"],
        },
        errore: null,
        created_at: "2026-04-21T09:45:00Z",
        completed_at: "2026-04-21T09:46:00Z",
        created_by: 1,
      }),
    });
  });

  await page.route("**/api/catasto/import/00000000-0000-0000-0000-000000000333/report**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            id: "00000000-0000-0000-0000-000000000777",
            particella_id: null,
            utenza_id: "00000000-0000-0000-0000-000000000666",
            anno_campagna: 2025,
            tipo: "VAL-02-cf_invalido",
            severita: "error",
            descrizione: "CF non valido",
            dati_json: { cf_raw: "BADCF" },
            status: "aperta",
            note_operatore: null,
            assigned_to: null,
            segnalazione_id: null,
            created_at: "2026-04-21T09:46:00Z",
            updated_at: "2026-04-21T09:46:00Z",
          },
        ],
        total: 1,
        page: 1,
        page_size: 50,
      }),
    });
  });

  await page.goto("/catasto/import/00000000-0000-0000-0000-000000000333");

  await expect(page.getByRole("heading", { name: "Dettaglio import", level: 2 })).toBeVisible();
  await expect(page.getByText("capacitas-detail.xlsx")).toBeVisible();
  await expect(page.getByText("Sintesi batch")).toBeVisible();
  await expect(page.getByText("Distretti rilevati")).toBeVisible();
  await expect(page.getByText("Arborea, Cabras")).toBeVisible();
  await expect(page.getByText("Preview (prime 50)")).toBeVisible();
  await expect(page.getByText("Lista anomalie")).toBeVisible();
  await expect(page.getByRole("cell", { name: "VAL-02-cf_invalido" }).first()).toBeVisible();
});

test("admin opens catasto import detail page for a distretti batch", async ({ page }) => {
  await loginAsAdmin(page);

  await page.route("**/api/catasto/import/00000000-0000-0000-0000-000000000553/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "00000000-0000-0000-0000-000000000553",
        filename: "distretti-detail.zip",
        tipo: "shapefile_distretti",
        anno_campagna: null,
        hash_file: null,
        righe_totali: 44,
        righe_importate: 42,
        righe_anomalie: 2,
        status: "completed",
        report_json: {
          righe_staging: 44,
          distretti_validi: 42,
          distretti_inseriti: 1,
          distretti_aggiornati: 4,
          distretti_invariati: 37,
          distretti_versionati: 5,
          distretti_assenti_nello_snapshot: 2,
          righe_scartate_senza_numero: 1,
          righe_scartate_senza_geometria: 1,
          comuni_rilevati: [],
        },
        errore: null,
        created_at: "2026-04-29T09:10:30Z",
        completed_at: "2026-04-29T09:12:00Z",
        created_by: 1,
      }),
    });
  });

  await page.route("**/api/catasto/import/00000000-0000-0000-0000-000000000553/report**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 50 }),
    });
  });

  await page.goto("/catasto/import/00000000-0000-0000-0000-000000000553");

  await expect(page.getByRole("heading", { name: "Dettaglio import", level: 2 })).toBeVisible();
  await expect(page.getByText("distretti-detail.zip")).toBeVisible();
  await expect(page.getByText("Sintesi batch")).toBeVisible();
  await expect(page.getByText("Righe totali")).toBeVisible();
  await expect(page.getByText("Nessun contatore disponibile")).toBeVisible();
  await expect(page.getByText("Nessuna preview")).toBeVisible();
});
