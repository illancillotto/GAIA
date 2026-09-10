import { render, renderHook, screen } from "@testing-library/react";
import { act } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  useTerritorioLayers: vi.fn(() => ({ groups: [] })),
  panel: vi.fn(),
  interrogationPanel: vi.fn(),
  unifiedSearch: vi.fn(),
  fieldTools: vi.fn(),
  interrogate: vi.fn(),
  clearInterrogation: vi.fn(),
  registeredMap: vi.fn(),
  useInterrogazione: vi.fn(() => ({
    point: null,
    gaia: [{ source_id: "particella", data: [{ id: "parcel-1" }] }],
    catastoUfficiale: [],
    territorio: [],
    interrogate: mocks.interrogate,
    clear: mocks.clearInterrogation,
  })),
  mapReady: null as ((map: { getContainer: () => HTMLElement; on: (type: "click", listener: (event: { lngLat: { lng: number; lat: number } }) => void) => void; off: (type: "click", listener: (event: { lngLat: { lng: number; lat: number } }) => void) => void } | null) => void) | null,
  mapClick: null as ((event: { lngLat: { lng: number; lat: number } }) => void) | null,
  particellaClick: null as ((particella: { id: string } | null) => void) | null,
}));

vi.mock("@/components/catasto/gis/TerritorioRegisteredMap", () => ({
  default: (props: { onMapReady?: typeof mocks.mapReady; onParticellaClick?: typeof mocks.particellaClick; overlayLayers?: unknown[] }) => {
    mocks.registeredMap(props);
    mocks.mapReady = props.onMapReady ?? null;
    mocks.particellaClick = props.onParticellaClick ?? null;
    return <div data-testid="map-canvas">canvas GIS</div>;
  },
}));

vi.mock("@/components/catasto/gis/use-territorio-layers", () => ({
  useTerritorioLayers: (...args: unknown[]) => mocks.useTerritorioLayers(...args),
}));

vi.mock("@/components/catasto/gis/TerritorioLayerPanel", () => ({
  default: (props: object) => {
    mocks.panel(props);
    return <div>pannello territorio</div>;
  },
}));

vi.mock("@/components/catasto/gis/use-interrogazione", () => ({
  useInterrogazione: (...args: unknown[]) => mocks.useInterrogazione(...args),
}));

vi.mock("@/components/catasto/gis/InterrogazionePanel", () => ({
  default: (props: object) => {
    mocks.interrogationPanel(props);
    return <div>pannello interrogazione</div>;
  },
}));

vi.mock("@/components/catasto/gis/TerritorioUnifiedSearch", () => ({
  default: (props: object) => {
    mocks.unifiedSearch(props);
    return <div>ricerca territorio</div>;
  },
}));

vi.mock("@/components/layout/app-shell-context", () => ({
  useAppShellContext: () => ({
    currentUser: { enabled_modules: ["gis"], role: "viewer" },
  }),
}));

vi.mock("@/components/catasto/gis/TerritorioFieldTools", () => ({
  default: (props: object) => {
    mocks.fieldTools(props);
    return <div>strumenti territorio</div>;
  },
}));

import TerritorioMapExperience, { findPortalTarget, usePortalTarget } from "@/components/catasto/gis/TerritorioMapExperience";

describe("TerritorioMapExperience", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.useInterrogazione.mockReturnValue({
      point: null,
      gaia: [{ source_id: "particella", data: [{ id: "parcel-1" }] }],
      catastoUfficiale: [],
      territorio: [],
      interrogate: mocks.interrogate,
      clear: mocks.clearInterrogation,
    });
  });

  test("returns no portal target outside a browser document", () => {
    expect(findPortalTarget(undefined, "expanded", "standard")).toBeNull();
    const { result } = renderHook(() => usePortalTarget(undefined, "missing", null));
    expect(result.current).toBeNull();
  });

  test("connects the owned map, token and basemap to territorio controls", () => {
    const { unmount } = render(
      <TerritorioMapExperience
        token="token"
        onGeometryDrawn={vi.fn()}
        onSelectionCleared={vi.fn()}
        selectedIds={[]}
        filters={{}}
        drawSignal={0}
        clearSignal={0}
        basemap="satellite"
      />,
    );
    expect(screen.getByText("canvas GIS")).toBeInTheDocument();
    expect(screen.getByText("pannello territorio")).toBeInTheDocument();
    expect(screen.queryByText("pannello interrogazione")).not.toBeInTheDocument();
    expect(screen.getByText("ricerca territorio")).toBeInTheDocument();
    act(() => {
      mocks.mapReady?.({
        getContainer: () => screen.getByTestId("map-canvas"),
        on: (_type, listener) => { mocks.mapClick = listener; },
        off: () => { mocks.mapClick = null; },
      });
    });
    expect(mocks.useTerritorioLayers).toHaveBeenLastCalledWith(
      expect.objectContaining({ getContainer: expect.any(Function) }),
      "token",
    );
    expect(mocks.panel).toHaveBeenLastCalledWith(expect.objectContaining({ basemap: "satellite" }));
    expect(mocks.useInterrogazione).toHaveBeenLastCalledWith("token", []);
    expect(mocks.unifiedSearch).toHaveBeenLastCalledWith(expect.objectContaining({
      token: "token",
      groups: [],
    }));
    unmount();
  });

  test("defaults the basemap to OSM", () => {
    render(
      <TerritorioMapExperience
        token={null}
        onGeometryDrawn={vi.fn()}
        onSelectionCleared={vi.fn()}
        selectedIds={[]}
        filters={{}}
        drawSignal={0}
        clearSignal={0}
      />,
    );
    expect(mocks.panel).toHaveBeenLastCalledWith(expect.objectContaining({ basemap: "osm" }));
    expect(screen.queryByText("pannello interrogazione")).not.toBeInTheDocument();
  });

  test("queries the clicked parcel point and mounts results inside its detail", () => {
    const target = document.createElement("div");
    target.id = "gis-particella-interrogation";
    document.body.append(target);
    mocks.useInterrogazione.mockReturnValue({
      point: { lon: 8.6, lat: 39.9 },
      gaia: [{ source_id: "particella", data: [{ id: "parcel-1" }] }],
      catastoUfficiale: [],
      territorio: [],
      interrogate: mocks.interrogate,
      clear: mocks.clearInterrogation,
    });
    const upstreamClick = vi.fn();
    const view = render(
      <TerritorioMapExperience
        token="token"
        onGeometryDrawn={vi.fn()}
        onSelectionCleared={vi.fn()}
        onParticellaClick={upstreamClick}
        selectedIds={[]}
        filters={{}}
        drawSignal={0}
        clearSignal={0}
      />,
    );
    expect(target).toHaveTextContent("pannello interrogazione");
    expect(mocks.interrogationPanel).toHaveBeenLastCalledWith(expect.objectContaining({
      scheda: {
        token: "token",
        particellaId: "parcel-1",
        currentUser: { enabled_modules: ["gis"], role: "viewer" },
      },
    }));
    act(() => mocks.mapReady?.({
      getContainer: () => screen.getByTestId("map-canvas"),
      on: (_type, listener) => { mocks.mapClick = listener; },
      off: () => { mocks.mapClick = null; },
    }));
    act(() => mocks.mapClick?.({ lngLat: { lng: 9, lat: 40 } }));
    act(() => mocks.particellaClick?.({ id: "parcel-2" }));
    expect(upstreamClick).toHaveBeenCalledWith({ id: "parcel-2" });
    expect(mocks.interrogate).toHaveBeenCalledWith({ lon: 9, lat: 40 });
    act(() => mocks.particellaClick?.(null));
    expect(mocks.clearInterrogation).toHaveBeenCalled();
    view.unmount();
    target.remove();
  });

  test("does not derive a sheet parcel id from non-string territorial data", () => {
    const target = document.createElement("div");
    target.id = "gis-particella-interrogation";
    document.body.append(target);
    mocks.useInterrogazione.mockReturnValue({
      point: { lon: 8.6, lat: 39.9 },
      gaia: [{ source_id: "particella", data: [{ id: 7 }] }],
      catastoUfficiale: [],
      territorio: [],
      interrogate: mocks.interrogate,
      clear: mocks.clearInterrogation,
    });
    const view = render(
      <TerritorioMapExperience token="token" onGeometryDrawn={vi.fn()} onSelectionCleared={vi.fn()} selectedIds={[]} filters={{}} drawSignal={0} clearSignal={0} />,
    );
    expect(mocks.interrogationPanel).toHaveBeenLastCalledWith(expect.objectContaining({
      scheda: expect.objectContaining({ particellaId: null }),
    }));
    view.unmount();
    target.remove();
  });

  test("moves territory controls into the GIS console and toolbar slots", () => {
    const slots = document.createElement("div");
    slots.innerHTML = '<div id="gis-territorio-layers"></div><div id="gis-toolbar-tools"></div>';
    document.body.append(slots);
    const view = render(
      <TerritorioMapExperience
        token="token"
        onGeometryDrawn={vi.fn()}
        onSelectionCleared={vi.fn()}
        selectedIds={[]}
        filters={{}}
        drawSignal={0}
        clearSignal={0}
      />,
    );
    expect(document.querySelector("#gis-territorio-layers")).toHaveTextContent("pannello territorio");
    expect(document.querySelector("#gis-toolbar-tools")).toHaveTextContent("ricerca territorio");
    expect(document.querySelector("#gis-toolbar-tools")).toHaveTextContent("strumenti territorio");
    expect(mocks.panel).toHaveBeenLastCalledWith(expect.objectContaining({ embedded: true }));
    expect(mocks.fieldTools).toHaveBeenLastCalledWith(expect.objectContaining({ compact: true }));
    expect(mocks.unifiedSearch).toHaveBeenLastCalledWith(expect.objectContaining({ compact: true }));
    view.unmount();
    slots.remove();
  });

  test("pulses parcel search results and the focused result on the map", () => {
    render(
      <TerritorioMapExperience token="token" onGeometryDrawn={vi.fn()} onSelectionCleared={vi.fn()} selectedIds={[]} filters={{}} drawSignal={0} clearSignal={0} />,
    );
    const feature = { type: "Feature", properties: { id: "parcel-1" }, geometry: { type: "Point", coordinates: [8.6, 39.9] } };
    const parcel = { id: "particella:parcel-1", kind: "particella", label: "Particella", detail: "", source: "GAIA", feature };
    const callbacks = mocks.unifiedSearch.mock.lastCall?.[0] as {
      onSearchResults: (results: unknown[]) => void;
      onResultFocus: (result: unknown) => void;
    };
    act(() => callbacks.onSearchResults([parcel, { ...parcel, id: "comune:1", kind: "comune", feature: undefined }]));
    expect(mocks.registeredMap.mock.lastCall?.[0]).toEqual(expect.objectContaining({
      overlayLayers: [expect.objectContaining({ layer_key: "gis-search-results", pulse: true, showFill: true })],
    }));
    act(() => callbacks.onResultFocus(parcel));
    expect(mocks.registeredMap.mock.lastCall?.[0]).toEqual(expect.objectContaining({
      overlayLayers: [expect.objectContaining({ layer_key: "gis-search-focus", color: "#F000B8" })],
    }));
    act(() => callbacks.onSearchResults([]));
    expect(mocks.registeredMap.mock.lastCall?.[0]).toEqual(expect.objectContaining({ overlayLayers: undefined }));
  });

  test("prefers the expanded GIS slots", () => {
    const slots = document.createElement("div");
    slots.innerHTML = '<div id="gis-territorio-layers"></div><div id="gis-toolbar-tools"></div><div id="gis-expanded-territorio-layers"></div><div id="gis-expanded-toolbar-tools"></div>';
    document.body.append(slots);
    const view = render(
      <TerritorioMapExperience
        token="token"
        onGeometryDrawn={vi.fn()}
        onSelectionCleared={vi.fn()}
        selectedIds={[]}
        filters={{}}
        drawSignal={0}
        clearSignal={0}
      />,
    );
    expect(document.querySelector("#gis-expanded-territorio-layers")).toHaveTextContent("pannello territorio");
    expect(document.querySelector("#gis-expanded-toolbar-tools")).toHaveTextContent("ricerca territorio");
    expect(document.querySelector("#gis-expanded-toolbar-tools")).toHaveTextContent("strumenti territorio");
    view.unmount();
    slots.remove();
  });
});
