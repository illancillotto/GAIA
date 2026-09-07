import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import GisWorkspace from "@/components/catasto/gis/GisWorkspace";

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

test("fits below navigation, updates on resize and exposes the console toggle", () => {
  let resized: () => void = () => {};
  const disconnect = vi.fn();
  vi.stubGlobal("ResizeObserver", class {
    constructor(callback: () => void) { resized = callback; }
    observe = vi.fn();
    disconnect = disconnect;
  });
  const bounds = vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({ top: 112 } as DOMRect);
  const change = vi.fn();
  const expand = vi.fn();
  const view = render(<GisWorkspace consoleOpen={false} onConsoleChange={change} onExpand={expand}><aside id="gis-console">Layers</aside></GisWorkspace>);
  const root = view.container.firstElementChild as HTMLElement;
  expect(root.style.getPropertyValue("--gis-top")).toBe("112px");
  const toggle = screen.getByRole("button", { name: "Apri Console GIS" });
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  expect(toggle).toHaveAttribute("aria-controls", "gis-console");
  fireEvent.click(toggle);
  expect(change).toHaveBeenLastCalledWith(true);
  view.rerender(<GisWorkspace consoleOpen onConsoleChange={change} onExpand={expand}><aside id="gis-console">Layers</aside></GisWorkspace>);
  fireEvent.click(screen.getByRole("button", { name: "Nascondi Console GIS" }));
  expect(change).toHaveBeenLastCalledWith(false);
  fireEvent.click(screen.getByRole("button", { name: "Vista estesa" }));
  expect(expand).toHaveBeenCalledOnce();
  bounds.mockReturnValue({ top: 52 } as DOMRect);
  act(resized);
  expect(root.style.getPropertyValue("--gis-top")).toBe("52px");
  bounds.mockReturnValue({ top: 60 } as DOMRect);
  fireEvent(window, new Event("resize"));
  expect(root.style.getPropertyValue("--gis-top")).toBe("60px");
  view.unmount();
  expect(disconnect).toHaveBeenCalledOnce();
});
