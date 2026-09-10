import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import TerritorioFieldTools, { printTerritorioMap } from "@/components/catasto/gis/TerritorioFieldTools";
import { buildTerritorioPrintHtml, mapScaleDenominator } from "@/components/catasto/gis/territorio-print";

function layer() {
  return { id: "ortho", name: "ortho", title: "Ortofoto <1977>", description: null, theme: "ortofoto", source: "ras_sitr", proxy_wms_url: "/proxy", legend_url: "/legend", default_opacity: 1, render_order: 1, queryable: "wms_visual_only" as const, attribution: "RAS & Sardegna" };
}

function mapMock() {
  const sources = new Map<string, { setData: ReturnType<typeof vi.fn> }>();
  const layers = new Set<string>();
  const listeners: Record<string, (event: { lngLat: { lng: number; lat: number }; preventDefault?: () => void }) => void> = {};
  return {
    listeners,
    sources,
    on: vi.fn((event: string, listener: typeof listeners[string]) => { listeners[event] = listener; }),
    off: vi.fn((event: string) => { delete listeners[event]; }),
    addSource: vi.fn((id: string) => { sources.set(id, { setData: vi.fn() }); }),
    getSource: vi.fn((id: string) => sources.get(id)),
    removeSource: vi.fn((id: string) => sources.delete(id)),
    addLayer: vi.fn((value: { id: string }) => layers.add(value.id)),
    getLayer: vi.fn((id: string) => layers.has(id)),
    removeLayer: vi.fn((id: string) => layers.delete(id)),
    getCanvas: () => ({ toDataURL: () => "data:image/png;base64,map" }),
    getCenter: () => ({ lat: 40 }),
    getZoom: () => 10,
  };
}

describe("territorio field tools", () => {
  afterEach(() => vi.restoreAllMocks());

  test("restarts the active tool and a completed measurement with a fresh source", () => {
    const map = mapMock();
    const view = render(<TerritorioFieldTools map={map as never} groups={[]} enabled={{}} />);
    const distance = screen.getByRole("button", { name: "Distanza" });
    fireEvent.click(distance);
    expect(map.addSource).toHaveBeenLastCalledWith(expect.any(String), expect.objectContaining({ data: { type: "FeatureCollection", features: [] } }));
    act(() => {
      map.listeners.click({ lngLat: { lng: 0, lat: 0 } });
      map.listeners.click({ lngLat: { lng: 1, lat: 0 } });
    });
    fireEvent.click(distance);
    expect(screen.queryByText("111.20 km")).not.toBeInTheDocument();
    expect(map.sources.size).toBe(1);
    act(() => {
      map.listeners.click({ lngLat: { lng: 0, lat: 0 } });
      map.listeners.click({ lngLat: { lng: 1, lat: 0 } });
      map.listeners.dblclick({ lngLat: { lng: 1, lat: 0 } });
    });
    expect(screen.getByText("111.20 km")).toBeInTheDocument();
    expect(map.listeners.click).toBeUndefined();
    fireEvent.click(distance);
    expect(map.sources.size).toBe(1);
    expect(map.listeners.click).toBeTypeOf("function");
    fireEvent.click(screen.getByRole("button", { name: "Area" }));
    expect(map.sources.size).toBe(1);
    view.unmount();
    expect(map.sources.size).toBe(0);
    expect(map.listeners.click).toBeUndefined();
  });
  test("measures clicks, completes on double click and clears the overlay", () => {
    const map = mapMock();
    render(<TerritorioFieldTools map={map as never} groups={[]} enabled={{}} />);
    fireEvent.click(screen.getByRole("button", { name: "Distanza" }));
    act(() => {
      map.listeners.click({ lngLat: { lng: 0, lat: 0 } });
      map.listeners.click({ lngLat: { lng: 1, lat: 0 } });
    });
    expect(screen.getByText("111.20 km")).toBeInTheDocument();
    const preventDefault = vi.fn();
    act(() => map.listeners.dblclick({ lngLat: { lng: 1, lat: 0 }, preventDefault }));
    expect(preventDefault).toHaveBeenCalled();
    expect(map.off).toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Pulisci" }));
    expect(screen.queryByText("111.20 km")).not.toBeInTheDocument();
    expect(map.removeSource).toHaveBeenCalled();
  });

  test("builds and opens the printable layout with active sources", () => {
    const map = mapMock();
    const popup = { opener: window, document: { write: vi.fn(), close: vi.fn() }, focus: vi.fn(), print: vi.fn() };
    const open = vi.spyOn(window, "open").mockReturnValue(popup as never);
    render(<TerritorioFieldTools map={map as never} groups={[{ theme: "ortofoto", label: "Ortofoto", layers: [layer()] }]} enabled={{ ortho: true }} />);
    fireEvent.click(screen.getByRole("button", { name: "Stampa mappa territoriale" }));
    expect(open).toHaveBeenCalledWith("", "_blank");
    expect(popup.opener).toBeNull();
    expect(popup.document.write).toHaveBeenCalledWith(expect.stringContaining("Ortofoto &lt;1977&gt;"));
    expect(popup.document.write).toHaveBeenCalledWith(expect.stringContaining("RAS &amp; Sardegna"));
    expect(popup.focus).toHaveBeenCalled();
    expect(popup.print).toHaveBeenCalled();
  });

  test("renders compact measurement and print commands", () => {
    const map = mapMock();
    const popup = { opener: window, document: { write: vi.fn(), close: vi.fn() }, focus: vi.fn(), print: vi.fn() };
    vi.spyOn(window, "open").mockReturnValue(popup as never);
    const view = render(<TerritorioFieldTools compact map={map as never} groups={[]} enabled={{}} />);
    const measurementToggle = screen.getByRole("button", { name: "Misure sul terreno" });
    expect(measurementToggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("button", { name: "Distanza" })).not.toBeInTheDocument();
    fireEvent.click(measurementToggle);
    expect(measurementToggle).toHaveAttribute("aria-expanded", "true");
    fireEvent.click(screen.getByRole("button", { name: "Distanza" }));
    expect(measurementToggle.className).toContain("bg-emerald-100");
    fireEvent.click(screen.getByRole("button", { name: "Stampa mappa territoriale" }));
    expect(popup.print).toHaveBeenCalledOnce();
    fireEvent.click(measurementToggle);
    expect(screen.queryByRole("button", { name: "Distanza" })).not.toBeInTheDocument();
    view.unmount();

    render(<TerritorioFieldTools compact map={null} groups={[]} enabled={{}} />);
    expect(screen.getByRole("button", { name: "Stampa mappa territoriale" })).toBeDisabled();
  });

  test("measures a geodetic area and supports a map-free controller", () => {
    const map = mapMock();
    const first = render(<TerritorioFieldTools map={map as never} groups={[]} enabled={{}} />);
    fireEvent.click(screen.getByRole("button", { name: "Area" }));
    act(() => {
      map.listeners.click({ lngLat: { lng: 0, lat: 0 } });
      map.listeners.click({ lngLat: { lng: 0.01, lat: 0 } });
      map.listeners.click({ lngLat: { lng: 0.01, lat: 0.01 } });
    });
    expect(screen.getByText(/ha$/)).toBeInTheDocument();
    act(() => map.listeners.dblclick({ lngLat: { lng: 0.01, lat: 0.01 } }));
    first.unmount();

    const second = render(<TerritorioFieldTools map={null} groups={[]} enabled={{}} />);
    expect(screen.getByRole("button", { name: "Stampa mappa territoriale" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Distanza" }));
    fireEvent.click(screen.getByRole("button", { name: "Pulisci" }));
    second.unmount();
    printTerritorioMap(null, [], {}, vi.fn());
  });

  test("stops cleanly when the browser blocks the print popup", () => {
    const map = mapMock();
    const blocked = vi.fn(() => null);
    printTerritorioMap(map as never, [], {}, blocked);
    expect(blocked).toHaveBeenCalled();
  });

  test("covers scale and empty-layout fallbacks", () => {
    expect(mapScaleDenominator(0, 0)).toBe(559082264);
    const html = buildTerritorioPrintHtml({ image: "map", scale: 1000, layers: [] });
    expect(html).toContain("Nessuno strato territoriale attivo");
    expect(html).toContain("Scala 1:1.000");
  });
});
