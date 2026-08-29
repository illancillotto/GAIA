import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import {
  useTerritorioLayers,
  type TerritorioMapAdapter,
} from "@/components/catasto/gis/use-territorio-layers";

const apiMocks = vi.hoisted(() => ({
  listGisTerritorioLayers: vi.fn(),
  getGisTerritorioLegend: vi.fn(),
}));

vi.mock("@/lib/api/territorio", () => apiMocks);

const layer = {
  id: "layer-1",
  name: "ras_aree_bonifica",
  title: "Aree della bonifica",
  description: "Descrizione",
  theme: "bonifica",
  source: "ras_sitr",
  proxy_wms_url: "/gis/external/layer-1/wms",
  legend_url: "/gis/external/layer-1/wms?request=GetLegendGraphic",
  default_opacity: 0.65,
  render_order: 0,
  queryable: "wfs_queryable" as const,
  attribution: "Regione Sardegna",
};

function mapAdapter() {
  const sources = new Set<string>();
  const layers = new Set(["distretti-fill"]);
  let errorListener: ((event: { error?: Error; sourceId?: string }) => void) | null = null;
  const map: TerritorioMapAdapter = {
    addSource: vi.fn((id: string) => sources.add(id)),
    getSource: vi.fn((id: string) => sources.has(id)),
    removeSource: vi.fn((id: string) => sources.delete(id)),
    addLayer: vi.fn((definition: object) => layers.add((definition as { id: string }).id)),
    getLayer: vi.fn((id: string) => layers.has(id)),
    removeLayer: vi.fn((id: string) => layers.delete(id)),
    setPaintProperty: vi.fn(),
    setTransformRequest: vi.fn(),
    on: vi.fn((_event, listener) => { errorListener = listener; }),
    off: vi.fn(),
  };
  return { map, emitError: (event: { error?: Error; sourceId?: string }) => errorListener?.(event) };
}

describe("useTerritorioLayers", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.listGisTerritorioLayers.mockResolvedValue({
      groups: [{ theme: "bonifica", label: "Bonifica e comprensori", layers: [layer] }],
      total: 1,
    });
    apiMocks.getGisTerritorioLegend.mockResolvedValue(new Blob(["legend"]));
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:legend") });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
  });

  test("loads the catalog and registers proxy raster below GAIA layers", async () => {
    const { map } = mapAdapter();
    const { result } = renderHook(() => useTerritorioLayers(map, "token"));
    await waitFor(() => expect(result.current.groups).toHaveLength(1));
    const transform = vi.mocked(map.setTransformRequest).mock.calls[0][0];
    expect(transform("/gis/external/layer-1/wms")).toEqual({
      url: "/gis/external/layer-1/wms",
      headers: { Authorization: "Bearer token" },
    });
    expect(transform("https://tiles.example.test/a")).toEqual({ url: "https://tiles.example.test/a" });

    act(() => result.current.toggleLayer(layer.id));

    await waitFor(() => expect(map.addSource).toHaveBeenCalled());
    expect(map.addSource).toHaveBeenCalledWith(
      "territorio-source-layer-1",
      expect.objectContaining({
        tiles: [expect.stringContaining("%7Bbbox-epsg-3857%7D")],
        attribution: "Regione Sardegna",
      }),
    );
    expect(map.addLayer).toHaveBeenCalledWith(
      expect.objectContaining({ id: "territorio-layer-layer-1" }),
      "distretti-fill",
    );
    await waitFor(() => expect(result.current.legendUrls[layer.id]).toBe("blob:legend"));

    act(() => result.current.setLayerOpacity(layer.id, 0.4));
    await waitFor(() => expect(map.setPaintProperty).toHaveBeenCalledWith("territorio-layer-layer-1", "raster-opacity", 0.4));

    act(() => result.current.toggleLayer(layer.id));
    await waitFor(() => expect(map.removeLayer).toHaveBeenCalledWith("territorio-layer-layer-1"));
    expect(map.removeSource).toHaveBeenCalledWith("territorio-source-layer-1");
  });

  test("isolates source, catalog and legend errors", async () => {
    const { map, emitError } = mapAdapter();
    apiMocks.getGisTerritorioLegend.mockRejectedValueOnce("offline");
    const { result } = renderHook(() => useTerritorioLayers(map, "token"));
    await waitFor(() => expect(result.current.groups).toHaveLength(1));
    act(() => result.current.toggleLayer(layer.id));
    await waitFor(() => expect(result.current.layerErrors[layer.id]).toBe("Legenda non disponibile"));

    act(() => emitError({ sourceId: "territorio-source-layer-1", error: new Error("WMS timeout") }));
    expect(result.current.layerErrors[layer.id]).toBe("WMS timeout");
    act(() => emitError({ sourceId: "internal-source", error: new Error("ignored") }));
    expect(result.current.layerErrors[layer.id]).toBe("WMS timeout");

    apiMocks.listGisTerritorioLayers.mockRejectedValueOnce("catalog offline");
    const failed = renderHook(() => useTerritorioLayers(map, "new-token"));
    await waitFor(() => expect(failed.result.current.catalogError).toBe("Catalogo territoriale non disponibile"));
  });

  test("handles missing token, registration failures and cleanup", async () => {
    const { map } = mapAdapter();
    const noToken = renderHook(() => useTerritorioLayers(map, null));
    expect(noToken.result.current.loading).toBe(false);
    const transform = vi.mocked(map.setTransformRequest).mock.calls.at(-1)?.[0];
    expect(transform?.("/gis/external/layer-1/wms")).toEqual({ url: "/gis/external/layer-1/wms" });

    const brokenMap = mapAdapter().map;
    vi.mocked(brokenMap.addSource).mockImplementation(() => { throw "broken"; });
    const active = renderHook(() => useTerritorioLayers(brokenMap, "token"));
    await waitFor(() => expect(active.result.current.groups).toHaveLength(1));
    act(() => active.result.current.toggleLayer(layer.id));
    await waitFor(() => expect(active.result.current.layerErrors[layer.id]).toBe("Sorgente non disponibile"));
    await waitFor(() => expect(active.result.current.legendUrls[layer.id]).toBe("blob:legend"));
    active.unmount();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:legend");

    noToken.unmount();
  });

  test("covers inactive async work and defensive error messages", async () => {
    let resolveCatalog: ((value: unknown) => void) | null = null;
    apiMocks.listGisTerritorioLayers.mockReturnValueOnce(new Promise((resolve) => { resolveCatalog = resolve; }));
    const abandoned = renderHook(() => useTerritorioLayers(null, "slow-token"));
    abandoned.unmount();
    await act(async () => {
      resolveCatalog?.({ groups: [], total: 0 });
      await Promise.resolve();
    });

    let rejectCatalog: ((reason: unknown) => void) | null = null;
    apiMocks.listGisTerritorioLayers.mockReturnValueOnce(new Promise((_resolve, reject) => { rejectCatalog = reject; }));
    const rejected = renderHook(() => useTerritorioLayers(null, "reject-token"));
    rejected.unmount();
    await act(async () => {
      rejectCatalog?.(new Error("late failure"));
      await Promise.resolve();
    });

    apiMocks.listGisTerritorioLayers.mockRejectedValueOnce(new Error("catalog failure"));
    const failed = renderHook(() => useTerritorioLayers(null, "error-token"));
    await waitFor(() => expect(failed.result.current.catalogError).toBe("catalog failure"));
  });

  test("uses default opacity and Error details when map or legend operations fail", async () => {
    const incompleteLayer = { ...layer, default_opacity: undefined };
    apiMocks.listGisTerritorioLayers.mockResolvedValueOnce({
      groups: [{ theme: "bonifica", label: "Bonifica", layers: [incompleteLayer] }],
      total: 1,
    });
    apiMocks.getGisTerritorioLegend.mockRejectedValueOnce(new Error("legend timeout"));
    const { map, emitError } = mapAdapter();
    vi.mocked(map.addSource).mockImplementation(() => { throw new Error("map rejected source"); });
    const active = renderHook(() => useTerritorioLayers(map, "token"));
    await waitFor(() => expect(active.result.current.groups).toHaveLength(1));
    act(() => active.result.current.toggleLayer(layer.id));
    await waitFor(() => expect(active.result.current.layerErrors[layer.id]).toBe("legend timeout"));
    act(() => emitError({ sourceId: "territorio-source-layer-1" }));
    expect(active.result.current.layerErrors[layer.id]).toBe("Sorgente non disponibile");
  });
});
