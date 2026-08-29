import { expect, test, type Page, type Request } from "@playwright/test";

async function loginAsAdmin(page: Page) {
  // Mock auth: live login hits the 7-device session cap on shared admin accounts.
  await page.route("**/api/auth/login", async (route) => {
    await json(route, { access_token: "playwright-gis-strumenti", token_type: "bearer" });
  });
  await page.route("**/api/auth/me", async (route) => {
    await json(route, {
      id: 1,
      username: "admin",
      email: "admin@example.local",
      role: "admin",
      is_active: true,
      module_accessi: true,
      module_rete: true,
      module_inventario: false,
      module_gis: true,
      module_catasto: true,
      module_utenze: false,
      module_operazioni: false,
      module_riordino: false,
      module_ruolo: false,
      module_presenze: true,
      enabled_modules: ["accessi", "rete", "gis", "catasto", "presenze"],
    });
  });
  await page.route("**/api/auth/my-permissions", async (route) => {
    await json(route, {
      sections: [],
      granted_keys: [],
    });
  });
  await page.route("**/api/dashboard/summary", async (route) => {
    await json(route, {
      nas_users: 0,
      nas_groups: 0,
      shares: 0,
      reviews: 0,
      snapshots: 0,
      sync_runs: 0,
    });
  });

  await page.goto("/login");
  await page.getByLabel("Username o email").fill("admin");
  await page.locator("input#password").fill("playwright");
  await page.getByRole("button", { name: "Accedi alla piattaforma" }).click();
  await page.waitForURL("**/");
}

function json(route: { fulfill: (response: Record<string, unknown>) => Promise<void> }, body: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

function multipartFields(request: Request): Record<string, string> {
  const raw = request.postDataBuffer()?.toString("latin1") ?? "";
  const fields: Record<string, string> = {};
  for (const part of raw.split(/--[\w-]+/).slice(1)) {
    const name = part.match(/name="([^"]+)"/)?.[1];
    if (!name || name === "file") continue;
    const value = part.split("\r\n\r\n").slice(1).join("\r\n\r\n").replace(/\r\n$/, "");
    if (value.includes("WebKitFormBoundary") || value.startsWith("--")) continue;
    fields[name] = value.replace(/\r\n--$/, "").trim();
  }
  return fields;
}

const editableLayer = {
  id: "layer-1",
  workspace: "rete",
  name: "rete_condotte",
  title: "Condotte ufficiali",
  source_type: "postgis",
  official_source: "postgis",
  metadata: {},
  is_active: true,
  effective_access_level: "editor",
  can_view: true,
  can_annotate: true,
  can_edit: true,
  can_approve: false,
  can_manage: false,
  created_at: "2026-08-25T08:00:00Z",
  updated_at: "2026-08-25T08:00:00Z",
};

const importItem = {
  id: "import-1",
  status: "validated",
  original_filename: "rilievo.zip",
  workspace: "rete",
  domain_module: "network",
  target_layer_name: "rilievo_rete_2026",
  target_layer_title: "rilievo rete 2026",
  official_source: "shapefile_upload",
  source_srid: 3003,
  encoding: "latin1",
  staging_table: "import_1",
  feature_count: 2,
  fields: [],
  validation_report: {},
  metadata: {},
  checksum_sha256: "a".repeat(64),
  created_at: "2026-08-25T08:00:00Z",
  updated_at: "2026-08-25T08:00:00Z",
};

const preview = {
  import_id: importItem.id,
  status: "validated",
  staging_table: "import_1",
  feature_count: 2,
  returned_count: 1,
  limit: 10,
  offset: 0,
  has_more: false,
  fields: [],
  features: [{ feature_seq: 1, attributes: { nome: "Condotta A", diametro: 120 }, source_srid: 3003 }],
};

test("gis strumenti smokes upload, preview, publish, reject and paged change requests", async ({ page }) => {
  const uploads: Record<string, string>[] = [];
  const changeRequests: Array<Record<string, unknown>> = [];
  let previewCalls = 0;
  let publishCalls = 0;
  let rejectCalls = 0;
  const history = [{ ...importItem, id: "import-resume", target_layer_title: "Rilievo da riprendere" }];

  await loginAsAdmin(page);

  await page.route("**/api/gis/layers**", async (route) => {
    await json(route, { items: [editableLayer], total: 1 });
  });
  await page.route("**/api/gis/exports**", async (route) => {
    await json(route, { items: [], total: 0 });
  });
  await page.route("**/api/gis/ogc/poc", async (route) => {
    await json(route, {
      recommended_server: "qgis-server",
      publishable_layer_count: 7,
    });
  });
  await page.route("**/api/gis/imports**", async (route) => {
    await json(route, { items: history, total: history.length });
  });
  await page.route("**/api/gis/imports/shapefile", async (route) => {
    uploads.push(multipartFields(route.request()));
    history.unshift(importItem);
    await json(route, importItem);
  });
  await page.route("**/api/gis/imports/*/preview**", async (route) => {
    previewCalls += 1;
    await json(route, preview);
  });
  await page.route("**/api/gis/imports/*/publish", async (route) => {
    publishCalls += 1;
    const published = { ...importItem, status: "published" };
    history[0] = published;
    await json(route, published);
  });
  await page.route("**/api/gis/imports/*/reject", async (route) => {
    rejectCalls += 1;
    await json(route, { ...history[history.length - 1], status: "rejected" });
  });
  await page.route("**/api/gis/imports/*/change-requests", async (route) => {
    const payload = route.request().postDataJSON() as Record<string, unknown>;
    changeRequests.push(payload);
    const offset = Number(payload.offset ?? 0);
    await json(route, offset === 0
      ? { created_count: 2, existing_count: 0, returned_count: 2, has_more: true }
      : { created_count: 1, existing_count: 1, returned_count: 1, has_more: false });
  });

  await page.goto("/gis/strumenti");

  await expect(page.getByRole("heading", { name: "Import e strumenti GIS" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Torna al catalogo" })).toHaveAttribute("href", "/gis/catalogo");
  await expect(page.getByRole("heading", { name: "QGIS Desktop e servizi OGC" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Coda e storico GIS" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Riprendi" })).toBeVisible();

  await page.getByRole("button", { name: "Controlla e carica" }).click();
  await expect(page.getByText("Scegli un file ZIP e indica area e titolo della mappa.")).toBeVisible();

  await page.getByLabel("File shapefile ZIP").setInputFiles({
    name: "Rilievo Rète 2026.zip",
    mimeType: "application/zip",
    buffer: Buffer.from("PK\x03\x04gaia-gis-smoke", "utf8"),
  });
  await page.getByText("Impostazioni tecniche facoltative").click();
  await expect(page.getByLabel("Nome tecnico")).toHaveValue("rilievo_rete_2026");
  await expect(page.getByLabel("Titolo comprensibile")).toHaveValue("rilievo rete 2026");

  await page.getByLabel("Sistema coordinate").fill("0");
  await page.getByRole("button", { name: "Controlla e carica" }).click();
  await expect(page.getByText("Il sistema di coordinate deve essere un numero valido.")).toBeVisible();

  await page.getByLabel("Sistema coordinate").fill("3003");
  await page.getByLabel("Codifica testo").fill("latin1");
  await page.getByRole("button", { name: "Controlla e carica" }).click();

  await expect(page.getByText("è stato controllato e salvato nell'area di prova.")).toBeVisible();
  await expect(page.getByText("Anteprima dei primi 1 elementi")).toBeVisible();
  await expect(page.getByText(/nome: Condotta A/)).toBeVisible();
  expect(uploads[0]).toMatchObject({
    workspace: "rete",
    domain_module: "network",
    target_layer_name: "rilievo_rete_2026",
    target_layer_title: "rilievo rete 2026",
    official_source: "shapefile_upload",
    source_srid: "3003",
    encoding: "latin1",
  });

  await page.getByRole("button", { name: "Mostra anteprima" }).click();
  await expect.poll(() => previewCalls).toBeGreaterThanOrEqual(2);

  await page.getByRole("button", { name: "Pubblica nel catalogo" }).click();
  await expect(page.getByRole("heading", { name: "Pubblicare questa mappa?" })).toBeVisible();
  await expect(page.getByText("La mappa sarà visibile nel catalogo agli utenti autorizzati.")).toBeVisible();
  expect(publishCalls).toBe(0);
  await page.getByRole("button", { name: "Conferma pubblicazione" }).click();
  await expect(page.getByText("Import pubblicato nel catalogo.")).toBeVisible();
  expect(publishCalls).toBe(1);

  await page.getByLabel("Motivo della proposta").fill("Rilievo aggiornato");
  await page.getByRole("button", { name: "Crea proposte di modifica" }).click();
  await expect(page.getByText("3 proposte create, 1 già presenti.")).toBeVisible();
  expect(changeRequests).toHaveLength(2);
  expect(changeRequests[0]).toMatchObject({
    target_layer_id: "layer-1",
    justification: "Rilievo aggiornato",
    limit: 100,
    offset: 0,
  });
  expect(changeRequests[1]).toMatchObject({ offset: 2 });

  await page.getByRole("button", { name: "Riprendi" }).last().click();
  await page.getByRole("button", { name: "Rigetta import" }).click();
  await expect(page.getByRole("heading", { name: "Rigettare questo import?" })).toBeVisible();
  await page.getByRole("button", { name: "Conferma rigetto" }).click();
  await expect(page.getByText("Import rigettato e area di prova rimossa.")).toBeVisible();
  expect(rejectCalls).toBe(1);

  await page.getByRole("button", { name: "Verifica piano OGC" }).click();
  await expect(page.getByText("qgis-server")).toBeVisible();
  await expect(page.getByText("Sola lettura", { exact: true })).toBeVisible();
});
