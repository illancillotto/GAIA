import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import CatastoGisCoordinatePage from "@/app/catasto/gis/coordinate/page";
import { buildCatastoGisCoordinateOverlay } from "@/lib/catasto-gis-coordinate-search";

const mocks = vi.hoisted(() => ({
  coordinate: "",
  mapProps: null as Record<string, unknown> | null,
}));

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(mocks.coordinate ? { coordinate: mocks.coordinate } : {}),
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: ReactNode; href: string }) => <a href={href}>{children}</a>,
}));

vi.mock("@/components/catasto/catasto-page", () => ({
  CatastoPage: ({ children, title }: { children: ReactNode; title: string }) => (
    <main>
      <h1>{title}</h1>
      {children}
    </main>
  ),
}));

vi.mock("@/components/catasto/gis/MapContainer", () => ({
  default: (props: Record<string, unknown>) => {
    mocks.mapProps = props;
    (props.onGeometryDrawn as (geometry: GeoJSON.Geometry) => void)({ type: "Point", coordinates: [8.5, 39.9] });
    (props.onSelectionCleared as () => void)();
    return <div data-testid="coordinate-map" />;
  },
}));

describe("Catasto GIS coordinate page", () => {
  beforeEach(() => {
    mocks.coordinate = "";
    mocks.mapProps = null;
  });

  test("renders recovery guidance when coordinates are missing", () => {
    render(<CatastoGisCoordinatePage />);

    expect(screen.getByRole("heading", { name: "Coordinate GIS" })).toBeInTheDocument();
    expect(screen.getByText("Coordinate mancanti o non valide")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Apri il GIS completo" })).toHaveAttribute("href", "/catasto/gis");
    expect(screen.queryByTestId("coordinate-map")).not.toBeInTheDocument();
  });

  test("renders a focused waypoint for valid coordinates", () => {
    mocks.coordinate = "39.904200, 8.591700";

    render(<CatastoGisCoordinatePage />);

    expect(screen.getByText("39.904200, 8.591700")).toBeInTheDocument();
    expect(screen.getByTestId("coordinate-map")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Apri strumenti GIS completi" })).toHaveAttribute("href", "/catasto/gis");
    expect(mocks.mapProps).toMatchObject({
      token: null,
      focusSignal: 1,
      focusOptions: { maxZoom: 15, padding: 48, duration: 700 },
      basemap: "satellite",
      mapLayers: { showDistretti: true, showDistrettiFill: false, showParticelleFill: true, showParticelleTiles: true },
    });
  });

  test("builds the map overlay from the normalized coordinate collection", () => {
    const geojson: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };

    expect(buildCatastoGisCoordinateOverlay("39.900000, 8.500000", geojson)).toEqual({
      label: "39.900000, 8.500000",
      geojson,
      layer: expect.objectContaining({
        layer_key: "coordinate-search",
        name: "Waypoint 39.900000, 8.500000",
        geojson,
        showCentroids: true,
        visible: true,
      }),
    });
  });
});
