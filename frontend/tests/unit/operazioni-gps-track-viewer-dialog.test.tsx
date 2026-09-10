import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  mapConstructor: vi.fn(),
  markerConstructor: vi.fn(),
  boundsExtend: vi.fn(),
}));

vi.mock("maplibre-gl", () => ({
  setWorkerUrl: vi.fn(),
  GPUInitializationError: class extends Error {
    statusMessage = null;
    constructor() { super("context lost"); }
  },
  Map: function Map(options: unknown) {
    return mocks.mapConstructor(options);
  },
  Marker: function Marker(options: unknown) {
    return mocks.markerConstructor(options);
  },
  NavigationControl: function NavigationControl() {},
  LngLatBounds: class {
    extend = mocks.boundsExtend;
  },
}));

import { GPUInitializationError } from "maplibre-gl";
import { OperazioniGpsTrackViewerDialog } from "@/components/operazioni/gps-track-viewer-dialog";

const point = { latitude: 39.9, longitude: 8.6, timestamp: "2026-09-09T10:00:00Z" };
const baseProps = {
  open: true,
  title: "Attivita GPS",
  points: [point],
  bounds: null,
  summary: null,
  viewerMode: "track",
  usesRawPayload: true,
  onClose: vi.fn(),
};

function createMap() {
  const handlers = new Map<string, (event?: unknown) => void>();
  return {
    handlers,
    addControl: vi.fn(),
    addSource: vi.fn(),
    addLayer: vi.fn(),
    easeTo: vi.fn(),
    fitBounds: vi.fn(),
    remove: vi.fn(),
    on: vi.fn((type: string, callback: (event?: unknown) => void) => handlers.set(type, callback)),
  };
}

function createMarker() {
  const marker = {
    setLngLat: vi.fn(),
    addTo: vi.fn(),
  };
  marker.setLngLat.mockReturnValue(marker);
  marker.addTo.mockReturnValue(marker);
  return marker;
}

describe("OperazioniGpsTrackViewerDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
      configurable: true,
      value: () => ({}),
    });
    mocks.mapConstructor.mockImplementation(() => createMap());
    mocks.markerConstructor.mockImplementation(() => createMarker());
  });

  test("does not initialize a map while closed or without points", () => {
    const { rerender } = render(<OperazioniGpsTrackViewerDialog {...baseProps} open={false} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    rerender(<OperazioniGpsTrackViewerDialog {...baseProps} points={[]} />);
    expect(screen.getByText("Traccia non disponibile")).toBeInTheDocument();
    expect(mocks.mapConstructor).not.toHaveBeenCalled();
  });

  test("renders one point, reports WebGL errors and removes the map", () => {
    const map = createMap();
    mocks.mapConstructor.mockReturnValueOnce(map);
    const view = render(<OperazioniGpsTrackViewerDialog {...baseProps} />);

    act(() => map.handlers.get("load")?.());
    expect(map.addSource).toHaveBeenCalledWith("activity-track", expect.objectContaining({
      data: expect.objectContaining({ geometry: { type: "Point", coordinates: [8.6, 39.9] } }),
    }));
    expect(map.easeTo).toHaveBeenCalledWith({ center: [8.6, 39.9], zoom: 14 });
    expect(mocks.markerConstructor).toHaveBeenCalledOnce();

    act(() => map.handlers.get("error")?.({ error: new Error("unrelated") }));
    expect(screen.queryByText("unrelated")).not.toBeInTheDocument();
    act(() => map.handlers.get("error")?.({ error: new GPUInitializationError({}, null) }));
    expect(screen.getByRole("alert")).toHaveTextContent("context lost");
    view.unmount();
    expect(map.remove).toHaveBeenCalledOnce();
  });

  test("renders a line, endpoints, sampled timeline and bounds", () => {
    const map = createMap();
    mocks.mapConstructor.mockReturnValueOnce(map);
    const points = Array.from({ length: 13 }, (_, index) => ({
      latitude: 39.9 + index / 100,
      longitude: 8.6 + index / 100,
      timestamp: null,
    }));
    render(
      <OperazioniGpsTrackViewerDialog
        {...baseProps}
        points={points}
        bounds={{ min_latitude: 39.9, max_latitude: 40.02, min_longitude: 8.6, max_longitude: 8.72 }}
        summary={{ provider_name: "provider", total_distance_km: 12, total_duration_seconds: 3600 }}
        viewerMode="segment"
        usesRawPayload={false}
      />,
    );

    act(() => map.handlers.get("load")?.());
    expect(map.addLayer).toHaveBeenCalledWith(expect.objectContaining({ id: "activity-track-line" }));
    expect(mocks.markerConstructor).toHaveBeenCalledTimes(2);
    expect(mocks.boundsExtend).toHaveBeenCalledTimes(12);
    expect(map.fitBounds).toHaveBeenCalled();
    expect(screen.getByText(/Timeline campionata: 12 punti/)).toBeInTheDocument();
    expect(screen.getByText("Segmento sintetico")).toBeInTheDocument();
  });

  test("shows WebGL2 and constructor failures", () => {
    Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
      configurable: true,
      value: () => null,
    });
    const unsupported = render(<OperazioniGpsTrackViewerDialog {...baseProps} />);
    expect(screen.getByRole("alert")).toHaveTextContent("WebGL2");
    unsupported.unmount();

    Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
      configurable: true,
      value: () => ({}),
    });
    mocks.mapConstructor.mockImplementationOnce(() => {
      throw new Error("GPU offline");
    });
    render(<OperazioniGpsTrackViewerDialog {...baseProps} />);
    expect(screen.getByRole("alert")).toHaveTextContent("GPU offline");
  });
});
