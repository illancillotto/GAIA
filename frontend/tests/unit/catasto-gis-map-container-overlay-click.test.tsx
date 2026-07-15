import { act, render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const mocks = vi.hoisted(() => {
  class MockMap {
    handlers = new Map<string, Array<(...args: any[]) => unknown>>();
    layerHandlers = new Map<string, Map<string, (...args: any[]) => unknown>>();
    layers = new Set<string>();
    sources = new Map<string, unknown>();
    renderedFeatures: Array<Record<string, any>> = [];
    canvas = { style: { cursor: "" } };

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
      this.sources.set(id, source);
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
    MockMap,
  };
});

vi.mock("maplibre-gl", () => ({
  default: {
    Map: class extends mocks.MockMap {
      constructor() {
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
  },
}));

vi.mock("maplibre-gl-draw", () => ({
  default: class {
    changeMode() {}
    deleteAll() {}
  },
}));

import MapContainer from "@/components/catasto/gis/MapContainer";

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
