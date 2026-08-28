import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import OrtofotoStoricheSelector from "@/components/catasto/gis/OrtofotoStoricheSelector";
import type { GisTerritorioLayer } from "@/lib/api/territorio";

function ortofoto(id: string, title: string): GisTerritorioLayer {
  return {
    id,
    name: id,
    title,
    description: null,
    theme: "ortofoto",
    source: "ras_sitr",
    proxy_wms_url: `/gis/external/${id}/wms`,
    legend_url: `/gis/external/${id}/wms?request=GetLegendGraphic`,
    default_opacity: 1,
    render_order: 1,
    queryable: "wms_visual_only",
    attribution: "Regione Sardegna",
  };
}

describe("OrtofotoStoricheSelector", () => {
  test("selects two years, changes comparison opacity and resets on basemap change", () => {
    const layers = [ortofoto("orto-1977", "Ortofoto 1977-1978"), ortofoto("orto-2006", "Ortofoto 2006")];
    const onToggle = vi.fn();
    const onOpacityChange = vi.fn();
    const { rerender } = render(
      <OrtofotoStoricheSelector layers={layers} enabled={{}} opacity={{}} basemap="osm" onToggle={onToggle} onOpacityChange={onOpacityChange} />,
    );

    fireEvent.change(screen.getByLabelText("Annata principale"), { target: { value: "orto-1977" } });
    expect(onToggle).toHaveBeenCalledWith("orto-1977");
    fireEvent.change(screen.getByLabelText("Annata di confronto"), { target: { value: "orto-2006" } });
    expect(onToggle).toHaveBeenCalledWith("orto-2006");
    fireEvent.change(screen.getByLabelText("Trasparenza confronto"), { target: { value: "0.35" } });
    expect(onOpacityChange).toHaveBeenCalledWith("orto-2006", 0.35);

    rerender(
      <OrtofotoStoricheSelector layers={layers} enabled={{ "orto-1977": true, "orto-2006": true }} opacity={{}} basemap="satellite" onToggle={onToggle} onOpacityChange={onOpacityChange} />,
    );
    expect(onToggle).toHaveBeenCalledWith("orto-1977");
    expect(onToggle).toHaveBeenCalledWith("orto-2006");
    expect(screen.getByLabelText("Annata principale")).toHaveValue("");
  });

  test("explains why comparison is disabled with the licensed single year", () => {
    render(
      <OrtofotoStoricheSelector layers={[ortofoto("orto-1977", "Ortofoto 1977-1978")]} enabled={{}} opacity={{}} basemap="osm" onToggle={vi.fn()} onOpacityChange={vi.fn()} />,
    );
    expect(screen.getByLabelText("Annata di confronto")).toBeDisabled();
    expect(screen.getByText(/Una sola annata e oggi autorizzata/)).toBeInTheDocument();
  });

  test("replaces and clears active primary and comparison layers", () => {
    const layers = [ortofoto("historic", "Mosaico storico"), ortofoto("orto-2006", "Ortofoto 2006")];
    const onToggle = vi.fn();
    const view = render(
      <OrtofotoStoricheSelector layers={layers} enabled={{ historic: true, "orto-2006": true }} opacity={{}} basemap="osm" onToggle={onToggle} onOpacityChange={vi.fn()} />,
    );
    expect(screen.getAllByRole("option", { name: "Mosaico storico" })).toHaveLength(2);

    fireEvent.change(screen.getByLabelText("Annata principale"), { target: { value: "historic" } });
    fireEvent.change(screen.getByLabelText("Annata principale"), { target: { value: "orto-2006" } });
    expect(onToggle).toHaveBeenCalledWith("historic");
    fireEvent.change(screen.getByLabelText("Annata principale"), { target: { value: "" } });

    fireEvent.change(screen.getByLabelText("Annata di confronto"), { target: { value: "historic" } });
    fireEvent.change(screen.getByLabelText("Annata di confronto"), { target: { value: "orto-2006" } });
    fireEvent.change(screen.getByLabelText("Annata di confronto"), { target: { value: "" } });
    expect(onToggle.mock.calls.filter(([id]) => id === "historic").length).toBeGreaterThan(1);

    view.rerender(
      <OrtofotoStoricheSelector layers={layers} enabled={{}} opacity={{}} basemap="google_satellite" onToggle={onToggle} onOpacityChange={vi.fn()} />,
    );
  });

  test("renders nothing when no historical imagery is available", () => {
    const { container } = render(
      <OrtofotoStoricheSelector layers={[]} enabled={{}} opacity={{}} basemap="osm" onToggle={vi.fn()} onOpacityChange={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
