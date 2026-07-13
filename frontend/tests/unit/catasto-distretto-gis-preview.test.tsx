import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { DistrettoGisPreview } from "@/components/catasto/distretti/distretto-gis-preview";
import type { CatDistretto, CatDistrettoKpi } from "@/types/catasto";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  catastoGetDistrettoGeojson: vi.fn(),
  mapProps: [] as Array<Record<string, unknown>>,
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api/catasto", () => ({
  catastoGetDistrettoGeojson: mocks.catastoGetDistrettoGeojson,
}));

vi.mock("next/dynamic", () => ({
  default: (_loader: unknown, options?: { loading?: () => React.ReactNode }) =>
    function MockMapContainer(props: Record<string, unknown>) {
      mocks.mapProps.push(props);
      (props.onGeometryDrawn as ((geometry: GeoJSON.Geometry) => void) | undefined)?.({
        type: "Point",
        coordinates: [8.5, 39.8],
      });
      (props.onSelectionCleared as (() => void) | undefined)?.();
      return (
        <div>
          {options?.loading?.()}
          <div data-testid="distretto-gis-map" />
        </div>
      );
    },
}));

const distretto: CatDistretto = {
  id: "distretto-1",
  num_distretto: "01",
  nome_distretto: "Sinis Nord Est",
  decreto_istitutivo: null,
  data_decreto: null,
  attivo: true,
  note: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const kpi: CatDistrettoKpi = {
  distretto_id: "distretto-1",
  anno: 2026,
  num_distretto: "01",
  totale_particelle: 12,
  totale_utenze: 7,
  totale_anomalie: 0,
  anomalie_error: 0,
  importo_totale_0648: "100",
  importo_totale_0985: "40",
  superficie_irrigabile_mq: "125000",
};

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });
  return { promise, resolve, reject };
}

describe("DistrettoGisPreview", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.mapProps.length = 0;
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.catastoGetDistrettoGeojson.mockResolvedValue({
      type: "Feature",
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [8.5, 39.8],
            [8.6, 39.8],
            [8.6, 39.9],
            [8.5, 39.9],
            [8.5, 39.8],
          ],
        ],
      },
      properties: { num_distretto: "01" },
    });
  });

  test("renders a read-only GIS preview filtered on the district", async () => {
    render(<DistrettoGisPreview distretto={distretto} kpi={kpi} />);

    expect(screen.getByText("Vista GIS read-only")).toBeInTheDocument();
    expect(screen.getByText("Particelle del distretto 01")).toBeInTheDocument();
    expect(screen.getByText("12 particelle")).toBeInTheDocument();
    expect(screen.getByText("12,5 ha")).toBeInTheDocument();
    expect(screen.getByTestId("distretto-gis-map")).toBeInTheDocument();

    await waitFor(() => {
      expect(mocks.catastoGetDistrettoGeojson).toHaveBeenCalledWith("token", "distretto-1");
    });
    await waitFor(() => {
      expect(mocks.mapProps.at(-1)?.focusSignal).toBe(1);
    });

    const props = mocks.mapProps.at(-1);
    expect(props?.token).toBeNull();
    expect(props?.filters).toEqual({ num_distretto: "01" });
    expect(props?.mapLayers).toEqual(
      expect.objectContaining({
        distretto: "01",
        distrettiOpacity: 0.08,
        particelleOpacity: 0.96,
        particelleColorMode: "district_preview",
        showParticelleFill: true,
        showDeliveryPoints: false,
      }),
    );
    expect(props?.focusGeojson).toEqual(
      expect.objectContaining({
        type: "FeatureCollection",
      }),
    );
    expect(props?.overlayLayers).toEqual([
      expect.objectContaining({
        layer_key: "distretto-distretto-1",
        name: "Distretto 01",
        color: "#FDBA74",
        outlineColor: "#C2410C",
        opacity: 0.68,
        geojson: expect.objectContaining({ type: "FeatureCollection" }),
      }),
    ]);
    expect(props?.focusOptions).toEqual({
      padding: 26,
      maxZoom: 15.7,
      duration: 450,
    });
  });

  test("keeps the map visible when the focus geometry cannot be loaded", async () => {
    mocks.catastoGetDistrettoGeojson.mockRejectedValueOnce(new Error("GeoJSON non disponibile"));

    render(<DistrettoGisPreview distretto={distretto} kpi={null} />);

    expect(screen.getByTestId("distretto-gis-map")).toBeInTheDocument();
    expect(await screen.findByText(/GeoJSON non disponibile/i)).toBeInTheDocument();
    expect(mocks.mapProps.at(-1)?.focusGeojson).toBeNull();
  });

  test("uses the default error when the focus endpoint rejects with a primitive value", async () => {
    mocks.catastoGetDistrettoGeojson.mockRejectedValueOnce("errore primitivo");

    render(<DistrettoGisPreview distretto={distretto} kpi={kpi} />);

    expect(
      await screen.findByText(/Impossibile centrare il distretto sulla mappa/i),
    ).toBeInTheDocument();
  });

  test("does not request focus geometry without an auth token", () => {
    mocks.getStoredAccessToken.mockReturnValueOnce(null);

    render(<DistrettoGisPreview distretto={distretto} kpi={null} />);

    expect(screen.getByText("0 particelle")).toBeInTheDocument();
    expect(screen.getByText("0,0 ha")).toBeInTheDocument();
    expect(mocks.catastoGetDistrettoGeojson).not.toHaveBeenCalled();
  });

  test("keeps focus disabled when the endpoint returns no geometry", async () => {
    mocks.catastoGetDistrettoGeojson.mockResolvedValueOnce({
      type: "Feature",
      geometry: null,
      properties: {},
    });

    render(<DistrettoGisPreview distretto={distretto} kpi={kpi} />);

    await waitFor(() => {
      expect(mocks.catastoGetDistrettoGeojson).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(mocks.mapProps.at(-1)?.focusGeojson).toBeNull();
    });
  });

  test("handles numeric and non-finite hectare inputs", () => {
    render(
      <DistrettoGisPreview
        distretto={distretto}
        kpi={{
          ...kpi,
          totale_particelle: 0,
          superficie_irrigabile_mq: Number.NaN as unknown as string,
        }}
      />,
    );

    expect(screen.getByText("0 particelle")).toBeInTheDocument();
    expect(screen.getByText("0,0 ha")).toBeInTheDocument();
  });

  test("ignores late geometry responses after unmount", async () => {
    const deferred = createDeferred<{
      type: "Feature";
      geometry: GeoJSON.Geometry;
      properties: Record<string, unknown>;
    }>();
    mocks.catastoGetDistrettoGeojson.mockReturnValueOnce(deferred.promise);

    const { unmount } = render(<DistrettoGisPreview distretto={distretto} kpi={kpi} />);
    unmount();
    deferred.resolve({
      type: "Feature",
      geometry: { type: "Point", coordinates: [8.5, 39.8] },
      properties: {},
    });

    await expect(deferred.promise).resolves.toEqual(expect.any(Object));
  });

  test("ignores late geometry errors after unmount", async () => {
    const deferred = createDeferred<never>();
    mocks.catastoGetDistrettoGeojson.mockReturnValueOnce(deferred.promise);

    const { unmount } = render(<DistrettoGisPreview distretto={distretto} kpi={kpi} />);
    unmount();
    deferred.reject(new Error("late error"));

    await expect(deferred.promise).rejects.toThrow("late error");
  });
});
