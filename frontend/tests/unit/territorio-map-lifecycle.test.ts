import { describe, expect, test, vi } from "vitest";

import {
  disposeTerritorioMap,
  registerTerritorioPointerCursors,
} from "@/components/catasto/gis/territorio-map-lifecycle";

describe("territorio map lifecycle", () => {
  test("registers pointer cursors for interactive layers", () => {
    const listeners = new Map<string, () => void>();
    const canvas = document.createElement("canvas");
    const map = {
      getCanvas: () => canvas,
      on: vi.fn((type: string, layerId: string, listener: () => void) => {
        listeners.set(`${type}:${layerId}`, listener);
      }),
    } as never;

    registerTerritorioPointerCursors(map, ["parcels"]);
    listeners.get("mouseenter:parcels")?.();
    expect(canvas.style.cursor).toBe("pointer");
    listeners.get("mouseleave:parcels")?.();
    expect(canvas.style.cursor).toBe("");
  });

  test("destroys draw state, removes the map and clears its owner", () => {
    const map = { remove: vi.fn() } as never;
    const draw = { destroy: vi.fn() };
    const onMapReady = vi.fn();
    disposeTerritorioMap(map, draw, onMapReady);
    expect(draw.destroy).toHaveBeenCalledOnce();
    expect(map.remove).toHaveBeenCalledOnce();
    expect(onMapReady).toHaveBeenCalledWith(null);

    disposeTerritorioMap(map, null, undefined);
    expect(map.remove).toHaveBeenCalledTimes(2);
  });
});
