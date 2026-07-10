import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { Dui2026LivePanel } from "@/components/catasto/gis/Dui2026LivePanel";
import type { Dui2026LayerResponse } from "@/types/gis";

const layer: Dui2026LayerResponse = {
  label: "DUI 2026 live",
  source_path: "/tmp/Dui2026-TOTALE-al_25-06-2026.shp",
  source_filename: "Dui2026-TOTALE-al_25-06-2026.shp",
  source_date: "2026-06-25",
  source_updated_at: "2026-06-26T07:43:00",
  tile_layer: "cat_dui_2026_current",
  rendering_mode: "martin_tiles",
  stats: {
    total_polygons: 2,
    in_ruolo_2025: 1,
    not_in_ruolo_2025: 1,
    with_contatore: 1,
    without_contatore: 1,
    with_telerilev: 1,
  },
  geojson: { type: "FeatureCollection", features: [] },
};

describe("Dui2026LivePanel", () => {
  test("renders Martin tile metadata and stats", () => {
    render(<Dui2026LivePanel data={layer} loading={false} error={null} visible={true} onToggleVisible={vi.fn()} />);

    expect(screen.getByText("DUI 2026")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("Rendering:")).toBeInTheDocument();
    expect(screen.getByText("tile Martin cat_dui_2026_current")).toBeInTheDocument();
  });

  test("renders fallback status and disables toggle without data", () => {
    const onToggleVisible = vi.fn();
    render(<Dui2026LivePanel data={null} loading={true} error={null} visible={false} onToggleVisible={onToggleVisible} />);

    expect(screen.getByText("Caricamento layer DUI 2026 dal NAS…")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Nascosto/ })).toBeDisabled();
  });

  test("renders GeoJSON fallback metadata", () => {
    render(
      <Dui2026LivePanel
        data={{ ...layer, tile_layer: null, rendering_mode: "geojson_fallback" }}
        loading={false}
        error={null}
        visible={true}
        onToggleVisible={vi.fn()}
      />,
    );

    expect(screen.getByText("fallback GeoJSON")).toBeInTheDocument();
  });

  test("renders Martin tile metadata without layer name", () => {
    const { tile_layer: _tileLayer, ...withoutTileLayer } = layer;
    render(
      <Dui2026LivePanel
        data={withoutTileLayer}
        loading={false}
        error={null}
        visible={true}
        onToggleVisible={vi.fn()}
      />,
    );

    expect(screen.getByText("tile Martin")).toBeInTheDocument();
  });

  test("renders explicit load errors", () => {
    render(<Dui2026LivePanel data={null} loading={false} error="NAS non raggiungibile" visible={false} onToggleVisible={vi.fn()} />);

    expect(screen.getByText("NAS non raggiungibile")).toBeInTheDocument();
  });
});
