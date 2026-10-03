import { expect, test } from "@playwright/test";

test("local Docker synthetic console shows data and actual tool history", async ({ page }) => {
  test.skip(process.env.GAIA_MCP_LIVE_CONSOLE !== "1", "Requires isolated synthetic Docker gateway");
  test.setTimeout(180_000);
  await page.goto("/login");
  await page.getByLabel("Username o email").fill("synthetic-mcp");
  await page.locator("input#password").fill("synthetic-login-password");
  await page.getByRole("button", { name: "Accedi alla piattaforma" }).click();
  await expect.poll(() => page.evaluate(() => Boolean(localStorage.getItem("gaia.access_token")))).toBe(true);
  await page.goto("/wiki/mcp?embedded=1");
  await page.getByRole("button", { name: "Interroga Data MCP" }).click();
  await expect(page.getByRole("region", { name: "Risposta sintetica" })).toBeVisible({ timeout: 120_000 });
  await page.getByRole("link", { name: "Dati MCP, richieste e log" }).click();
  await page.getByRole("button", { name: "Carica dati e richieste" }).click();
  await expect(page.getByRole("button", { name: "subjects (300)" })).toBeVisible();
  await page.getByRole("button", { name: "subjects (300)" }).click();
  await expect(page.getByRole("region", { name: "Dati sintetici" })).toContainText("Soggetto sintetico");
  await page.getByRole("button", { name: "Record successivi" }).click();
  await expect(page.getByRole("region", { name: "Storico chiamate" })).toContainText("search_subjects");
  await page.getByRole("region", { name: "Storico chiamate" }).locator("details").first().locator("summary").click();
  await expect(page.getByRole("region", { name: "Storico chiamate" })).toContainText("gaia_synthetic_db");
  await page.screenshot({ path: "/tmp/gaia-mcp-console-browser.png", fullPage: true });
});
