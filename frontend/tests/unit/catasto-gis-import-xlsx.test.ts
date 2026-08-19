import { describe, expect, test } from "vitest";

import {
  buildDraftOverlayLayer,
  buildFoundSelectionItems,
  buildImportStatsFromDetail,
  buildParticellaRefsFromRows,
  countFeaturesWithGeometry,
} from "@/lib/catasto-gis-import-xlsx";
import type { GisResolveRefsResponse, GisSavedSelectionDetail } from "@/types/gis";

const polygonFeature = {
  type: "Feature" as const,
  geometry: {
    type: "Polygon" as const,
    coordinates: [[[8.55, 39.88], [8.56, 39.88], [8.56, 39.89], [8.55, 39.89], [8.55, 39.88]]],
  },
  properties: { id: "particella-1" },
};

describe("catasto GIS XLSX import helpers", () => {
  test("normalizes worksheet rows with the existing aliases, trimming and header-based row indexes", () => {
    const refs = buildParticellaRefsFromRows([
      { Comune: " Arborea ", SEZIONE: " A ", foglio: 14, Particella: " 82 ", Subalterno: " 7 " },
      { COMUNE: "", Sezione: null, Foglio: "  ", PARTICELLA: undefined, SUB: " B " },
      { comune: "Cabras", sezione: "", FOGLO: "ignored", particella: "999", sub: "" },
      { foglio: "2", particella: "3" },
    ]);

    expect(refs).toEqual([
      { row_index: 2, comune: "Arborea", sezione: "A", foglio: "14", particella: "82", sub: "7" },
      { row_index: 3, comune: null, sezione: null, foglio: null, particella: null, sub: "B" },
      { row_index: 4, comune: "Cabras", sezione: null, foglio: null, particella: "999", sub: null },
      { row_index: 5, comune: null, sezione: null, foglio: "2", particella: "3", sub: null },
    ]);
  });

  test("keeps the 5000-row limit used by the page before resolving references", () => {
    const rows = Array.from({ length: 5002 }, (_, index) => ({ comune: `Comune ${index}`, foglio: index }));
    const refs = buildParticellaRefsFromRows(rows);

    expect(refs).toHaveLength(5000);
    expect(refs[0].row_index).toBe(2);
    expect(refs[4999].row_index).toBe(5001);
    expect(refs[4999].comune).toBe("Comune 4999");
  });

  test("builds saved-selection items only from found rows with a particella id", () => {
    const resolved: GisResolveRefsResponse = {
      processed: 4,
      found: 2,
      not_found: 1,
      multiple: 1,
      invalid: 0,
      results: [
        {
          row_index: 2,
          comune_input: "Arborea",
          sezione_input: null,
          foglio_input: "14",
          particella_input: "82",
          sub_input: "A",
          esito: "FOUND",
          message: "OK",
          particella_id: "p-1",
        },
        {
          row_index: 3,
          comune_input: "Cabras",
          foglio_input: "9",
          particella_input: "999",
          esito: "NOT_FOUND",
          message: "missing",
          particella_id: null,
        },
        {
          row_index: 4,
          comune_input: "Oristano",
          foglio_input: "1",
          particella_input: "2",
          esito: "FOUND",
          message: "id missing",
          particella_id: null,
        },
        {
          row_index: 5,
          comune_input: "Terralba",
          sezione_input: "B",
          foglio_input: "7",
          particella_input: "8",
          sub_input: null,
          esito: "FOUND",
          message: "OK",
          particella_id: "p-2",
        },
      ],
      geojson: null,
    };

    expect(buildFoundSelectionItems(resolved)).toEqual([
      {
        particella_id: "p-1",
        source_row_index: 2,
        source_ref: { comune: "Arborea", sezione: null, foglio: "14", particella: "82", sub: "A" },
      },
      {
        particella_id: "p-2",
        source_row_index: 5,
        source_ref: { comune: "Terralba", sezione: "B", foglio: "7", particella: "8", sub: null },
      },
    ]);
  });

  test("uses null source row and source_ref fields when the resolver omits them", () => {
    const resolved: GisResolveRefsResponse = {
      processed: 1,
      found: 1,
      not_found: 0,
      multiple: 0,
      invalid: 0,
      results: [{ esito: "FOUND", message: "OK", particella_id: "p-minimal" }],
      geojson: null,
    };

    expect(buildFoundSelectionItems(resolved)).toEqual([
      {
        particella_id: "p-minimal",
        source_row_index: null,
        source_ref: {
          comune: undefined,
          sezione: undefined,
          foglio: undefined,
          particella: undefined,
          sub: undefined,
        },
      },
    ]);
  });

  test("counts only GeoJSON features with geometry", () => {
    expect(countFeaturesWithGeometry({ type: "FeatureCollection", features: [polygonFeature, { ...polygonFeature, geometry: null as GeoJSON.Geometry | null }] })).toBe(1);
    expect(countFeaturesWithGeometry(null)).toBe(0);
    expect(countFeaturesWithGeometry(undefined)).toBe(0);
  });

  test("builds the same draft overlay layer shape used by the page", () => {
    const resolved: GisResolveRefsResponse = {
      processed: 2,
      found: 1,
      not_found: 1,
      multiple: 0,
      invalid: 0,
      results: [
        {
          row_index: 2,
          comune_input: "Arborea",
          sezione_input: null,
          foglio_input: "14",
          particella_input: "82",
          sub_input: "A",
          esito: "FOUND",
          message: "OK",
          particella_id: "p-1",
        },
      ],
      geojson: { type: "FeatureCollection", features: [polygonFeature] },
    };

    expect(buildDraftOverlayLayer({
      fileName: "gis-selezione.xlsx",
      layerIndex: 8,
      layerColors: ["#10B981", "#F59E0B", "#3B82F6"],
      resolved,
      withGeometry: 1,
    })).toEqual({
      layer_key: "draft-8",
      saved_selection_id: null,
      name: "gis-selezione",
      color: "#3B82F6",
      opacity: 0.55,
      visible: true,
      source_filename: "gis-selezione.xlsx",
      geojson: resolved.geojson,
      importStats: {
        processed: 2,
        found: 1,
        notFound: 1,
        multiple: 0,
        invalid: 0,
        withGeometry: 1,
      },
      importedItems: [
        {
          particella_id: "p-1",
          source_row_index: 2,
          source_ref: { comune: "Arborea", sezione: null, foglio: "14", particella: "82", sub: "A" },
        },
      ],
      isPersisted: false,
    });
  });

  test("uses an empty GeoJSON fallback and default color for draft layers", () => {
    const resolved: GisResolveRefsResponse = {
      processed: 0,
      found: 0,
      not_found: 0,
      multiple: 0,
      invalid: 0,
      results: [],
      geojson: null,
    };

    expect(buildDraftOverlayLayer({
      fileName: "senza-estensione",
      layerIndex: 3,
      layerColors: [],
      resolved,
      withGeometry: 0,
    })).toMatchObject({
      layer_key: "draft-3",
      name: "senza-estensione",
      color: "#10B981",
      geojson: { type: "FeatureCollection", features: [] },
      importedItems: [],
    });
  });

  test("rebuilds import stats from saved details with the previous fallback semantics", () => {
    const detail = {
      id: "selection-1",
      name: "Saved",
      color: "#10B981",
      source_filename: null,
      n_particelle: 7,
      n_with_geometry: 4,
      import_summary: null,
      created_at: "2026-08-19T00:00:00Z",
      updated_at: "2026-08-19T00:00:00Z",
      geojson: null,
    } satisfies GisSavedSelectionDetail;

    expect(buildImportStatsFromDetail(detail)).toEqual({
      processed: 7,
      found: 7,
      notFound: 0,
      multiple: 0,
      invalid: 0,
      withGeometry: 4,
    });

    expect(buildImportStatsFromDetail({
      ...detail,
      import_summary: { processed: "10", found: "6", notFound: "2", multiple: "1", invalid: "1" },
    })).toEqual({
      processed: 10,
      found: 6,
      notFound: 2,
      multiple: 1,
      invalid: 1,
      withGeometry: 4,
    });

    expect(buildImportStatsFromDetail({
      ...detail,
      n_particelle: 3,
      n_with_geometry: 2,
      import_summary: {},
    })).toEqual({
      processed: 3,
      found: 3,
      notFound: 0,
      multiple: 0,
      invalid: 0,
      withGeometry: 2,
    });
  });
});
