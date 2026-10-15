import { test, expect, type Frame, type Page } from "@playwright/test";
import { openReadyDistrettiList } from "./helpers/distretti-readiness";

async function loginAsAdmin(page: Page) {
  const username = process.env.PLAYWRIGHT_ADMIN_USERNAME ?? "admin";
  const password = process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? "#0r1st4n3s1";

  await page.goto("/login");
  await page.getByLabel("Username o email").fill(username);
  await page.locator("input#password").fill(password);
  await page.getByRole("button", { name: "Accedi alla piattaforma" }).click();
  await page.waitForURL("**/");
}

async function getDistrettoWorkspace(page: Page): Promise<Frame> {
  const iframe = await page.locator('iframe[title^="Distretto "]').elementHandle();
  const workspace = await iframe?.contentFrame();
  if (!workspace) throw new Error("District workspace has no content frame");
  return workspace;
}

test("admin navigates catasto distretti -> distretto detail -> particella detail", async ({ page }) => {
  await loginAsAdmin(page);

  const distrettoRowCount = await openReadyDistrettiList(page);
  const distrettoRows = page.locator("table.data-table tbody tr");
  test.skip(distrettoRowCount === 0, "Nessun distretto disponibile nello stack locale: esegui seed/import shapefile prima del drill-down.");

  const firstDistrettoRow = page.locator("table.data-table tbody tr").first();
  await expect(firstDistrettoRow).toBeVisible();
  await firstDistrettoRow.click();

  const workspace = await getDistrettoWorkspace(page);
  await workspace.waitForURL("**/catasto/distretti/**");

  await expect(workspace.getByText("N. distretto:")).toBeVisible();
  await expect(workspace.locator(".metric-card").getByText("Particelle", { exact: true })).toBeVisible();
  await expect(workspace.locator(".metric-card").getByText("Utenze", { exact: true })).toBeVisible();
  await expect(workspace.locator(".metric-card").getByText("Importo 0648", { exact: true })).toBeVisible();
  await expect(workspace.locator(".metric-card").getByText("Importo 0985", { exact: true })).toBeVisible();

  await expect(workspace.getByRole("button", { name: "Particelle" })).toBeVisible();
  await expect(workspace.getByRole("button", { name: "Anomalie" })).toBeVisible();

  await expect(workspace.getByText("Particelle (prime 200)")).toBeVisible();

  const firstParticellaRow = workspace.locator("table.data-table tbody tr").first();
  await expect(firstParticellaRow).toBeVisible();
  await firstParticellaRow.click();

  await workspace.waitForURL("**/catasto/particelle/**");

  await expect(workspace.getByText("Utilizzatore / pagatore annualità")).toBeVisible();
  await expect(workspace.getByText("Anomalie", { exact: true })).toBeVisible();
  await expect(workspace.getByText("Storico", { exact: true })).toBeVisible();
});

test("admin navigates catasto distretti -> anomalie tab -> anomaly workspace", async ({ page }) => {
  await loginAsAdmin(page);

  const distrettoRowCount = await openReadyDistrettiList(page);
  const distrettoRows = page.locator("table.data-table tbody tr");
  test.skip(distrettoRowCount === 0, "Nessun distretto disponibile nello stack locale: esegui seed/import shapefile prima del drill-down.");

  await distrettoRows.first().click();
  const workspace = await getDistrettoWorkspace(page);
  await workspace.waitForURL("**/catasto/distretti/**");

  await workspace.getByRole("button", { name: "Anomalie" }).click();
  await expect(workspace.getByText("Anomalie aperte (prime 200)")).toBeVisible();

  const viewComplete = workspace.getByRole("link", { name: "Vista completa" });
  await expect(viewComplete).toBeVisible();
  await viewComplete.click();

  await workspace.waitForURL("**/catasto/anomalie");
  const manualTab = workspace.getByRole("navigation", { name: "Code anomalie" })
    .getByRole("button", { name: /^Triage manuale/ });
  await manualTab.click();
  await expect(manualTab).toHaveAttribute("aria-pressed", "true");
  const register = workspace.locator("article").filter({
    has: workspace.getByText("Registro completo anomalie", { exact: true }),
  });
  await expect(register).toBeVisible();
  await expect(register.getByLabel("Tipo", { exact: true })).toBeVisible();
  await expect(register.getByRole("combobox", { name: "Severità", exact: true })).toBeVisible();
  await expect(register.getByRole("combobox", { name: "Stato", exact: true })).toBeVisible();
  await expect(register.getByRole("button", { name: "Reset registro", exact: true })).toBeVisible();
  const resetContext = workspace.getByRole("button", { name: "Reset contesto", exact: true });
  await expect(resetContext).toBeVisible();
  const anomalyRows = register.locator("table.data-table tbody tr");
  const emptyState = register.getByText("Nessuna anomalia", { exact: true });
  await expect(anomalyRows.first().or(emptyState)).toBeVisible();
  await expect(resetContext).toBeEnabled();
  await expect(register.getByText("Caricamento...", { exact: true })).toHaveCount(0);
  await expect(workspace.getByText("Errore caricamento", { exact: true })).toHaveCount(0);

  if (await anomalyRows.count()) {
    await expect(anomalyRows.first()).toBeVisible();
    await expect(anomalyRows.first().getByRole("button", { name: "Chiudi", exact: true })).toBeVisible();
  } else {
    await expect(anomalyRows).toHaveCount(0);
    await expect(register.getByRole("button", { name: "Chiudi", exact: true })).toHaveCount(0);
    await expect(emptyState).toBeVisible();
  }
});
