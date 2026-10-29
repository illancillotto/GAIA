import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const noticePdf = readFileSync(join(__dirname, "../fixtures/notice-preview.pdf"));
test.use({ channel: "chromium" });

for (const width of [1440, 390]) {
  test(`anteprima, selezione e caricamento su Poste ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript(() => {
      if (window.top === window) localStorage.setItem("gaia.access_token", "invio-solleciti-browser-test");
    });
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const item = {
      id: "item-1", batch_id: "batch-1", display_name: "Societa Agricola Quattro Mori", codice_fiscale: "00048250955", status: "generated",
      years_json: [2021], payload_json: {}, generated_document_path: "/nas/solleciti/00048250955.pdf",
      download_url: "/ruolo/tributi/solleciti/items/item-1/download",
    };
    const batch = {
      id: "batch-1", title: "Sollecito tributi 00048250955 - Template GAIA", status: "generated",
      items_total: 1, items_generated: 1, items_failed: 0, created_at: "2026-10-29T10:57:00Z", generated_at: "2026-10-29T10:57:00Z", items: [item],
    };
    const lot = {
      id: "lot-1", title: "Solleciti 2021", status: "open", created_by: 1, created_at: "2026-10-29T11:00:00Z", counts: { address_pending: 1 },
      priced_total: 0, postal_options: {}, portal_snapshot: null, draft_expires_at: null, active_job: null, events: [], items: [],
    };
    let created: unknown = null;
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      let data: unknown = {};
      if (path.endsWith("/auth/me")) data = { id: 1, username: "operatore", role: "admin", is_active: true, enabled_modules: ["ruolo"] };
      if (path.endsWith("/auth/my-permissions")) data = { sections: [], granted_keys: ["ruolo.tributi.view", "ruolo.tributi.manage_status"] };
      if (path.endsWith("/batches")) data = { items: [batch], total: 1, page: 1, page_size: 50 };
      if (path.endsWith("/batch-1")) data = batch;
      if (path.endsWith("/candidates")) data = { items: [], total: 0, page: 1, page_size: 50 };
      if (path.endsWith("/poste-dispatch/lots")) {
        if (route.request().method() === "POST") created = route.request().postDataJSON();
        data = route.request().method() === "POST" ? lot : { items: created ? [lot] : [], total: created ? 1 : 0, page: 1, page_size: 50 };
      }
      if (path.endsWith("/lots/lot-1")) data = lot;
      if (path.endsWith("/batch-overview")) data = [{ batch_id: "batch-1", items: [{ item_id: "item-1", label: item.display_name, status: "generated", sendable: true, pec_sent: true }] }];
      if (path.endsWith("/items/item-1/download")) {
        await route.fulfill({ status: 200, contentType: "application/pdf", body: noticePdf });
        return;
      }
      await route.fulfill({ status: 200, json: data });
    });
    await page.goto("/ruolo/tributi/solleciti?embedded=1");
    await expect(page.getByText("Inviato via PEC", { exact: true })).toBeVisible();
    await page.getByRole("checkbox", { name: /Seleziona per Posta Online: Sollecito tributi 00048250955/ }).check();
    await page.getByRole("button", { name: /Sollecito tributi 00048250955/ }).click();
    await expect(page.getByTitle("Anteprima avviso generato")).toHaveAttribute("src", /^blob:/);
    await expect(page.getByText("Avviso già inviato via PEC")).toBeVisible();
    await expect(page.getByRole("checkbox", { name: "Seleziona per Posta Online", exact: true })).toBeChecked();
    await page.getByRole("textbox", { name: "Titolo lotto Poste" }).fill("Solleciti 2021");
    await page.screenshot({ path: `/tmp/gaia-invio-solleciti-${width}.png`, fullPage: true });
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
    await page.getByRole("button", { name: "Carica su Poste (1)" }).click();
    await expect(page.getByRole("region", { name: "Dettaglio lotto Poste" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Posta Online" })).toHaveAttribute("aria-selected", "true");
    expect(created).toEqual({ title: "Solleciti 2021", batch_item_ids: ["item-1"] });
    await page.screenshot({ path: `/tmp/gaia-invio-solleciti-poste-${width}.png`, fullPage: true });
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
    await page.goto("/ruolo/tributi/solleciti/poste?embedded=1");
    await expect(page.getByRole("tab", { name: "Posta Online" })).toHaveAttribute("aria-selected", "true");
    expect(errors).toEqual([]);
  });
}
