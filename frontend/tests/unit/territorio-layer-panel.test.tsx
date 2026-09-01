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

function fireLayer(year: number) {
  return {
    ...layer,
    id: `fire-${year}`,
    name: `ras_aree_incendiate_${year}`,
    title: `Aree percorse dal fuoco - ${year}`,
    theme: "eventi",
    render_order: year,
    attribution: `Dati Regione Sardegna ${year}`,
  };
}

function state(overrides: Partial<TerritorioLayerState> = {}): TerritorioLayerState {
  return {
    groups: [{ theme: "bonifica", label: "Bonifica e comprensori", layers: [layer] }],
    loading: false,
    catalogError: null,
    catalogDisabled: false,
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

  test("explains when territorial consultation is disabled", () => {
    render(
      <TerritorioLayerPanel
        {...state({
          groups: [],
          enabled: {},
          catalogDisabled: true,
          catalogError: "Consultazione territoriale non attiva in questo ambiente.",
        })}
        basemap="osm"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Territorio/i }));
    expect(screen.getByRole("status")).toHaveTextContent(
      "Consultazione territoriale non attiva in questo ambiente.",
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
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

  test("groups fire layers in a yearly selector and keeps one visible toggle", () => {
    const fires = Array.from({ length: 20 }, (_, index) => fireLayer(2005 + index));
    const props = state({
      groups: [{ theme: "eventi", label: "Eventi territoriali", layers: fires }],
      enabled: {},
      opacity: {},
      legendUrls: {},
    });
    const view = render(<TerritorioLayerPanel {...props} basemap="osm" />);
    fireEvent.click(screen.getByRole("button", { name: /Territorio/i }));

    const selector = screen.getByLabelText("Anno aree percorse dal fuoco");
    expect(screen.getAllByRole("option")).toHaveLength(21);
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    fireEvent.change(selector, { target: { value: "fire-2023" } });
    expect(props.toggleLayer).toHaveBeenCalledWith("fire-2023");

    const activeProps = state({
      groups: [{ theme: "eventi", label: "Eventi territoriali", layers: fires }],
      enabled: { "fire-2023": true },
      opacity: { "fire-2023": 0.65 },
      legendUrls: {},
    });
    view.rerender(<TerritorioLayerPanel {...activeProps} basemap="osm" />);
    expect(screen.getByLabelText("Anno aree percorse dal fuoco")).toHaveValue("fire-2023");
    expect(screen.getAllByRole("checkbox")).toHaveLength(1);
    expect(screen.getByLabelText("Attribuzioni strati attivi")).toHaveTextContent(
      "Dati Regione Sardegna 2023",
    );
    fireEvent.change(screen.getByLabelText("Anno aree percorse dal fuoco"), {
      target: { value: "fire-2023" },
    });
    expect(activeProps.toggleLayer).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Anno aree percorse dal fuoco"), {
      target: { value: "fire-2022" },
    });
    expect(activeProps.toggleLayer).toHaveBeenCalledWith("fire-2023");
    expect(activeProps.toggleLayer).toHaveBeenCalledWith("fire-2022");
    activeProps.toggleLayer.mockClear();
    fireEvent.change(screen.getByLabelText("Anno aree percorse dal fuoco"), {
      target: { value: "" },
    });
    expect(activeProps.toggleLayer).toHaveBeenCalledWith("fire-2023");
  });
});
