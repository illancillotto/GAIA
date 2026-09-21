import { expect, test, type Page } from "@playwright/test";
import { candidateFixture, evidenceFixture, noticeFixture, positionFixture } from "../unit/notice-register-fixtures";
import type { ImportBatch, ImportRow } from "../../src/components/ruolo/notice-register/import-client";

async function mockRegister(page: Page, canEdit = true) {
  const document = noticeFixture({ positions: [positionFixture()], position_count: 1, unlinked_count: 1,
    recovery_review_count: 1, anomalies: ["collegamenti_mancanti", "notifica_da_verificare", "step_da_verificare"] });
  const writes: unknown[] = [];
  await page.addInitScript(() => localStorage.setItem("gaia.access_token", "register-browser-test"));
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    const pack = (items: unknown[]) => ({ items, total: items.length, page: 1, page_size: 20 });
    let data: unknown = {};
    if (url.pathname.endsWith("/auth/me")) data = { id: 1, username: "operatore", email: "test@example.local", role: "admin", is_active: true, module_ruolo: true, enabled_modules: ["ruolo"] };
    if (url.pathname.endsWith("/auth/my-permissions")) data = { sections: [], granted_keys: canEdit ? ["ruolo.tributi.view", "ruolo.tributi.manage_status"] : ["ruolo.tributi.view"] };
    if (url.pathname.endsWith("/dashboard/summary")) data = { nas_users: 0, nas_groups: 0, shares: 0, reviews: 0, snapshots: 0, sync_runs: 0 };
    if (url.pathname.includes("/registro-avvisi")) {
      data = pack([]);
      if (url.pathname.endsWith("/registro-avvisi")) data = pack([document]);
      if (url.pathname.endsWith("/doc-1")) data = document;
      if (url.pathname.endsWith("/evidenze")) data = pack([evidenceFixture]);
      if (url.pathname.endsWith("/candidati")) data = pack([candidateFixture]);
      if (url.pathname.endsWith("/ammissibilita")) data = {
        document_id: document.id, version: document.version, checked_at: "2026-09-21T10:00:00Z",
        eligible: false, authorizes_dispatch: false, reasons: ["step_non_liberato"],
        positions: [{ position_id: "pos-1", avviso_id: null, tax_year: 2022, eligible: false, reasons: ["collegamenti_mancanti"] }],
      };
      if (route.request().method() !== "GET") {
        const payload = route.request().postDataJSON();
        writes.push(payload);
        document.version += 1;
        document.positions[0].avviso = candidateFixture;
        document.positions[0].avviso_id = candidateFixture.id;
        data = { document_id: document.id, resource_id: candidateFixture.id, version: document.version };
      }
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(data) });
  });
  return writes;
}

for (const width of [1440, 390]) {
  test(`verifica consultiva e registrazione invio passato ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const writes = await mockRegister(page);
    await page.goto("/ruolo/tributi/registro-avvisi?embedded=1");
    await page.getByRole("button", { name: "Apri CUM-2022-2023" }).click();
    await page.getByRole("button", { name: "Verifica dati aggiornati" }).click();
    await expect(page.getByText("Affidamento STEP presente o da verificare.")).toBeVisible();
    await expect(page.getByText(/non prenota e non autorizza un invio/)).toBeVisible();
    expect(writes).toHaveLength(0);
    await page.getByText("Registra invio gia effettuato", { exact: true }).click();
    const form = page.getByRole("form", { name: "Invio gia effettuato" });
    await form.getByRole("button", { name: "Salva registrazione" }).click();
    expect(writes).toHaveLength(0);
    await form.getByRole("combobox", { name: /^Canale/ }).selectOption("pec");
    await form.getByLabel("Tracking o protocollo (facoltativo)").fill("PROTOCOLLO-123");
    await form.getByLabel("Data e ora invio (ora locale)").fill("2024-06-29T12:00");
    await form.getByLabel("Riferimento evidenza dell'invio").fill("Distinta 42");
    await form.getByLabel("Motivo della registrazione o correzione").fill("Riscontro archivio");
    await form.getByRole("checkbox").check();
    await page.screenshot({ path: `/tmp/gaia-notice-attempt-${width}.png`, fullPage: true });
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
    await form.getByRole("button", { name: "Salva registrazione" }).click();
    await expect(page.getByText("Registrazione salvata. Verifica lo stato aggiornato.")).toBeVisible();
    expect(writes).toEqual([{
      expected_version: 1, reason: "Riscontro archivio", data: {
        channel: "pec", tracking_code: "PROTOCOLLO-123",
        sent_at: await page.evaluate(() => new Date("2024-06-29T12:00").toISOString()),
        evidence_reference: "Distinta 42", confirmed: true,
      },
    }]);
    expect(errors).toEqual([]);
  });
}

async function mockReconciliation(page: Page, canEdit = true) {
  await mockRegister(page, canEdit);
  const source = noticeFixture({ id: "poste", source_system: "poste_db", document_number: "Poste storico" });
  const target = noticeFixture({ id: "excel", source_system: "excel_2022_2023", document_number: "Excel cumulativo", positions: [positionFixture()], position_count: 1 });
  const batch: ImportBatch = { id: "batch", filename: "variante.xlsx", source: "excel_2022_2023", status: "confirmed", digest: "sha256", parser_version: "v1", actor_id: 1, confirmed_by: 1, created_at: "2026-09-18", confirmed_at: "2026-09-18", reason: "Import storico", summary: { rows: 1, ignored_non_operational: 0, outcomes: { conflict: 1 } } };
  const row: ImportRow = { id: "row", row_number: 2, source_key: "CUM", fingerprint: "fingerprint", outcome: "conflict", document_id: "excel", anomalies: [], resolution: null, payload: { document_number: "Variante cumulativo", tax_code: "TESTCF", positions: [], original: { H: "Variante da verificare" } } };
  const writes: { data: Record<string, unknown>; expected_version: number; reason: string }[] = [];
  await page.route("**/api/ruolo/tributi/registro-avvisi**", async (route) => {
    const url = new URL(route.request().url());
    const pack = (items: unknown[]) => ({ items, total: items.length, page: 1, page_size: 10 });
    let data: unknown = pack([]);
    if (url.pathname.endsWith("/registro-avvisi")) data = pack(url.searchParams.has("reconciliation_candidates") ? [target] : [source, target]);
    if (url.pathname.endsWith("/poste")) data = source;
    if (url.pathname.endsWith("/excel")) data = target;
    if (url.pathname.endsWith("/importazioni")) data = pack([batch]);
    if (url.pathname.endsWith("/batch")) data = batch;
    if (url.pathname.endsWith("/righe")) data = pack(url.searchParams.get("review") === "open" && row.resolution ? [] : [row]);
    if (route.request().method() === "POST") {
      const payload = route.request().postDataJSON();
      writes.push(payload);
      if (url.pathname.endsWith("/annulla")) {
        source.reconciled_into_id = null;
        source.version += 1;
      } else if (url.pathname.endsWith("/riconciliazione")) {
        source.reconciled_into_id = target.id;
        source.version += 1;
      } else row.resolution = { decision: payload.data.decision, reason: payload.reason, actor_id: 1, decided_at: "2026-09-18", document_id: "excel", document_version: target.version + 1, evidence_id: "evidence-variant" };
      target.version += 1;
      data = { document_id: target.id, version: target.version, resource_id: source.id };
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(data) });
  });
  return writes;
}

for (const width of [1440, 390]) {
  test(`riconciliazione e conflitti ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const writes = await mockReconciliation(page);
    await page.goto("/ruolo/tributi/registro-avvisi?embedded=1");
    await page.getByRole("button", { name: "Apri Poste storico" }).click();
    await page.getByLabel("Numero documento, riferimento annuale, tracking o CF").fill("TESTCF");
    await page.getByRole("button", { name: "Cerca documenti" }).click();
    await page.getByRole("button", { name: "Confronta Excel cumulativo" }).click();
    const form = page.getByRole("form", { name: "Conferma riconciliazione Poste" });
    await form.getByRole("button", { name: "Salva registrazione" }).click();
    expect(writes).toHaveLength(0);
    await form.getByRole("checkbox").check();
    await form.getByLabel("Motivo della registrazione o correzione").fill("Riscontro originale Poste e Excel");
    await page.screenshot({ path: `/tmp/gaia-reconcile-${width}-compare.png`, fullPage: true });
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
    await form.getByRole("button", { name: "Salva registrazione" }).click();
    await page.getByRole("button", { name: "Apri documento riconciliato" }).click();
    await expect(page.getByRole("heading", { name: "Excel cumulativo", exact: true })).toBeVisible();
    expect(writes[0]).toEqual({ expected_version: 1, reason: "Riscontro originale Poste e Excel", data: { target_document_id: "excel", target_version: 1, confirmed: true } });
    await page.getByRole("button", { name: "Torna al registro" }).click();
    await page.getByRole("button", { name: "Riconciliati", exact: true }).click();
    await page.getByRole("button", { name: "Importazioni", exact: true }).click();
    await page.getByRole("button", { name: "variante.xlsx", exact: true }).click();
    await page.getByRole("button", { name: "Confronta variante e risolvi" }).click();
    const conflict = page.getByRole("form", { name: "Risolvi conflitto importazione" });
    await conflict.getByLabel("Decisione sul conflitto").selectOption("register_evidence");
    await conflict.getByRole("checkbox").check();
    await conflict.getByLabel("Motivo della registrazione o correzione").fill("Variante conservata per ulteriore verifica");
    await page.screenshot({ path: `/tmp/gaia-reconcile-${width}-conflict.png`, fullPage: true });
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
    await conflict.getByRole("button", { name: "Salva registrazione" }).click();
    await expect(page.getByText("Conflitto risolto: Conserva variante come evidenza")).toBeVisible();
    await page.getByLabel("Stato conflitti").selectOption("open");
    await expect(page.getByText("Nessuna riga per questo filtro.")).toBeVisible();
    await page.getByLabel("Stato conflitti").selectOption("resolved");
    await expect(page.getByText("Conflitto risolto: Conserva variante come evidenza")).toBeVisible();
    expect(writes[1]).toEqual({ expected_version: 2, reason: "Variante conservata per ulteriore verifica", data: { decision: "register_evidence", fingerprint: "fingerprint", document_id: "excel", confirmed: true } });
    expect(errors).toEqual([]);
  });
}

test("viewer consulta il confronto senza riconciliare o risolvere", async ({ page }) => {
  const writes = await mockReconciliation(page, false);
  await page.goto("/ruolo/tributi/registro-avvisi?embedded=1");
  await page.getByRole("button", { name: "Apri Poste storico" }).click();
  await expect(page.getByRole("heading", { name: "Poste storico", exact: true })).toBeVisible();
  await expect(page.getByRole("form", { name: "Cerca documento da riconciliare" })).toHaveCount(0);
  await page.getByRole("button", { name: "Torna al registro" }).click();
  await page.getByRole("button", { name: "Importazioni", exact: true }).click();
  await page.getByRole("button", { name: "variante.xlsx", exact: true }).click();
  await page.getByRole("button", { name: "Confronta variante e risolvi" }).click();
  await expect(page.getByRole("heading", { name: "Excel cumulativo", exact: true })).toBeVisible();
  await expect(page.getByRole("form", { name: "Risolvi conflitto importazione" })).toHaveCount(0);
  expect(writes).toEqual([]);
});

for (const width of [1440, 390]) {
  test(`annullamento auditato riconciliazione ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const writes = await mockReconciliation(page);
    await page.goto("/ruolo/tributi/registro-avvisi?embedded=1");
    await page.getByRole("button", { name: "Apri Poste storico" }).click();
    await page.getByLabel("Numero documento, riferimento annuale, tracking o CF").fill("TESTCF");
    await page.getByRole("button", { name: "Cerca documenti" }).click();
    await page.getByRole("button", { name: "Confronta Excel cumulativo" }).click();
    const reconcile = page.getByRole("form", { name: "Conferma riconciliazione Poste" });
    await reconcile.getByRole("checkbox").check();
    await reconcile.getByLabel("Motivo della registrazione o correzione").fill("Confronto archivio");
    await reconcile.getByRole("button", { name: "Salva registrazione" }).click();
    const undo = page.getByRole("form", { name: "Annulla riconciliazione" });
    await undo.getByRole("button", { name: "Salva registrazione" }).click();
    expect(writes).toHaveLength(1);
    await undo.getByRole("checkbox").check();
    await undo.getByLabel("Motivo della registrazione o correzione").fill("Rilevata associazione errata");
    await page.screenshot({ path: `/tmp/gaia-undo-${width}.png`, fullPage: true });
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
    await undo.getByRole("button", { name: "Salva registrazione" }).click();
    await expect(page.getByRole("form", { name: "Cerca documento da riconciliare" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Apri documento riconciliato" })).toHaveCount(0);
    expect(writes[1]).toEqual({ expected_version: 2, reason: "Rilevata associazione errata", data: { target_document_id: "excel", target_version: 2, confirmed: true } });
    expect(errors).toEqual([]);
  });
}

for (const width of [1440, 390]) {
  test(`registro e collegamento operatore ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const writes = await mockRegister(page);
    await page.goto("/ruolo/tributi/registro-avvisi?embedded=1");
    await expect(page.getByRole("heading", { name: "Documenti, notifiche e recupero crediti" })).toBeVisible();
    await page.getByRole("button", { name: "Anomalie", exact: true }).click();
    await page.getByRole("button", { name: "Apri CUM-2022-2023" }).click();
    await expect(page.getByRole("heading", { name: "CUM-2022-2023", exact: true })).toBeVisible();
    await page.getByText("Cerca e collega avviso", { exact: true }).click();
    await page.getByLabel("CNC, CF, nominativo o UUID").fill("TESTCF");
    await page.getByRole("button", { name: "Cerca candidati" }).click();
    await page.getByRole("button", { name: "Seleziona CNC-2022-001" }).click();
    const form = page.getByRole("form", { name: "Conferma collegamento" });
    await form.getByRole("button", { name: "Salva registrazione" }).click();
    expect(writes).toHaveLength(0);
    await form.getByRole("checkbox").check();
    await form.getByLabel("Motivo della registrazione o correzione").fill("Verifica documento originale");
    await page.screenshot({ path: `/tmp/gaia-register-${width}-confirmation.png`, fullPage: true });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
    expect(overflow).toBe(false);
    await form.getByRole("button", { name: "Salva registrazione" }).click();
    await expect(page.getByText("Registrazione salvata. Verifica lo stato aggiornato.")).toBeVisible();
    await expect(page.getByRole("link", { name: "CNC-2022-001" })).toBeVisible();
    expect(writes).toEqual([{ expected_version: 1, reason: "Verifica documento originale", data: { avviso_id: "avviso-1", confirmed: true } }]);
    await page.screenshot({ path: `/tmp/gaia-register-${width}-detail.png`, fullPage: true });
    expect(errors).toEqual([]);
  });
}

test("lettura sola e messaggio importazioni", async ({ page }) => {
  await mockRegister(page, false);
  await page.goto("/ruolo/tributi/registro-avvisi?embedded=1");
  await expect(page.getByText("Accesso in sola lettura.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Registra avviso storico" })).toHaveCount(0);
  await page.getByRole("button", { name: "Importazioni", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Importazioni Excel e Poste" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Prepara anteprima Excel" })).toHaveCount(0);
});

for (const width of [1440, 390]) {
  test(`anteprima e conferma import ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await mockRegister(page);
    let confirmations = 0;
    const batch = { id: "batch-1", filename: "avvisi.xlsx", source: "excel_2022_2023", status: "preview", digest: "sha256",
      parser_version: "v1", actor_id: 1, confirmed_by: null as number | null, created_at: "2026-09-18", confirmed_at: null as string | null,
      reason: null as string | null, summary: { rows: 1, ignored_non_operational: 1, outcomes: { new: 1 } as Record<string, number> } };
    await page.route("**/api/ruolo/tributi/registro-avvisi/importazioni**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      const pack = (items: unknown[]) => ({ items, total: items.length, page: 1, page_size: 10 });
      let data: unknown = batch;
      if (path.endsWith("/importazioni")) data = pack([]);
      if (path.endsWith("/righe")) data = pack([{ id: "row-1", row_number: 3, source_key: "CUM", fingerprint: "fp", outcome: batch.status === "preview" ? "new" : "imported",
        document_id: batch.status === "preview" ? null : "doc-1", anomalies: ["notifica_da_verificare"], payload: { document_number: "CUM", tax_code: "TESTCF", positions: [], original: { I: "29/06/204" }, dates: { I: "2024-06-29" } } }]);
      if (path.endsWith("/conferma")) {
        expect(route.request().postDataJSON()).toEqual({ confirmed: true, digest: "sha256", reason: "Verifica import archivio" });
        confirmations += 1; batch.status = "confirmed"; batch.confirmed_by = 1; batch.confirmed_at = "2026-09-18";
        batch.reason = "Verifica import archivio"; batch.summary.outcomes = { imported: 1 };
      }
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(data) });
    });
    await page.goto("/ruolo/tributi/registro-avvisi?embedded=1");
    await page.getByRole("button", { name: "Importazioni", exact: true }).click();
    await expect(page.getByText("Nessuna importazione presente.")).toBeVisible();
    await page.getByLabel("Excel avvisi 2022/2023").setInputFiles({ name: "avvisi.xlsx", mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", buffer: Buffer.from("fixture API mock") });
    await page.getByRole("button", { name: "Prepara anteprima Excel" }).click();
    await expect(page.getByText(/Anteprima: registro non modificato/)).toBeVisible();
    const form = page.getByRole("form", { name: "Conferma importazione" });
    await form.getByRole("button").click();
    expect(confirmations).toBe(0);
    await form.getByRole("checkbox").check();
    await form.getByLabel("Motivo importazione").fill("Verifica import archivio");
    await page.screenshot({ path: `/tmp/gaia-import-${width}-preview.png`, fullPage: true });
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
    await form.getByRole("button").click();
    await expect(page.getByText(/Importazione confermata/)).toBeVisible();
    await page.getByRole("button", { name: "Apri documento nel registro" }).click();
    await expect(page.getByRole("heading", { name: "CUM-2022-2023", exact: true })).toBeVisible();
    expect(confirmations).toBe(1);
    expect(errors).toEqual([]);
  });
}
