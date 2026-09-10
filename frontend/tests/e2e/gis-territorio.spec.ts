import { expect, test, type Locator, type Page, type Route } from "@playwright/test";

const ENABLED = process.env.PLAYWRIGHT_GIS_TERRITORIO_ENABLED === "true";
const PARCEL_ID = "00000000-0000-0000-0000-000000004201";
const RAS_LAYER_ID = "00000000-0000-0000-0000-000000000101";
const ADE_LAYER_ID = "00000000-0000-0000-0000-000000000102";
const ORTHO_LAYER_ID = "00000000-0000-0000-0000-000000000103";
const MUNICIPAL_LAYER_ID = "00000000-0000-0000-0000-000000000104";
const TRANSPARENT_PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAQAAAAEACAYAAABccqhmAAAAIGNIUk0AAHomAACAhAAA+gAAAIDoAAB1MAAA6mAAADqYAAAXcJy6UTwAAAAGYktHRAD/AP8A/6C9p5MAAAEVSURBVHja7cExAQAAAMKg9U/tawigAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB4AwE8AAHYKUMEAAAAAElFTkSuQmCC",
  "base64",
);

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function clickMapCanvas(canvas: Locator, xRatio: number, yRatio: number): Promise<void> {
  await canvas.evaluate((element, position) => {
    const bounds = element.getBoundingClientRect();
    element.dispatchEvent(new MouseEvent("click", {
      bubbles: true,
      clientX: bounds.left + bounds.width * position.xRatio,
      clientY: bounds.top + bounds.height * position.yRatio,
    }));
  }, { xRatio, yRatio });
}

async function loginWithGis(page: Page) {
  await page.route("**/api/auth/login", (route) => json(route, {
    access_token: "playwright-gis-territorio",
    token_type: "bearer",
  }));
  await page.route("**/api/auth/me", (route) => json(route, {
    id: 1,
    username: "gis-admin",
    email: "gis-admin@example.local",
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
    module_presenze: false,
    enabled_modules: ["accessi", "rete", "gis", "catasto"],
  }));
  await page.route("**/api/auth/my-permissions", (route) => json(route, {
    sections: [],
    granted_keys: [],
  }));
  await page.route("**/api/dashboard/summary", (route) => json(route, {
    nas_users: 0,
    nas_groups: 0,
    shares: 0,
    reviews: 0,
    snapshots: 0,
    sync_runs: 0,
  }));

  await page.goto("/login");
  await page.getByLabel("Username o email").fill("gis-admin");
  await page.locator("input#password").fill("playwright");
  await page.getByRole("button", { name: "Accedi alla piattaforma" }).click();
  await page.waitForURL("**/");
}

async function installBrowserStubs(page: Page) {
  await page.addInitScript(() => {
    const host = window as Window & {
      __territorioPrintHtml?: string;
      __territorioPrintCalled?: boolean;
    };
    HTMLCanvasElement.prototype.toDataURL = () => "data:image/png;base64,cHJpbnQ=";
    window.open = () => ({
      document: {
        write: (html: string) => { host.__territorioPrintHtml = html; },
        close: () => undefined,
      },
      focus: () => undefined,
      print: () => { host.__territorioPrintCalled = true; },
    }) as unknown as Window;
  });

  const image = (route: Route) => route.fulfill({
    status: 200,
    contentType: "image/png",
    headers: { "Access-Control-Allow-Origin": "*" },
    body: TRANSPARENT_PNG,
  });
  await page.route("https://tile.openstreetmap.org/**", image);
  await page.route("https://services.arcgisonline.com/**", image);
  await page.route("**/api/catasto/gis/tiles/**", image);
  await page.route("**/gis/external/**", image);
}

function territoryCatalog() {
  const layer = (
    id: string,
    name: string,
    title: string,
    queryable: "wfs_queryable" | "wms_infoable" | "wms_visual_only",
    source: "ras_sitr" | "ade_catasto",
    attribution: string,
  ) => ({
    id,
    name,
    title,
    description: `${title} per smoke controllato`,
    theme: "",
    source,
    proxy_wms_url: `/gis/external/${id}/wms`,
    legend_url: `/gis/external/${id}/wms?request=GetLegendGraphic`,
    default_opacity: 0.7,
    render_order: 10,
    queryable,
    attribution,
  });
  const ras = layer(
    RAS_LAYER_ID,
    "ras_distretti_irrigui",
    "Distretti irrigui RAS",
    "wfs_queryable",
    "ras_sitr",
    "Regione Autonoma della Sardegna - CC BY 4.0",
  );
  const ade = layer(
    ADE_LAYER_ID,
    "ade_particelle_wms",
    "Particelle catastali AdE",
    "wms_infoable",
    "ade_catasto",
    "Agenzia delle Entrate - CC BY 4.0",
  );
  const ortho = layer(
    ORTHO_LAYER_ID,
    "ras_ortofoto_1977",
    "Ortofoto storica 1977-1978",
    "wms_visual_only",
    "ras_sitr",
    "Regione Autonoma della Sardegna - Ortofoto 1977-1978",
  );
  const municipal = layer(
    MUNICIPAL_LAYER_ID,
    "ras_limiti_comunali",
    "Limiti amministrativi comunali CTR",
    "wfs_queryable",
    "ras_sitr",
    "Regione Autonoma della Sardegna - CC BY 4.0",
  );
  return {
    groups: [
      { theme: "bonifica", label: "Bonifica e comprensori", layers: [{ ...ras, theme: "bonifica" }] },
      { theme: "catasto_ufficiale", label: "Catasto ufficiale", layers: [{ ...ade, theme: "catasto_ufficiale" }] },
      { theme: "ortofoto", label: "Ortofoto storiche", layers: [{ ...ortho, theme: "ortofoto" }] },
      { theme: "amministrativo", label: "Limiti amministrativi", layers: [{ ...municipal, theme: "amministrativo" }] },
    ],
    total: 4,
  };
}

function interrogationResponse(layerIds: string[]) {
  const source = (
    sourceId: string,
    title: string,
    status: "ok" | "empty" | "failed" | "skipped",
    data: Array<Record<string, unknown>>,
    message: string | null,
  ) => ({ source_id: sourceId, title, status, duration_ms: 4.2, data, message });

  const emptyLevel = (key: "gaia" | "catasto_ufficiale" | "territorio") => ({ key, sources: [] });
  if (layerIds[0] === RAS_LAYER_ID) {
    return {
      lon: 8.59,
      lat: 39.91,
      srid: 4326,
      radius_m: 150,
      gaia: emptyLevel("gaia"),
      catasto_ufficiale: emptyLevel("catasto_ufficiale"),
      territorio: {
        key: "territorio",
        sources: [source(RAS_LAYER_ID, "Distretti irrigui RAS", "ok", [{ nome: "Comprensorio regionale" }], null)],
      },
    };
  }
  if (layerIds[0] === ADE_LAYER_ID) {
    return {
      lon: 8.59,
      lat: 39.91,
      srid: 4326,
      radius_m: 150,
      gaia: emptyLevel("gaia"),
      catasto_ufficiale: {
        key: "catasto_ufficiale",
        sources: [source(ADE_LAYER_ID, "Particelle catastali AdE", "failed", [], "Sorgente mock non raggiungibile.")],
      },
      territorio: emptyLevel("territorio"),
    };
  }
  return {
    lon: 8.59,
    lat: 39.91,
    srid: 4326,
    radius_m: 150,
    gaia: {
      key: "gaia",
      sources: [
        source("particella", "Particella GAIA", "ok", [{ id: PARCEL_ID, comune: "Arborea", foglio: "14", particella: "82" }], null),
        source("distretto", "Distretto irriguo GAIA", "ok", [{ numero: "12", nome: "Distretto GAIA 12" }], null),
        source("punto_consegna", "Punto di consegna", "empty", [], "Nessun elemento trovato."),
        source("rete_condotte", "Rete condotte", "empty", [], "Nessuna condotta nel raggio."),
        source("dui", "Domanda irrigua", "ok", [{ domanda: "DUI-2026-001" }], null),
        source("ruolo_utenze", "Ruolo e utenze", "empty", [], "Nessun elemento trovato."),
      ],
    },
    catasto_ufficiale: emptyLevel("catasto_ufficiale"),
    territorio: emptyLevel("territorio"),
  };
}

async function mockTerritoryApis(page: Page) {
  const polls = new Map<string, number>();
  const requestedLayerIds: string[] = [];
  let sheetSequence = 0;

  await page.route("**/api/gis/territorio/layers", (route) => json(route, territoryCatalog()));
  await page.route(`**/api/gis/external/${MUNICIPAL_LAYER_ID}/wfs**`, (route) => json(route, {
    type: "FeatureCollection",
    features: [{
      type: "Feature",
      id: "arborea",
      properties: { nome: "Arborea" },
      geometry: { type: "Polygon", coordinates: [[[8.55, 39.75], [8.68, 39.75], [8.68, 39.88], [8.55, 39.75]]] },
    }],
  }));
  await page.route("**/api/gis/interroga", (route) => {
    const payload = route.request().postDataJSON() as { layer_ids?: string[] };
    requestedLayerIds.push(...(payload.layer_ids ?? []));
    return json(route, interrogationResponse(payload.layer_ids ?? []));
  });
  await page.route("**/api/gis/scheda-territoriale", (route) => {
    sheetSequence += 1;
    const id = `00000000-0000-0000-0000-00000000020${sheetSequence}`;
    polls.set(id, 0);
    return json(route, {
      id,
      particella_id: PARCEL_ID,
      status: "queued",
      artifact_path: null,
      checksum_sha256: null,
      source_snapshot: {},
      error_message: null,
    });
  });
  await page.route("**/api/gis/scheda-territoriale/*/pdf", (route) => route.fulfill({
    status: 200,
    contentType: "application/pdf",
    body: Buffer.from("%PDF-1.4 mocked territory sheet"),
  }));
  await page.route("**/api/gis/scheda-territoriale/*", (route) => {
    const id = route.request().url().split("/").at(-1) ?? "";
    const count = (polls.get(id) ?? 0) + 1;
    polls.set(id, count);
    return json(route, {
      id,
      particella_id: PARCEL_ID,
      status: count > 1 ? "completed" : "processing",
      artifact_path: count > 1 ? `/tmp/${id}.pdf` : null,
      checksum_sha256: count > 1 ? "a".repeat(64) : null,
      source_snapshot: { disclaimer: "Scheda istruttoria, non CDU." },
      error_message: null,
    });
  });

  return requestedLayerIds;
}

async function mockCatastoApis(page: Page) {
  await page.route("**/api/catasto/gis/select", (route) => json(route, {
    n_particelle: 0,
    superficie_ha: 0,
    per_foglio: [],
    per_distretto: [],
    particelle: [],
    truncated: false,
  }));
  await page.route("**/api/catasto/gis/saved-selections", (route) => json(route, []));
  await page.route("**/api/catasto/distretti", (route) => json(route, [{
    id: "00000000-0000-0000-0000-000000000012",
    num_distretto: "12",
    nome_distretto: "Arborea",
    attivo: true,
  }]));
  await page.route("**/api/catasto/gis/search", (route) => json(route, {
    query: "Arborea",
    mode_requested: "auto",
    mode_resolved: "particella",
    total: 1,
    results: [{
      id: PARCEL_ID,
      nome_comune: "Arborea",
      codice_catastale: "A123",
      foglio: "14",
      particella: "82",
      subalterno: null,
      superficie_mq: 1200,
      superficie_grafica_mq: 1198,
      utenza_denominazione: "Azienda agricola mock",
      utenza_cf: null,
    }],
    geojson: {
      type: "FeatureCollection",
      features: [{
        type: "Feature",
        properties: { id: PARCEL_ID },
        geometry: {
          type: "Polygon",
          coordinates: [[[8.585, 39.905], [8.595, 39.905], [8.595, 39.915], [8.585, 39.905]]],
        },
      }],
    },
  }));
  await page.route("**/api/catasto/gis/ade-wfs/runs/latest", (route) => json(route, { detail: "Nessun run" }, 404));
  await page.route("**/api/catasto/gis/dui/latest-layer", (route) => json(route, { detail: "Nessun layer" }, 404));
  await page.route("**/api/catasto/gis/whitecompany-reports/layer**", (route) => json(route, { detail: "Nessun report" }, 404));
  await page.route("**/api/catasto/gis/particella/*/popup", (route) => json(route, {
    id: PARCEL_ID,
    cfm: "A123-14-82",
    nome_comune: "Arborea",
    codice_catastale: "A123",
    cod_comune_capacitas: 165,
    foglio: "14",
    particella: "82",
    subalterno: null,
    superficie_mq: 1200,
    superficie_grafica_mq: 1198,
    num_distretto: "12",
    nome_distretto: "Arborea",
    is_current: true,
    suppressed: false,
    source_type: "catasto",
    missing_reason: null,
    missing_fields: [],
    ha_ruolo: false,
    ha_ruolo_inferito: false,
    ruolo_summary: null,
    titolare: null,
    swapped_capacitas: null,
    anomalie_aperte: [],
    n_anomalie_aperte: 0,
  }));

  await page.route(`**/api/catasto/particelle/${PARCEL_ID}**`, (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/consorzio")) return json(route, { particella_id: PARCEL_ID, units: [] });
    if (path.endsWith("/history") || path.endsWith("/utenze") || path.endsWith("/anomalie")) return json(route, []);
    return json(route, {
      id: PARCEL_ID,
      foglio: "14",
      particella: "82",
      subalterno: null,
      nome_comune: "Arborea",
      cod_comune_capacitas: 165,
      codice_catastale: "A123",
      num_distretto: "12",
      superficie_mq: 1200,
      superficie_grafica_mq: 1198,
      fuori_distretto: false,
      capacitas_last_sync_at: null,
      capacitas_last_sync_status: null,
      capacitas_last_sync_error: null,
      swapped_capacitas: null,
    });
  });
}

test("GIS console and toolbar tools fit desktop and mobile viewports", async ({ page }) => {
  test.skip(!ENABLED, "Set PLAYWRIGHT_GIS_TERRITORIO_ENABLED=true to run the optional smoke.");
  await installBrowserStubs(page);
  await loginWithGis(page);
  await mockTerritoryApis(page);
  await mockCatastoApis(page);
  const initialParcelTiles: string[] = [];
  const browserMessages: string[] = [];
  page.on("pageerror", (error) => browserMessages.push(`pageerror: ${error.message}`));
  page.on("request", (request) => {
    const pathname = new URL(request.url()).pathname;
    if (pathname.startsWith("/tiles/cat_particelle_current/")) {
      initialParcelTiles.push(request.url());
    }
  });
  page.on("console", (message) => browserMessages.push(`${message.type()}: ${message.text()}`));
  await page.goto("/catasto/gis");
  const consolePanel = page.getByRole("complementary", { name: "Console GIS" });
  const canvas = page.locator("canvas.maplibregl-canvas");
  await expect.poll(() => initialParcelTiles.length, {
    message: `MapLibre non ha richiesto le tile particelle. Console: ${browserMessages.join(" | ")}`,
  }).toBeGreaterThan(0);
  for (const viewport of [{ width: 1920, height: 900 }, { width: 1280, height: 720 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    await expect(canvas).toBeVisible();
    await expect(consolePanel).toBeHidden();
    await expect(page.getByRole("button", { name: "Ricerca nel comprensorio" })).toBeInViewport({ ratio: 1 });
    await expect(page.getByRole("button", { name: "Misure sul terreno" })).toBeInViewport({ ratio: 1 });
    await expect(page.getByRole("button", { name: "Stampa mappa territoriale" })).toBeInViewport({ ratio: 1 });
    await expect(page.getByRole("button", { name: "Sfondo mappa" })).toBeInViewport({ ratio: 1 });
    await expect(page.getByRole("button", { name: "Interroga punto" })).toHaveCount(0);
    await page.getByRole("button", { name: "Stampa mappa territoriale" }).click({ trial: true });
    await page.getByRole("button", { name: "Apri Console GIS" }).click();
    await expect(consolePanel).toBeVisible();
    await expect(consolePanel.getByRole("button", { name: /Territorio/ })).toBeVisible();
    await expect(consolePanel.getByRole("button", { name: "Riempimento particelle" })).toHaveAttribute("aria-pressed", "false");
    await expect(consolePanel.getByRole("button", { name: "Disegna area", exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Chiudi strumenti GIS" }).click();
    await expect(consolePanel).toBeHidden();
  }
  await page.getByRole("button", { name: "Sfondo mappa" }).click();
  await expect(page.getByRole("button", { name: "Vista classica" })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Vista satellitare" }).click();
  await page.getByRole("button", { name: "Misure sul terreno" }).click();
  await page.getByRole("button", { name: "Distanza", exact: true }).click();
  await clickMapCanvas(canvas, 0.4, 0.4);
  await clickMapCanvas(canvas, 0.6, 0.4);
  await expect(page.locator("output")).not.toBeEmpty();
  await page.getByRole("button", { name: "Distanza", exact: true }).click();
  await expect(page.locator("output")).toHaveCount(0);
  await clickMapCanvas(canvas, 0.4, 0.4);
  await clickMapCanvas(canvas, 0.6, 0.4);
  await expect(page.locator("output")).not.toBeEmpty();
  await page.screenshot({ path: "/tmp/gaia-gis-mobile.png" });
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.screenshot({ path: "/tmp/gaia-gis-desktop.png" });
});

test("territorio smokes map consultation, sheets, measurements, print and QGIS", async ({ page }) => {
  test.skip(!ENABLED, "Set PLAYWRIGHT_GIS_TERRITORIO_ENABLED=true to run the optional smoke.");

  await installBrowserStubs(page);
  await loginWithGis(page);
  const requestedLayerIds = await mockTerritoryApis(page);
  await mockCatastoApis(page);

  await page.goto("/catasto/gis");
  await expect(page.getByRole("heading", { name: "GAIA GIS" })).toBeVisible();
  await page.getByRole("button", { name: "Apri Console GIS" }).click();
  await page.getByRole("button", { name: /Territorio/ }).click();

  await page.getByRole("checkbox", { name: /Distretti irrigui RAS/ }).check();
  await page.getByRole("checkbox", { name: /Limiti amministrativi comunali CTR/ }).check();
  await expect(page.getByText("Regione Autonoma della Sardegna - CC BY 4.0", { exact: true })).toBeVisible();
  await page.getByLabel("Annata principale").selectOption(ORTHO_LAYER_ID);
  await expect(page.getByText(/Una sola annata e oggi autorizzata/)).toBeVisible();
  await expect(page.getByRole("button", { name: /richiesta di modifica/i })).toHaveCount(0);
  await page.getByRole("button", { name: /Territorio/ }).click();
  await page.getByRole("button", { name: "Chiudi strumenti GIS" }).click();

  await page.getByRole("button", { name: "Ricerca nel comprensorio" }).click();
  const searchPanel = page.getByRole("region", { name: "Ricerca unica GIS" });
  const canvas = page.locator("canvas.maplibregl-canvas");
  const [searchPanelBox, canvasBox] = await Promise.all([searchPanel.boundingBox(), canvas.boundingBox()]);
  if (!searchPanelBox || !canvasBox) throw new Error("GIS search panel or map canvas has no bounding box");
  expect(Math.abs(searchPanelBox.x - canvasBox.x)).toBeLessThan(40);
  await page.getByLabel("Cerca nel GIS").fill("Arborea");
  await page.getByRole("button", { name: "Cerca", exact: true }).click();
  await expect(page.getByText("GAIA Catasto", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: /Arborea - Fg\. 14, Part\. 82.*GAIA Catasto/ }).click();
  await expect(page.getByText("RAS SITR", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: /Arborea RAS SITR/ }).click();

  await expect(canvas).toBeVisible();

  await page.getByRole("button", { name: "Apri Console GIS" }).click();
  await page.getByRole("button", { name: "Disegna area", exact: true }).click();
  const drawBox = await canvas.boundingBox();
  if (!drawBox) throw new Error("Map canvas has no bounding box for polygon drawing");
  const firstVertex = { x: drawBox.width * 0.62, y: drawBox.height * 0.35 };
  await canvas.click({ position: firstVertex });
  await canvas.click({ position: { x: drawBox.width * 0.85, y: drawBox.height * 0.35 } });
  await canvas.click({ position: { x: drawBox.width * 0.73, y: drawBox.height * 0.65 } });
  await canvas.click({ position: firstVertex });
  await page.getByRole("button", { name: "Apri Console GIS" }).click();
  await expect(page.getByText("0 particelle selezionate")).toBeVisible();
  await page.getByRole("button", { name: "Cancella selezione" }).click();
  await expect(page.getByRole("button", { name: "Cancella selezione" })).toHaveCount(0);
  await page.getByRole("button", { name: "Chiudi strumenti GIS" }).click();

  const box = await canvas.boundingBox();
  if (!box) throw new Error("Map canvas has no bounding box");
  for (let index = 0; index < 4; index += 1) {
    await page.locator(".maplibregl-ctrl-zoom-in").click();
  }
  await page.waitForTimeout(1_000);
  const closeParcel = page.getByRole("button", { name: "Chiudi dettaglio particella GIS" });
  const parcelCandidates = [
    [0.5, 0.5], [0.45, 0.45], [0.55, 0.45], [0.45, 0.55], [0.55, 0.55],
    [0.4, 0.5], [0.6, 0.5], [0.5, 0.4], [0.5, 0.6],
    [0.75, 0.4], [0.85, 0.4], [0.9, 0.4], [0.75, 0.55], [0.85, 0.55], [0.9, 0.55],
  ] as const;
  for (const [xRatio, yRatio] of parcelCandidates) {
    await clickMapCanvas(canvas, xRatio, yRatio);
    await page.waitForTimeout(200);
    if (await closeParcel.count()) break;
  }
  await expect(closeParcel).toBeVisible();
  await page.getByText("Dati territoriali sul punto").click();

  await expect(page.getByRole("heading", { name: "GAIA", exact: true })).toBeVisible();
  await expect(page.getByText("Distretto GAIA 12")).toBeVisible();
  await expect(page.locator("article").filter({ hasText: "Rete condotte" })).toContainText("Nessun risultato");
  await expect(page.locator("article").filter({ hasText: "Particelle catastali AdE" })).toContainText("Sorgente non raggiungibile");
  await expect(page.locator("article").filter({ hasText: "Distretti irrigui RAS" })).toContainText("Comprensorio regionale");
  await expect(page.locator("article").filter({ hasText: "Ortofoto storica 1977-1978" })).toContainText("Non interrogabile");
  expect(requestedLayerIds).toEqual(expect.arrayContaining([RAS_LAYER_ID, ADE_LAYER_ID]));
  expect(requestedLayerIds).not.toContain(ORTHO_LAYER_ID);

  await page.getByRole("button", { name: "Genera scheda territoriale" }).click();
  await expect(page.getByRole("link", { name: "Scarica scheda territoriale PDF" })).toBeVisible();
  await page.getByRole("button", { name: "Chiudi" }).click();

  await page.getByRole("button", { name: "Misure sul terreno" }).click();
  await page.getByRole("button", { name: "Distanza" }).click();
  await clickMapCanvas(canvas, 0.35, 0.45);
  await clickMapCanvas(canvas, 0.55, 0.45);
  await expect(page.locator("output")).toContainText(/m|km/);
  await page.getByRole("button", { name: "Stampa mappa territoriale" }).click();
  await expect.poll(() => page.evaluate(() => Boolean((window as Window & { __territorioPrintCalled?: boolean }).__territorioPrintCalled))).toBe(true);
  await expect.poll(() => page.evaluate(() => (window as Window & { __territorioPrintHtml?: string }).__territorioPrintHtml ?? "")).toContain("Attribuzioni");

  await page.goto(`/catasto/particelle/${PARCEL_ID}`);
  await expect(page.getByRole("heading", { level: 2, name: "Fg.14 Part.82" })).toBeVisible();
  await page.getByRole("button", { name: "Genera scheda territoriale" }).click();
  await expect(page.getByRole("link", { name: "Scarica scheda territoriale PDF" })).toBeVisible();

  await page.route("**/api/gis/layers**", (route) => json(route, { items: [], total: 0 }));
  await page.route("**/api/gis/exports**", (route) => json(route, { items: [], total: 0 }));
  await page.route("**/api/gis/imports**", (route) => json(route, { items: [], total: 0 }));
  await page.route("**/api/gis/ogc/poc", (route) => json(route, { recommended_server: "qgis-server", publishable_layer_count: 1 }));
  await page.route("**/api/gis/qgis/project", (route) => route.fulfill({
    status: 200,
    contentType: "application/zip",
    headers: { "Content-Disposition": "attachment; filename=gaia-gis-platform.qgz" },
    body: Buffer.from("PK mocked qgis project"),
  }));
  await page.goto("/gis/strumenti");
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Scarica progetto QGIS" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("gaia-gis-platform.qgz");
  await expect(page.getByRole("status")).toContainText("Progetto QGIS scaricato.");
});
