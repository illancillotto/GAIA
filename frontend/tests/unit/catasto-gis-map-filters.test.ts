import { describe, expect, test } from "vitest";

import { buildParticelleFilter } from "@/components/catasto/gis/MapContainer";

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
});
