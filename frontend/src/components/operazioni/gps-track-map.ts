import { LngLatBounds, Map as MapLibreMap, Marker, NavigationControl } from "maplibre-gl";
import type { StyleSpecification } from "@maplibre/maplibre-gl-style-spec";

import {
  WEBGL2_REQUIRED_MESSAGE,
  canCreateWebGL2Context,
  mapInitializationErrorMessage,
  registerMapGPUErrorHandler,
} from "@/lib/maplibre-support";

export type GpsTrackPoint = {
  latitude: number;
  longitude: number;
  timestamp?: string | null;
};

const MAP_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};

function createMarkerElement(toneClass: string): HTMLDivElement {
  const element = document.createElement("div");
  element.className = `gps-map-marker ${toneClass}`;
  return element;
}

function renderGpsTrack(map: MapLibreMap, coordinates: [number, number][]): void {
  map.addSource("activity-track", {
    type: "geojson",
    data: {
      type: "Feature",
      geometry: coordinates.length > 1
        ? { type: "LineString", coordinates }
        : { type: "Point", coordinates: coordinates[0] },
      properties: {},
    },
  });

  if (coordinates.length > 1) {
    map.addLayer({
      id: "activity-track-line",
      type: "line",
      source: "activity-track",
      paint: { "line-color": "#1D4E35", "line-width": 5, "line-opacity": 0.88 },
      layout: { "line-cap": "round", "line-join": "round" },
    });
  }

  new Marker({ element: createMarkerElement("gps-map-marker-start") })
    .setLngLat(coordinates[0])
    .addTo(map);
  if (coordinates.length > 1) {
    new Marker({ element: createMarkerElement("gps-map-marker-end") })
      .setLngLat(coordinates.at(-1) as [number, number])
      .addTo(map);
  }

  if (coordinates.length === 1) {
    map.easeTo({ center: coordinates[0], zoom: 14 });
    return;
  }

  const bounds = new LngLatBounds(coordinates[0], coordinates[0]);
  for (const coordinate of coordinates.slice(1)) bounds.extend(coordinate);
  map.fitBounds(bounds, { padding: 56, maxZoom: 15, duration: 0 });
}

export function mountGpsTrackMap(
  container: HTMLDivElement,
  points: GpsTrackPoint[],
  onError: (message: string | null) => void,
): (() => void) | undefined {
  onError(null);
  if (!canCreateWebGL2Context()) {
    onError(WEBGL2_REQUIRED_MESSAGE);
    return undefined;
  }

  let map: MapLibreMap;
  try {
    map = new MapLibreMap({ container, style: MAP_STYLE, attributionControl: {} });
  } catch (error) {
    onError(mapInitializationErrorMessage(error, "Mappa GPS temporaneamente non disponibile"));
    return undefined;
  }

  map.addControl(new NavigationControl({ showCompass: true, showZoom: true }), "top-right");
  registerMapGPUErrorHandler(
    map,
    onError,
    "Impossibile ripristinare la mappa GPS WebGL2.",
  );
  const coordinates = points.map((point) => [point.longitude, point.latitude] as [number, number]);
  map.on("load", () => renderGpsTrack(map, coordinates));
  return () => map.remove();
}
