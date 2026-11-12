import { expect, test } from "@playwright/test";

for (const width of [1440, 390]) {
  test(`storia particella, contribuenti e proprietà documentata ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 960 });
    await page.addInitScript(() => localStorage.setItem("gaia.access_token", "synthetic-parcel-history"));
    const errors: string[] = [];
    page.on("pageerror", error => errors.push(error.message));
    const writes: string[] = [];
    await page.route("**/api/**", async route => {
      const url = new URL(route.request().url());
      const path = url.pathname;
      if (route.request().method() !== "GET") writes.push(path);
      let data: unknown = [];
      if (path.endsWith("/auth/me")) data = { id: 1, username: "synthetic", role: "viewer", is_active: true, enabled_modules: ["ruolo"] };
      else if (path.endsWith("/auth/my-permissions")) data = { sections: [], granted_keys: ["ruolo.avvisi", "ruolo.tributi.view"] };
      else if (path.endsWith("/particelle/storia")) data = { items: [{ id: "parcel", comune: "ORISTANO", comune_codice: "G113", foglio: "12", particella: "100", subalterno: "", first_year: 2011, last_year: 2013, years_count: 2 }], total: 1, page: 1, page_size: 25 };
      else if (path.endsWith("/particelle/storia/parcel")) {
        data = { id: "parcel", reference: { comune_nome: "ORISTANO", comune_codice: "G113", foglio: "12", particella: "100", subalterno: "", sezione: null }, identity_incomplete: false, first_year: 2011, last_year: 2013,
          taxes: [{ id: "row1", year: 2011, notice_id: "notice1", notice_number: "001", name: "Mario Rossi", tax_code: "SYNTHETIC1", partita_tax_code: null, co_holders: null, maintenance: 10, irrigation: 0, institutional: 2, total: 12, area_ha: 1, irrigated_ha: 0, crop: null, district: "1" }, { id: "row2", year: 2013, notice_id: "notice2", notice_number: "002", name: "Anna Bianchi", tax_code: "SYNTHETIC2", partita_tax_code: null, co_holders: null, maintenance: 15, irrigation: 0, institutional: 2, total: 17, area_ha: 1, irrigated_ha: 0, crop: null, district: "1" }],
          cadastre: { completeness: "not_certified", cessation: "documented_suppression", events: [{ id: "event1", name: "Giovanni Verdi", tax_code: "SYNTHETIC3", right: "Proprietà", share: "1/2", from_date: "1990-01-01", act_date: "1989-12-01", act: "Successione documentata", document_id: "doc" }], documents: [{ id: "doc", filename: "Visura storica sintetica.pdf", observed_at: "2026-11-12", recorded_at: "2026-11-12", type: "Storica", extraction_status: "completed", owners: [{ name: "Anna Bianchi", tax_code: "SYNTHETIC2", right: "Proprietà", share: "1/1" }], ambiguous: false, suppressed: true, suppressed_at: "2024-01-01" }] } };
      }
      await route.fulfill({ json: data });
    });
    await page.goto("/ruolo/particelle?embedded=1");
    await expect(page.getByRole("heading", { name: "1 particelle trovate" })).toBeVisible();
    await page.getByLabel("Comune", { exact: true }).fill("Oristano");
    await page.getByLabel("Foglio", { exact: true }).fill("12");
    await page.getByLabel("Particella", { exact: true }).fill("100");
    await page.getByRole("button", { name: "Cerca particella", exact: true }).click();
    await expect(page).toHaveURL(/comune=Oristano&foglio=12&particella=100/);
    await page.getByRole("link", { name: /ORISTANO.*Apri storia/ }).click();
    await expect(page.getByText("Mario Rossi", { exact: true })).toBeVisible();
    await expect(page.getByText("Anna Bianchi", { exact: true })).toBeVisible();
    await expect(page.getByText(/Nessuna riga importata per questo anno/)).toBeVisible();
    await expect(page.getByText("Non documentata", { exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: `/tmp/gaia-parcel-history-20261112/taxes-${width}.png`, fullPage: true });
    await page.getByRole("tab", { name: "Proprietà catastale", exact: true }).click();
    await expect(page.getByText("Giovanni Verdi", { exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Apri visura originale" })).toHaveAttribute("href", "/catasto/documents/doc");
    await expect(page.getByText(/Soppressione catastale documentata/)).toContainText("Non equivale alla cessazione del tributo");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: `/tmp/gaia-parcel-history-20261112/cadastre-${width}.png`, fullPage: true });
    await page.getByRole("link", { name: /Torna ai risultati/ }).click();
    await expect(page.getByLabel("Foglio", { exact: true })).toHaveValue("12");
    expect(writes).toEqual([]);
    expect(errors).toEqual([]);
  });
}

test("servizio non disponibile non viene mostrato come archivio vuoto", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("gaia.access_token", "synthetic"));
  let attempts = 0;
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/auth/me")) return route.fulfill({ json: { id: 1, role: "viewer", enabled_modules: ["ruolo"], is_active: true } });
    if (path.endsWith("/auth/my-permissions")) return route.fulfill({ json: { sections: [], granted_keys: ["ruolo.avvisi"] } });
    if (path.endsWith("/particelle/storia")) {
      attempts++;
      return attempts === 1 ? route.fulfill({ status: 404, json: { detail: "Not Found" } }) : route.fulfill({ json: { items: [], total: 0, page: 1, page_size: 25 } });
    }
    return route.fulfill({ json: [] });
  });
  await page.goto("/ruolo/particelle?embedded=1");
  await expect(page.getByRole("alert").filter({ hasText: "servizio potrebbe non essere ancora aggiornato" })).toBeVisible();
  await expect(page.getByText("0 particelle trovate")).toHaveCount(0);
  await page.getByRole("button", { name: "Riprova" }).click();
  await expect(page.getByRole("heading", { name: "Nessuna particella trovata" })).toBeVisible();
});
