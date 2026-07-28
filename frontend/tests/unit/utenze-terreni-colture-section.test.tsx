import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import {
  UtenzeTerreniColtureSection,
  buildCropOverlayLayers,
  cropFeatureLabel,
  formatLandCropArea,
  formatLandCropEuro,
} from "@/components/utenze/utenze-terreni-colture-section";
import type { RuoloSubjectLandCropsResponse } from "@/types/ruolo";

const mocks = vi.hoisted(() => ({
  getSubjectLandCrops: vi.fn(),
  mapProps: [] as Array<Record<string, unknown>>,
}));

vi.mock("@/lib/ruolo-api", () => ({
  getSubjectLandCrops: (...args: unknown[]) => mocks.getSubjectLandCrops(...args),
}));

vi.mock("next/dynamic", () => ({
  default: (_loader: unknown, options?: { loading?: () => React.ReactNode }) =>
    function MockMapContainer(props: Record<string, unknown>) {
      mocks.mapProps.push(props);
      (props.onGeometryDrawn as (() => void) | undefined)?.();
      (props.onSelectionCleared as (() => void) | undefined)?.();
      return (
        <div>
          {options?.loading?.()}
          <div data-testid="land-crops-map" />
        </div>
      );
    },
}));

function buildSummary(overrides: Partial<RuoloSubjectLandCropsResponse> = {}): RuoloSubjectLandCropsResponse {
  const geojson: GeoJSON.FeatureCollection = {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry: {
          type: "Polygon",
          coordinates: [
            [
              [8, 39],
              [8.1, 39],
              [8.1, 39.1],
              [8, 39.1],
              [8, 39],
            ],
          ],
        },
        properties: {
          coltura: "RISO",
          foglio: "12",
          particella: "34",
        },
      },
      {
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: [8.2, 39.2],
        },
        properties: {
          coltura: "MEDICA",
        },
      },
    ],
  };

  return {
    subject_id: "subject-1",
    anno_riferimento: 2025,
    available_years: [2025, 2024],
    totals: {
      avvisi_count: 1,
      particelle_count: 2,
      particelle_returned_count: 2,
      comuni_count: 1,
      colture_count: 2,
      distretti_count: 1,
      sup_catastale_ha: 2.4,
      sup_irrigata_ha: 1.75,
      importo_totale_euro: 345.67,
      warning_count: 1,
      mapped_count: 1,
      unmapped_count: 1,
    },
    colture: [
      {
        coltura: "RISO",
        particelle_count: 1,
        sup_catastale_ha: 1.25,
        sup_irrigata_ha: 1,
        importo_totale_euro: 300,
        comune: ["ORISTANO"],
        distretto: ["D1"],
      },
      {
        coltura: "MEDICA",
        particelle_count: 1,
        sup_catastale_ha: 1.15,
        sup_irrigata_ha: 0.75,
        importo_totale_euro: 45.67,
        comune: ["ORISTANO"],
        distretto: ["D1"],
      },
    ],
    comuni: [
      {
        comune_nome: "ORISTANO",
        particelle_count: 2,
        sup_catastale_ha: 2.4,
        sup_irrigata_ha: 1.75,
        importo_totale_euro: 345.67,
        coltura: ["MEDICA", "RISO"],
        distretto: ["D1"],
      },
    ],
    distretti: [
      {
        distretto: "D1",
        particelle_count: 2,
        sup_catastale_ha: 2.4,
        sup_irrigata_ha: 1.75,
        importo_totale_euro: 345.67,
        comune: ["ORISTANO"],
        coltura: ["MEDICA", "RISO"],
      },
    ],
    particelle: [
      {
        id: "particella-1",
        avviso_id: "avviso-1",
        codice_cnc: "CNC-1",
        codice_partita: "P-1",
        comune_nome: "ORISTANO",
        comune_codice: "G113",
        foglio: "12",
        particella: "34",
        subalterno: null,
        distretto: "D1",
        domanda_irrigua: null,
        coltura: "RISO",
        sup_catastale_ha: 1.25,
        sup_irrigata_ha: 1,
        importo_totale_euro: 300,
        catasto_parcel_id: null,
        cat_particella_id: "cat-1",
        cat_particella_match_status: "matched",
        cat_particella_match_confidence: "high",
        ade_scan_status: null,
        ade_scan_classification: null,
        is_mapped: true,
        has_warning: false,
      },
      {
        id: "particella-2",
        avviso_id: "avviso-1",
        codice_cnc: "CNC-1",
        codice_partita: "P-1",
        comune_nome: "ORISTANO",
        comune_codice: "G113",
        foglio: "12",
        particella: "35",
        subalterno: "1",
        distretto: "D1",
        domanda_irrigua: null,
        coltura: null,
        sup_catastale_ha: 1.15,
        sup_irrigata_ha: 0.75,
        importo_totale_euro: 45.67,
        catasto_parcel_id: null,
        cat_particella_id: null,
        cat_particella_match_status: "unmatched",
        cat_particella_match_confidence: null,
        ade_scan_status: null,
        ade_scan_classification: null,
        is_mapped: false,
        has_warning: true,
      },
    ],
    geojson_requested: false,
    geojson_limited: false,
    geojson: null,
    ...overrides,
  };
}

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });
  return { promise, resolve, reject };
}

describe("UtenzeTerreniColtureSection helpers", () => {
  test("formats values and builds crop overlay layers", () => {
    expect(formatLandCropArea(1.234)).toBe("1,23 ha");
    expect(formatLandCropArea(null)).toBe("-");
    expect(formatLandCropEuro(12.5)).toContain("12,50");
    expect(formatLandCropEuro(undefined)).toBe("-");
    expect(cropFeatureLabel({ type: "Feature", geometry: { type: "Point", coordinates: [8, 39] }, properties: { coltura: "  RISO  " } })).toBe("RISO");
    expect(cropFeatureLabel({ type: "Feature", geometry: { type: "Point", coordinates: [8, 39] }, properties: {} })).toBe("Coltura non indicata");
    expect(buildCropOverlayLayers(null)).toEqual([]);

    const layers = buildCropOverlayLayers(buildSummary({ geojson: buildSummary().geojson ?? undefined }).geojson);
    expect(layers).toEqual([]);

    const geoSummary = buildSummary();
    const geojson = {
      type: "FeatureCollection",
      features: [
        { type: "Feature", geometry: null, properties: { coltura: "NON GIS" } } as unknown as GeoJSON.Feature,
        { type: "Feature", geometry: { type: "Point", coordinates: [8, 39] }, properties: { coltura: "RISO" } },
        { type: "Feature", geometry: { type: "Point", coordinates: [8.1, 39] }, properties: { coltura: "RISO" } },
        { type: "Feature", geometry: { type: "Point", coordinates: [8.2, 39] }, properties: { coltura: "MEDICA" } },
      ],
    } satisfies GeoJSON.FeatureCollection;
    geoSummary.geojson = geojson;
    const grouped = buildCropOverlayLayers(geoSummary.geojson);
    expect(grouped).toHaveLength(2);
    expect(grouped[0].name).toBe("RISO");
    expect(grouped[0].geojson?.features).toHaveLength(2);
  });
});

describe("UtenzeTerreniColtureSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.mapProps.length = 0;
  });

  test("renders summary, switches year and loads GIS by default", async () => {
    const summary = buildSummary();
    const mapSummary = buildSummary({
      geojson_requested: true,
      geojson_limited: true,
      geojson: {
        type: "FeatureCollection",
        features: [
          { type: "Feature", geometry: { type: "Point", coordinates: [8, 39] }, properties: { coltura: "RISO" } },
          { type: "Feature", geometry: { type: "Point", coordinates: [8.1, 39] }, properties: { coltura: "MEDICA" } },
        ],
      },
    });
    const mapSummary2024 = buildSummary({
      anno_riferimento: 2024,
      available_years: [2025, 2024],
      geojson_requested: true,
      geojson_limited: true,
      geojson: mapSummary.geojson,
    });
    mocks.getSubjectLandCrops
      .mockResolvedValueOnce(summary)
      .mockResolvedValueOnce(mapSummary)
      .mockResolvedValueOnce(mapSummary)
      .mockResolvedValueOnce(buildSummary({ anno_riferimento: 2024, available_years: [2025, 2024] }))
      .mockResolvedValueOnce(mapSummary2024);

    render(<UtenzeTerreniColtureSection subjectId="subject-1" token="token" />);

    expect(await screen.findByText("Terreni e colture a ruolo 2025")).toBeInTheDocument();
    expect(screen.getByText("Prevalente: RISO")).toBeInTheDocument();
    expect(screen.getByText("Dove sono i terreni")).toBeInTheDocument();
    expect(screen.getByText("Da collegare")).toBeInTheDocument();
    expect(await screen.findByTestId("land-crops-map")).toBeInTheDocument();
    expect(screen.getByText("2 geometrie caricate")).toBeInTheDocument();
    expect(screen.getByText("Layer limitato per performance.")).toBeInTheDocument();
    await waitFor(() => {
      expect(mocks.getSubjectLandCrops).toHaveBeenNthCalledWith(2, "token", "subject-1", {
        anno: 2025,
        include_geojson: true,
        particelle_limit: 160,
        geojson_limit: 500,
      });
    });
    expect(mocks.mapProps[0].overlayLayers).toHaveLength(2);

    fireEvent.click(screen.getByRole("button", { name: "Ricarica mappa" }));
    await waitFor(() => {
      expect(mocks.getSubjectLandCrops).toHaveBeenNthCalledWith(3, "token", "subject-1", {
        anno: 2025,
        include_geojson: true,
        particelle_limit: 160,
        geojson_limit: 500,
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "2024" }));
    await waitFor(() => {
      expect(mocks.getSubjectLandCrops).toHaveBeenNthCalledWith(4, "token", "subject-1", {
        anno: 2024,
        include_geojson: false,
        particelle_limit: 160,
      });
    });
    await waitFor(() => {
      expect(mocks.getSubjectLandCrops).toHaveBeenNthCalledWith(5, "token", "subject-1", {
        anno: 2024,
        include_geojson: true,
        particelle_limit: 160,
        geojson_limit: 500,
      });
    });
  });

  test("renders empty, access and generic error states", async () => {
    mocks.getSubjectLandCrops.mockResolvedValueOnce(buildSummary({
      totals: { ...buildSummary().totals, particelle_count: 0 },
      colture: [],
      comuni: [],
      distretti: [],
      particelle: [],
    }));
    const emptyRender = render(<UtenzeTerreniColtureSection subjectId="subject-empty" token="token" />);
    expect(await screen.findByText("Nessun terreno o coltura a ruolo collegato a questo soggetto.")).toBeInTheDocument();
    emptyRender.unmount();

    mocks.getSubjectLandCrops.mockRejectedValueOnce("403 Module access");
    const accessRender = render(<UtenzeTerreniColtureSection subjectId="subject-denied" token="token" />);
    expect(await screen.findByText(/Il modulo Ruolo non e accessibile/)).toBeInTheDocument();
    accessRender.unmount();

    mocks.getSubjectLandCrops.mockRejectedValueOnce(new Error("403 Module access"));
    const accessErrorRender = render(<UtenzeTerreniColtureSection subjectId="subject-denied-error" token="token" />);
    expect(await screen.findByText(/Il modulo Ruolo non e accessibile/)).toBeInTheDocument();
    accessErrorRender.unmount();

    mocks.getSubjectLandCrops.mockRejectedValueOnce("Errore ruolo");
    render(<UtenzeTerreniColtureSection subjectId="subject-error" token="token" />);
    expect(await screen.findByText("Errore caricamento terreni e colture a ruolo")).toBeInTheDocument();
  });

  test("renders map load error and no-geometry state", async () => {
    mocks.getSubjectLandCrops
      .mockResolvedValueOnce(buildSummary())
      .mockRejectedValueOnce(new Error("Errore GIS"))
      .mockResolvedValueOnce(buildSummary())
      .mockResolvedValueOnce(buildSummary({ geojson_requested: true, geojson: { type: "FeatureCollection", features: [] } }));

    const firstRender = render(<UtenzeTerreniColtureSection subjectId="subject-map-error" token="token" />);
    expect(await screen.findByText("Errore GIS")).toBeInTheDocument();
    firstRender.unmount();

    render(<UtenzeTerreniColtureSection subjectId="subject-map-empty" token="token" />);
    expect(await screen.findByText("Nessuna geometria GIS disponibile per le particelle collegate. Verificare i match catastali.")).toBeInTheDocument();
  });

  test("shows manual map reload errors", async () => {
    mocks.getSubjectLandCrops
      .mockResolvedValueOnce(buildSummary())
      .mockResolvedValueOnce(buildSummary({ geojson_requested: true }))
      .mockRejectedValueOnce(new Error("Errore reload GIS"));

    render(<UtenzeTerreniColtureSection subjectId="subject-map-reload-error" token="token" />);

    fireEvent.click(await screen.findByRole("button", { name: "Ricarica mappa" }));
    expect(await screen.findByText("Errore reload GIS")).toBeInTheDocument();
  });

  test("renders fallback summary branches and ignores map click without reference year", async () => {
    mocks.getSubjectLandCrops.mockResolvedValueOnce(buildSummary({
      anno_riferimento: null,
      available_years: [2025],
      totals: {
        ...buildSummary().totals,
        warning_count: 0,
      },
      colture: [],
    }));

    render(<UtenzeTerreniColtureSection subjectId="subject-no-year" token="token" />);

    expect(await screen.findByText("Terreni e colture a ruolo")).toBeInTheDocument();
    expect(screen.getByText("Coltura non indicata")).toBeInTheDocument();
    expect(screen.getByText("Collegamenti senza warning")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Apri mappa terreni" }));
    expect(mocks.getSubjectLandCrops).toHaveBeenCalledTimes(1);
  });

  test("ignores late successful and failed loads after unmount", async () => {
    const successful = createDeferred<RuoloSubjectLandCropsResponse>();
    mocks.getSubjectLandCrops.mockReturnValueOnce(successful.promise);
    const firstRender = render(<UtenzeTerreniColtureSection subjectId="subject-late-ok" token="token" />);
    firstRender.unmount();
    successful.resolve(buildSummary());

    const failed = createDeferred<RuoloSubjectLandCropsResponse>();
    mocks.getSubjectLandCrops.mockReturnValueOnce(failed.promise);
    const secondRender = render(<UtenzeTerreniColtureSection subjectId="subject-late-fail" token="token" />);
    secondRender.unmount();
    failed.reject(new Error("late"));

    await waitFor(() => {
      expect(mocks.getSubjectLandCrops).toHaveBeenCalledTimes(2);
    });
  });

  test("ignores late automatic GIS loads after unmount", async () => {
    const mapSuccessful = createDeferred<RuoloSubjectLandCropsResponse>();
    mocks.getSubjectLandCrops
      .mockResolvedValueOnce(buildSummary())
      .mockReturnValueOnce(mapSuccessful.promise);
    const firstRender = render(<UtenzeTerreniColtureSection subjectId="subject-late-map-ok" token="token" />);
    expect(await screen.findByText("Terreni e colture a ruolo 2025")).toBeInTheDocument();
    firstRender.unmount();
    mapSuccessful.resolve(buildSummary({ geojson_requested: true }));

    const mapFailed = createDeferred<RuoloSubjectLandCropsResponse>();
    mocks.getSubjectLandCrops
      .mockResolvedValueOnce(buildSummary())
      .mockReturnValueOnce(mapFailed.promise);
    const secondRender = render(<UtenzeTerreniColtureSection subjectId="subject-late-map-fail" token="token" />);
    expect(await screen.findByText("Terreni e colture a ruolo 2025")).toBeInTheDocument();
    secondRender.unmount();
    mapFailed.reject(new Error("late map"));

    await waitFor(() => {
      expect(mocks.getSubjectLandCrops).toHaveBeenCalledTimes(4);
    });
  });
});
