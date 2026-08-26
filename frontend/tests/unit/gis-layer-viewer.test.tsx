import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import {
  GisLayerViewer,
  buildGisLayerStyleLayers,
  getMartinZoomRange,
  loadGisLayerMapData,
} from "@/app/gis/catalogo/layer-viewer";
import type { GisCatalogLayer } from "@/types/gis";

const mocks = vi.hoisted(() => ({
  listGisLayerFeatures: vi.fn(),
  mapConstructor: vi.fn(),
  mapInstances: [] as Array<Record<string, ReturnType<typeof vi.fn>>>,
}));

vi.mock("@/lib/api/gis", () => ({
  listGisLayerFeatures: (...args: unknown[]) => mocks.listGisLayerFeatures(...args),
}));

vi.mock("maplibre-gl", () => ({
  default: {
    Map: function Map(options: unknown) {
      return mocks.mapConstructor(options);
    },
    NavigationControl: function NavigationControl() {},
    ScaleControl: function ScaleControl() {},
  },
}));

const layer = {
  id: "layer-1",
  workspace: "rete",
  name: "rete_condotte",
  title: "Condotte irrigue",
  source_type: "postgis",
  official_source: "postgis",
  geometry_type: "MULTILINESTRING",
  martin_layer_id: null,
  metadata: {},
  is_active: true,
  effective_access_level: "viewer",
  can_view: true,
  can_annotate: false,
  can_edit: false,
  can_approve: false,
  can_manage: false,
  created_at: "2026-08-25T08:00:00Z",
  updated_at: "2026-08-25T08:00:00Z",
} satisfies GisCatalogLayer;

function createMapInstance() {
  const instance = {
    addControl: vi.fn(),
    addSource: vi.fn(),
    addLayer: vi.fn(),
    remove: vi.fn(),
    on: vi.fn((event: string, callback: () => void) => {
      if (event === "load") callback();
    }),
  };
  mocks.mapInstances.push(instance);
  return instance;
}

describe("GIS layer viewer", () => {
  beforeEach(() => {
    mocks.listGisLayerFeatures.mockReset();
    mocks.mapConstructor.mockReset();
    mocks.mapInstances.length = 0;
    mocks.mapConstructor.mockImplementation(() => createMapInstance());
  });

  test("builds distinct map styles for points, lines and polygons", () => {
    expect(buildGisLayerStyleLayers("POINT", "points")[0]).toMatchObject({
      type: "circle",
      "source-layer": "points",
    });
    expect(buildGisLayerStyleLayers("MULTILINESTRING")[0]).toMatchObject({ type: "line" });
    expect(buildGisLayerStyleLayers(null)).toHaveLength(2);
    expect(buildGisLayerStyleLayers("MULTIPOLYGON", "areas")[0]).toMatchObject({
      type: "fill",
      "source-layer": "areas",
    });
  });

  test("reads Martin zoom limits from catalog metadata", () => {
    expect(getMartinZoomRange({ tiles: { minzoom: 11, maxzoom: 19 } })).toEqual({
      minzoom: 11,
      maxzoom: 19,
    });
    expect(getMartinZoomRange({ tiles: {} })).toEqual({ minzoom: 7, maxzoom: 22 });
    expect(getMartinZoomRange({ tiles: null })).toEqual({ minzoom: 7, maxzoom: 22 });
    expect(getMartinZoomRange({ tiles: [] })).toEqual({ minzoom: 7, maxzoom: 22 });
    expect(getMartinZoomRange({ tiles: "martin" })).toEqual({ minzoom: 7, maxzoom: 22 });
  });

  test("loads paginated GeoJSON and skips records without geometry", async () => {
    mocks.listGisLayerFeatures
      .mockResolvedValueOnce({
        items: [
          { feature_id: "1", label: "Uno", attributes: {}, geometry: { type: "Point", coordinates: [9, 40] } },
          { feature_id: "2", label: "Due", attributes: {}, geometry: null },
        ],
        total: 3,
        limit: 50,
        offset: 0,
        has_more: true,
      })
      .mockResolvedValueOnce({
        items: [{ feature_id: "3", label: "Tre", attributes: {}, geometry: { type: "Point", coordinates: [10, 41] } }],
        total: 3,
        limit: 50,
        offset: 2,
        has_more: false,
      });

    const result = await loadGisLayerMapData("token", "layer-1");

    expect(result.featureCollection.features).toHaveLength(2);
    expect(result.truncated).toBe(false);
    expect(mocks.listGisLayerFeatures).toHaveBeenNthCalledWith(2, "token", "layer-1", undefined, 50, 2);
  });

  test("stops on empty pages and reports truncation at the configured limit", async () => {
    mocks.listGisLayerFeatures
      .mockResolvedValueOnce({
        items: [{ feature_id: "1", label: "Uno", attributes: {}, geometry: { type: "Point", coordinates: [9, 40] } }],
        total: 2,
        limit: 50,
        offset: 0,
        has_more: true,
      })
      .mockResolvedValueOnce({ items: [], total: 2, limit: 50, offset: 1, has_more: true });

    await expect(loadGisLayerMapData("token", "layer-1", 1)).resolves.toMatchObject({ truncated: true });
    await expect(loadGisLayerMapData("token", "layer-1", 10)).resolves.toMatchObject({ truncated: true });
  });

  test("renders Martin vector tiles without loading fallback features", async () => {
    const { unmount } = render(
      <GisLayerViewer
        token="token"
        layer={{
          ...layer,
          martin_layer_id: "rete condotte",
          metadata: { tiles: { minzoom: 12, maxzoom: 18 } },
        }}
      />,
    );

    await waitFor(() => expect(screen.queryByText("Caricamento mappa...")).not.toBeInTheDocument());
    const map = mocks.mapInstances[0];
    expect(mocks.listGisLayerFeatures).not.toHaveBeenCalled();
    expect(map.addSource).toHaveBeenCalledWith("gaia-catalog-layer", {
      type: "vector",
      tiles: ["http://localhost:3000/tiles/rete%20condotte/{z}/{x}/{y}"],
      minzoom: 12,
      maxzoom: 18,
    });
    expect(mocks.mapConstructor).toHaveBeenCalledWith(
      expect.objectContaining({ center: [8.6, 39.85], zoom: 12 }),
    );
    expect(map.addLayer).toHaveBeenCalled();
    unmount();
    expect(map.remove).toHaveBeenCalled();
  });

  test("renders fallback GeoJSON, truncation feedback and load errors", async () => {
    mocks.listGisLayerFeatures.mockResolvedValueOnce({
      items: Array.from({ length: 1000 }, (_, index) => ({ feature_id: String(index), label: `Elemento ${index}`, attributes: {}, geometry: { type: "LineString", coordinates: [[9, 40], [10, 41]] } })),
      total: 1001,
      limit: 50,
      offset: 0,
      has_more: true,
    });
    render(<GisLayerViewer token="token" layer={layer} />);
    await waitFor(() => expect(mocks.mapInstances[0].addSource).toHaveBeenCalled());
    expect(screen.getByText(/Vista rapida limitata/)).toBeInTheDocument();

    mocks.listGisLayerFeatures.mockRejectedValueOnce(new Error("feature offline"));
    render(<GisLayerViewer token="token" layer={{ ...layer, id: "layer-error" }} />);
    expect(await screen.findByText("feature offline")).toBeInTheDocument();

    mocks.mapConstructor.mockImplementationOnce(() => {
      throw "webgl offline";
    });
    mocks.listGisLayerFeatures.mockResolvedValueOnce({ items: [], total: 0, limit: 50, offset: 0, has_more: false });
    render(<GisLayerViewer token="token" layer={{ ...layer, id: "layer-webgl" }} />);
    expect(await screen.findByText("Mappa temporaneamente non disponibile")).toBeInTheDocument();
  });

  test("ignores late data, map load and errors after unmount", async () => {
    let resolveFeatures: (value: unknown) => void = () => undefined;
    mocks.listGisLayerFeatures.mockReturnValueOnce(new Promise((resolve) => { resolveFeatures = resolve; }));
    const lateData = render(<GisLayerViewer token="token" layer={layer} />);
    lateData.unmount();
    resolveFeatures({ items: [], total: 0, limit: 50, offset: 0, has_more: false });
    await waitFor(() => expect(mocks.listGisLayerFeatures).toHaveBeenCalled());

    let rejectFeatures: (reason: unknown) => void = () => undefined;
    mocks.listGisLayerFeatures.mockReturnValueOnce(new Promise((_, reject) => { rejectFeatures = reject; }));
    const lateError = render(<GisLayerViewer token="token" layer={{ ...layer, id: "late-error" }} />);
    lateError.unmount();
    rejectFeatures(new Error("late"));
    await waitFor(() => expect(mocks.listGisLayerFeatures).toHaveBeenCalledTimes(2));

    let loadCallback: () => void = () => undefined;
    mocks.mapConstructor.mockImplementationOnce(() => ({
      ...createMapInstance(),
      on: vi.fn((_event: string, callback: () => void) => { loadCallback = callback; }),
    }));
    const lateMap = render(<GisLayerViewer token="token" layer={{ ...layer, martin_layer_id: "late" }} />);
    await waitFor(() => expect(mocks.mapConstructor).toHaveBeenCalled());
    lateMap.unmount();
    loadCallback();
  });
});
