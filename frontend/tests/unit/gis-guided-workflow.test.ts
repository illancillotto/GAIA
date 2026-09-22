import { describe, expect, test } from "vitest";

import {
  buildGuidedChangeInput,
  coordinatesTextFromGeometry,
  emptyGuidedChangeDraft,
  geometryFromCoordinates,
  guidedChangeValidation,
  guidedDraftFromChangeRequest,
  parseGuidedValue,
  readableValue,
  type GuidedChangeDraft,
} from "@/app/gis/catalogo/guided-workflow";
import type {
  GisCatalogChangeRequest,
  GisCatalogLayer,
  GisCatalogLayerFeature,
} from "@/types/gis";

const layer = {
  id: "layer-1",
  workspace: "rete",
  name: "condotte",
  title: "Condotte",
  domain_module: "network",
  source_type: "postgis",
  official_source: "network",
  geometry_type: "LINESTRING",
  feature_id_column: "id",
  metadata: {},
  is_active: true,
  effective_access_level: "editor",
  can_view: true,
  can_annotate: true,
  can_edit: true,
  can_approve: false,
  can_manage: false,
  created_at: "2026-08-25T08:00:00Z",
  updated_at: "2026-08-25T08:00:00Z",
} satisfies GisCatalogLayer;

const feature: GisCatalogLayerFeature = {
  feature_id: "pipe-1",
  label: "pipe-1 - Condotta 1",
  attributes: { id: "pipe-1", diameter: 120, active: true, note: null },
  geometry: {
    type: "LineString",
    coordinates: [
      [8.4, 39.9],
      [8.5, 40],
    ],
  },
};

function draft(overrides: Partial<GuidedChangeDraft> = {}): GuidedChangeDraft {
  return { ...emptyGuidedChangeDraft, ...overrides };
}

function request(
  overrides: Partial<GisCatalogChangeRequest> = {},
): GisCatalogChangeRequest {
  return {
    id: "change-1",
    layer_id: layer.id,
    feature_id: "pipe-1",
    change_type: "attribute_update",
    status: "submitted",
    payload: { before: { diameter: 120 }, after: { diameter: 160 } },
    justification: "Rilievo",
    requested_by_user_id: 1,
    reviewed_by_user_id: null,
    review_notes: null,
    reviewed_at: null,
    created_at: "2026-08-25T08:00:00Z",
    updated_at: "2026-08-25T08:00:00Z",
    ...overrides,
  };
}

describe("guided GIS workflow helpers", () => {
  test.each(["Polygon", "MultiLineString", "POLYGON", "multilinestring"])(
    "formats only the first coordinate group for %s without mutating it",
    (type) => {
      const coordinates = [[[1, 2], [3, 4]], [[9, 10], [11, 12]]];
      const geometry = { type, coordinates };
      const snapshot = structuredClone(geometry);
      expect(coordinatesTextFromGeometry(geometry)).toBe("1, 2\n3, 4");
      expect(geometry).toEqual(snapshot);
      expect(coordinatesTextFromGeometry({ type, coordinates: [null, coordinates[1]] })).toBe("");
      expect(coordinatesTextFromGeometry({ type, coordinates: [[], coordinates[1]] })).toBe("");
      expect(coordinatesTextFromGeometry({ type, coordinates: [] })).toBe("");
    },
  );

  test.each(["POLYGON", "MULTIPOLYGON"])("closes %s rings differing only in Y without duplicating closed rings", (geometryType) => {
    const selectedLayer = { ...layer, geometry_type: geometryType };
    const expectedRing = [[1, 2], [3, 4], [1, 6], [1, 2]];
    const coordinates = geometryType === "POLYGON" ? [expectedRing] : [[expectedRing]];
    expect(geometryFromCoordinates("1,2\n3,4\n1,6", selectedLayer)).toEqual({
      type: geometryType === "POLYGON" ? "Polygon" : "MultiPolygon", coordinates,
    });
    expect(geometryFromCoordinates("1,2\n3,4\n1,6\n1,2", selectedLayer)?.coordinates).toEqual(coordinates);
  });

  test("formats supported and malformed geometries as coordinate rows", () => {
    expect(
      coordinatesTextFromGeometry({ type: "Point", coordinates: [8.4, 39.9] }),
    ).toBe("8.4, 39.9");
    expect(
      coordinatesTextFromGeometry({
        type: "LineString",
        coordinates: [
          [1, 2],
          [3, 4],
        ],
      }),
    ).toBe("1, 2\n3, 4");
    expect(
      coordinatesTextFromGeometry({
        type: "Polygon",
        coordinates: [
          [
            [1, 2],
            [3, 4],
          ],
        ],
      }),
    ).toBe("1, 2\n3, 4");
    expect(
      coordinatesTextFromGeometry({
        type: "MultiLineString",
        coordinates: [
          [
            [1, 2],
            [3, 4],
          ],
        ],
      }),
    ).toBe("1, 2\n3, 4");
    expect(
      coordinatesTextFromGeometry({
        type: "MultiPolygon",
        coordinates: [
          [
            [
              [1, 2],
              [3, 4],
            ],
          ],
        ],
      }),
    ).toBe("1, 2\n3, 4");
    expect(
      coordinatesTextFromGeometry({ type: "Unknown", coordinates: [[1, 2]] }),
    ).toBe("");
    expect(
      coordinatesTextFromGeometry({ type: "Point", coordinates: null }),
    ).toBe("");
    expect(coordinatesTextFromGeometry(null)).toBe("");
    expect(
      coordinatesTextFromGeometry({ type: "Point", coordinates: [8.4] }),
    ).toBe("8.4, ");
    expect(
      coordinatesTextFromGeometry({ type: "Point", coordinates: [] }),
    ).toBe(", ");
    expect(
      coordinatesTextFromGeometry({ type: "Polygon", coordinates: [] }),
    ).toBe("");
    expect(
      coordinatesTextFromGeometry({ type: "MultiLineString", coordinates: [] }),
    ).toBe("");
    expect(
      coordinatesTextFromGeometry({ type: "MultiPolygon", coordinates: [] }),
    ).toBe("");
  });

  test("builds point, line and polygon geometries without JSON input", () => {
    expect(
      geometryFromCoordinates("", { ...layer, geometry_type: null }),
    ).toBeNull();
    expect(geometryFromCoordinates("x, 2", layer)).toBeNull();
    expect(geometryFromCoordinates("1, 2, 3", layer)).toBeNull();
    expect(
      geometryFromCoordinates("1, 2\n3, 4", {
        ...layer,
        geometry_type: "POINT",
      }),
    ).toBeNull();
    expect(
      geometryFromCoordinates("1, 2", { ...layer, geometry_type: null }),
    ).toEqual({ type: "Point", coordinates: [1, 2] });
    expect(
      geometryFromCoordinates("1, 2", {
        ...layer,
        geometry_type: "MULTIPOINT",
      }),
    ).toEqual({ type: "MultiPoint", coordinates: [[1, 2]] });
    expect(geometryFromCoordinates("1, 2", layer)).toBeNull();
    expect(geometryFromCoordinates("1;2\n3 4", layer)).toEqual({
      type: "LineString",
      coordinates: [
        [1, 2],
        [3, 4],
      ],
    });
    expect(
      geometryFromCoordinates("1,2\n3,4", {
        ...layer,
        geometry_type: "MULTILINESTRING",
      }),
    ).toEqual({
      type: "MultiLineString",
      coordinates: [
        [
          [1, 2],
          [3, 4],
        ],
      ],
    });
    expect(
      geometryFromCoordinates("1,2\n3,4", {
        ...layer,
        geometry_type: "POLYGON",
      }),
    ).toBeNull();
    expect(
      geometryFromCoordinates("1,2\n3,4\n5,6", {
        ...layer,
        geometry_type: "POLYGON",
      }),
    ).toEqual({
      type: "Polygon",
      coordinates: [
        [
          [1, 2],
          [3, 4],
          [5, 6],
          [1, 2],
        ],
      ],
    });
    expect(
      geometryFromCoordinates("1,2\n3,4\n1,2", {
        ...layer,
        geometry_type: "POLYGON",
      }),
    ).toEqual({
      type: "Polygon",
      coordinates: [
        [
          [1, 2],
          [3, 4],
          [1, 2],
        ],
      ],
    });
    expect(
      geometryFromCoordinates("1,2\n3,4\n5,6", {
        ...layer,
        geometry_type: "MULTIPOLYGON",
      }),
    ).toEqual({
      type: "MultiPolygon",
      coordinates: [
        [
          [
            [1, 2],
            [3, 4],
            [5, 6],
            [1, 2],
          ],
        ],
      ],
    });
    expect(
      geometryFromCoordinates("1,2\n3,4", layer, {
        ...feature,
        geometry: { type: "MultiLineString", coordinates: [] },
      }),
    ).toEqual({
      type: "MultiLineString",
      coordinates: [
        [
          [1, 2],
          [3, 4],
        ],
      ],
    });
  });

  test("preserves primitive types when users enter guided values", () => {
    expect(parseGuidedValue(" 42 ", 1)).toBe(42);
    expect(parseGuidedValue("abc", 1)).toBe("abc");
    expect(parseGuidedValue("si", false)).toBe(true);
    expect(parseGuidedValue("TRUE", false)).toBe(true);
    expect(parseGuidedValue("1", false)).toBe(true);
    expect(parseGuidedValue("no", true)).toBe(false);
    expect(parseGuidedValue("FALSE", true)).toBe(false);
    expect(parseGuidedValue("0", true)).toBe(false);
    expect(parseGuidedValue("forse", true)).toBe("forse");
    expect(parseGuidedValue(" testo ")).toBe("testo");
  });

  test("derives editable drafts from each existing request shape", () => {
    expect(guidedDraftFromChangeRequest()).toBe(emptyGuidedChangeDraft);
    expect(guidedDraftFromChangeRequest(request())).toMatchObject({
      fieldName: "diameter",
      newValue: "160",
      featureId: "pipe-1",
    });
    expect(
      guidedDraftFromChangeRequest(
        request({ feature_id: null, justification: null, payload: {} }),
      ),
    ).toMatchObject({
      featureId: "",
      fieldName: "",
      newValue: "",
      justification: "",
    });
    expect(
      guidedDraftFromChangeRequest(
        request({
          change_type: "feature_create",
          payload: {
            properties: { name: "Nuova" },
            geometry: { type: "Point", coordinates: [8.4, 39.9] },
          },
        }),
      ),
    ).toMatchObject({
      propertyName: "name",
      propertyValue: "Nuova",
      coordinates: "8.4, 39.9",
    });
    expect(
      guidedDraftFromChangeRequest(
        request({
          change_type: "feature_create",
          payload: { properties: { name: null } },
        }),
      ),
    ).toMatchObject({ propertyValue: "" });
  });

  test("reports each guided validation problem and accepts complete drafts", () => {
    expect(guidedChangeValidation(draft(), layer)).toMatch(/Seleziona/);
    expect(
      guidedChangeValidation(draft({ featureId: "pipe-1" }), layer),
    ).toMatch(/motivo/);
    expect(
      guidedChangeValidation(
        draft({ featureId: "pipe-1", justification: "Rilievo" }),
        layer,
      ),
    ).toMatch(/campo/);
    expect(
      guidedChangeValidation(
        draft({ changeType: "feature_create", justification: "Rilievo" }),
        layer,
      ),
    ).toMatch(/dato descrittivo/);
    expect(
      guidedChangeValidation(
        draft({
          changeType: "geometry_update",
          featureId: "pipe-1",
          justification: "Rilievo",
          coordinates: "errate",
        }),
        layer,
      ),
    ).toMatch(/coordinate valide/);
    expect(
      guidedChangeValidation(
        draft({
          featureId: "pipe-1",
          fieldName: "diameter",
          newValue: "160",
          justification: "Rilievo",
        }),
        layer,
        feature,
      ),
    ).toBeNull();
    expect(
      guidedChangeValidation(
        draft({
          changeType: "feature_create",
          propertyName: "name",
          propertyValue: "Nuova",
          coordinates: "8.4,39.9",
          justification: "Rilievo",
        }),
        { ...layer, geometry_type: "POINT" },
      ),
    ).toBeNull();
  });

  test.each([
    ["attribute_update", "Seleziona l'elemento della mappa da correggere."],
    ["geometry_update", "Seleziona l'elemento della mappa da correggere."],
    ["feature_delete", "Seleziona l'elemento della mappa da correggere."],
    ["feature_create", "Spiega il motivo della richiesta prima di continuare."],
  ] as const)("preserves the first missing requirement for %s", (changeType, expected) => {
    expect(guidedChangeValidation(draft({ changeType }), layer)).toBe(expected);
    expect(guidedChangeValidation(draft({ changeType, featureId: "pipe-1" }), layer))
      .toBe("Spiega il motivo della richiesta prima di continuare.");
  });

  test.each([
    { fieldName: "", newValue: "160" },
    { fieldName: "diameter", newValue: " \t " },
  ])("requires both attribute fields: %j", (fields) => {
    expect(guidedChangeValidation(draft({ featureId: "pipe-1", justification: "Rilievo", ...fields }), layer))
      .toBe("Scegli il campo e inserisci il nuovo valore.");
  });

  test.each([
    { propertyName: " \t ", propertyValue: "Nuova" },
    { propertyName: "name", propertyValue: " \t " },
  ])("checks descriptive data before coordinates: %j", (properties) => {
    const values = draft({ changeType: "feature_create", justification: "Rilievo", coordinates: "invalid", ...properties });
    expect(guidedChangeValidation(values, layer))
      .toBe("Inserisci almeno un dato descrittivo per il nuovo elemento.");
    expect(guidedChangeValidation({ ...values, propertyName: "name", propertyValue: "Nuova" }, layer))
      .toBe("Inserisci coordinate valide, una coppia X e Y per riga.");
  });

  test("does not validate geometry for attribute updates or deletions", () => {
    const values = draft({ featureId: "pipe-1", justification: "Rilievo", fieldName: " ", newValue: "0", coordinates: "invalid" });
    expect(guidedChangeValidation(values, layer)).toBeNull();
    expect(guidedChangeValidation({ ...values, changeType: "feature_delete", fieldName: "", newValue: "" }, layer)).toBeNull();
  });

  test("validates coordinates using the selected feature before the layer type", () => {
    const values = draft({ changeType: "geometry_update", featureId: "pipe-1", justification: "Rilievo", coordinates: "1,2" });
    expect(guidedChangeValidation(values, layer))
      .toBe("Inserisci coordinate valide, una coppia X e Y per riga.");
    expect(guidedChangeValidation(values, layer, { ...feature, geometry: { type: "Point", coordinates: [1, 2] } })).toBeNull();
  });

  test("builds API inputs for all correction types", () => {
    expect(
      buildGuidedChangeInput(
        draft({
          featureId: "pipe-1",
          fieldName: "diameter",
          newValue: "160",
          justification: " Rilievo ",
        }),
        layer,
        feature,
      ),
    ).toEqual({
      featureId: "pipe-1",
      changeType: "attribute_update",
      payload: { before: { diameter: 120 }, after: { diameter: 160 } },
      justification: "Rilievo",
    });
    expect(
      buildGuidedChangeInput(
        draft({
          featureId: "pipe-1",
          fieldName: "diameter",
          newValue: "180",
          justification: "Rilievo",
        }),
        layer,
        null,
        request(),
      ),
    ).toMatchObject({
      payload: { before: { diameter: 120 }, after: { diameter: 180 } },
    });
    expect(
      buildGuidedChangeInput(
        draft({
          changeType: "geometry_update",
          featureId: "pipe-1",
          coordinates: "1,2\n3,4",
          justification: "Rilievo",
        }),
        layer,
        feature,
      ),
    ).toMatchObject({
      payload: {
        geometry: {
          type: "LineString",
          coordinates: [
            [1, 2],
            [3, 4],
          ],
        },
      },
    });
    expect(
      buildGuidedChangeInput(
        draft({
          changeType: "feature_create",
          propertyName: "name",
          propertyValue: " Nuova ",
          coordinates: "8.4,39.9",
          justification: "Inserimento",
        }),
        { ...layer, geometry_type: "POINT" },
      ),
    ).toEqual({
      featureId: undefined,
      changeType: "feature_create",
      payload: {
        properties: { name: "Nuova" },
        geometry: { type: "Point", coordinates: [8.4, 39.9] },
      },
      justification: "Inserimento",
    });
    expect(
      buildGuidedChangeInput(
        draft({
          changeType: "feature_delete",
          featureId: "pipe-1",
          justification: "Doppione",
        }),
        layer,
        feature,
      ),
    ).toMatchObject({
      featureId: "pipe-1",
      payload: { before: feature.attributes },
    });
  });

  test("renders readable summaries for empty, structured and primitive values", () => {
    expect(readableValue(null)).toBe("non valorizzato");
    expect(readableValue("")).toBe("non valorizzato");
    expect(readableValue({ active: true })).toBe('{"active":true}');
    expect(readableValue(false)).toBe("false");
  });
});
