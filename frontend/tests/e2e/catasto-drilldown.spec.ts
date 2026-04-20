import { test, expect } from "@playwright/test";

test("admin navigates catasto distretti -> distretto detail -> particella detail", async ({ page }) => {
  const username = process.env.PLAYWRIGHT_ADMIN_USERNAME ?? "admin";
  const password = process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? "#0r1st4n3s1";

  await page.goto("/login");
  await page.getByLabel("Username o email").fill(username);
  await page.locator("input#password").fill(password);
  await page.getByRole("button", { name: "Accedi alla piattaforma" }).click();

  await page.waitForURL("**/");

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

