import { afterEach, describe, expect, test, vi } from "vitest";

import {
  buildClickableLayerIds,
  buildCentroidFeatureCollection,
  buildLayerGeojson,
  buildOverlayFeatureClickPayload,
  ensureGoogleSatelliteLayer,
  ensureGoogleSatelliteLayerWithKey,
} from "@/components/catasto/gis/MapContainer";
import type { GisMapOverlayLayer } from "@/types/gis";

function overlayLayer(geojson: GeoJSON.FeatureCollection): GisMapOverlayLayer {
  return {
    layer_key: "whitecompany-reports",
    name: "Segnalazioni WhiteCompany",
    color: "#E11D48",
    outlineColor: "#7F1D1D",
    featureClickMode: "overlay",
    visible: true,
    geojson,
  };
}

describe("Catasto GIS map overlay helpers", () => {
  afterEach(() => vi.restoreAllMocks());

  test("returns no centroids for an absent collection", () => {
    expect(buildCentroidFeatureCollection(null)).toEqual({
      type: "FeatureCollection",
      features: [],
    });
  });

  test("keeps point overlays as centroid features", () => {
    const collection = buildCentroidFeatureCollection({
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: { type: "Point", coordinates: [8.6, 39.9] },
          properties: { id: "report-1" },
        },
      ],
    });

    expect(collection.features).toEqual([
      {
        type: "Feature",
        geometry: { type: "Point", coordinates: [8.6, 39.9] },
        properties: { id: "report-1" },
      },
    ]);
  });

  test("expands multipoint overlays to clickable centroid features", () => {
    const collection = buildCentroidFeatureCollection({
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: { type: "MultiPoint", coordinates: [[8.6, 39.9], [8.7, 40]] },
          properties: { id: "group-1" },
        },
      ],
    });

    expect(collection.features).toHaveLength(2);
    expect(collection.features[0]).toMatchObject({
      geometry: { type: "Point", coordinates: [8.6, 39.9] },
      properties: { id: "group-1" },
    });
    expect(collection.features[1]).toMatchObject({
      geometry: { type: "Point", coordinates: [8.7, 40] },
      properties: { id: "group-1" },
    });
  });

  test("centers polygon and multipolygon overlays and skips unsupported geometry", () => {
    const collection = buildCentroidFeatureCollection({
      type: "FeatureCollection",
      features: [
        { type: "Feature", properties: null, geometry: null },
        {
          type: "Feature",
          properties: null,
          geometry: { type: "Polygon", coordinates: [[[8, 39], [10, 39], [10, 41], [8, 39]]] },
        },
        {
          type: "Feature",
          properties: { id: "multi" },
          geometry: {
            type: "MultiPolygon",
            coordinates: [
              [[[8, 39], [9, 39], [9, 40], [8, 39]]],
              [[[10, 41], [11, 41], [11, 42], [10, 41]]],
            ],
          },
        },
        {
          type: "Feature",
          properties: {},
          geometry: { type: "LineString", coordinates: [] },
        },
      ],
    });

    expect(collection.features).toHaveLength(2);
    expect(collection.features[0].geometry).toEqual({ type: "Point", coordinates: [9, 40] });
    expect(collection.features[1].geometry).toEqual({ type: "Point", coordinates: [9.5, 40.5] });
  });

  test("uses empty properties for point and multipoint features without metadata", () => {
    const collection = buildCentroidFeatureCollection({
      type: "FeatureCollection",
      features: [
        { type: "Feature", properties: null, geometry: { type: "Point", coordinates: [8, 39] } },
        { type: "Feature", properties: null, geometry: { type: "MultiPoint", coordinates: [[9, 40]] } },
      ],
    });
    expect(collection.features.map((feature) => feature.properties)).toEqual([{}, {}]);
  });

  test("adds overlay click metadata for WhiteCompany report features", () => {
    const layer = buildLayerGeojson(
      overlayLayer({
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            geometry: { type: "Point", coordinates: [8.6, 39.9] },
            properties: { id: "report-1", report_number: "REP-WHITE-1" },
          },
        ],
      }),
    );

    expect(layer.features[0].properties).toEqual(
      expect.objectContaining({
        id: "report-1",
        report_number: "REP-WHITE-1",
        __overlayLayerKey: "whitecompany-reports",
        __overlayName: "Segnalazioni WhiteCompany",
        __overlayColor: "#E11D48",
        __overlayOutlineColor: "#7F1D1D",
        __overlayFeatureClickMode: "overlay",
      }),
    );
  });

  test("builds empty layers and default overlay metadata", () => {
    const empty = buildLayerGeojson({
      ...overlayLayer({ type: "FeatureCollection", features: [] }),
      geojson: null,
    });
    expect(empty.features).toEqual([]);

    const defaults = buildLayerGeojson({
      ...overlayLayer({
        type: "FeatureCollection",
        features: [{ type: "Feature", properties: null, geometry: { type: "Point", coordinates: [8, 39] } }],
      }),
      outlineColor: undefined,
      featureClickMode: undefined,
    });
    expect(defaults.features[0].properties).toMatchObject({
      __overlayOutlineColor: "#E11D48",
      __overlayPulse: false,
      __overlayPulseUntil: null,
      __overlayFeatureClickMode: null,
      __overlaySavedSelectionId: null,
    });
  });

  test("builds overlay click payload without treating the id as a particella id", () => {
    const payload = buildOverlayFeatureClickPayload({
      geometry: { type: "Point", coordinates: [8.6, 39.9] },
      properties: {
        id: "report-1",
        __overlayLayerKey: "whitecompany-reports",
        __overlayName: "Segnalazioni WhiteCompany",
      },
    });

    expect(payload).toEqual({
      layer_key: "whitecompany-reports",
      layer_name: "Segnalazioni WhiteCompany",
      properties: {
        id: "report-1",
        __overlayLayerKey: "whitecompany-reports",
        __overlayName: "Segnalazioni WhiteCompany",
      },
      geometry: { type: "Point", coordinates: [8.6, 39.9] },
    });
    expect(buildOverlayFeatureClickPayload({ properties: { id: "report-1" } })).toBeNull();
    expect(buildOverlayFeatureClickPayload({})).toBeNull();
    expect(buildOverlayFeatureClickPayload({ properties: { __overlayLayerKey: "  " } })).toBeNull();
    expect(buildOverlayFeatureClickPayload({
      properties: { __overlayLayerKey: 12, __overlayName: 42 },
    })).toEqual({
      layer_key: "12",
      layer_name: null,
      properties: { __overlayLayerKey: 12, __overlayName: 42 },
      geometry: null,
    });
  });

  test("includes overlay fill and point centroid layers in the clickable layer list", () => {
    const available = new Set([
      "overlay-whitecompany-reports-fill",
      "overlay-whitecompany-reports-centroid",
      "delivery-points-with-meter",
      "particelle-hitbox",
    ]);

    expect(buildClickableLayerIds(["whitecompany-reports"], (layerId) => available.has(layerId))).toEqual([
      "overlay-whitecompany-reports-fill",
      "overlay-whitecompany-reports-centroid",
      "delivery-points-with-meter",
      "particelle-hitbox",
    ]);
  });

  test("creates and reuses Google satellite layers only with a valid session", async () => {
    const addSource = vi.fn();
    const addLayer = vi.fn();
    const getLayer = vi.fn((id: string) => id === "google-satellite-tiles" ? { id } : null);
    const map = { getLayer, getSource: vi.fn(), addSource, addLayer } as never;
    expect(await ensureGoogleSatelliteLayer(map)).toBe(true);
    expect(await ensureGoogleSatelliteLayerWithKey(map, "key")).toBe(true);
    expect(addLayer).not.toHaveBeenCalled();

    getLayer.mockReturnValue(null);
    expect(await ensureGoogleSatelliteLayerWithKey(map, "")).toBe(false);

    const fetchMock = vi.spyOn(globalThis, "fetch");
    fetchMock.mockResolvedValueOnce({ ok: false } as Response);
    expect(await ensureGoogleSatelliteLayerWithKey(map, "key")).toBe(false);

    fetchMock.mockResolvedValueOnce({ ok: true, json: async () => ({}) } as Response);
    expect(await ensureGoogleSatelliteLayerWithKey(map, "key")).toBe(false);

    fetchMock.mockResolvedValueOnce({ ok: true, json: async () => ({ session: "session 1" }) } as Response);
    expect(await ensureGoogleSatelliteLayerWithKey(map, "key value")).toBe(true);
    expect(addSource).toHaveBeenCalledWith("google-satellite", expect.objectContaining({
      tiles: [expect.stringContaining("session=session%201&key=key%20value")],
    }));
    expect(addLayer).toHaveBeenLastCalledWith(
      expect.objectContaining({ id: "google-satellite-tiles" }),
      undefined,
    );

    (map as { getSource: ReturnType<typeof vi.fn> }).getSource.mockReturnValue({});
    getLayer.mockImplementation((id: string) => id === "distretti-fill" ? { id } : null);
    fetchMock.mockResolvedValueOnce({ ok: true, json: async () => ({ session: "session-2" }) } as Response);
    expect(await ensureGoogleSatelliteLayerWithKey(map, "key")).toBe(true);
    expect(addLayer).toHaveBeenLastCalledWith(
      expect.objectContaining({ id: "google-satellite-tiles" }),
      "distretti-fill",
    );
  });
});
