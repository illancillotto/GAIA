import { test, expect, type Page } from "@playwright/test";
import * as XLSX from "xlsx";

function buildCapacitasWorkbookBuffer(): Buffer {
  const rows = [
    {
      ANNO: "2025",
      PVC: "95",
      COM: "165",
      CCO: `PW-${Date.now()}`,
      FRA: "1",
      DISTRETTO: "10",
      "Unnamed: 7": "Distretto 10",
      COMUNE: "Arborea",
      SEZIONE: "",
      FOGLIO: "5",
      PARTIC: "120",
      SUB: "1",
      "SUP.CATA.": "1000",
      "SUP.IRRIGABILE": "1000",
      "Ind. Spese Fisse": "1.5",
      "Imponibile s.f.": "1500",
      "ESENTE 0648": "false",
      "ALIQUOTA 0648": "0.1",
      "IMPORTO 0648": "150",
      "ALIQUOTA 0985": "0.2",
      "IMPORTO 0985": "300",
      DENOMINAZIONE: "Playwright Test",
      "CODICE FISCALE": "Dnifse64c01l122y",
    },
  ];
  const worksheet = XLSX.utils.json_to_sheet(rows);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Ruoli 2025");
  return XLSX.write(workbook, { type: "buffer", bookType: "xlsx" }) as Buffer;
}

async function loginAsAdmin(page: Page) {
  const username = process.env.PLAYWRIGHT_ADMIN_USERNAME ?? "admin";
  const password = process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? "#0r1st4n3s1";

  await page.goto("/login");
  await page.getByLabel("Username o email").fill(username);
  await page.locator("input#password").fill(password);
  await page.getByRole("button", { name: "Accedi alla piattaforma" }).click();
  await page.waitForURL("**/");
}

test("admin completes catasto import wizard through report step", async ({ page }) => {
  await loginAsAdmin(page);
  await page.goto("/catasto/import");

  await expect(page.getByText("Wizard import Capacitas (Ruoli) con polling stato e report anomalie.")).toBeVisible();

  await page.getByLabel("File Excel").setInputFiles({
    name: "capacitas-playwright.xlsx",
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: buildCapacitasWorkbookBuffer(),
  });

  await page.getByRole("button", { name: "Avvia import" }).click();

  await expect(page.getByText("Stato import")).toBeVisible();
  await expect(page.getByText("Contatori anomalie")).toBeVisible({ timeout: 45_000 });
  await expect(page.getByText("Preview (prime 50)")).toBeVisible();
  await expect(page.getByText("Lista anomalie", { exact: true })).toBeVisible();
});

test("catasto import wizard shows empty report state when batch has no anomalies", async ({ page }) => {
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
  await page.route("**/api/catasto/import/history**", async (route) => {
    const status = new URL(route.request().url()).searchParams.get("status");
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(
        status === "failed"
          ? []
          : [
              {
                id: "00000000-0000-0000-0000-000000000110",
                filename: "capacitas-history.xlsx",
                tipo: "capacitas_ruolo",
                anno_campagna: 2025,
                hash_file: "mock-history",
                righe_totali: 12,
                righe_importate: 12,
                righe_anomalie: 2,
                status: "completed",
                report_json: null,
                errore: null,
                created_at: "2026-04-21T09:45:00Z",
                completed_at: "2026-04-21T09:46:00Z",
                created_by: 1,
              },
            ],
      ),
    });
  });
  await page.route("**/api/catasto/import/capacitas**", async (route) => {
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ batch_id: "00000000-0000-0000-0000-000000000111", status: "processing" }),
    });
  });
  await page.route("**/api/catasto/import/00000000-0000-0000-0000-000000000111/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "00000000-0000-0000-0000-000000000111",
        filename: "capacitas-empty.xlsx",
        tipo: "capacitas_ruolo",
        anno_campagna: 2025,
        hash_file: "mock-empty",
        righe_totali: 1,
        righe_importate: 1,
        righe_anomalie: 0,
        status: "completed",
        report_json: {
          anno_campagna: 2025,
          righe_totali: 1,
          righe_importate: 1,
          righe_con_anomalie: 0,
          anomalie: {},
          preview_anomalie: [],
          distretti_rilevati: [10],
          comuni_rilevati: ["Arborea"],
        },
        errore: null,
        created_at: "2026-04-21T10:00:00Z",
        completed_at: "2026-04-21T10:00:02Z",
        created_by: 1,
      }),
    });
  });
  await page.route("**/api/catasto/import/00000000-0000-0000-0000-000000000111/report**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 50 }),
    });
  });

  await page.goto("/catasto/import");
  await expect(page.getByText("Audit import")).toBeVisible();
  await expect(page.getByText("Batch totali")).toBeVisible();
  await expect(page.getByText("Ultimo completato")).toBeVisible();
  await expect(page.getByText("Storico import recenti")).toBeVisible();
  await expect(page.getByText("capacitas-history.xlsx")).toBeVisible();
  await page.getByLabel("Stato").selectOption("failed");
  await expect(page.getByText("Nessuno storico disponibile")).toBeVisible();
  await page.getByLabel("Stato").selectOption("");
  await expect(page.getByText("capacitas-history.xlsx")).toBeVisible();
  await page.getByLabel("File Excel").setInputFiles({
    name: "capacitas-empty.xlsx",
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: buildCapacitasWorkbookBuffer(),
  });
  await page.getByRole("button", { name: "Avvia import" }).click();

  await expect(page.getByText("Sintesi batch")).toBeVisible();
  await expect(page.getByText("Anno campagna")).toBeVisible();
  await expect(page.getByText("Arborea")).toBeVisible();
  await expect(page.getByText("Contatori anomalie", { exact: true })).toBeVisible();
  await expect(page.getByText("Nessun contatore disponibile")).toBeVisible();
  await expect(page.getByText("Nessuna preview")).toBeVisible();
  await expect(page.getByText("Nessuna anomalia")).toBeVisible();
});

test("catasto import wizard shows batch failure details", async ({ page }) => {
  await loginAsAdmin(page);

  await page.route("**/api/catasto/import/capacitas**", async (route) => {
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ batch_id: "00000000-0000-0000-0000-000000000222", status: "processing" }),
    });
  });
  await page.route("**/api/catasto/import/00000000-0000-0000-0000-000000000222/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "00000000-0000-0000-0000-000000000222",
        filename: "capacitas-failed.xlsx",
        tipo: "capacitas_ruolo",
        anno_campagna: 2025,
        hash_file: "mock-failed",
        righe_totali: 1,
        righe_importate: 0,
        righe_anomalie: 0,
        status: "failed",
        report_json: null,
        errore: "Workbook non valido o foglio Ruoli mancante",
        created_at: "2026-04-21T10:00:00Z",
        completed_at: "2026-04-21T10:00:01Z",
        created_by: 1,
      }),
    });
  });
  await page.route("**/api/catasto/import/00000000-0000-0000-0000-000000000222/report**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 50 }),
    });
  });

  await page.goto("/catasto/import");
  await page.getByLabel("File Excel").setInputFiles({
    name: "capacitas-failed.xlsx",
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: buildCapacitasWorkbookBuffer(),
  });
  await page.getByRole("button", { name: "Avvia import" }).click();

  await expect(page.getByText("Import fallito")).toBeVisible();
  await expect(page.getByText("Workbook non valido o foglio Ruoli mancante")).toBeVisible();
  await expect(page.getByText("Nessun contatore disponibile")).toBeVisible();
});
