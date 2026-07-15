import { describe, expect, test } from "vitest";

import {
  buildClickableLayerIds,
  buildCentroidFeatureCollection,
  buildLayerGeojson,
  buildOverlayFeatureClickPayload,
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
});
