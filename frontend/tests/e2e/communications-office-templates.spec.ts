import { expect, test } from "@playwright/test";
import catalog from "../../../backend/app/modules/communications/template_catalog.json";

for (const width of [1440, 390]) {
  test(`modelli ufficio modificabili e salvati solo come bozze ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript(() => localStorage.setItem("gaia.access_token", "synthetic-office-template-test"));
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    let reads = 0;
    const writes: string[] = [];
    const templates: object[] = [];
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      let data: unknown = [];
      if (path.endsWith("/auth/me")) data = { id: 1, username: "synthetic", role: "admin", is_active: true, enabled_modules: ["ruolo"] };
      else if (path.endsWith("/auth/my-permissions")) data = { sections: [], granted_keys: ["ruolo.tributi.view", "ruolo.tributi.manage_status"] };
      else if (path.endsWith("/admin/monitor")) data = { paused: true, transport_enabled: false, worker_seen_at: null, queues: {}, uncertain: 0, unmatched_receipts: 0 };
      else if (path.endsWith("/admin/templates")) data = templates;
      else if (path.endsWith("/admin/template-catalog")) {
        reads++;
        if (reads === 1) { await route.fulfill({ status: 503, json: { detail: "Catalogo temporaneamente non disponibile" } }); return; }
        data = catalog;
      } else if (path.includes("/communications/") && route.request().method() !== "GET") {
        writes.push(path);
        expect(path).toMatch(/\/communications\/templates$/);
        const input = route.request().postDataJSON();
        expect(input).not.toHaveProperty("status");
        data = { ...input, id: `synthetic-${templates.length}`, version: 1, status: "draft" };
        templates.push(data as object);
      }
      await route.fulfill({ status: 200, json: data });
    });
    await page.goto("/gaia/communications?embedded=1");
    await page.getByRole("button", { name: "Modelli di partenza 2021 e variabili" }).click();
    await expect(page.getByRole("alert").filter({ hasText: "Catalogo temporaneamente" })).toBeVisible();
    await page.getByRole("button", { name: "Modelli di partenza 2021 e variabili" }).click();
    await expect(page.getByText(catalog.note)).toBeVisible();
    for (const proposal of catalog.proposals) {
      await page.getByRole("button", { name: `Usa ${proposal.name}`, exact: true }).click();
      await expect(page.getByLabel("Codice template")).toHaveValue(proposal.code);
      await expect(page.getByLabel("Canale template")).toHaveValue(proposal.channel);
      await expect(page.getByLabel("Corpo template")).toHaveValue(proposal.body);
      expect(writes).toHaveLength(templates.length);
      await page.getByLabel("Corpo template").fill(`${proposal.body}\nTesto revisionato dall'ufficio.`);
      await page.getByRole("button", { name: "Salva nuova versione bozza" }).click();
      await expect(page.getByLabel("Codice template")).toHaveValue("");
    }
    expect(writes).toHaveLength(2);
    await expect(page.getByRole("button", { name: "Approva questa versione", exact: true })).toHaveCount(2);
    await page.getByText("Variabili disponibili · solo testo semplice").click();
    await expect(page.getByText("{{importo_documento}}", { exact: true })).toBeVisible();
    expect(errors).toEqual([]);
    await page.screenshot({ path: `/tmp/gaia-office-templates-20261107/catalog-${width}.png`, fullPage: true });
  });
}
