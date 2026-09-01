import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

const mocks = vi.hoisted(() => ({ received: null as Record<string, unknown> | null }));

vi.mock("next/dynamic", () => ({
  default: (loader: () => Promise<unknown>) => {
    void loader();
    return (props: Record<string, unknown>) => {
    mocks.received = props;
    return <div>mappa registrata</div>;
    };
  },
}));
vi.mock("@/components/catasto/gis/territorio-map-registry", () => ({}));
vi.mock("@/components/catasto/gis/MapContainer", () => ({ default: () => null }));

import TerritorioRegisteredMap from "@/components/catasto/gis/TerritorioRegisteredMap";

describe("TerritorioRegisteredMap", () => {
  test("forwards the map contract after registry initialization", () => {
    render(
      <TerritorioRegisteredMap
        token="token"
        onGeometryDrawn={vi.fn()}
        onSelectionCleared={vi.fn()}
        selectedIds={["parcel-1"]}
        filters={{}}
        drawSignal={1}
        clearSignal={2}
      />,
    );
    expect(screen.getByText("mappa registrata")).toBeVisible();
    expect(mocks.received).toMatchObject({ token: "token", selectedIds: ["parcel-1"], drawSignal: 1, clearSignal: 2 });
  });
});
