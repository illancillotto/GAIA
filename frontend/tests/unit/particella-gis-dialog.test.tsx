import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  map: vi.fn(),
  actions: vi.fn(),
  close: vi.fn(),
  loader: null as null | (() => Promise<unknown>),
  loading: null as null | (() => React.ReactNode),
}));

vi.mock("next/dynamic", () => ({
  default: (loader: () => Promise<unknown>, options: { loading: () => React.ReactNode }) => {
    mocks.loader = loader;
    mocks.loading = options.loading;
    return (props: object) => {
    mocks.map(props);
    return <div data-testid="map" />;
    };
  },
}));

vi.mock("@/components/catasto/gis/MapContainer", () => ({ default: () => null }));

vi.mock("@/components/catasto/gis/SchedaTerritorialeActions", () => ({
  default: (props: object) => {
    mocks.actions(props);
    return <div data-testid="sheet-actions" />;
  },
}));

vi.mock("@/components/layout/app-shell-context", () => ({
  useAppShellContext: () => ({
    currentUser: { enabled_modules: ["gis"], role: "viewer" },
  }),
}));

import { ParticellaGisDialog } from "@/components/catasto/gis/ParticellaGisDialog";

const match = {
  particella_id: "parcel-1",
  foglio: "12",
  particella: "34",
  subalterno: "5",
  comune: "Oristano",
  num_distretto: 2,
};

const geojson = {
  type: "Feature",
  geometry: { type: "Polygon", coordinates: [] },
  properties: { geometry_type: "Polygon", source: "GAIA" },
};

describe("ParticellaGisDialog", () => {
  beforeEach(() => {
    mocks.map.mockClear();
    mocks.actions.mockClear();
    mocks.close.mockClear();
    window.localStorage.setItem("gaia.access_token", "token");
  });

  test("renders nothing without a parcel", () => {
    const { container } = render(
      <ParticellaGisDialog open={false} match={null} geojson={null} centroid={null} onClose={mocks.close} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  test("exposes the dynamic map loading state", async () => {
    const Loading = mocks.loading;
    expect(Loading).not.toBeNull();
    render(<>{Loading?.()}</>);
    expect(screen.getByText("Caricamento GIS...")).toBeInTheDocument();
    await expect(mocks.loader?.()).resolves.toEqual(expect.objectContaining({ default: expect.any(Function) }));
  });

  test("exposes the sheet action while the map dialog is closed", () => {
    render(
      <ParticellaGisDialog open={false} match={match as never} geojson={null} centroid={null} onClose={mocks.close} />,
    );
    expect(mocks.actions).toHaveBeenLastCalledWith(expect.objectContaining({
      token: "token",
      particellaId: "parcel-1",
      currentUser: { enabled_modules: ["gis"], role: "viewer" },
    }));
    expect(screen.getByTestId("sheet-actions")).toBeInTheDocument();
  });

  test("builds the focused parcel map and handles every close control", async () => {
    render(
      <ParticellaGisDialog
        open
        match={match as never}
        geojson={geojson as never}
        centroid={{ lon: 9.1, lat: 39.9 }}
        onClose={mocks.close}
      />,
    );
    expect(screen.getByText("Fg.12 Part.34 Sub.5")).toBeInTheDocument();
    expect(screen.getByText("Oristano · Distretto 2")).toBeInTheDocument();
    expect(screen.getByText("Disponibile")).toBeInTheDocument();
    expect(screen.getByText("Polygon")).toBeInTheDocument();
    const osm = screen.getByRole("link", { name: "Apri su OSM" });
    expect(osm).toHaveAttribute("href", expect.stringContaining("mlat=39.9"));
    fireEvent.click(osm);

    await waitFor(() => expect(mocks.map).toHaveBeenLastCalledWith(expect.objectContaining({ token: "token" })));
    const mapProps = mocks.map.mock.calls.at(-1)?.[0];
    expect(mapProps.focusGeojson.features[0].properties).toEqual(expect.objectContaining({ id: "parcel-1", source: "GAIA" }));
    expect(mapProps.overlayLayers[0]).toEqual(expect.objectContaining({ layer_key: "particella-parcel-1" }));
    mapProps.onGeometryDrawn();
    mapProps.onSelectionCleared();

    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    fireEvent.keyDown(window, { key: "Escape" });
    const backdrop = screen.getByRole("dialog");
    fireEvent.mouseDown(backdrop);
    fireEvent.mouseDown(screen.getByTestId("map"));
    fireEvent.keyDown(window, { key: "Enter" });
    expect(mocks.close).toHaveBeenCalledTimes(3);
  });

  test("renders missing optional map data without navigation", () => {
    const sparseMatch = { ...match, subalterno: null, comune: null, num_distretto: null };
    render(
      <ParticellaGisDialog
        open
        match={sparseMatch as never}
        geojson={{ type: "Feature", geometry: null, properties: { geometry_type: 7 } } as never}
        centroid={null}
        onClose={mocks.close}
      />,
    );
    expect(screen.getByText("Fg.12 Part.34")).toBeInTheDocument();
    expect(screen.getByText("Comune n/d · Distretto —")).toBeInTheDocument();
    expect(screen.getByText("Assente")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(3);
    const osm = screen.getByRole("link", { name: "Apri su OSM" });
    expect(osm).toHaveAttribute("href", "#");
    fireEvent.click(osm);
    expect(mocks.map).toHaveBeenLastCalledWith(expect.objectContaining({
      focusGeojson: null,
      focusSignal: 0,
      overlayLayers: [],
    }));
  });

  test("accepts geometry without properties and non-finite coordinates", () => {
    render(
      <ParticellaGisDialog
        open
        match={{ ...match, particella_id: "" } as never}
        geojson={{ type: "Feature", geometry: geojson.geometry, properties: null } as never}
        centroid={{ lon: Number.POSITIVE_INFINITY, lat: Number.NaN }}
        onClose={mocks.close}
      />,
    );
    expect(screen.getByText("Disponibile")).toBeInTheDocument();
    expect(mocks.map).toHaveBeenLastCalledWith(expect.objectContaining({ selectedIds: [] }));
  });
});
