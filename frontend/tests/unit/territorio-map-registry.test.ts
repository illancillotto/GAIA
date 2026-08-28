import { describe, expect, test, vi } from "vitest";

const mocks = vi.hoisted(() => ({ created: [] as object[] }));

vi.mock("maplibre-gl", () => {
  class Map {
    constructor(_options: object) {
      mocks.created.push(this);
    }
  }
  return { default: { Map } };
});

import maplibregl from "maplibre-gl";
import { subscribeTerritorioMaps } from "@/components/catasto/gis/territorio-map-registry";

describe("territorio map registry", () => {
  test("publishes MapLibre instances and supports unsubscribe", () => {
    const listener = vi.fn();
    const unsubscribe = subscribeTerritorioMaps(listener);
    expect(listener).toHaveBeenCalledWith([]);

    const map = new maplibregl.Map({} as never);
    expect(listener).toHaveBeenLastCalledWith([map]);
    unsubscribe();
    new maplibregl.Map({} as never);
    expect(listener).toHaveBeenCalledTimes(2);
  });

  test("does not wrap MapLibre twice", async () => {
    vi.resetModules();
    (maplibregl as unknown as { __gaiaTerritorioRegistry?: boolean }).__gaiaTerritorioRegistry = true;
    const module = await import("@/components/catasto/gis/territorio-map-registry");
    const listener = vi.fn();
    module.subscribeTerritorioMaps(listener);
    expect(listener).toHaveBeenCalledWith([]);
  });
});
