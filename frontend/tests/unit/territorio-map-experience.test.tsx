import { render, screen } from "@testing-library/react";
import { act } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  useTerritorioLayers: vi.fn(() => ({ groups: [] })),
  panel: vi.fn(),
  interrogationPanel: vi.fn(),
  useInterrogazione: vi.fn(() => ({ open: false })),
  mapListener: null as ((maps: Array<{ getContainer: () => HTMLElement }>) => void) | null,
}));

vi.mock("@/components/catasto/gis/MapContainer", () => ({
  default: () => <div data-testid="map-canvas">canvas GIS</div>,
}));

vi.mock("@/components/catasto/gis/territorio-map-registry", () => ({
  subscribeTerritorioMaps: (listener: typeof mocks.mapListener) => {
    mocks.mapListener = listener;
    listener?.([]);
    return vi.fn();
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

import TerritorioMapExperience from "@/components/catasto/gis/TerritorioMapExperience";

describe("TerritorioMapExperience", () => {
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
    expect(screen.getByText("pannello interrogazione")).toBeInTheDocument();
    act(() => {
      mocks.mapListener?.([{ getContainer: () => screen.getByTestId("map-canvas") }]);
    });
    expect(mocks.useTerritorioLayers).toHaveBeenLastCalledWith(
      expect.objectContaining({ getContainer: expect.any(Function) }),
      "token",
    );
    expect(mocks.panel).toHaveBeenLastCalledWith(expect.objectContaining({ basemap: "satellite" }));
    expect(mocks.useInterrogazione).toHaveBeenLastCalledWith(
      expect.objectContaining({ getContainer: expect.any(Function) }),
      "token",
      [],
    );
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
  });
});
