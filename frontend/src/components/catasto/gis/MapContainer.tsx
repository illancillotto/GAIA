"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import MapboxDraw from "maplibre-gl-draw";

import { catastoGisGetPopup } from "@/lib/api/catasto";
import type { GisFilters, GisMapOverlayLayer, ParticellaPopupData } from "@/types/gis";

interface MapContainerProps {
  token: string | null;
  onGeometryDrawn: (geometry: GeoJSON.Geometry) => void;
  onSelectionCleared: () => void;
  selectedIds: string[];
  filters: GisFilters;
  mapLayers?: {
    showDistretti: boolean;
    showDistrettiFill?: boolean;
    showParticelle: boolean;
    showParticelleFill?: boolean;
    distrettiOpacity?: number;
    particelleOpacity?: number;
    distretto?: string | null;
    highlightSelected?: boolean;
  };
  overlayLayers?: GisMapOverlayLayer[];
  focusGeojson?: GeoJSON.FeatureCollection | null;
  focusSignal?: number;
  drawSignal: number;
  clearSignal: number;
  resizeSignal?: number;
  className?: string;
}

type DrawControl = InstanceType<typeof MapboxDraw> & {
  changeMode: (mode: string) => void;
  deleteAll: () => void;
};

type DrawEvent = {
  features?: Array<GeoJSON.Feature<GeoJSON.Geometry>>;
};

type Position = [number, number] | [number, number, number];
type LinearRing = Position[];
type PolygonCoords = LinearRing[];
type MultiPolygonCoords = PolygonCoords[];

const CONSORZIO_BOUNDS: [[number, number], [number, number]] = [
  [8.39, 39.62],
  [8.93, 40.13],
];
const CONSORZIO_MAX_BOUNDS: [[number, number], [number, number]] = [
  [8.2, 39.45],
  [9.1, 40.25],
];

function canCreateWebGLContext(): boolean {
  try {
    const canvas = window.document.createElement("canvas");
    return Boolean(canvas.getContext("webgl2") ?? canvas.getContext("webgl") ?? canvas.getContext("experimental-webgl"));
  } catch {
    return false;
  }
}

function getGeometryRings(geom: GeoJSON.Geometry): PolygonCoords {
  if (geom.type === "Polygon") return geom.coordinates as unknown as PolygonCoords;
  if (geom.type === "MultiPolygon") return (geom.coordinates as unknown as MultiPolygonCoords).flat();
  return [];
}

function getGeometryBoundsCenter(geom: GeoJSON.Geometry): [number, number] | null {
  const rings = getGeometryRings(geom);
  let minLng = Number.POSITIVE_INFINITY;
  let minLat = Number.POSITIVE_INFINITY;
  let maxLng = Number.NEGATIVE_INFINITY;
  let maxLat = Number.NEGATIVE_INFINITY;

  for (const ring of rings) {
    for (const point of ring) {
      minLng = Math.min(minLng, point[0]);
      minLat = Math.min(minLat, point[1]);
      maxLng = Math.max(maxLng, point[0]);
      maxLat = Math.max(maxLat, point[1]);
    }
  }

  if (!Number.isFinite(minLng) || !Number.isFinite(minLat) || !Number.isFinite(maxLng) || !Number.isFinite(maxLat)) {
    return null;
  }

  return [(minLng + maxLng) / 2, (minLat + maxLat) / 2];
}

function buildCentroidFeatureCollection(collection: GeoJSON.FeatureCollection | null | undefined): GeoJSON.FeatureCollection {
  if (!collection) return { type: "FeatureCollection", features: [] };

  const features: GeoJSON.Feature[] = [];
  for (const feature of collection.features) {
    if (!feature.geometry) continue;
    const center = getGeometryBoundsCenter(feature.geometry);
    if (!center) continue;
    features.push({
      type: "Feature",
      geometry: {
        type: "Point",
        coordinates: center,
      },
      properties: {
        ...(feature.properties ?? {}),
      },
    });
  }

  return { type: "FeatureCollection", features };
}

function buildOverlayFeatureCollection(overlayLayers: GisMapOverlayLayer[] | undefined): GeoJSON.FeatureCollection {
  if (!overlayLayers || overlayLayers.length === 0) {
    return { type: "FeatureCollection", features: [] };
  }

  const features: GeoJSON.Feature[] = [];
  for (const layer of overlayLayers) {
    if (!layer.visible || !layer.geojson) continue;
    for (const feature of layer.geojson.features) {
      features.push({
        ...feature,
        properties: {
          ...(feature.properties ?? {}),
          __overlayLayerKey: layer.layer_key,
          __overlayName: layer.name,
          __overlayColor: layer.color,
          __overlayOpacity: layer.opacity ?? 0.55,
          __overlaySavedSelectionId: layer.saved_selection_id ?? null,
        },
      });
    }
  }

  return { type: "FeatureCollection", features };
}

function fitCollectionBounds(map: maplibregl.Map, collection: GeoJSON.FeatureCollection | null | undefined): void {
  if (!collection || collection.features.length === 0) return;

  try {
    const bounds = new maplibregl.LngLatBounds();
    for (const feature of collection.features) {
      const geom = feature.geometry;
      if (!geom) continue;
      const rings = getGeometryRings(geom);
      for (const ring of rings) {
        for (const point of ring) bounds.extend([point[0], point[1]]);
      }
    }
    if (!bounds.isEmpty()) {
      map.fitBounds(bounds, { padding: 40, duration: 600, maxZoom: 16 });
    }
  } catch {
    // Fit bounds is best-effort.
  }
}

export default function MapContainer({
  token,
  onGeometryDrawn,
  onSelectionCleared,
  selectedIds,
  filters,
  mapLayers,
  overlayLayers,
  focusGeojson,
  focusSignal,
  drawSignal,
  clearSignal,
  resizeSignal,
  className,
}: MapContainerProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const drawRef = useRef<DrawControl | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const handlersRef = useRef({ onGeometryDrawn, onSelectionCleared, token });
  const [mapError, setMapError] = useState<string | null>(null);
  const [mapReadyVersion, setMapReadyVersion] = useState(0);
  const resizeRafRef = useRef<number | null>(null);
  const combinedOverlayGeojson = useMemo(() => buildOverlayFeatureCollection(overlayLayers), [overlayLayers]);
  const overlayCentroids = useMemo(
    () => buildCentroidFeatureCollection(combinedOverlayGeojson),
    [combinedOverlayGeojson],
  );

  useEffect(() => {
    handlersRef.current = { onGeometryDrawn, onSelectionCleared, token };
  }, [onGeometryDrawn, onSelectionCleared, token]);

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    if (!canCreateWebGLContext()) {
      setMapError("WebGL non e disponibile in questo browser o in questa sessione. Il GIS richiede WebGL attivo.");
      return;
    }

    let map: maplibregl.Map;
    try {
      map = new maplibregl.Map({
        container: mapContainerRef.current,
        style: {
          version: 8,
          sources: {
            osm: {
              type: "raster",
              tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
              tileSize: 256,
              attribution: "OpenStreetMap contributors",
            },
          },
          layers: [
            {
              id: "osm-tiles",
              type: "raster",
              source: "osm",
              minzoom: 0,
              maxzoom: 19,
            },
          ],
        },
        bounds: CONSORZIO_BOUNDS,
        maxBounds: CONSORZIO_MAX_BOUNDS,
        fitBoundsOptions: {
          padding: 28,
        },
      });
    } catch (error) {
      setMapError(error instanceof Error ? error.message : "Impossibile inizializzare il GIS WebGL.");
      return;
    }

    map.on("error", (event) => {
      const message = event.error?.message;
      if (message?.toLowerCase().includes("webgl")) {
        setMapError(message);
      }
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-right");

    const draw = new MapboxDraw({
      displayControlsDefault: false,
      controls: {},
    }) as DrawControl;
    map.addControl(draw as unknown as maplibregl.IControl, "top-left");
    drawRef.current = draw;

    map.on("load", () => {
      map.addSource("distretti-source", {
        type: "vector",
        tiles: [`${window.location.origin}/tiles/cat_distretti/{z}/{x}/{y}`],
        minzoom: 7,
        maxzoom: 16,
      });

      map.addLayer({
        id: "distretti-fill",
        type: "fill",
        source: "distretti-source",
        "source-layer": "cat_distretti",
        minzoom: 7,
        paint: {
          "fill-color": "#3B82F6",
          "fill-opacity": 0.14,
        },
      });

      map.addLayer({
        id: "distretti-outline",
        type: "line",
        source: "distretti-source",
        "source-layer": "cat_distretti",
        minzoom: 7,
        paint: {
          "line-color": "#1D4ED8",
          "line-width": 1.5,
        },
      });

      map.addSource("particelle-source", {
        type: "vector",
        tiles: [`${window.location.origin}/tiles/cat_particelle_current/{z}/{x}/{y}`],
        minzoom: 13,
        maxzoom: 20,
      });

      map.addLayer({
        id: "particelle-fill",
        type: "fill",
        source: "particelle-source",
        "source-layer": "cat_particelle_current",
        minzoom: 13,
        paint: {
          "fill-color": ["case", ["==", ["get", "ha_anomalie"], true], "#EF4444", "#6366F1"],
          "fill-opacity": 0.38,
        },
      });

      map.addLayer({
        id: "particelle-outline",
        type: "line",
        source: "particelle-source",
        "source-layer": "cat_particelle_current",
        minzoom: 14,
        paint: {
          "line-color": "#4338CA",
          "line-width": 0.5,
        },
      });

      map.addLayer({
        id: "particelle-selected-outline",
        type: "line",
        source: "particelle-source",
        "source-layer": "cat_particelle_current",
        minzoom: 13,
        paint: {
          "line-color": "#F59E0B",
          "line-width": 2.5,
        },
        filter: ["in", ["get", "id"], ["literal", []]],
      });

      map.addSource("uploaded-particelle-source", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addSource("uploaded-particelle-centroids-source", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "uploaded-particelle-fill",
        type: "fill",
        source: "uploaded-particelle-source",
        paint: {
          "fill-color": ["coalesce", ["get", "__overlayColor"], "#10B981"],
          "fill-opacity": [
            "*",
            ["coalesce", ["get", "__overlayOpacity"], 0.55],
            [
              "interpolate",
              ["linear"],
              ["zoom"],
              8,
              1,
              11,
              0.75,
              14,
              0.5,
            ],
          ],
        },
      });
      map.addLayer({
        id: "uploaded-particelle-outline",
        type: "line",
        source: "uploaded-particelle-source",
        paint: {
          "line-color": ["coalesce", ["get", "__overlayColor"], "#10B981"],
          "line-opacity": [
            "*",
            ["coalesce", ["get", "__overlayOpacity"], 0.55],
            0.9,
          ],
          "line-width": [
            "interpolate",
            ["linear"],
            ["zoom"],
            8,
            2.5,
            12,
            2,
            16,
            1.25,
          ],
        },
      });
      map.addLayer({
        id: "uploaded-particelle-centroids",
        type: "circle",
        source: "uploaded-particelle-centroids-source",
        paint: {
          "circle-color": ["coalesce", ["get", "__overlayColor"], "#10B981"],
          "circle-radius": [
            "interpolate",
            ["linear"],
            ["zoom"],
            7,
            4.5,
            10,
            4,
            13,
            3,
            16,
            0,
          ],
          "circle-opacity": [
            "*",
            ["coalesce", ["get", "__overlayOpacity"], 0.55],
            [
              "interpolate",
              ["linear"],
              ["zoom"],
              7,
              1,
              12,
              0.85,
              16,
              0,
            ],
          ],
          "circle-stroke-color": "#FFFFFF",
          "circle-stroke-opacity": [
            "*",
            ["coalesce", ["get", "__overlayOpacity"], 0.55],
            0.95,
          ],
          "circle-stroke-width": [
            "interpolate",
            ["linear"],
            ["zoom"],
            7,
            1.2,
            12,
            0.8,
            16,
            0,
          ],
        },
      });

      map.on("click", async (event) => {
        const currentToken = handlersRef.current.token;
        if (!currentToken) return;

        // Query in priority order: uploaded (green) > MVT particelle
        const clickableLayers = ["uploaded-particelle-fill", "particelle-fill"].filter(
          (l) => map.getLayer(l) != null,
        );
        const features = map.queryRenderedFeatures(event.point, { layers: clickableLayers });
        const id = features[0]?.properties?.id;
        if (!id) return;

        popupRef.current?.remove();
        try {
          const data = await catastoGisGetPopup(currentToken, String(id));
          popupRef.current = new maplibregl.Popup({ maxWidth: "320px" })
            .setLngLat(event.lngLat)
            .setHTML(buildPopupHtml(data))
            .addTo(map);
        } catch {
          // Popup failures are non-blocking for the map interaction.
        }
      });

      for (const layerId of ["particelle-fill", "uploaded-particelle-fill", "distretti-fill"]) {
        map.on("mouseenter", layerId, () => {
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", layerId, () => {
          map.getCanvas().style.cursor = "";
        });
      }

      setMapReadyVersion((value) => value + 1);
    });

    const drawEventTarget = map as unknown as {
      on: (type: string, listener: (event: DrawEvent) => void) => void;
    };
    const handleDraw = (event: DrawEvent) => {
      const geometry = event.features?.[0]?.geometry;
      if (geometry) handlersRef.current.onGeometryDrawn(geometry);
    };
    drawEventTarget.on("draw.create", handleDraw);
    drawEventTarget.on("draw.update", handleDraw);
    drawEventTarget.on("draw.delete", () => handlersRef.current.onSelectionCleared());

    mapRef.current = map;

    return () => {
      if (resizeRafRef.current != null) {
        window.cancelAnimationFrame(resizeRafRef.current);
        resizeRafRef.current = null;
      }
      popupRef.current?.remove();
      map.remove();
      mapRef.current = null;
      drawRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!mapContainerRef.current) return;
    const map = mapRef.current;
    if (!map) return;

    const container = mapContainerRef.current;
    const resize = () => {
      if (resizeRafRef.current != null) window.cancelAnimationFrame(resizeRafRef.current);
      resizeRafRef.current = window.requestAnimationFrame(() => {
        map.resize();
      });
    };

    resize();

    const observer = new ResizeObserver(() => resize());
    observer.observe(container);
    return () => {
      observer.disconnect();
      if (resizeRafRef.current != null) {
        window.cancelAnimationFrame(resizeRafRef.current);
        resizeRafRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (drawSignal <= 0) return;
    drawRef.current?.changeMode("draw_polygon");
  }, [drawSignal]);

  useEffect(() => {
    if (clearSignal <= 0) return;
    drawRef.current?.deleteAll();
    popupRef.current?.remove();
  }, [clearSignal]);

  useEffect(() => {
    if (!resizeSignal) return;
    mapRef.current?.resize();
  }, [resizeSignal]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || mapReadyVersion === 0) return;

    const showDistretti = mapLayers?.showDistretti ?? true;
    const showDistrettiFill = mapLayers?.showDistrettiFill ?? false;
    const showParticelle = mapLayers?.showParticelle ?? true;
    const showParticelleFill = mapLayers?.showParticelleFill ?? true;
    const distrettiOpacity = mapLayers?.distrettiOpacity ?? 0.3;
    const particelleOpacity = mapLayers?.particelleOpacity ?? 0.42;

    if (map.getLayer("distretti-fill")) {
      map.setLayoutProperty("distretti-fill", "visibility", showDistretti && showDistrettiFill ? "visible" : "none");
      map.setPaintProperty("distretti-fill", "fill-opacity", distrettiOpacity);
    }
    if (map.getLayer("distretti-outline")) {
      map.setLayoutProperty("distretti-outline", "visibility", showDistretti ? "visible" : "none");
      map.setPaintProperty("distretti-outline", "line-opacity", Math.min(1, distrettiOpacity + 0.15));
    }
    if (map.getLayer("particelle-fill")) {
      map.setLayoutProperty("particelle-fill", "visibility", showParticelle && showParticelleFill ? "visible" : "none");
      map.setPaintProperty("particelle-fill", "fill-opacity", particelleOpacity);
    }
    if (map.getLayer("particelle-outline")) {
      map.setLayoutProperty("particelle-outline", "visibility", showParticelle ? "visible" : "none");
      map.setPaintProperty("particelle-outline", "line-opacity", Math.min(1, particelleOpacity + 0.2));
    }

    const distretto = (mapLayers?.distretto ?? filters.num_distretto ?? null) || null;
    if (map.getLayer("distretti-fill")) {
      map.setFilter("distretti-fill", distretto ? ["==", ["get", "num_distretto"], distretto] : null);
      map.setFilter("distretti-outline", distretto ? ["==", ["get", "num_distretto"], distretto] : null);
    }

    if (map.getLayer("particelle-fill")) {
      map.setFilter("particelle-fill", distretto ? ["==", ["get", "num_distretto"], distretto] : null);
      map.setFilter("particelle-outline", distretto ? ["==", ["get", "num_distretto"], distretto] : null);
    }

    const highlight = mapLayers?.highlightSelected ?? true;
    if (map.getLayer("particelle-selected-outline")) {
      map.setLayoutProperty("particelle-selected-outline", "visibility", highlight ? "visible" : "none");
      map.setFilter(
        "particelle-selected-outline",
        selectedIds.length > 0 ? ["in", ["get", "id"], ["literal", selectedIds]] : ["in", ["get", "id"], ["literal", []]],
      );
    }
  }, [filters.num_distretto, mapLayers, mapReadyVersion, selectedIds]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || mapReadyVersion === 0) return;

    const source = map.getSource("uploaded-particelle-source") as maplibregl.GeoJSONSource | undefined;
    const centroidSource = map.getSource("uploaded-particelle-centroids-source") as maplibregl.GeoJSONSource | undefined;
    if (!source || !centroidSource) return;

    source.setData(combinedOverlayGeojson);
    centroidSource.setData(overlayCentroids);
  }, [combinedOverlayGeojson, mapReadyVersion, overlayCentroids]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || mapReadyVersion === 0 || !focusSignal) return;
    fitCollectionBounds(map, focusGeojson);
  }, [focusGeojson, focusSignal, mapReadyVersion]);

  if (mapError) {
    return (
      <div className="flex h-full min-h-[560px] w-full items-center justify-center rounded-2xl border border-amber-200 bg-amber-50 p-8 text-center">
        <div className="max-w-xl">
          <p className="text-base font-semibold text-amber-900">GIS non disponibile</p>
          <p className="mt-2 text-sm leading-6 text-amber-800">{mapError}</p>
          <p className="mt-4 text-xs leading-5 text-amber-700">
            Abilita accelerazione hardware/WebGL nel browser o apri GAIA in una sessione non sandboxata. Le API GIS e le tiles restano disponibili, ma
            MapLibre non puo renderizzare senza WebGL.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={mapContainerRef}
      className={`maplibregl-map relative h-full min-h-[560px] w-full overflow-hidden rounded-2xl ${className ?? ""}`.trim()}
    />
  );
}

function buildPopupHtml(data: ParticellaPopupData): string {
  const superficie = data.superficie_mq ?? data.superficie_grafica_mq;
  const superficieText = superficie != null ? `${superficie.toLocaleString("it-IT")} mq` : "-";
  const anomalie =
    data.n_anomalie_aperte > 0
      ? `<span style="color:#DC2626;font-weight:600">${data.n_anomalie_aperte} anomalie aperte</span>`
      : `<span style="color:#059669;font-weight:600">Nessuna anomalia aperta</span>`;

  return `
    <div style="font-family:system-ui,sans-serif;font-size:13px;line-height:1.5;color:#111827">
      <div style="font-weight:700;margin-bottom:4px">${escapeHtml(data.cfm || "Particella")}</div>
      <div>Comune: ${escapeHtml(data.nome_comune || data.codice_catastale || "-")}</div>
      <div>Foglio: ${escapeHtml(data.foglio || "-")} - Part.: ${escapeHtml(data.particella || "-")}${data.subalterno ? ` - Sub: ${escapeHtml(data.subalterno)}` : ""}</div>
      <div>Superficie: ${escapeHtml(superficieText)}</div>
      <div>Distretto: ${escapeHtml(data.num_distretto || "-")}${data.nome_distretto ? ` (${escapeHtml(data.nome_distretto)})` : ""}</div>
      <div style="margin-top:4px">${anomalie}</div>
      <div style="margin-top:8px">
        <a href="/catasto/particelle/${encodeURIComponent(data.id)}" style="color:#4F46E5;font-weight:600;text-decoration:none">
          Apri scheda completa
        </a>
      </div>
    </div>
  `;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
