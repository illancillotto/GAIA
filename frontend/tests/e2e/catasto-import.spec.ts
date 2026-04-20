import { test, expect } from "@playwright/test";
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

test("admin completes catasto import wizard through report step", async ({ page }) => {
  const username = process.env.PLAYWRIGHT_ADMIN_USERNAME ?? "admin";
  const password = process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? "#0r1st4n3s1";

  await page.goto("/login");
  await page.getByLabel("Username o email").fill(username);
  await page.locator("input#password").fill(password);
  await page.getByRole("button", { name: "Accedi alla piattaforma" }).click();

  await page.waitForURL("**/");
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
