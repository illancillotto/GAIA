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

test("admin navigates catasto distretti -> distretto detail -> particella detail", async ({ page }) => {
  await loginAsAdmin(page);

  await page.goto("/catasto/distretti");
  await expect(page.getByText("Tabella distretti")).toBeVisible();

  const distrettoRows = page.locator("table.data-table tbody tr");
  const distrettoRowCount = await distrettoRows.count();
  test.skip(distrettoRowCount === 0, "Nessun distretto disponibile nello stack locale: esegui seed/import shapefile prima del drill-down.");

  const firstDistrettoRow = page.locator("table.data-table tbody tr").first();
  await expect(firstDistrettoRow).toBeVisible();
  await firstDistrettoRow.click();

  await page.waitForURL("**/catasto/distretti/**");

  await expect(page.getByText("N. distretto:")).toBeVisible();
  await expect(page.getByText("Particelle", { exact: true })).toBeVisible();
  await expect(page.getByText("Utenze", { exact: true })).toBeVisible();
  await expect(page.getByText("Importo 0648", { exact: true })).toBeVisible();
  await expect(page.getByText("Importo 0985", { exact: true })).toBeVisible();

  await expect(page.getByRole("button", { name: "Particelle" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Anomalie" })).toBeVisible();

  await expect(page.getByText("Particelle (prime 200)")).toBeVisible();

  const firstApriLink = page.getByRole("link", { name: "Apri" }).first();
  await expect(firstApriLink).toBeVisible();
  await firstApriLink.click();

  await page.waitForURL("**/catasto/particelle/**");

  await expect(page.getByText("Ruoli tributo")).toBeVisible();
  await expect(page.getByText("Anomalie", { exact: true })).toBeVisible();
  await expect(page.getByText("Storico", { exact: true })).toBeVisible();
});

test("admin navigates catasto distretti -> anomalie tab -> anomaly workspace", async ({ page }) => {
  await loginAsAdmin(page);

  await page.goto("/catasto/distretti");
  await expect(page.getByText("Tabella distretti")).toBeVisible();

  const distrettoRows = page.locator("table.data-table tbody tr");
  const distrettoRowCount = await distrettoRows.count();
  test.skip(distrettoRowCount === 0, "Nessun distretto disponibile nello stack locale: esegui seed/import shapefile prima del drill-down.");

  await distrettoRows.first().click();
  await page.waitForURL("**/catasto/distretti/**");

  await page.getByRole("button", { name: "Anomalie" }).click();
  await expect(page.getByText("Anomalie aperte (prime 200)")).toBeVisible();

  const viewComplete = page.getByRole("link", { name: "Vista completa" });
  await expect(viewComplete).toBeVisible();
  await viewComplete.click();

  await page.waitForURL("**/catasto/anomalie");
  await expect(page.getByText("Filtri")).toBeVisible();
  await expect(page.getByRole("button", { name: "Applica filtri" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Reset" })).toBeVisible();

  const closeButtons = page.getByRole("button", { name: "Chiudi" });
  if (await closeButtons.count()) {
    await expect(closeButtons.first()).toBeVisible();
  } else {
    await expect(page.getByText("Nessuna anomalia")).toBeVisible();
  }
});
