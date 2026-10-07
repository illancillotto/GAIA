import { test, expect, type Page } from "@playwright/test";
import * as XLSX from "xlsx";

async function loginAsAdmin(page: Page) {
  const username = process.env.PLAYWRIGHT_ADMIN_USERNAME ?? "admin";
  const password = process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? "#0r1st4n3s1";

  await page.goto("/login");
  await page.getByLabel("Username o email").fill(username);
  await page.locator("input#password").fill(password);
  await page.getByRole("button", { name: "Accedi alla piattaforma" }).click();
  await page.waitForURL("**/");
}

function buildWorkbookBuffer(): Buffer {
  const workbook = XLSX.utils.book_new();
  const worksheet = XLSX.utils.json_to_sheet([
    { comune: "Arborea", foglio: "14", particella: "82", sub: "A" },
    { comune: "Cabras", foglio: "9", particella: "999", sub: "" },
  ]);
  XLSX.utils.book_append_sheet(workbook, worksheet, "Selezione");
  return XLSX.write(workbook, { type: "buffer", bookType: "xlsx" }) as Buffer;
}

async function setupGisWorkspace(page: Page) {
  await loginAsAdmin(page);

  await page.route("**/api/catasto/distretti", async (route) => {
    await route.fulfill({ json: [{
      id: "00000000-0000-0000-0000-000000004401",
      num_distretto: "12",
      nome_distretto: "Distretto test",
      decreto_istitutivo: null,
      data_decreto: null,
      attivo: true,
      note: null,
      created_at: "2026-04-30T09:10:00Z",
      updated_at: "2026-04-30T09:10:00Z",
    }] });
  });
  await page.route("**/api/catasto/distretti/*/geojson", async (route) => {
    await route.fulfill({ json: {
      type: "Feature",
      properties: { num_distretto: "12" },
      geometry: { type: "Polygon", coordinates: [[[8.55, 39.88], [8.56, 39.88], [8.56, 39.89], [8.55, 39.89], [8.55, 39.88]]] },
    } });
  });

  const savedSelections: Array<{
    id: string;
    name: string;
    color: string;
    source_filename: string | null;
    n_particelle: number;
    n_with_geometry: number;
    import_summary: Record<string, unknown> | null;
    created_at: string;
    updated_at: string;
    geojson: GeoJSON.FeatureCollection;
  }> = [];

  await page.route("**/api/catasto/gis/resolve-refs", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        processed: 2,
        found: 1,
        not_found: 1,
        multiple: 0,
        invalid: 0,
        results: [
          {
            row_index: 2,
            comune_input: "Arborea",
            sezione_input: null,
            foglio_input: "14",
            particella_input: "82",
            sub_input: "A",
            esito: "FOUND",
            message: "OK",
            particella_id: "00000000-0000-0000-0000-000000004201",
          },
          {
            row_index: 3,
            comune_input: "Cabras",
            sezione_input: null,
            foglio_input: "9",
            particella_input: "999",
            sub_input: null,
            esito: "NOT_FOUND",
            message: "Particella non trovata",
            particella_id: null,
          },
        ],
        geojson: {
          type: "FeatureCollection",
          features: [
            {
              type: "Feature",
              geometry: {
                type: "Polygon",
                coordinates: [[[8.55, 39.88], [8.56, 39.88], [8.56, 39.89], [8.55, 39.89], [8.55, 39.88]]],
              },
              properties: {
                id: "00000000-0000-0000-0000-000000004201",
                num_distretto: "12",
              },
            },
          ],
        },
      }),
    });
  });

  await page.route("**/api/catasto/gis/saved-selections", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(
          savedSelections.map(({ geojson: _geojson, ...summary }) => summary),
        ),
      });
      return;
    }

    const payload = route.request().postDataJSON() as {
      name: string;
      color: string;
      source_filename?: string | null;
      import_summary?: Record<string, unknown> | null;
    };
    const detail = {
      id: "00000000-0000-0000-0000-000000004301",
      name: payload.name,
      color: payload.color,
      source_filename: payload.source_filename ?? null,
      n_particelle: 1,
      n_with_geometry: 1,
      import_summary: payload.import_summary ?? null,
      created_at: "2026-04-30T09:10:00Z",
      updated_at: "2026-04-30T09:10:00Z",
      geojson: {
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            geometry: {
              type: "Polygon",
              coordinates: [[[8.55, 39.88], [8.56, 39.88], [8.56, 39.89], [8.55, 39.89], [8.55, 39.88]]],
            },
            properties: {
              id: "00000000-0000-0000-0000-000000004201",
              num_distretto: "12",
            },
          },
        ],
      } satisfies GeoJSON.FeatureCollection,
    };
    savedSelections.splice(0, savedSelections.length, detail);

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(detail),
    });
  });

  await page.route("**/api/catasto/gis/saved-selections/*", async (route) => {
    const selectionId = route.request().url().split("/").at(-1) ?? "";

    if (route.request().method() === "GET") {
      const detail = savedSelections.find((item) => item.id === selectionId);
      await route.fulfill({
        status: detail ? 200 : 404,
        contentType: "application/json",
        body: JSON.stringify(detail ?? { detail: "Not found" }),
      });
      return;
    }

    if (route.request().method() === "PATCH") {
      const payload = route.request().postDataJSON() as { name?: string; color?: string };
      const detail = savedSelections.find((item) => item.id === selectionId);
      if (detail) {
        detail.name = payload.name ?? detail.name;
        detail.color = payload.color ?? detail.color;
        detail.updated_at = "2026-04-30T09:11:00Z";
      }
      await route.fulfill({
        status: detail ? 200 : 404,
        contentType: "application/json",
        body: JSON.stringify(detail ?? { detail: "Not found" }),
      });
      return;
    }

    const index = savedSelections.findIndex((item) => item.id === selectionId);
    if (index >= 0) savedSelections.splice(index, 1);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true }),
    });
  });

  await page.route("**/api/catasto/gis/search", async (route) => {
    const payload = route.request().postDataJSON() as { query?: string; mode?: string };
    const query = payload.query ?? "";
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        query,
        mode_requested: payload.mode ?? "auto",
        mode_resolved: query.includes("RSS") ? "codice_fiscale" : "particella",
        total: 1,
        results: [
          {
            id: "00000000-0000-0000-0000-000000004201",
            cfm: "CFM-4201",
            cod_comune_capacitas: 165,
            cod_comune_istat: 165,
            codice_catastale: "A123",
            nome_comune: "Arborea",
            foglio: "14",
            particella: "82",
            subalterno: "A",
            superficie_mq: 1200,
            superficie_grafica_mq: 1198,
            num_distretto: "12",
            nome_distretto: "Distretto 12",
            utenza_cf: "RSSMRA80A01H501Z",
            utenza_denominazione: "Azienda Agricola Rossi",
            ha_anomalie: false,
            match_source: query.includes("RSS") ? "codice_fiscale" : "particella",
            match_value: query,
          },
        ],
        geojson: {
          type: "FeatureCollection",
          features: [
            {
              type: "Feature",
              geometry: {
                type: "Polygon",
                coordinates: [[[8.55, 39.88], [8.56, 39.88], [8.56, 39.89], [8.55, 39.89], [8.55, 39.88]]],
              },
              properties: {
                id: "00000000-0000-0000-0000-000000004201",
              },
            },
          ],
        },
      }),
    });
  });

  await page.route("**/api/catasto/gis/particella/*/popup", async (route) => {
    if (!route.request().url().endsWith("/00000000-0000-0000-0000-000000004201/popup")) {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "00000000-0000-0000-0000-000000004201",
        cfm: "CFM-4201",
        cod_comune_capacitas: 165,
        cod_comune_istat: 165,
        codice_catastale: "A123",
        nome_comune: "Arborea",
        foglio: "14",
        particella: "82",
        subalterno: "A",
        superficie_mq: 1200,
        superficie_grafica_mq: 1198,
        num_distretto: "12",
        nome_distretto: "Distretto 12",
        n_anomalie_aperte: 0,
        titolare: {
          codice_fiscale: "RSSMRA80A01H501Z",
          partita_iva: null,
          denominazione: "Azienda Agricola Rossi",
          titoli: null,
          source: "utenza",
        },
        ha_ruolo: true,
        ruolo_summary: null,
        swapped_capacitas: null,
        anomalie_aperte: [],
      }),
    });
  });
}

test("catasto gis imports xlsx and manages saved selections", async ({ page }) => {
  await setupGisWorkspace(page);
  await page.goto("/catasto/gis");
  await page.getByRole("button", { name: "Apri Console GIS" }).click();

  await expect(page.getByRole("complementary", { name: "Console GIS" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Distretti", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Riempimento particelle", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Evidenzia sel." })).toBeVisible();
  await expect(page.getByPlaceholder("Cerca per numero o nome")).toBeVisible();
  await expect(page.getByText("Nessuna selezione salvata.")).toBeVisible();

  await page.getByPlaceholder("Cerca per numero o nome").fill("12");
  await expect(page.getByPlaceholder("Cerca per numero o nome")).toHaveValue("12");
  await page.getByRole("button", { name: "Distretto 12 Distretto test", exact: true }).click();
  await expect(page.getByText("Filtro attivo: distretto 12")).toBeVisible();
  const districtPanel = page.getByRole("button", { name: /Distretti irrigui Filtro attivo/ }).locator("..");
  await districtPanel.getByRole("button", { name: "Tutti", exact: true }).click();
  await expect(page.getByText("Filtro attivo: distretto 12")).toHaveCount(0);
  await page.getByRole("button", { name: "Pulisci filtro distretti" }).click();
  await expect(page.getByPlaceholder("Cerca per numero o nome")).toHaveValue("");

  const resolveRequest = page.waitForRequest((request) => request.url().endsWith("/api/catasto/gis/resolve-refs"));
  await page.locator('input[type="file"]').setInputFiles({
    name: "gis-selezione.xlsx",
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: buildWorkbookBuffer(),
  });
  expect((await resolveRequest).postDataJSON()).toEqual({
    include_geometry: true,
    items: [
      { row_index: 2, comune: "Arborea", sezione: null, foglio: "14", particella: "82", sub: "A" },
      { row_index: 3, comune: "Cabras", sezione: null, foglio: "9", particella: "999", sub: null },
    ],
  });

  await expect(page.locator("label").filter({ has: page.locator('input[type="file"]') }).getByText("gis-selezione.xlsx", { exact: true })).toBeVisible();
  await expect(page.getByText("Import completato: trovate 1/2. Non trovate: 1.")).toBeVisible();
  await expect(page.getByPlaceholder("Nome layer")).toHaveValue("gis-selezione");
  const importedLayer = page.getByPlaceholder("Nome layer").locator("../..");
  await expect(importedLayer.getByText("trovate", { exact: true }).locator("..")).toHaveText(/^1\s*trovate$/);
  await expect(importedLayer.getByText("in mappa", { exact: true }).locator("..")).toHaveText(/^1\s*in mappa$/);
  await expect(importedLayer.getByText("scarti", { exact: true }).locator("..")).toHaveText(/^1\s*scarti$/);

  await page.getByRole("button", { name: "Salva permanentemente" }).click();
  await expect(page.getByText("Layer salvato: gis-selezione (1 particelle).")).toBeVisible();
  await expect(page.getByText("1 particelle · 1 in mappa")).toBeVisible();

  await page.getByTitle("Colore layer", { exact: true }).fill("#EF4444");
  const updateRequest = page.waitForRequest((request) => request.method() === "PATCH" && request.url().includes("/api/catasto/gis/saved-selections/"));
  await page.getByRole("button", { name: "Aggiorna metadati salvati" }).click();
  expect((await updateRequest).postDataJSON()).toMatchObject({ color: "#EF4444" });
  await expect(page.getByText("Layer aggiornato: gis-selezione.")).toBeVisible();

  await page.getByRole("button", { name: "Rimuovi", exact: true }).click();
  await expect(page.getByPlaceholder("Nome layer")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Aggiungi in mappa" })).toBeVisible();
  await page.getByRole("button", { name: "Aggiungi in mappa" }).click();
  await expect(page.getByText("Layer caricato: gis-selezione.")).toBeVisible();
  await expect(page.getByTitle("Colore layer", { exact: true })).toHaveValue("#ef4444");

  await page.getByRole("button", { name: "Elimina" }).click();
  await expect(page.getByText("Nessuna selezione salvata.")).toBeVisible();
  await expect(page.getByPlaceholder("Nome layer")).toHaveCount(0);
});

test("catasto gis fiscal search opens parcel role details", async ({ page }) => {
  await setupGisWorkspace(page);
  await page.goto("/catasto/gis");
  await page.getByRole("button", { name: "Ricerca nel comprensorio" }).click();
  const search = page.getByRole("region", { name: "Ricerca unica GIS" });
  await search.getByRole("searchbox", { name: "Cerca nel GIS" }).fill("RSSMRA80A01H501Z");
  const searchRequest = page.waitForRequest((request) => request.url().endsWith("/api/catasto/gis/search"));
  await search.getByRole("button", { name: "Cerca", exact: true }).click();
  expect((await searchRequest).postDataJSON()).toMatchObject({ query: "RSSMRA80A01H501Z", mode: "auto" });
  await expect(search.getByRole("listitem")).toHaveCount(1);
  await expect(search.getByText("Azienda Agricola Rossi")).toBeVisible();
  await search.getByRole("button", { name: /Arborea - Fg\. 14, Part\. 82/ }).click();
  await page.getByRole("button", { name: "Ricerca nel comprensorio" }).click();
  const popupRequest = page.waitForRequest((request) => request.url().endsWith("/api/catasto/gis/particella/00000000-0000-0000-0000-000000004201/popup"));
  const parcelPanel = page.locator("[data-gis-parcel-panel]");
  await expect(async () => {
    await page.locator("canvas.maplibregl-canvas").click({ timeout: 5000 });
    await expect(parcelPanel.getByText("A ruolo", { exact: true })).toBeVisible({ timeout: 1000 });
  }).toPass({ timeout: 10000, intervals: [250, 500, 1000] });
  await popupRequest;
  await expect(parcelPanel.getByText("CFM-4201", { exact: true })).toBeVisible();
});

test("catasto gis shows graceful fallback when WebGL is unavailable", async ({ page }) => {
  await page.addInitScript(() => {
    const originalGetContext = HTMLCanvasElement.prototype.getContext;
    Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
      configurable: true,
      value(this: HTMLCanvasElement, contextId: string, options?: unknown) {
        if (contextId === "webgl" || contextId === "webgl2" || contextId === "experimental-webgl") {
          return null;
        }
        return originalGetContext.call(this, contextId as never, options as never);
      },
    });
  });

  await loginAsAdmin(page);

  await page.route("**/api/catasto/gis/saved-selections", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  await page.goto("/catasto/gis");

  await expect(page.getByText("GIS non disponibile")).toBeVisible();
  expect(await page.evaluate(() => ({
    webgl2Unavailable: document.createElement("canvas").getContext("webgl2") === null,
    canvas2dAvailable: document.createElement("canvas").getContext("2d") !== null,
  }))).toEqual({ webgl2Unavailable: true, canvas2dAvailable: true });
  await expect(
    page.getByText("WebGL2 non e disponibile in questo browser o in questa sessione. Il GIS richiede WebGL2 attivo."),
  ).toBeVisible();
  await expect(page.getByText(/MapLibre non puo renderizzare senza WebGL/)).toBeVisible();
});
