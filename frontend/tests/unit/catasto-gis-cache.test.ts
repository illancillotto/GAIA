import { afterEach, describe, expect, test, vi } from "vitest";

import {
  DEFAULT_GIS_TILE_REVISION,
  GIS_TILE_REVISION_STORAGE_KEY,
  GIS_TILE_REVISION_UPDATED_EVENT,
  getStoredGisTileRevision,
  storeGisTileRevision,
} from "@/lib/catasto-gis-cache";

describe("catasto gis cache", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  test("returns default revision on server and when storage is empty", () => {
    vi.stubGlobal("window", undefined);
    expect(getStoredGisTileRevision()).toBe(DEFAULT_GIS_TILE_REVISION);
  });

  test("reads stored revision from localStorage", () => {
    window.localStorage.setItem(GIS_TILE_REVISION_STORAGE_KEY, "rev-42");
    expect(getStoredGisTileRevision()).toBe("rev-42");
  });

  test("falls back to default when localStorage returns null", () => {
    vi.spyOn(window.localStorage, "getItem").mockReturnValue(null);
    expect(getStoredGisTileRevision()).toBe(DEFAULT_GIS_TILE_REVISION);
  });

  test("stores revision and dispatches update event", () => {
    const handler = vi.fn();
    window.addEventListener(GIS_TILE_REVISION_UPDATED_EVENT, handler);

    storeGisTileRevision("rev-99");

    expect(window.localStorage.getItem(GIS_TILE_REVISION_STORAGE_KEY)).toBe("rev-99");
    expect(handler).toHaveBeenCalledTimes(1);
    expect((handler.mock.calls[0][0] as CustomEvent).detail).toEqual({ revision: "rev-99" });
  });

  test("storeGisTileRevision is a no-op on server", () => {
    vi.stubGlobal("window", undefined);
    expect(() => storeGisTileRevision("rev-server")).not.toThrow();
  });
});
