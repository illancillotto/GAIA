import { describe, expect, test } from "vitest";

import {
  deliveryPointResults,
  districtResults,
  geometryBbox,
  isInGaiaComprensorio,
  municipalityResults,
  parcelResults,
} from "@/components/catasto/gis/territorio-unified-search";

describe("territorio unified search helpers", () => {
  test("computes bboxes for geometries and rejects missing coordinates", () => {
    expect(geometryBbox({ type: "Polygon", coordinates: [[[8.5, 39.8], [8.7, 40], [8.5, 39.8]]] })).toEqual([8.5, 39.8, 8.7, 40]);
    expect(geometryBbox({ type: "GeometryCollection", geometries: [
      { type: "Point", coordinates: [8.6, 39.9] },
      { type: "Point", coordinates: [8.8, 40.1] },
    ] })).toEqual([8.6, 39.9, 8.8, 40.1]);
    expect(geometryBbox({ type: "GeometryCollection", geometries: [] })).toBeNull();
    expect(geometryBbox(null)).toBeNull();
    expect(geometryBbox({ type: "LineString", coordinates: [] })).toBeNull();
    expect(geometryBbox({ type: "LineString", coordinates: [null] as never })).toBeNull();
  });

  test("maps parcels and verifies comprensorio bounds", () => {
    const response = {
      results: [
        { id: "p1", nome_comune: "Arborea", codice_catastale: "A357", foglio: "14", particella: "82", utenza_denominazione: "Azienda" },
        { id: "p2", codice_catastale: "H501", foglio: null, particella: null, utenza_cf: "RSS" },
        { id: "p3" },
      ],
      geojson: { type: "FeatureCollection", features: [
        { type: "Feature", properties: { id: "p1" }, geometry: { type: "Point", coordinates: [8.6, 39.9] } },
        { type: "Feature", properties: null, geometry: { type: "Point", coordinates: [8.6, 39.9] } },
      ] },
    } as never;
    const results = parcelResults(response);
    expect(results.map((item) => item.source)).toEqual(["GAIA Catasto", "GAIA Catasto", "GAIA Catasto"]);
    expect(results[0]).toMatchObject({ label: "Arborea - Fg. 14, Part. 82", detail: "Azienda" });
    expect(results[1].detail).toBe("RSS");
    expect(results[2].detail).toBe("Particella catastale GAIA");
    expect(isInGaiaComprensorio(results[0])).toBe(true);
    expect(isInGaiaComprensorio({ ...results[0], bbox: undefined, center: [12.5, 41.9] })).toBe(false);
    expect(isInGaiaComprensorio({ ...results[0], bbox: undefined })).toBe(false);
    for (const bbox of [[7, 39.8, 8, 39.9], [9, 39.8, 10, 39.9], [8.5, 38, 8.6, 39], [8.5, 41, 8.6, 42]] as const) {
      expect(isInGaiaComprensorio({ ...results[0], bbox: [...bbox] })).toBe(false);
    }
    expect(parcelResults({ results: [{ id: "p4" }] } as never)[0].feature).toBeUndefined();
  });

  test("filters districts, municipalities and delivery points with source badges", () => {
    const districts = districtResults([
      { id: "d1", num_distretto: "12", nome_distretto: "Arborea" },
      { id: "d2", num_distretto: "4", nome_distretto: null },
    ] as never, "arbo");
    expect(districts[0]).toMatchObject({ kind: "distretto", source: "GAIA Distretti" });
    expect(districtResults([{ id: "d2", num_distretto: "4", nome_distretto: null }] as never, "4")[0].detail).toBe("Distretto irriguo GAIA");

    const municipalities = municipalityResults({ type: "FeatureCollection", features: [
      { type: "Feature", id: "c1", properties: { NOME_COMUNE: "Arborea" }, geometry: { type: "Polygon", coordinates: [[[8.5, 39.8], [8.7, 39.8], [8.5, 39.8]]] } },
      { type: "Feature", properties: { nome: "Oristano" }, geometry: null },
      { type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [8.6, 39.9] } },
    ] }, "arb");
    expect(municipalities[0]).toMatchObject({ label: "Arborea", source: "RAS SITR" });
    expect(municipalityResults({ type: "FeatureCollection", features: [
      { type: "Feature", properties: { nome: "Oristano" }, geometry: null },
      { type: "Feature", properties: null, geometry: { type: "Point", coordinates: [8.6, 39.9] } },
      { type: "Feature", properties: { nome: null, name: "  " }, geometry: { type: "Point", coordinates: [8.6, 39.9] } },
    ] }, "ori")).toEqual([]);

    const feature = { type: "Feature", id: "fallback", properties: { id: "dp1", punto_consegna_code: "PDC-10", distretto_code: "12" }, geometry: { type: "Point", coordinates: [8.6, 39.9] } } as GeoJSON.Feature;
    expect(deliveryPointResults([feature, feature], "pdc")).toEqual([
      expect.objectContaining({ label: "PdC PDC-10", detail: "Distretto 12", source: "GAIA PdC" }),
    ]);
    expect(deliveryPointResults([{ ...feature, properties: { id: "dp2", punto_consegna: "A1" } }], "a1")[0].detail).toBe("Punto di consegna GAIA");
    expect(deliveryPointResults([{ ...feature, id: "dp3", properties: { code: "B1" } }], "b1")[0].id).toBe("pdc:dp3");
    expect(deliveryPointResults([{ ...feature, properties: {} }], "x")).toEqual([]);
    expect(deliveryPointResults([{ ...feature, id: undefined, properties: {} }], "x")).toEqual([]);
  });
});
