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
  test.skip(true, "La ricerca singola è stata rimossa: resta solo l’elaborazione massiva.");
});

test("admin executes catasto anagrafica bulk search", async ({ page }) => {
  await loginAsAdmin(page);

  await page.route("**/api/catasto/elaborazioni-massive/particelle/jobs?**", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [] }) });
  });

  await page.route("**/api/catasto/elaborazioni-massive/particelle/jobs/upload", async (route) => {
    expect(route.request().method()).toBe("POST");
    expect(route.request().headers()["content-type"]).toContain("multipart/form-data");
    expect(route.request().postDataBuffer()?.toString("utf8")).toContain("anagrafica.csv");
    expect(route.request().postDataBuffer()?.toString("utf8")).toContain("165,5,120");
    expect(route.request().postDataBuffer()?.toString("utf8")).toContain("999,9,999");
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "00000000-0000-0000-0000-000000000801",
        created_at: "2026-05-15T10:00:00Z",
        started_at: "2026-05-15T10:00:00Z",
        completed_at: "2026-05-15T10:00:01Z",
        source_filename: "anagrafica.csv",
        kind: "COMUNE_FOGLIO_PARTICELLA_INTESTATARI",
        status: "completed",
        skipped_rows: 0,
        total_rows: 2,
        processed_rows: 2,
        current_label: "Elaborazione completata.",
        error_message: null,
        summary: { total: 2, found: 1, notFound: 1, multiple: 0, invalid: 0, error: 0 },
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

  await page.goto("/catasto/elaborazioni-massive");

  await page.locator("input#catasto-bulk-file").setInputFiles({
    name: "anagrafica.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("comune,foglio,particella\n165,5,120\n999,9,999\n", "utf8"),
  });

  await page.getByRole("button", { name: "Elabora righe" }).click();

  await expect(page.getByText("Riepilogo")).toBeVisible();
  const summary = page.locator("article").filter({ has: page.getByText("Riepilogo", { exact: true }) });
  await expect(summary.getByText("FOUND: 1", { exact: true })).toBeVisible();
  await expect(summary.getByText("NOT_FOUND: 1", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Export CSV", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Export Excel", exact: true })).toBeVisible();
  await expect(page.getByText("Nessuna particella trovata.")).toBeVisible();
});
