import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import TerritorioLayerPanel from "@/components/catasto/gis/TerritorioLayerPanel";
import type { TerritorioLayerState } from "@/components/catasto/gis/use-territorio-layers";

const layer = {
  id: "layer-1",
  name: "ras_aree_bonifica",
  title: "Aree della bonifica",
  description: "Descrizione",
  theme: "bonifica",
  source: "ras_sitr",
  proxy_wms_url: "/gis/external/layer-1/wms",
  legend_url: "/gis/external/layer-1/wms?request=GetLegendGraphic",
  default_opacity: 0.65,
  render_order: 0,
  queryable: "wfs_queryable" as const,
  attribution: "Dati Regione Sardegna",
};

function state(overrides: Partial<TerritorioLayerState> = {}): TerritorioLayerState {
  return {
    groups: [{ theme: "bonifica", label: "Bonifica e comprensori", layers: [layer] }],
    loading: false,
    catalogError: null,
    enabled: { [layer.id]: true },
    opacity: { [layer.id]: 0.65 },
    layerErrors: {},
    legendUrls: { [layer.id]: "blob:legend" },
    toggleLayer: vi.fn(),
    setLayerOpacity: vi.fn(),
    ...overrides,
  };
}

describe("TerritorioLayerPanel", () => {
  test("groups layers and exposes consultation, source, opacity, legend and attribution", () => {
    const props = state();
    render(<TerritorioLayerPanel {...props} basemap="osm" />);
    fireEvent.click(screen.getByRole("button", { name: /Territorio/i }));

    expect(screen.getByRole("region", { name: "Bonifica e comprensori" })).toBeInTheDocument();
    expect(screen.getByText("solo consultazione")).toBeInTheDocument();
    expect(screen.getByText("Fonte: Regione Sardegna")).toBeInTheDocument();
    expect(screen.getByAltText("Legenda Aree della bonifica")).toHaveAttribute("src", "blob:legend");
    expect(screen.getByLabelText("Attribuzioni strati attivi")).toHaveTextContent("Dati Regione Sardegna");

    fireEvent.click(screen.getByRole("checkbox"));
    expect(props.toggleLayer).toHaveBeenCalledWith(layer.id);
    fireEvent.change(screen.getByLabelText("Opacita Aree della bonifica"), { target: { value: "0.4" } });
    expect(props.setLayerOpacity).toHaveBeenCalledWith(layer.id, 0.4);
  });

  test("shows isolated layer and catalog errors without breaking other groups", () => {
    render(
      <TerritorioLayerPanel
        {...state({
          catalogError: "Catalogo non disponibile",
          layerErrors: { [layer.id]: "timeout" },
        })}
        basemap="osm"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Territorio/i }));
    expect(screen.getByText("Catalogo non disponibile")).toBeInTheDocument();
    expect(screen.getByText(/Sorgente momentaneamente non disponibile: timeout/)).toBeInTheDocument();
    expect(screen.getByText("Aree della bonifica")).toBeInTheDocument();
  });

  test("collapses and reports loading state", () => {
    render(<TerritorioLayerPanel {...state({ loading: true, enabled: {} })} basemap="osm" />);
    const button = screen.getByRole("button", { name: /Territorio/i });
    expect(button).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(button);
    expect(screen.getByText("Caricamento strati...")).toBeInTheDocument();
    fireEvent.click(button);
    expect(screen.queryByText("Caricamento strati...")).not.toBeInTheDocument();
  });

  test("uses AdE source labels and layer defaults while a legend is loading", () => {
    const adeLayer = { ...layer, source: "agenzia_entrate", title: "Particelle ufficiali" };
    render(
      <TerritorioLayerPanel
        {...state({
          groups: [{ theme: "catasto_ufficiale", label: "Cartografia catastale ufficiale", layers: [adeLayer] }],
          enabled: { [adeLayer.id]: true },
          opacity: {},
          legendUrls: {},
        })}
        basemap="osm"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Territorio/i }));
    expect(screen.getByText("Fonte: Agenzia delle Entrate")).toBeInTheDocument();
    expect(screen.getByText("Opacita 65%")).toBeInTheDocument();
    expect(screen.queryByAltText("Legenda Particelle ufficiali")).not.toBeInTheDocument();
  });
});
