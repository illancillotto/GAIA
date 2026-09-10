import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import GisWorkspace, { GisBasemapControl } from "@/components/catasto/gis/GisWorkspace";

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

test("fits below navigation, updates on resize and exposes the console toggle", () => {
  let resized: () => void = () => {};
  const disconnect = vi.fn();
  vi.stubGlobal("ResizeObserver", class {
    constructor(callback: () => void) { resized = callback; }
    observe = vi.fn();
    disconnect = disconnect;
  });
  const bounds = vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({ top: 112, left: 220 } as DOMRect);
  const change = vi.fn();
  const expand = vi.fn();
  const basemapChange = vi.fn();
  const view = render(<GisWorkspace consoleOpen={false} onConsoleChange={change} onExpand={expand} basemap="osm" onBasemapChange={basemapChange} googleTilesConfigured={false}><aside id="gis-console">Layers</aside></GisWorkspace>);
  const root = view.container.firstElementChild as HTMLElement;
  expect(root.querySelector("#gis-toolbar-tools")).toBeInTheDocument();
  expect(root.style.getPropertyValue("--gis-top")).toBe("112px");
  expect(root.style.getPropertyValue("--gis-left")).toBe("220px");
  const toggle = screen.getByRole("button", { name: "Apri Console GIS" });
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  expect(toggle).toHaveAttribute("aria-controls", "gis-console");
  fireEvent.click(toggle);
  expect(change).toHaveBeenLastCalledWith(true);
  fireEvent.click(screen.getByRole("button", { name: "Sfondo mappa" }));
  expect(screen.getByRole("button", { name: "Vista classica" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.queryByRole("button", { name: "Google Earth" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Vista satellitare" }));
  expect(basemapChange).toHaveBeenCalledWith("satellite");
  view.rerender(<GisWorkspace consoleOpen onConsoleChange={change} onExpand={expand} basemap="satellite" onBasemapChange={basemapChange} googleTilesConfigured={false}><aside id="gis-console">Layers</aside></GisWorkspace>);
  fireEvent.click(screen.getByRole("button", { name: "Nascondi Console GIS" }));
  expect(change).toHaveBeenLastCalledWith(false);
  fireEvent.click(screen.getByRole("button", { name: "Vista estesa" }));
  expect(expand).toHaveBeenCalledOnce();
  bounds.mockReturnValue({ top: 52, left: 16 } as DOMRect);
  act(resized);
  expect(root.style.getPropertyValue("--gis-top")).toBe("52px");
  expect(root.style.getPropertyValue("--gis-left")).toBe("16px");
  bounds.mockReturnValue({ top: 60, left: 24 } as DOMRect);
  fireEvent(window, new Event("resize"));
  expect(root.style.getPropertyValue("--gis-top")).toBe("60px");
  expect(root.style.getPropertyValue("--gis-left")).toBe("24px");
  view.unmount();
  expect(disconnect).toHaveBeenCalledOnce();
});

test("offers Google Earth only when map tiles are configured", () => {
  const change = vi.fn();
  render(<GisBasemapControl basemap="google_satellite" onBasemapChange={change} googleTilesConfigured />);
  fireEvent.click(screen.getByRole("button", { name: "Sfondo mappa" }));
  expect(screen.getByRole("button", { name: "Google Earth" })).toHaveAttribute("aria-pressed", "true");
  fireEvent.click(screen.getByRole("button", { name: "Vista classica" }));
  expect(change).toHaveBeenCalledWith("osm");
});
