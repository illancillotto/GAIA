import { beforeEach, describe, expect, test, vi } from "vitest";

import { runCatastoGisSmartSearch } from "@/lib/catasto-gis-search-runner";

const mocks = vi.hoisted(() => ({
  catastoGisSearch: vi.fn(),
}));

vi.mock("@/lib/api/catasto", () => ({
  catastoGisSearch: mocks.catastoGisSearch,
}));

const modeLabels = {
  auto: "Auto",
  particella: "Particella",
  codice_fiscale: "Codice fiscale",
  denominazione: "Denominazione",
} as const;

describe("catasto GIS smart search runner", () => {
  beforeEach(() => {
    mocks.catastoGisSearch.mockReset();
  });

  test("resolves coordinate queries without calling the API", async () => {
    const result = await runCatastoGisSmartSearch("token", "39,9042 8,5917", "auto", modeLabels);

    expect(mocks.catastoGisSearch).not.toHaveBeenCalled();
    expect(result.info).toBe("Coordinate: 39.904200, 8.591700.");
    expect(result.focusOptions).toEqual({ maxZoom: 15, padding: 48, duration: 700 });
    expect(result.response.total).toBe(1);
    const pointFeature = result.focusGeojson?.features.find((feature) => feature.geometry?.type === "Point");
    expect(pointFeature?.geometry).toEqual({
      type: "Point",
      coordinates: [8.5917, 39.9042],
    });
  });

  test("runs text search through the Catasto GIS API", async () => {
    const geojson: GeoJSON.FeatureCollection = {
      type: "FeatureCollection",
      features: [{ type: "Feature", geometry: null, properties: { id: "p1" } }],
    };
    mocks.catastoGisSearch.mockResolvedValue({
      query: "foglio 1",
      mode_requested: "auto",
      mode_resolved: "particella",
      total: 1,
      results: [],
      geojson,
    });

    const result = await runCatastoGisSmartSearch("token", "foglio 1", "auto", modeLabels);

    expect(mocks.catastoGisSearch).toHaveBeenCalledWith("token", { query: "foglio 1", mode: "auto", limit: 25 });
    expect(result.info).toBe("Ricerca Particella: 1 risultati.");
    expect(result.focusGeojson).toBe(geojson);
  });

  test("reports empty text search without focus geojson", async () => {
    mocks.catastoGisSearch.mockResolvedValue({
      query: "missing",
      mode_requested: "auto",
      mode_resolved: "auto",
      total: 0,
      results: [],
      geojson: { type: "FeatureCollection", features: [] },
    });

    const result = await runCatastoGisSmartSearch("token", "missing", "auto", modeLabels);

    expect(result.info).toBe("Nessun risultato per “missing”.");
    expect(result.focusGeojson).toBeNull();
  });
});
