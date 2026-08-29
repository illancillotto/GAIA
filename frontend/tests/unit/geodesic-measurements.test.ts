import { describe, expect, test } from "vitest";

import {
  formatMeasurement,
  geodesicArea,
  geodesicDistance,
} from "@/components/catasto/gis/geodesic-measurements";

describe("geodesic measurements", () => {
  test("measures the known one-degree equatorial arc", () => {
    expect(geodesicDistance([{ lon: 0, lat: 0 }, { lon: 1, lat: 0 }]))
      .toBeCloseTo(111_195, -1);
    expect(geodesicDistance([{ lon: 0, lat: 0 }])).toBe(0);
  });

  test("measures a one-degree spherical square and degenerate polygons", () => {
    const area = geodesicArea([
      { lon: 0, lat: 0 }, { lon: 1, lat: 0 },
      { lon: 1, lat: 1 }, { lon: 0, lat: 1 },
    ]);
    expect(area).toBeCloseTo(12_363_718_000, -6);
    expect(geodesicArea([{ lon: 0, lat: 0 }, { lon: 1, lat: 0 }])).toBe(0);
  });

  test("formats metric values for field use", () => {
    expect(formatMeasurement(950, "distance")).toBe("950.0 m");
    expect(formatMeasurement(1500, "distance")).toBe("1.50 km");
    expect(formatMeasurement(9000, "area")).toBe("9000.0 m2");
    expect(formatMeasurement(25_000, "area")).toBe("2.50 ha");
  });
});
