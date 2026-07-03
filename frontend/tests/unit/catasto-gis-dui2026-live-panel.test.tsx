import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { Dui2026LivePanel } from "@/components/catasto/gis/Dui2026LivePanel";


describe("Dui2026LivePanel", () => {
  test("renders loading state", () => {
    render(
      <Dui2026LivePanel
        data={null}
        loading
        error={null}
        visible
        onToggleVisible={() => undefined}
      />,
    );

    expect(screen.getByText("Caricamento layer DUI 2026 dal NAS…")).toBeInTheDocument();
  });

  test("renders error state", () => {
    render(
      <Dui2026LivePanel
        data={null}
        loading={false}
        error="NAS non raggiungibile"
        visible={false}
        onToggleVisible={() => undefined}
      />,
    );

    expect(screen.getByText("NAS non raggiungibile")).toBeInTheDocument();
  });

  test("renders stats and toggles visibility", () => {
    const onToggleVisible = vi.fn();
    render(
      <Dui2026LivePanel
        data={{
          label: "DUI 2026 live",
          source_path: "/tmp/Dui2026-TOTALE-al_25-06-2026.shp",
          source_filename: "Dui2026-TOTALE-al_25-06-2026.shp",
          source_date: "2026-06-25",
          source_updated_at: "2026-06-26T07:43:00",
          stats: {
            total_polygons: 9445,
            in_ruolo_2025: 6123,
            not_in_ruolo_2025: 3322,
            with_contatore: 5010,
            without_contatore: 4435,
            with_telerilev: 1220,
          },
          geojson: { type: "FeatureCollection", features: [] },
        }}
        loading={false}
        error={null}
        visible={false}
        onToggleVisible={onToggleVisible}
      />,
    );

    expect(screen.getByText("9445")).toBeInTheDocument();
    expect(screen.getByText("6123")).toBeInTheDocument();
    expect(screen.getByText("3322")).toBeInTheDocument();
    expect(screen.getByText(/Snapshot/)).toHaveTextContent("2026-06-25");

    fireEvent.click(screen.getByRole("button", { name: "Nascosto" }));

    expect(onToggleVisible).toHaveBeenCalledTimes(1);
  });
});
