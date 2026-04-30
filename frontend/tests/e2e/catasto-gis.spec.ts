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

test("catasto gis imports xlsx and manages saved selections", async ({ page }) => {
  await loginAsAdmin(page);

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

  await page.goto("/catasto/gis");

  await expect(page.getByText("Catasto GIS")).toBeVisible();
  await expect(page.getByRole("button", { name: "Distretti" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Particelle" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Evidenzia sel." })).toBeVisible();
  await expect(page.getByPlaceholder("es. 03")).toBeVisible();
  await expect(page.getByText("Nessuna selezione salvata.")).toBeVisible();

  await page.getByPlaceholder("es. 03").fill("12");
  await expect(page.getByPlaceholder("es. 03")).toHaveValue("12");
  await page.getByTitle("Rimuovi filtro").click();
  await expect(page.getByPlaceholder("es. 03")).toHaveValue("");

  await page.locator('input[type="file"]').setInputFiles({
    name: "gis-selezione.xlsx",
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: buildWorkbookBuffer(),
  });

  await expect(page.getByText("gis-selezione.xlsx")).toBeVisible();
  await expect(page.getByText("Import completato: trovate 1/2. Non trovate: 1.")).toBeVisible();
  await expect(page.locator('input[placeholder="Nome selezione"]')).toHaveValue("gis-selezione");
  await expect(page.getByText("trovate", { exact: true })).toBeVisible();
  await expect(page.getByText("in mappa", { exact: true })).toBeVisible();
  await expect(page.getByText("scarti", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Salva selezione" }).click();
  await expect(page.getByText("Selezione salvata: gis-selezione (1 particelle).")).toBeVisible();
  await expect(page.getByText("1 particelle · 1 in mappa")).toBeVisible();

  await page.locator('input[type="color"]').fill("#EF4444");
  await page.getByRole("button", { name: "Aggiorna" }).first().click();
  await expect(page.getByText("Selezione salvata aggiornata.")).toBeVisible();

  await page.getByRole("button", { name: "Rimuovi" }).click();
  await expect(page.getByRole("button", { name: "Carica in mappa" })).toBeVisible();
  await page.getByRole("button", { name: "Carica in mappa" }).click();
  await expect(page.getByText("Selezione caricata: gis-selezione.")).toBeVisible();

  await page.getByRole("button", { name: "Elimina" }).click();
  await expect(page.getByText("Nessuna selezione salvata.")).toBeVisible();
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
  await expect(
    page.getByText("WebGL non e disponibile in questo browser o in questa sessione. Il GIS richiede WebGL attivo."),
  ).toBeVisible();
  await expect(page.getByText(/MapLibre non puo renderizzare senza WebGL/)).toBeVisible();
});
