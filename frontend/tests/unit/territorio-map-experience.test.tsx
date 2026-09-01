import { render, screen } from "@testing-library/react";
import { act } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  useTerritorioLayers: vi.fn(() => ({ groups: [] })),
  panel: vi.fn(),
  interrogationPanel: vi.fn(),
  unifiedSearch: vi.fn(),
  useInterrogazione: vi.fn(() => ({
    open: false,
    gaia: [{ source_id: "particella", data: [{ id: "parcel-1" }] }],
  })),
  mapListener: null as ((maps: Array<{ getContainer: () => HTMLElement }>) => void) | null,
}));

vi.mock("@/components/catasto/gis/TerritorioRegisteredMap", () => ({
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
  default: () => <div>strumenti territorio</div>,
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
    expect(screen.getByText("ricerca territorio")).toBeInTheDocument();
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
    expect(mocks.unifiedSearch).toHaveBeenLastCalledWith(expect.objectContaining({
      token: "token",
      groups: [],
    }));
    expect(mocks.interrogationPanel).toHaveBeenLastCalledWith(expect.objectContaining({
      scheda: {
        token: "token",
        particellaId: "parcel-1",
        currentUser: { enabled_modules: ["gis"], role: "viewer" },
      },
    }));
    unmount();
  });

  test("defaults the basemap to OSM", () => {
    mocks.useInterrogazione.mockReturnValueOnce({
      open: false,
      gaia: [{ source_id: "particella", data: [{ id: 7 }] }],
    });
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
    expect(mocks.interrogationPanel).toHaveBeenLastCalledWith(expect.objectContaining({
      scheda: expect.objectContaining({ particellaId: null }),
    }));
  });
});
