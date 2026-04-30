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

test("catasto distretti page shows imported-year fallback and opens detail", async ({ page }) => {
  await loginAsAdmin(page);

  const currentYear = new Date().getFullYear();
  const importedYear = currentYear - 1;

  await page.route("**/api/catasto/import/history**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "00000000-0000-0000-0000-000000000811",
          filename: "capacitas-anno-precedente.xlsx",
          tipo: "capacitas_ruolo",
          anno_campagna: importedYear,
          status: "completed",
          created_at: "2026-04-29T08:00:00Z",
          completed_at: "2026-04-29T08:02:00Z",
        },
      ]),
    });
  });

  await page.route("**/api/catasto/distretti", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "00000000-0000-0000-0000-000000000901",
          num_distretto: "12",
          nome_distretto: "Distretto Nord",
          attivo: true,
        },
        {
          id: "00000000-0000-0000-0000-000000000902",
          num_distretto: "27",
          nome_distretto: "Distretto Sud",
          attivo: true,
        },
      ]),
    });
  });

  await page.route("**/api/catasto/distretti/*/kpi**", async (route) => {
    const url = new URL(route.request().url());
    const distrettoId = url.pathname.split("/").at(-2);
    const anno = Number(url.searchParams.get("anno"));
    const payload =
      distrettoId === "00000000-0000-0000-0000-000000000901"
        ? {
            totale_particelle: 12,
            totale_utenze: 7,
            superficie_irrigabile_mq: 125000,
            importo_totale_0648: "4567.89",
            importo_totale_0985: "876.54",
            totale_anomalie: 3,
            anno_campagna: anno,
          }
        : {
            totale_particelle: 4,
            totale_utenze: 2,
            superficie_irrigabile_mq: 30000,
            importo_totale_0648: "1000.00",
            importo_totale_0985: "250.00",
            totale_anomalie: 1,
            anno_campagna: anno,
          };

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(payload),
    });
  });

  await page.goto("/catasto/distretti");

  await expect(page.getByText("Tabella distretti")).toBeVisible();
  await expect(
    page.getByText(`L'anno corrente (${currentYear}) non risulta ancora caricato. Mostro i dati dell'anno ${importedYear}.`),
  ).toBeVisible();
  await expect(page.getByText("Distretto Nord")).toBeVisible();
  await expect(page.getByText("Distretto Sud")).toBeVisible();
  await expect(page.getByText("15.50 ha")).toBeVisible();
  await expect(page.getByText(/5567,89/)).toBeVisible();

  await page.locator("table.data-table tbody tr").first().click();
  await page.waitForURL("**/catasto/distretti/00000000-0000-0000-0000-000000000901");
});

test("catasto distretto detail supports year fallback, tab switch and exports", async ({ page }) => {
  await loginAsAdmin(page);

  const currentYear = new Date().getFullYear();
  const importedYear = currentYear - 1;
  const distrettoId = "00000000-0000-0000-0000-000000000901";

  await page.route("**/api/catasto/import/history**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "00000000-0000-0000-0000-000000000811",
          filename: "capacitas-anno-precedente.xlsx",
          tipo: "capacitas_ruolo",
          anno_campagna: importedYear,
          status: "completed",
          created_at: "2026-04-29T08:00:00Z",
          completed_at: "2026-04-29T08:02:00Z",
        },
      ]),
    });
  });

  await page.route(`**/api/catasto/distretti/${distrettoId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: distrettoId,
        num_distretto: "12",
        nome_distretto: "Distretto Nord",
        attivo: true,
      }),
    });
  });

  await page.route(`**/api/catasto/distretti/${distrettoId}/kpi**`, async (route) => {
    const anno = Number(new URL(route.request().url()).searchParams.get("anno"));
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        totale_particelle: 12,
        totale_utenze: 7,
        superficie_irrigabile_mq: 125000,
        importo_totale_0648: "4567.89",
        importo_totale_0985: "876.54",
        totale_anomalie: 3,
        anno_campagna: anno,
      }),
    });
  });

  await page.route("**/api/catasto/particelle**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "00000000-0000-0000-0000-000000001001",
          cod_comune_capacitas: 101,
          nome_comune: "Arborea",
          foglio: "14",
          particella: "82",
          subalterno: "A",
          superficie_mq: 12000,
          superficie_grafica_mq: 11950,
          num_distretto: "12",
        },
      ]),
    });
  });

  await page.route("**/api/catasto/anomalie**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            id: "00000000-0000-0000-0000-000000001021",
            tipo: "SUP-01",
            severita: "warning",
            status: "aperta",
            descrizione: "Superficie incoerente",
          },
        ],
        total: 1,
        page: 1,
        page_size: 200,
      }),
    });
  });

  await page.goto(`/catasto/distretti/${distrettoId}`);

  await expect(page.getByText("Distretto Nord")).toBeVisible();
  await expect(page.getByText("N. distretto:")).toBeVisible();
  await expect(
    page.getByText(`L'anno corrente (${currentYear}) non risulta ancora caricato. Mostro i dati dell'anno ${importedYear}.`),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Esporta CSV" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Esporta XLS" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Esporta PDF" })).toBeVisible();
  await expect(page.getByText("Particelle (prime 200)")).toBeVisible();
  await expect(page.getByText("Arborea")).toBeVisible();

  await page.getByRole("button", { name: "Anomalie" }).click();
  await expect(page.getByText("Anomalie aperte (prime 200)")).toBeVisible();
  await expect(page.getByText("Superficie incoerente")).toBeVisible();
  await expect(page.getByRole("link", { name: "Vista completa" })).toHaveAttribute("href", "/catasto/anomalie");
});
