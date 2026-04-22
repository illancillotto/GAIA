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

test("admin executes catasto anagrafica single search", async ({ page }) => {
  await loginAsAdmin(page);

  await page.route("**/api/catasto/anagrafica/search**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        matches: [
          {
            particella_id: "00000000-0000-0000-0000-000000000501",
            comune_id: "00000000-0000-0000-0000-000000000601",
            comune: "Arborea",
            cod_comune_capacitas: 165,
            codice_catastale: "A357",
            foglio: "5",
            particella: "120",
            subalterno: "1",
            num_distretto: "10",
            nome_distretto: "Distretto 10",
            superficie_mq: "1000.00",
            utenza_latest: {
              id: "00000000-0000-0000-0000-000000000701",
              cco: "UT-SEED-001",
              anno_campagna: 2025,
              stato: "importata",
              num_distretto: 10,
              nome_distretto: "Distretto 10",
              sup_irrigabile_mq: "900.00",
              denominazione: "Fenu Denise",
              codice_fiscale: "DNIFSE64C01L122Y",
              ha_anomalie: false,
            },
            intestatari: [
              {
                id: "00000000-0000-0000-0000-000000000801",
                codice_fiscale: "DNIFSE64C01L122Y",
                denominazione: "Fenu Denise",
                tipo: "PF",
                cognome: "Fenu",
                nome: "Denise",
                data_nascita: null,
                luogo_nascita: null,
                ragione_sociale: null,
                source: "capacitas",
                last_verified_at: null,
                deceduto: null,
              },
            ],
            anomalie_count: 1,
            anomalie_top: [{ tipo: "VAL-06-imponibile", count: 1 }],
          },
        ],
      }),
    });
  });

  await page.goto("/catasto/ricerca-anagrafica");
  await expect(page.getByRole("heading", { name: "Ricerca anagrafica" }).first()).toBeVisible();

  await page.getByLabel("Comune (codice Capacitas o nome)").fill("165");
  await page.getByLabel("Foglio *").fill("5");
  await page.getByLabel("Particella *").fill("120");
  await page.getByRole("button", { name: "Cerca", exact: true }).click();

  await expect(page.getByText("Codice Capacitas:")).toBeVisible();
  await expect(page.getByText("Fenu Denise", { exact: true })).toBeVisible();
  await expect(page.getByText("ID utenza:")).toBeVisible();
  await expect(page.getByRole("link", { name: "Apri particella" })).toBeVisible();
});

test("admin executes catasto anagrafica bulk search", async ({ page }) => {
  await loginAsAdmin(page);

  await page.route("**/api/catasto/anagrafica/bulk-search", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        results: [
          {
            row_index: 2,
            comune_input: "165",
            foglio_input: "5",
            particella_input: "120",
            esito: "FOUND",
            message: "OK",
            particella_id: "00000000-0000-0000-0000-000000000501",
            matches_count: 1,
            match: {
              particella_id: "00000000-0000-0000-0000-000000000501",
              comune_id: "00000000-0000-0000-0000-000000000601",
              comune: "Arborea",
              cod_comune_capacitas: 165,
              codice_catastale: "A357",
              foglio: "5",
              particella: "120",
              subalterno: "1",
              num_distretto: "10",
              nome_distretto: "Distretto 10",
              superficie_mq: "1000.00",
              utenza_latest: {
                id: "00000000-0000-0000-0000-000000000701",
                cco: "UT-SEED-001",
                anno_campagna: 2025,
                stato: "importata",
                num_distretto: 10,
                nome_distretto: "Distretto 10",
                sup_irrigabile_mq: "900.00",
                denominazione: "Fenu Denise",
                codice_fiscale: "DNIFSE64C01L122Y",
                ha_anomalie: false,
              },
              intestatari: [],
              anomalie_count: 0,
              anomalie_top: [],
            },
          },
          {
            row_index: 3,
            comune_input: "999",
            foglio_input: "9",
            particella_input: "999",
            esito: "NOT_FOUND",
            message: "Nessuna particella trovata.",
            particella_id: null,
            match: null,
            matches_count: 0,
          },
        ],
      }),
    });
  });

  await page.goto("/catasto/ricerca-anagrafica");
  await page.getByRole("button", { name: "Elaborazione massiva" }).click();

  await page.getByLabel("File ricerca anagrafica").setInputFiles({
    name: "anagrafica.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("comune,foglio,particella\n165,5,120\n999,9,999\n", "utf8"),
  });

  await page.getByRole("button", { name: "Elabora righe" }).click();

  await expect(page.getByText("Riepilogo")).toBeVisible();
  await expect(page.getByText("FOUND: 1", { exact: true })).toBeVisible();
  await expect(page.getByText("NOT_FOUND: 1", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Export CSV" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Export Excel" })).toBeVisible();
  await expect(page.getByText("Nessuna particella trovata.")).toBeVisible();
});
