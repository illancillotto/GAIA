import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const mocks = vi.hoisted(() => {
  class MockMap {
    handlers = new Map<string, Array<(...args: any[]) => unknown>>();
    layerHandlers = new Map<string, Map<string, (...args: any[]) => unknown>>();
    layers = new Set<string>();
    sources = new Map<string, unknown>();
    renderedFeatures: Array<Record<string, any>> = [];
    canvas = { style: { cursor: "" } };
    fitBounds = vi.fn();
    easeTo = vi.fn();
    getZoom = vi.fn(() => 10);

    on(type: string, layerOrHandler: string | ((event: any) => unknown), maybeHandler?: (event: any) => unknown) {
      if (typeof layerOrHandler === "string" && maybeHandler) {
        const byType = this.layerHandlers.get(type) ?? new Map<string, (...args: any[]) => unknown>();
        byType.set(layerOrHandler, maybeHandler);
        this.layerHandlers.set(type, byType);
        return this;
      }
      const handlers = this.handlers.get(type) ?? [];
      handlers.push(layerOrHandler as (event: any) => unknown);
      this.handlers.set(type, handlers);
      return this;
    }

    emit(type: string, event: Record<string, unknown> = {}) {
      return Promise.all((this.handlers.get(type) ?? []).map((handler) => handler(event)));
    }

    addControl() {}
    remove() {}
    resize() {}
    triggerRepaint() {}
    addSource(id: string, source: unknown) {
      this.sources.set(id, {
        ...(source as object),
        setData: vi.fn(),
        setTiles: vi.fn(),
      });
    }
    getSource(id: string) {
      return this.sources.get(id) ?? null;
    }
    addLayer(layer: { id: string }) {
      this.layers.add(layer.id);
    }
    removeLayer(id: string) {
      this.layers.delete(id);
    }
    removeSource(id: string) {
      this.sources.delete(id);
    }
    getLayer(id: string) {
      return this.layers.has(id) ? { id } : null;
    }
    setLayoutProperty() {}
    setPaintProperty() {}
    setLayerZoomRange() {}
    setFilter() {}
    getCanvas() {
      return this.canvas;
    }
    queryRenderedFeatures() {
      return this.renderedFeatures;
    }
  }

  return {
    lastMap: null as MockMap | null,
    constructorError: null as Error | null,
    lastDraw: null as null | {
      emit: (type: string, ...args: unknown[]) => void;
      features: Map<string | number, GeoJSON.Feature>;
      start: ReturnType<typeof vi.fn>;
      stop: ReturnType<typeof vi.fn>;
      setMode: ReturnType<typeof vi.fn>;
      selectFeature: ReturnType<typeof vi.fn>;
      clear: ReturnType<typeof vi.fn>;
    },
    MockMap,
  };
});

vi.mock("maplibre-gl", () => ({
  Map: class extends mocks.MockMap {
    constructor() {
      if (mocks.constructorError) throw mocks.constructorError;
      super();
      mocks.lastMap = this;
    }
  },
  NavigationControl: class {},
  ScaleControl: class {},
  Popup: class {
    setLngLat() { return this; }
    setHTML() { return this; }
    addTo() { return this; }
    remove() {}
  },
  LngLatBounds: class {
    empty = true;
    extend() { this.empty = false; }
    isEmpty() { return this.empty; }
  },
  GPUInitializationError: class extends Error {
    statusMessage = null;
    constructor() { super("map GPU lost"); }
  },
}));

vi.mock("terra-draw", () => ({
  TerraDraw: class {
    listeners = new Map<string, Set<(...args: unknown[]) => void>>();
    features = new Map<string | number, GeoJSON.Feature>();
    start = vi.fn();
    stop = vi.fn();
    setMode = vi.fn();
    selectFeature = vi.fn();
    clear = vi.fn(() => this.emit("change", [], "delete"));
    constructor() { mocks.lastDraw = this; }
    on(type: string, listener: (...args: unknown[]) => void) {
      const listeners = this.listeners.get(type) ?? new Set();
      listeners.add(listener);
      this.listeners.set(type, listeners);
    }
    off(type: string, listener: (...args: unknown[]) => void) {
      this.listeners.get(type)?.delete(listener);
    }
    emit(type: string, ...args: unknown[]) {
      this.listeners.get(type)?.forEach((listener) => listener(...args));
    }
    getSnapshotFeature(featureId: string | number) { return this.features.get(featureId); }
  },
  TerraDrawPolygonMode: class {},
  TerraDrawSelectMode: class {},
}));

vi.mock("terra-draw-maplibre-gl-adapter", () => ({
  TerraDrawMapLibreGLAdapter: class {},
}));

import MapContainer from "@/components/catasto/gis/MapContainer";
import { GPUInitializationError } from "maplibre-gl";
import {
  GIS_TILE_REVISION_STORAGE_KEY,
  GIS_TILE_REVISION_UPDATED_EVENT,
} from "@/lib/catasto-gis-cache";

describe("MapContainer overlay marker click", () => {
  beforeEach(() => {
    Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
      configurable: true,
      value: () => ({}),
    });
    vi.stubGlobal(
      "ResizeObserver",
      class {
        observe() {}
        disconnect() {}
      },
    );
  });

  afterEach(() => {
    vi.clearAllMocks();
    mocks.lastMap = null;
    mocks.lastDraw = null;
    mocks.constructorError = null;
  });

  test("applies district preview styles, focus bounds and tile refresh signals", async () => {
    const polygon: GeoJSON.FeatureCollection = {
      type: "FeatureCollection",
      features: [{
        type: "Feature",
        properties: {},
        geometry: { type: "Polygon", coordinates: [[[8, 39], [9, 39], [9, 40], [8, 39]]] },
      }],
    };
    const view = render(
      <MapContainer
        token="token"
        onGeometryDrawn={vi.fn()}
        onSelectionCleared={vi.fn()}
        selectedIds={["parcel-1"]}
        filters={{}}
        mapLayers={{
          showDistretti: true,
          distrettoColors: { "1": "#ff0000" },
          particelleColorMode: "district_preview",
          particelleQuickFilter: "all",
        }}
        overlayLayers={[{
          layer_key: "focus",
          name: "Focus",
          color: "#00ff00",
          visible: true,
          geojson: polygon,
        }]}
        focusGeojson={{
          type: "FeatureCollection",
          features: [
            { type: "Feature", properties: {}, geometry: null },
            ...polygon.features,
          ],
        }}
        focusSignal={1}
        focusOptions={{ padding: 24, duration: 0, maxZoom: 14 }}
        drawSignal={0}
        clearSignal={0}
      />,
    );
    const map = mocks.lastMap!;
    await act(async () => { await map.emit("load"); });
    await waitFor(() => expect(map.fitBounds).toHaveBeenCalled());

    act(() => {
      window.dispatchEvent(new StorageEvent("storage", { key: "unrelated" }));
      window.dispatchEvent(new StorageEvent("storage", { key: GIS_TILE_REVISION_STORAGE_KEY }));
      window.dispatchEvent(new CustomEvent(GIS_TILE_REVISION_UPDATED_EVENT, { detail: { revision: "next" } }));
      window.dispatchEvent(new CustomEvent(GIS_TILE_REVISION_UPDATED_EVENT));
      window.dispatchEvent(new Event("focus"));
      document.dispatchEvent(new Event("visibilitychange"));
    });

    view.rerender(
      <MapContainer
        token="token"
        onGeometryDrawn={vi.fn()}
        onSelectionCleared={vi.fn()}
        selectedIds={[]}
        filters={{}}
        mapLayers={{
          showDistretti: true,
          particelleColorMode: "district_preview",
          particelleQuickFilter: "ruolo",
        }}
        focusGeojson={polygon}
        focusSignal={2}
        drawSignal={0}
        clearSignal={0}
      />,
    );
    await waitFor(() => expect(map.fitBounds).toHaveBeenCalledTimes(2));
    view.rerender(
      <MapContainer
        token="token"
        onGeometryDrawn={vi.fn()}
        onSelectionCleared={vi.fn()}
        selectedIds={[]}
        filters={{}}
        mapLayers={{
          showDistretti: true,
          particelleColorMode: "district_preview",
          particelleQuickFilter: "ruolo_inferito",
        }}
        focusGeojson={{
          type: "FeatureCollection",
          features: [{ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: [] } }],
        }}
        focusSignal={3}
        drawSignal={0}
        clearSignal={0}
      />,
    );

    view.rerender(
      <MapContainer
        token="token"
        onGeometryDrawn={vi.fn()}
        onSelectionCleared={vi.fn()}
        selectedIds={[]}
        filters={{}}
        mapLayers={{ showDistretti: true }}
        focusGeojson={{ type: "FeatureCollection", features: [] }}
        focusSignal={4}
        drawSignal={0}
        clearSignal={0}
      />,
    );

    const particelleSource = map.getSource("particelle-source") as { setTiles: ReturnType<typeof vi.fn> };
    await waitFor(() => expect(particelleSource.setTiles).toHaveBeenCalled());
  });

  test("renders WebGL2, constructor and restored GPU failures", async () => {
    Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
      configurable: true,
      value: () => null,
    });
    const unavailable = render(
      <MapContainer token="token" onGeometryDrawn={vi.fn()} onSelectionCleared={vi.fn()} selectedIds={[]} filters={{}} drawSignal={0} clearSignal={0} />,
    );
    expect(await waitFor(() => screen.getByText(/richiede WebGL2 attivo/))).toBeInTheDocument();
    unavailable.unmount();

    Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
      configurable: true,
      value: () => ({}),
    });
    mocks.constructorError = new Error("constructor offline");
    const failed = render(
      <MapContainer token="token" onGeometryDrawn={vi.fn()} onSelectionCleared={vi.fn()} selectedIds={[]} filters={{}} drawSignal={0} clearSignal={0} />,
    );
    expect(await waitFor(() => screen.getByText("constructor offline"))).toBeInTheDocument();
    failed.unmount();

    mocks.constructorError = null;
    render(
      <MapContainer token="token" onGeometryDrawn={vi.fn()} onSelectionCleared={vi.fn()} selectedIds={[]} filters={{}} drawSignal={0} clearSignal={0} />,
    );
    const map = mocks.lastMap!;
    await act(async () => { await map.emit("error", { error: new Error("source failure") }); });
    expect(screen.queryByText("source failure")).not.toBeInTheDocument();
    await act(async () => { await map.emit("error", { error: new GPUInitializationError({}, null) }); });
    expect(await waitFor(() => screen.getByText("map GPU lost"))).toBeInTheDocument();
  });

  test("ignores map clicks without a token", async () => {
    render(
      <MapContainer token={null} onGeometryDrawn={vi.fn()} onSelectionCleared={vi.fn()} selectedIds={[]} filters={{}} drawSignal={1} clearSignal={0} />,
    );
    const map = mocks.lastMap!;
    await act(async () => { await map.emit("load"); });
    await act(async () => { await map.emit("click", { point: { x: 0, y: 0 } }); });
    expect(map.queryRenderedFeatures()).toEqual([]);
  });

  test("publishes the map lifecycle and translates Terra Draw events", async () => {
    const onMapReady = vi.fn();
    const onGeometryDrawn = vi.fn();
    const onSelectionCleared = vi.fn();
    const view = render(
      <MapContainer
        token="token"
        onGeometryDrawn={onGeometryDrawn}
        onSelectionCleared={onSelectionCleared}
        onMapReady={onMapReady}
        selectedIds={[]}
        filters={{}}
        drawSignal={0}
        clearSignal={0}
      />,
    );

    await waitFor(() => expect(mocks.lastMap).not.toBeNull());
    expect(onMapReady).toHaveBeenCalledWith(mocks.lastMap);
    await act(async () => {
      await mocks.lastMap?.emit("load");
    });
    await waitFor(() => expect(mocks.lastDraw).not.toBeNull());
    expect(mocks.lastDraw?.start).toHaveBeenCalledOnce();

    const polygon: GeoJSON.Feature<GeoJSON.Polygon> = {
      type: "Feature",
      properties: {},
      geometry: {
        type: "Polygon",
        coordinates: [[[8.5, 39.8], [8.6, 39.8], [8.5, 39.9], [8.5, 39.8]]],
      },
    };
    mocks.lastDraw?.features.set("polygon-1", polygon);
    act(() => mocks.lastDraw?.emit("finish", "polygon-1", { mode: "polygon", action: "draw" }));
    expect(onGeometryDrawn).toHaveBeenLastCalledWith(polygon.geometry);
    expect(mocks.lastDraw?.setMode).toHaveBeenCalledWith("select");
    expect(mocks.lastDraw?.selectFeature).toHaveBeenCalledWith("polygon-1");

    act(() => mocks.lastDraw?.emit("change", ["polygon-1"], "update"));
    expect(onGeometryDrawn).toHaveBeenCalledTimes(2);
    act(() => mocks.lastDraw?.emit("change", ["polygon-1"], "create"));
    expect(onGeometryDrawn).toHaveBeenCalledTimes(2);
    act(() => mocks.lastDraw?.emit("change", ["polygon-1"], "delete"));
    expect(onSelectionCleared).toHaveBeenCalledOnce();
    act(() => mocks.lastDraw?.emit("finish", "missing", { mode: "polygon", action: "draw" }));
    expect(onGeometryDrawn).toHaveBeenCalledTimes(2);

    view.rerender(
      <MapContainer
        token="token"
        onGeometryDrawn={onGeometryDrawn}
        onSelectionCleared={onSelectionCleared}
        onMapReady={onMapReady}
        selectedIds={[]}
        filters={{}}
        drawSignal={1}
        clearSignal={1}
      />,
    );
    expect(mocks.lastDraw?.setMode).toHaveBeenCalledWith("polygon");
    expect(mocks.lastDraw?.clear).toHaveBeenCalledOnce();

    view.unmount();
    expect(mocks.lastDraw?.stop).toHaveBeenCalledOnce();
    expect(onMapReady).toHaveBeenLastCalledWith(null);
    act(() => mocks.lastDraw?.emit("change", ["polygon-1"], "delete"));
    expect(onSelectionCleared).toHaveBeenCalledOnce();
  });

  test("dispatches WhiteCompany point overlays without fetching a particella popup", async () => {
    const onOverlayFeatureClick = vi.fn();
    const onParticellaClick = vi.fn();
    const onDeliveryPointClick = vi.fn();

    render(
      <MapContainer
        token="token"
        onGeometryDrawn={vi.fn()}
        onSelectionCleared={vi.fn()}
        onParticellaClick={onParticellaClick}
        onDeliveryPointClick={onDeliveryPointClick}
        onOverlayFeatureClick={onOverlayFeatureClick}
        selectedIds={[]}
        filters={{}}
        overlayLayers={[]}
        drawSignal={0}
        clearSignal={0}
      />,
    );

    expect(mocks.lastMap).not.toBeNull();
    const map = mocks.lastMap!;

    await act(async () => {
      await map.emit("load");
    });

    await waitFor(() => {
      expect(map.handlers.get("click")?.length).toBe(1);
    });

    map.renderedFeatures = [
      {
        id: "report-1",
        layer: { id: "overlay-whitecompany-reports-centroid" },
        geometry: { type: "Point", coordinates: [8.6, 39.9] },
        properties: {
          id: "report-1",
          report_number: "REP-WHITE-1",
          __overlayLayerKey: "whitecompany-reports",
          __overlayName: "Segnalazioni WhiteCompany",
          __overlayFeatureClickMode: "overlay",
        },
      },
    ];

    await act(async () => {
      await map.emit("click", { point: { x: 10, y: 12 }, lngLat: { lng: 8.6, lat: 39.9 } });
    });

    expect(onParticellaClick).toHaveBeenCalledWith(null);
    expect(onDeliveryPointClick).toHaveBeenCalledWith(null);
    expect(onOverlayFeatureClick).toHaveBeenCalledWith({
      layer_key: "whitecompany-reports",
      layer_name: "Segnalazioni WhiteCompany",
      properties: expect.objectContaining({
        id: "report-1",
        report_number: "REP-WHITE-1",
        __overlayFeatureClickMode: "overlay",
      }),
      geometry: { type: "Point", coordinates: [8.6, 39.9] },
    });
  });
});
