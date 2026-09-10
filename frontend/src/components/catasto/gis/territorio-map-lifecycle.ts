import type { Map as MapLibreMap } from "maplibre-gl";

import type { TerritorioDrawController } from "@/components/catasto/gis/territorio-draw";

export function registerTerritorioPointerCursors(
  map: MapLibreMap,
  layerIds: string[],
): void {
  for (const layerId of layerIds) {
    map.on("mouseenter", layerId, () => { map.getCanvas().style.cursor = "pointer"; });
    map.on("mouseleave", layerId, () => { map.getCanvas().style.cursor = ""; });
  }
}

export function disposeTerritorioMap(
  map: MapLibreMap,
  draw: TerritorioDrawController | null,
  onMapReady: ((map: MapLibreMap | null) => void) | undefined,
): void {
  draw?.destroy();
  map.remove();
  onMapReady?.(null);
}
