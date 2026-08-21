import { describe, expect, test } from "vitest";

import {
  buildCatastoGisCoordinateFeatureCollection,
  buildCatastoGisCoordinateHref,
  formatCatastoGisCoordinateLabel,
  parseCatastoGisCoordinateSearch,
} from "@/lib/catasto-gis-coordinate-search";

describe("catasto GIS coordinate search helpers", () => {
  test("parses decimal latitude and longitude with dot separator", () => {
    expect(parseCatastoGisCoordinateSearch("39.9042, 8.5917")).toEqual({
      lat: 39.9042,
      lon: 8.5917,
      source: "decimal",
    });
  });

  test("parses decimal latitude and longitude with Italian decimal commas", () => {
    expect(parseCatastoGisCoordinateSearch("39,9042 8,5917")).toEqual({
      lat: 39.9042,
      lon: 8.5917,
      source: "decimal",
    });
  });

  test("parses decimal latitude and longitude with alternate separators", () => {
    expect(parseCatastoGisCoordinateSearch("39,9042; 8,5917")).toEqual({
      lat: 39.9042,
      lon: 8.5917,
      source: "decimal",
    });
    expect(parseCatastoGisCoordinateSearch("(39.9042 / 8.5917)")).toEqual({
      lat: 39.9042,
      lon: 8.5917,
      source: "decimal",
    });
  });

  test("parses DMS coordinates with trailing directions", () => {
    const parsed = parseCatastoGisCoordinateSearch(`39°54'15"N 8°35'30"E`);

    expect(parsed?.source).toBe("dms");
    expect(parsed?.lat).toBeCloseTo(39.904167, 6);
    expect(parsed?.lon).toBeCloseTo(8.591667, 6);
  });

  test("parses DMS coordinates with leading directions", () => {
    const parsed = parseCatastoGisCoordinateSearch("N 39 54 15 E 8 35 30");

    expect(parsed?.source).toBe("dms");
    expect(parsed?.lat).toBeCloseTo(39.904167, 6);
    expect(parsed?.lon).toBeCloseTo(8.591667, 6);
  });

  test("parses signed DMS coordinates without directions", () => {
    const parsed = parseCatastoGisCoordinateSearch(`39°54'15" 8°35'30"`);

    expect(parsed?.source).toBe("dms");
    expect(parsed?.lat).toBeCloseTo(39.904167, 6);
    expect(parsed?.lon).toBeCloseTo(8.591667, 6);
  });

  test("parses negative signed DMS coordinates without directions", () => {
    expect(parseCatastoGisCoordinateSearch("-39° -8°")).toEqual({
      lat: -39,
      lon: -8,
      source: "dms",
    });
  });

  test("parses DMS coordinates with omitted minutes and seconds", () => {
    expect(parseCatastoGisCoordinateSearch("39°N 8°E")).toEqual({
      lat: 39,
      lon: 8,
      source: "dms",
    });
  });

  test("applies south and west negative directions", () => {
    const parsed = parseCatastoGisCoordinateSearch(`39°54'15"S 8°35'30"W`);

    expect(parsed?.source).toBe("dms");
    expect(parsed?.lat).toBeCloseTo(-39.904167, 6);
    expect(parsed?.lon).toBeCloseTo(-8.591667, 6);
  });

  test("rejects out of range coordinates and malformed DMS", () => {
    expect(parseCatastoGisCoordinateSearch("")).toBeNull();
    expect(parseCatastoGisCoordinateSearch(" , ; / ")).toBeNull();
    expect(parseCatastoGisCoordinateSearch("91, 8")).toBeNull();
    expect(parseCatastoGisCoordinateSearch("39, 181")).toBeNull();
    expect(parseCatastoGisCoordinateSearch("39°61'00\"N 8°35'30\"E")).toBeNull();
    expect(parseCatastoGisCoordinateSearch("39°54'60\"N 8°35'30\"E")).toBeNull();
    expect(parseCatastoGisCoordinateSearch(`39°61'00" 8°35'30"`)).toBeNull();
    expect(parseCatastoGisCoordinateSearch("39°N 8°N")).toBeNull();
    expect(parseCatastoGisCoordinateSearch("foglio 1 particella 2")).toBeNull();
  });

  test("builds encoded Catasto GIS href from valid coordinates", () => {
    expect(buildCatastoGisCoordinateHref("39,9042 8,5917")).toBe("/catasto/gis/coordinate?coordinate=39.904200%2C+8.591700");
    expect(buildCatastoGisCoordinateHref("not coordinates")).toBeNull();
  });

  test("formats labels and waypoint GeoJSON in longitude latitude order", () => {
    const coordinate = { lat: 39.9042, lon: 8.5917, source: "decimal" as const };

    expect(formatCatastoGisCoordinateLabel(coordinate)).toBe("39.904200, 8.591700");
    const collection = buildCatastoGisCoordinateFeatureCollection(coordinate);

    expect(collection.type).toBe("FeatureCollection");
    expect(collection.features).toHaveLength(2);
    expect(collection.features[0]).toMatchObject({
      type: "Feature",
      geometry: { type: "Polygon" },
      properties: {
        id: "coordinate-search-waypoint",
        label: "39.904200, 8.591700",
        source: "decimal",
        role: "waypoint-halo",
      },
    });
    expect(collection.features[0].geometry?.type === "Polygon" ? collection.features[0].geometry.coordinates[0] : []).toHaveLength(5);
    expect(collection.features[1]).toEqual({
      type: "Feature",
      geometry: { type: "Point", coordinates: [8.5917, 39.9042] },
      properties: {
        id: "coordinate-search",
        label: "39.904200, 8.591700",
        source: "decimal",
        role: "waypoint-point",
      },
    });
  });
});
