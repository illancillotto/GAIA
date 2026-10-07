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

function buildDistrettiWorkbookBuffer(): Buffer {
  const worksheet = XLSX.utils.json_to_sheet([
    { ANNO: 2025, N_DISTRETTO: 10, DISTRETTO: "Distretto 10", COMUNE: "Arborea", SEZIONE: "", FOGLIO: "5", PARTIC: "120", SUB: "1" },
  ]);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Distretti");
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

async function mockCapacitasPreview(page: Page, filename: string) {
  await page.route("**/api/catasto/import/capacitas/preview", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        filename,
        anno_campagna: 2025,
        file_hash: "mock-preview-hash-123456",
        is_exact_duplicate: false,
        duplicate_batch: null,
        active_batch: null,
        summary: { nuove: 1, modificate: 0, invariate: 0, rimosse: 0 },
        preview_items: [],
        warnings: [],
      }),
    });
  });
}

test("admin completes catasto import wizard through report step", async ({ page }) => {
  await loginAsAdmin(page);

  await page.route("**/api/catasto/import/summary**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        tipo: "capacitas_ruolo",
        totale_batch: 9,
        processing_batch: 0,
        completed_batch: 8,
        failed_batch: 1,
        replaced_batch: 4,
        ultimo_completed_at: "2026-04-30T05:49:06Z",
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
                id: "00000000-0000-0000-0000-000000000300",
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
                created_at: "2026-04-30T05:30:00Z",
                completed_at: "2026-04-30T05:31:00Z",
                created_by: 1,
              },
            ],
      ),
    });
  });
  await page.route("**/api/catasto/import/capacitas/preview", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        filename: "capacitas-playwright.xlsx",
        anno_campagna: 2025,
        file_hash: "mock-preview-hash-123456",
        is_exact_duplicate: false,
        duplicate_batch: null,
        active_batch: {
          id: "00000000-0000-0000-0000-000000000300",
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
          created_at: "2026-04-30T05:30:00Z",
          completed_at: "2026-04-30T05:31:00Z",
          created_by: 1,
        },
        summary: {
          nuove: 1,
          modificate: 1,
          invariate: 0,
          rimosse: 0,
        },
        preview_items: [
          {
            key: "PW-001|165|5|120|1|DNIFSE64C01L122Y|Playwright Test",
            change_type: "changed",
            cco: "PW-001",
            cod_comune_capacitas: 165,
            foglio: "5",
            particella: "120",
            subalterno: "1",
            codice_fiscale: "DNIFSE64C01L122Y",
            denominazione: "Playwright Test",
            changed_fields: ["importo_0985"],
          },
          {
            key: "PW-002|165|6|121|1|DNIFSE64C01L122Y|Playwright Test 2",
            change_type: "new",
            cco: "PW-002",
            cod_comune_capacitas: 165,
            foglio: "6",
            particella: "121",
            subalterno: "1",
            codice_fiscale: "DNIFSE64C01L122Y",
            denominazione: "Playwright Test 2",
            changed_fields: [],
          },
        ],
        warnings: [],
      }),
    });
  });
  await page.route("**/api/catasto/import/capacitas", async (route) => {
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ batch_id: "00000000-0000-0000-0000-000000000301", status: "processing" }),
    });
  });
  await page.route("**/api/catasto/import/00000000-0000-0000-0000-000000000301/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "00000000-0000-0000-0000-000000000301",
        filename: "capacitas-playwright.xlsx",
        tipo: "capacitas_ruolo",
        anno_campagna: 2025,
        hash_file: "mock-success",
        righe_totali: 2,
        righe_importate: 2,
        righe_anomalie: 2,
        status: "completed",
        report_json: {
          anno_campagna: 2025,
          righe_totali: 2,
          righe_importate: 2,
          righe_con_anomalie: 2,
          anomalie: {
            "VAL-02-cf_invalido": { count: 1 },
            "VAL-07-importi": { count: 1 },
          },
          preview_anomalie: [
            { riga: 2, tipo: "VAL-02-cf_invalido", cf_raw: "AAAAAA00A00A000A" },
            { riga: 3, tipo: "VAL-07-importi", expected: 300, found: 330 },
          ],
          distretti_rilevati: [10],
          comuni_rilevati: ["Arborea"],
        },
        errore: null,
        created_at: "2026-04-30T05:49:00Z",
        completed_at: "2026-04-30T05:49:06Z",
        created_by: 1,
      }),
    });
  });
  await page.route("**/api/catasto/import/00000000-0000-0000-0000-000000000301/report**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            id: "00000000-0000-0000-0000-000000000401",
            particella_id: null,
            utenza_id: "00000000-0000-0000-0000-000000000501",
            anno_campagna: 2025,
            tipo: "VAL-02-cf_invalido",
            severita: "error",
            descrizione: "Codice fiscale non valido",
            dati_json: { cf_raw: "AAAAAA00A00A000A" },
            status: "aperta",
            note_operatore: null,
            assigned_to: null,
            segnalazione_id: null,
            created_at: "2026-04-30T05:49:05Z",
            updated_at: "2026-04-30T05:49:05Z",
          },
        ],
        total: 1,
        page: 1,
        page_size: 50,
      }),
    });
  });

  await page.goto("/catasto/import");

  await expect(page.getByText("Wizard import Catasto/GIS con polling stato, audit batch e report di finalizzazione.")).toBeVisible();

  await page.locator('input[type="file"]').first().setInputFiles({
    name: "capacitas-playwright.xlsx",
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: buildCapacitasWorkbookBuffer(),
  });

  await page.getByRole("button", { name: "Analizza file" }).click();
  await expect(page.getByText("Preview import Capacitas")).toBeVisible();
  await expect(page.getByText("Nuove")).toBeVisible();
  await page.getByRole("button", { name: "Conferma nuovo snapshot" }).click();

  await expect(page.getByText("Sintesi batch")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("Contatori anomalie")).toBeVisible({ timeout: 45_000 });
  await expect(page.getByText("Preview (prime 50)")).toBeVisible();
  await expect(page.getByText("Lista anomalie", { exact: true })).toBeVisible();
});

test("catasto import wizard shows empty report state when batch has no anomalies", async ({ page }) => {
  await loginAsAdmin(page);
  await mockCapacitasPreview(page, "capacitas-empty.xlsx");

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
  await page.route("**/api/catasto/import/capacitas", async (route) => {
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
  await page.locator("#catasto-import-capacitas-file").setInputFiles({
    name: "capacitas-empty.xlsx",
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: buildCapacitasWorkbookBuffer(),
  });
  await page.getByRole("button", { name: "Analizza file" }).click();
  await expect(page.getByText("Preview import Capacitas", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Conferma nuovo snapshot" }).click();

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
  await mockCapacitasPreview(page, "capacitas-failed.xlsx");

  await page.route("**/api/catasto/import/capacitas", async (route) => {
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
  await page.locator("#catasto-import-capacitas-file").setInputFiles({
    name: "capacitas-failed.xlsx",
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: buildCapacitasWorkbookBuffer(),
  });
  await page.getByRole("button", { name: "Analizza file" }).click();
  await expect(page.getByText("Preview import Capacitas", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Conferma nuovo snapshot" }).click();

  await expect(page.getByText("Import fallito")).toBeVisible();
  await expect(page.getByText("Workbook non valido o foglio Ruoli mancante")).toBeVisible();
  await expect(page.getByText("Nessun contatore disponibile")).toBeVisible();
});

test("catasto import wizard handles autonomous distretti Excel flow", async ({ page }) => {
  await loginAsAdmin(page);

  await page.route("**/api/catasto/import/summary**", async (route) => {
    const tipo = new URL(route.request().url()).searchParams.get("tipo");
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(
        tipo === "distretti_excel"
          ? {
              tipo: "distretti_excel",
              totale_batch: 3,
              processing_batch: 0,
              completed_batch: 2,
              failed_batch: 1,
              replaced_batch: 0,
              ultimo_completed_at: "2026-04-29T09:12:00Z",
            }
          : {
              tipo: "capacitas_ruolo",
              totale_batch: 1,
              processing_batch: 0,
              completed_batch: 1,
              failed_batch: 0,
              replaced_batch: 0,
              ultimo_completed_at: "2026-04-29T09:00:00Z",
            },
      ),
    });
  });
  await page.route("**/api/catasto/import/history**", async (route) => {
    const tipo = new URL(route.request().url()).searchParams.get("tipo");
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(
        tipo === "distretti_excel"
          ? [
              {
                id: "00000000-0000-0000-0000-000000000441",
                filename: "distretti-history.xlsx",
                tipo: "distretti_excel",
                anno_campagna: null,
                hash_file: null,
                righe_totali: 44,
                righe_importate: 44,
                righe_anomalie: 2,
                status: "completed",
                report_json: null,
                errore: null,
                created_at: "2026-04-29T09:10:00Z",
                completed_at: "2026-04-29T09:12:00Z",
                created_by: 1,
              },
            ]
          : [],
      ),
    });
  });
  await page.route("**/api/catasto/import/distretti/excel", async (route) => {
    expect(route.request().method()).toBe("POST");
    expect(route.request().postDataBuffer()?.toString("latin1")).toContain('filename="distretti.xlsx"');
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ batch_id: "00000000-0000-0000-0000-000000000444", status: "processing" }),
    });
  });
  await page.route("**/api/catasto/import/00000000-0000-0000-0000-000000000444/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "00000000-0000-0000-0000-000000000444",
        filename: "distretti-aggiornati.xlsx",
        tipo: "distretti_excel",
        anno_campagna: null,
        hash_file: null,
        righe_totali: 44,
        righe_importate: 42,
        righe_anomalie: 2,
        status: "completed",
        report_json: {
          righe_totali: 44,
          righe_univoche: 42,
          particelle_aggiornate: 4,
          righe_senza_match_particella: 2,
          history_written: 5,
          distretti_creati: 1,
          righe_scartate_comune_non_risolto: 1,
          righe_duplicate_conflitto: 1,
        },
        errore: null,
        created_at: "2026-04-29T09:10:30Z",
        completed_at: "2026-04-29T09:12:00Z",
        created_by: 1,
      }),
    });
  });
  await page.route("**/api/catasto/import/00000000-0000-0000-0000-000000000444/report**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 50 }),
    });
  });

  await page.goto("/catasto/import");
  await page.getByRole("button", { name: "Aggiorna distretti (Excel)" }).click();
  await expect(page.getByText("distretti-history.xlsx")).toBeVisible();
  await expect(page.getByText("Ultimo completato")).toBeVisible();

  await page.locator("#catasto-import-distretti-file").setInputFiles({
    name: "distretti.xlsx",
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: buildDistrettiWorkbookBuffer(),
  });
  await page.getByRole("button", { name: "Avvia import" }).click();

  await expect(page.getByText("Risultato aggiornamento distretti")).toBeVisible();
  await expect(page.getByText("Chiavi univoche", { exact: true }).locator("..")).toContainText("42");
  await expect(page.getByText("Particelle aggiornate", { exact: true }).locator("..")).toContainText("4");
  await expect(page.locator("p").filter({ hasText: /^Senza match$/ }).locator("..")).toContainText("2");
  await expect(page.getByText("Storico scritto", { exact: true }).locator("..")).toContainText("5");
  await expect(page.getByText("distretti-aggiornati.xlsx")).toBeVisible();
});

test("catasto import wizard reopens historical distretti batch report from history", async ({ page }) => {
  await loginAsAdmin(page);

  await page.route("**/api/catasto/import/summary**", async (route) => {
    const tipo = new URL(route.request().url()).searchParams.get("tipo");
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        tipo: tipo ?? "distretti_excel",
        totale_batch: 5,
        processing_batch: 0,
        completed_batch: 4,
        failed_batch: 1,
        replaced_batch: 0,
        ultimo_completed_at: "2026-04-29T10:15:00Z",
      }),
    });
  });
  await page.route("**/api/catasto/import/history**", async (route) => {
    const tipo = new URL(route.request().url()).searchParams.get("tipo");
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(
        tipo === "distretti_excel"
          ? [
              {
                id: "00000000-0000-0000-0000-000000000551",
                filename: "distretti-storico.xlsx",
                tipo: "distretti_excel",
                anno_campagna: null,
                hash_file: null,
                righe_totali: 44,
                righe_importate: 42,
                righe_anomalie: 2,
                status: "completed",
                report_json: {
                  righe_totali: 44,
                  righe_univoche: 42,
                  particelle_aggiornate: 3,
                  righe_senza_match_particella: 1,
                  history_written: 3,
                  righe_scartate_comune_non_risolto: 1,
                  righe_duplicate_conflitto: 1,
                },
                errore: null,
                created_at: "2026-04-29T10:10:00Z",
                completed_at: "2026-04-29T10:15:00Z",
                created_by: 1,
              },
            ]
          : [],
      ),
    });
  });
  await page.route("**/api/catasto/import/00000000-0000-0000-0000-000000000551/report**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 50 }),
    });
  });

  await page.goto("/catasto/import");
  await page.getByRole("button", { name: "Aggiorna distretti (Excel)" }).click();
  await expect(page.getByRole("cell", { name: "distretti-storico.xlsx" })).toBeVisible();

  await page.getByRole("button", { name: "Apri report" }).click();

  await expect(page.getByText("Risultato aggiornamento distretti")).toBeVisible();
  await expect(page.locator("p").filter({ hasText: "distretti-storico.xlsx" })).toBeVisible();
  await expect(page.getByText("Chiavi univoche", { exact: true }).locator("..")).toContainText("42");
  await expect(page.locator("p").filter({ hasText: /^Senza match$/ }).locator("..")).toContainText("1");
  await expect(page.getByText("Storico scritto", { exact: true }).locator("..")).toContainText("3");
  await expect(page.getByText("Particelle aggiornate", { exact: true }).locator("..")).toContainText("3");
});
