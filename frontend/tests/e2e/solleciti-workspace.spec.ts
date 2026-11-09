import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

test.use({ channel: "chromium" });
const pdf = readFileSync(join(__dirname, "../fixtures/notice-preview.pdf"));

for (const width of [1440, 390]) {
  test(`ricerca unica, PDF e preparazione senza lotti ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 950 });
    await page.addInitScript(() => {
      if (window.top === window) localStorage.setItem("gaia.access_token", "synthetic-workspace-test");
    });
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    let preparation: unknown = null;
    let generation: unknown = null;
    let searchedFor: string | null = null;
    let reconciliation: unknown = null;
    const available = {
      item_id: "i1", batch_id: "b1", notice_number: "020210000000001", codice_fiscale: "12345678901",
      label: "Azienda sintetica", years: [2021], document_status: "generated", amount: 100,
      can_prepare: true, download_url: "/ruolo/tributi/solleciti/items/i1/download",
      poste_dispatches: [], account_key: "none", account_label: "Da assegnare", lot_id: null, stage: "available",
    };
    const sent = { ...available, item_id: "i2", notice_number: "020210000000002", label: "Contribuente sintetico", can_prepare: false, account_key: "1", account_label: "account-test", lot_id: "lot-existing", stage: "sent", poste_dispatches: [{ id: "d1", notice_number: "020210000000002", status: "sent", poste_draft_id: "POSTE-SYNTHETIC", poste_status: "Accettato", draft_created_at: null, sent_at: "2026-11-05T10:00:00Z", tracking_number: "TRACK-SYNTHETIC", upload_requested_by_username: "operator-test", updated_at: "2026-11-05T10:00:00Z", poste_username: "account-test" }] };
    const lot = { id: "lot-new", title: "Preparazione avvisi Posta Online", status: "open", created_by: 1, created_at: "2026-11-06T08:00:00Z", counts: { address_pending: 1 }, priced_total: 0, postal_options: {}, portal_snapshot: null, draft_expires_at: null, credential_id: 1, poste_username: "account-test", active_job: { mode: "poste_dispatch_addresses", status: "pending" }, events: [], items: [] };
    await page.route("**/api/**", async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname;
      let data: unknown = {};
      if (path.endsWith("/auth/me")) data = { id: 1, username: "operator-test", role: "admin", is_active: true, enabled_modules: ["ruolo"] };
      if (path.endsWith("/auth/my-permissions")) data = { sections: [], granted_keys: ["ruolo.tributi.view", "ruolo.tributi.manage_status"] };
      if (path.endsWith("/batches") || path.endsWith("/poste-dispatch/candidates")) data = { items: [], total: 0, page: 1, page_size: 50 };
      if (path.endsWith("/poste-dispatch/accounts")) data = [{ id: 1, label: "Account test", username: "account-test", active: true }];
      if (path.endsWith("/poste-dispatch/lots")) data = { items: preparation ? [lot] : [], total: preparation ? 1 : 0, page: 1, page_size: 50 };
      if (path.endsWith("/lots/lot-new")) data = lot;
      if (path.endsWith("/solleciti/workspace")) {
        const account = url.searchParams.get("account");
        searchedFor = url.searchParams.get("q");
        const prepared = preparation ? { ...available, can_prepare: false, stage: "processing", lot_id: "lot-new", account_key: "1", account_label: "account-test" } : available;
        let items = account === "1" ? [sent] : [prepared, sent];
        const stage = url.searchParams.get("stage");
        if (stage && stage !== "all") items = items.filter((item) => item.stage === stage);
        data = { groups: [{ years: [2021], account_key: "none", account_label: "Da assegnare", total: 1, stages: { available: 1 } }, { years: [2021], account_key: "1", account_label: "account-test", total: 1, stages: { sent: 1 } }], items, total: items.length, page: 1, page_size: 20 };
      }
      if (path.endsWith("/workspace/generate")) { generation = route.request().postDataJSON(); data = { created: [], reused: ["i1"], problems: [] }; }
      if (path.endsWith("/workspace/prepare")) { preparation = route.request().postDataJSON(); data = lot; }
      if (path.endsWith("/workspace/reconcile")) { reconciliation = route.request().postDataJSON(); data = { queued_jobs: [42], busy_lots: 0 }; }
      if (path.endsWith("/items/i1/download")) { await route.fulfill({ status: 200, contentType: "application/pdf", body: pdf }); return; }
      await route.fulfill({ status: 200, json: data });
    });
    await page.goto("/ruolo/tributi/solleciti?embedded=1");
    const states = page.getByRole("navigation", { name: "Stati avvisi su Poste" });
    await expect(states.getByRole("button", { name: "Spedito · 1" })).toBeVisible();
    await expect(page.getByText(/ID Poste: POSTE-SYNTHETIC · Spedito il/)).toBeVisible();
    await states.getByRole("button", { name: "Spedito · 1" }).click();
    await expect(page.getByRole("button", { name: "Apri avviso 020210000000001" })).toHaveCount(0);
    await expect(page.getByRole("checkbox", { name: "Prepara avviso 020210000000002" })).toBeDisabled();
    await states.getByRole("button", { name: "Tutti · 2" }).click();
    await expect(page.getByRole("button", { name: "Apri avviso 020210000000001" })).toBeVisible();
    await page.getByRole("button", { name: "Apri avviso 020210000000002" }).click();
    await page.getByText("ID Poste, date e storico", { exact: true }).click();
    await expect(page.getByText("POSTE-SYNTHETIC", { exact: true })).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Avvisi per anno e account" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Storico lotti di generazione" })).toHaveCount(0);
    await page.getByText("Altri filtri", { exact: true }).click();
    await page.getByRole("combobox", { name: "Account Poste", exact: true }).selectOption("1");
    await expect(page.getByRole("button", { name: "Apri avviso 020210000000001" })).toHaveCount(0);
    await page.getByRole("button", { name: "Controlla account su Poste" }).click();
    await expect(page.getByText(/Controlli accodati: 1/)).toBeVisible();
    expect(reconciliation).toEqual({ credential_id: 1, year: 2021 });
    await page.getByRole("button", { name: "Reimposta filtri" }).click();
    await expect(page.getByRole("button", { name: "Genera o recupera PDF" })).toBeDisabled();
    await expect(page.getByLabel("CF / P.IVA", { exact: true })).toHaveCount(0);
    await expect(page.getByLabel("Anno da generare")).toHaveCount(0);
    await page.getByLabel("Cerca contribuente o avviso").fill("12345678901");
    await page.getByRole("button", { name: "Cerca" }).click();
    await expect.poll(() => searchedFor).toBe("12345678901");
    expect(generation).toBeNull();
    const inputBox = (await page.getByLabel("Cerca contribuente o avviso").boundingBox())!;
    const searchBox = (await page.getByRole("button", { name: "Cerca", exact: true }).boundingBox())!;
    expect(inputBox.x + inputBox.width <= searchBox.x || inputBox.y + inputBox.height <= searchBox.y || searchBox.y + searchBox.height <= inputBox.y).toBe(true);
    await page.getByRole("button", { name: "Apri avviso 020210000000001" }).click();
    await expect(page.getByTitle("Anteprima avviso generato")).toHaveAttribute("src", /^blob:/);
    await page.getByTitle("Anteprima avviso generato").scrollIntoViewIfNeeded();
    await expect.poll(() => page.frames().some((frame) => frame.url().startsWith("chrome-extension://"))).toBe(true);
    const pdfViewer = page.frames().find((frame) => frame.url().startsWith("chrome-extension://"))!;
    await expect(pdfViewer.locator("pdf-viewer")).toBeVisible();
    await expect(pdfViewer.locator("viewer-toolbar")).toBeVisible();
    await expect.poll(() => pdfViewer.locator("pdf-viewer").evaluate((element) =>
      (element as HTMLElement & { loadState_: string }).loadState_
    )).toBe("success");
    await page.screenshot({ path: `/tmp/gaia-solleciti-ux-20261106/semplice-${width}.png`, fullPage: true });
    expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
    await page.getByRole("checkbox", { name: "Prepara avviso 020210000000001" }).check();
    await expect(page.getByRole("region", { name: "Prepara su Poste" })).toBeInViewport();
    await page.screenshot({ path: `/tmp/gaia-solleciti-ux-20261106/selezione-${width}.png` });
    await page.getByRole("combobox", { name: "Account per la preparazione" }).selectOption("1");
    await page.getByRole("button", { name: "Prepara su Poste" }).click();
    await expect(page.getByText(/Preparazione avviata/)).toBeVisible();
    await expect(page.getByRole("region", { name: "Dettaglio lotto Poste" })).toHaveCount(0);
    await expect(page.getByRole("checkbox", { name: "Prepara avviso 020210000000001" })).toBeDisabled();
    await expect(page.getByRole("region", { name: "Prepara su Poste" })).toHaveCount(0);
    expect(preparation).toEqual({ item_ids: ["i1"], credential_id: 1 });
    await expect(page.getByRole("tab", { name: "Solleciti generati" })).toHaveAttribute("aria-selected", "true");
    expect(errors).toEqual([]);
  });
}
