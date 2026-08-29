import maplibregl from "maplibre-gl";

type MapListener = (maps: readonly maplibregl.Map[]) => void;

const maps: maplibregl.Map[] = [];
const listeners = new Set<MapListener>();
const OriginalMap = maplibregl.Map;

function publish(map: maplibregl.Map): void {
  maps.push(map);
  for (const listener of listeners) listener(maps);
}

if (!(maplibregl as unknown as { __gaiaTerritorioRegistry?: boolean }).__gaiaTerritorioRegistry) {
  class RegisteredMap extends OriginalMap {
    constructor(options: maplibregl.MapOptions) {
      super(options);
      publish(this);
    }
  }
  maplibregl.Map = RegisteredMap;
  (maplibregl as unknown as { __gaiaTerritorioRegistry?: boolean }).__gaiaTerritorioRegistry = true;
}

export function subscribeTerritorioMaps(listener: MapListener): () => void {
  listeners.add(listener);
  listener(maps);
  return () => listeners.delete(listener);
}
