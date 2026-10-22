import { expect, test, type Page, type Route } from "@playwright/test";

const AVVISO_ID = "00000000-0000-0000-0000-0000000000aa";
const CONTRIBUENTE_ID = "00000000-0000-0000-0000-0000000000c1";
const DOCUMENTO_ID = "00000000-0000-0000-0000-0000000000d1";
const now = "2026-10-21T08:00:00Z";

const link = {
  id: "00000000-0000-0000-0000-0000000000e1",
  documento_id: DOCUMENTO_ID,
  reference_key: "020190006018040",
  codice_cnc: "020190006018040",
  anno_rif: 2019,
  status: "linked",
  ruolo_avviso_id: AVVISO_ID,
  candidate_avviso_ids: null,
  tributi_count: 3,
  imp_carico: "63.49",
  imp_carico_pagato: "10.00",
  imp_discaricato: "0.00",
};

const contribuente = {
  id: CONTRIBUENTE_ID,
  cod_ent: "14215",
  codice_fiscale: "RSSMRA80A01G113X",
  denominazione: "ROSSI MARIO",
  numero_documenti: 1,
  importo: "63.49",
  pagato: "10.00",
  residuo: "53.49",
  stato_documenti: "Non Pagato",
  detail_synced_at: now,
};

function apiBody(path: string): unknown {
  if (path.endsWith("/auth/me")) {
    return { id: 1, username: "admin", role: "super_admin", is_active: true, enabled_modules: ["elaborazioni", "ruolo"] };
  }
  if (path.endsWith("/auth/my-permissions")) return { sections: [], granted_keys: ["ruolo.tributi.view"] };
  if (path.includes("notifications")) return { items: [], unread_count: 0 };
  if (path.endsWith("/elaborazioni/step/overview")) {
    return {
      contribuenti: 3354, documenti: 3410, tributi: 21265, pagamenti: 3237, pdf_scaricati: 3410,
      residuo_totale: "1313193.06", ultimo_aggiornamento: now,
      links: { linked: 7000, not_found: 319, ambiguous: 0, unrecognized: 36 },
      import_archives: ["raccolta-completa.zip"],
    };
  }
  if (path.endsWith("/elaborazioni/step/credentials")) {
    return [{ id: 1, label: "STEP Consorzio", username: "utente", portal_url: "https://prunesenti-step.servizienti.it/PrunesEntiPp/?c=0044", active: true, min_delay_ms: 600, last_used_at: now, last_error: null, consecutive_failures: 0, created_at: now, updated_at: now }];
  }
  if (path.endsWith("/elaborazioni/step/jobs")) {
    return [{ id: 7, credential_id: 1, requested_by_user_id: 1, status: "succeeded", mode: "sync", payload_json: { mode: "sync" }, result_json: { list_rows: 3354, details: 1, register: { updated: 1 } }, error_detail: null, started_at: now, completed_at: now, created_at: now, updated_at: now }];
  }
  if (path.endsWith(`/elaborazioni/step/contribuenti/${CONTRIBUENTE_ID}`)) {
    return {
      ...contribuente,
      anagrafica_json: { "Codice fiscale": contribuente.codice_fiscale, Comune: "ORISTANO" },
      situazione_contabile_json: { "Tot. Dovuto": "53,49" },
      sections_json: [],
      document_reconciliation_json: { status: "matched" },
      last_seen_at: now,
      documenti: [{
        id: DOCUMENTO_ID, num_doc: "20241421500000003", prg_coo: "1", section: "Documenti Emessi",
        des_doc: "Consorzio - quote ordinarie", des_trib: "Avv. N. 020190006018040", anno_rif: "2019",
        data_notifica: "2024-11-16", tot_dovuto: "53.49", imp_carico: "63.49", tot_pagato: "10.00", residuo: "53.49",
        pdf_status: "downloaded", pdf_original_filename: "Doc_1.pdf",
        tributi: [{ position: 1, partita: "1110371", cod_tributo: "0985", des_tributo: "Consorzio - quote ordinarie", tipo_tributo: "Imposta", anno_rif: 2019, imp_carico: "50.00", imp_carico_pagato: "10.00", imp_discaricato: "0.00", avviso_reference_raw: "020190006018040", codice_cnc: "020190006018040" }],
        links: [link],
      }],
      pagamenti: [],
    };
  }
  if (path.endsWith("/elaborazioni/step/contribuenti")) return { items: [contribuente], total: 1, page: 1, page_size: 25 };
  if (path.endsWith("/elaborazioni/step/ruolo-links")) return { items: [], total: 0, page: 1, page_size: 25 };
  if (path.endsWith(`/elaborazioni/step/ruolo-avvisi/${AVVISO_ID}`)) {
    return [{ contribuente_id: CONTRIBUENTE_ID, codice_fiscale: contribuente.codice_fiscale, denominazione: "ROSSI MARIO", documento_id: DOCUMENTO_ID, num_doc: "20241421500000003", data_notifica: "2024-11-16", pdf_status: "downloaded", link }];
  }
  if (path.endsWith(`/ruolo/avvisi/${AVVISO_ID}`)) {
    return {
      id: AVVISO_ID, import_job_id: "99999999-9999-9999-9999-999999999999", codice_cnc: "020190006018040", anno_tributario: 2019,
      subject_id: null, codice_fiscale_raw: contribuente.codice_fiscale, nominativo_raw: "ROSSI MARIO", domicilio_raw: null,
      residenza_raw: null, n2_extra_raw: null, codice_utenza: null, importo_totale_0648: null, importo_totale_0985: 63.49,
      importo_totale_0668: null, importo_totale_euro: 63.49, importo_totale_lire: null, n4_campo_sconosciuto: null,
      display_name: "ROSSI MARIO", is_linked: false, created_at: now, updated_at: now, partite: [],
    };
  }
  return [];
}

async function mockApi(page: Page): Promise<void> {
  await page.addInitScript(() => localStorage.setItem("gaia.access_token", "step-e2e"));
  await page.route("**/api/**", async (route: Route) => {
    await route.fulfill({ status: 200, json: apiBody(new URL(route.request().url()).pathname) });
  });
  await page.routeWebSocket("**/ws/**", (socket) => socket.close());
}

for (const width of [1440, 390]) {
  test(`STEP: archivio, contribuente e collegamento all'avviso a ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await mockApi(page);

    await page.goto("/elaborazioni/step");
    await expect(page.getByText("Riscossione coattiva STEP: archivio e collegamento al ruolo.")).toBeVisible();
    await expect(page.getByText("STEP Consorzio")).toBeVisible();
    if (width === 1440) {
      await expect(page.getByRole("link", { name: "STEP riscossione" })).toBeVisible();
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);

    await page.getByRole("button", { name: "ROSSI MARIO" }).click();
    const avvisoLink = page.getByRole("link", { name: "Avviso 020190006018040 (2019)" });
    await expect(avvisoLink).toBeVisible();
    await expect(avvisoLink).toHaveAttribute("href", `/ruolo/avvisi/${AVVISO_ID}`);

    await page.goto(`/ruolo/avvisi/${AVVISO_ID}`);
    const card = page.getByRole("region", { name: "Riscossione STEP" });
    await expect(card).toContainText("Documento 20241421500000003 · ROSSI MARIO");
    await expect(card.getByRole("link", { name: "Apri archivio STEP" })).toHaveAttribute("href", "/elaborazioni/step");
    await expect(page.getByText("Ripartizione importi")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    expect(errors).toEqual([]);
  });
}
