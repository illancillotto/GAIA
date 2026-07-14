import { createPropertyExpression, latest } from "@maplibre/maplibre-gl-style-spec";
import { describe, expect, test } from "vitest";

import {
  buildDeliveryPointFilter,
  buildMeterVisibilityFilter,
  buildOverlayCentroidOpacity,
  buildOverlayFillOpacity,
  buildParticelleFillOpacity,
  buildParticelleFilter,
  buildParticelleOutlineColor,
  shouldShowDeliveryPointLayer,
} from "@/components/catasto/gis/map-filters";

describe("catasto GIS particelle quick filters", () => {
  test("Tutte does not add ruolo filters", () => {
    expect(buildParticelleFilter(null, "all")).toBeNull();
    expect(buildParticelleFilter("12", "all")).toEqual(["==", ["get", "num_distretto"], "12"]);
  });

  test("A ruolo filters only parcels with exact ruolo", () => {
    expect(buildParticelleFilter(null, "ruolo")).toEqual([
      "any",
      ["==", ["get", "ha_ruolo"], true],
      ["==", ["get", "ha_ruolo"], 1],
      ["==", ["get", "ha_ruolo"], "true"],
    ]);
  });

  test("Ruolo inferito filters only inferred ruolo parcels", () => {
    expect(buildParticelleFilter("7", "ruolo_inferito")).toEqual([
      "all",
      ["==", ["get", "num_distretto"], "7"],
      [
        "any",
        ["==", ["get", "ha_ruolo_inferito"], true],
        ["==", ["get", "ha_ruolo_inferito"], 1],
        ["==", ["get", "ha_ruolo_inferito"], "true"],
      ],
    ]);
  });

  test("Delivery points follow the selected district", () => {
    expect(buildDeliveryPointFilter(null)).toBeNull();
    expect(buildDeliveryPointFilter("24")).toEqual(["==", ["get", "distretto_code"], "24"]);
  });

  test("Delivery point meter filters combine district and meter presence", () => {
    expect(buildMeterVisibilityFilter(null, true)).toEqual([
      "any",
      ["==", ["get", "has_meter"], true],
      ["==", ["get", "has_meter"], 1],
      ["==", ["get", "has_meter"], "true"],
    ]);
    expect(buildMeterVisibilityFilter("24", false)).toEqual([
      "all",
      ["==", ["get", "distretto_code"], "24"],
      [
        "any",
        ["==", ["get", "has_meter"], false],
        ["==", ["get", "has_meter"], 0],
        ["==", ["get", "has_meter"], "false"],
      ],
    ]);
  });

  test("Delivery point quick filter toggles the expected layer", () => {
    expect(shouldShowDeliveryPointLayer("all", true)).toBe(true);
    expect(shouldShowDeliveryPointLayer("all", false)).toBe(true);
    expect(shouldShowDeliveryPointLayer("with_meter", true)).toBe(true);
    expect(shouldShowDeliveryPointLayer("with_meter", false)).toBe(false);
    expect(shouldShowDeliveryPointLayer("without_meter", true)).toBe(false);
    expect(shouldShowDeliveryPointLayer("without_meter", false)).toBe(true);
  });

  test("Particelle fill opacity highlights incomplete and filtered parcels", () => {
    expect(buildParticelleFillOpacity(0.5, "all")).toEqual([
      "case",
      [
        "any",
        ["==", ["coalesce", ["to-string", ["get", "codice_catastale"]], ""], ""],
        ["==", ["coalesce", ["to-string", ["get", "foglio"]], ""], ""],
        ["==", ["coalesce", ["to-string", ["get", "particella"]], ""], ""],
      ],
      ["*", 0.22, 0.45],
      0.5,
    ]);
    expect(buildParticelleFillOpacity(0.1, "ruolo")).toEqual([
      "case",
      [
        "any",
        ["==", ["coalesce", ["to-string", ["get", "codice_catastale"]], ""], ""],
        ["==", ["coalesce", ["to-string", ["get", "foglio"]], ""], ""],
        ["==", ["coalesce", ["to-string", ["get", "particella"]], ""], ""],
      ],
      ["*", 0.1, 0.45],
      [
        "any",
        ["==", ["get", "ha_ruolo"], true],
        ["==", ["get", "ha_ruolo"], 1],
        ["==", ["get", "ha_ruolo"], "true"],
      ],
      0.1,
      0.05,
    ]);
    expect(buildParticelleFillOpacity(0.3, "ruolo_inferito")).toContain(0.05);
  });

  test("Overlay opacities fade with zoom using pre-multiplied stops", () => {
    expect(buildOverlayFillOpacity(0.7)).toEqual([
      "interpolate",
      ["linear"],
      ["zoom"],
      8,
      0.7,
      11,
      0.7 * 0.75,
      14,
      0.7 * 0.5,
    ]);
    expect(buildOverlayCentroidOpacity(0.7)).toEqual([
      "interpolate",
      ["linear"],
      ["zoom"],
      7,
      0.7,
      12,
      0.7 * 0.85,
      16,
      0,
    ]);
  });

  test("Overlay opacities are valid MapLibre paint expressions", () => {
    // Regression: a nested ["*", opacity, ["interpolate", ..., ["zoom"], ...]] is rejected
    // by MapLibre and makes addLayer fail silently, leaving overlay fills invisible.
    const fill = createPropertyExpression(buildOverlayFillOpacity(0.7), latest.paint_fill["fill-opacity"]);
    expect(fill.result).toBe("success");
    const centroid = createPropertyExpression(buildOverlayCentroidOpacity(0.7), latest.paint_circle["circle-opacity"]);
    expect(centroid.result).toBe("success");
  });

  test("Particelle outline color adapts to basemap", () => {
    expect(buildParticelleOutlineColor("osm")).toEqual([
      "case",
      [
        "any",
        ["==", ["coalesce", ["to-string", ["get", "codice_catastale"]], ""], ""],
        ["==", ["coalesce", ["to-string", ["get", "foglio"]], ""], ""],
        ["==", ["coalesce", ["to-string", ["get", "particella"]], ""], ""],
      ],
      "#C4008E",
      "#4F46E5",
    ]);
    expect(buildParticelleOutlineColor("satellite")).toContain("#FACC15");
    expect(buildParticelleOutlineColor("google_satellite")).toContain("#EAB308");
    expect(buildParticelleOutlineColor(null)).toContain("#4F46E5");
  });
});
