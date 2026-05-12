"use client";

import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import MapboxDraw from "maplibre-gl-draw";

import { catastoGisGetPopup } from "@/lib/api/catasto";
import type { GisFilters, GisMapOverlayLayer, ParticellaPopupData } from "@/types/gis";

interface MapContainerProps {
  token: string | null;
  onGeometryDrawn: (geometry: GeoJSON.Geometry) => void;
  onSelectionCleared: () => void;
  onParticellaClick?: (particella: ParticellaPopupData | null) => void;
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
    distrettoColors?: Record<string, string>;
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

function buildLayerGeojson(layer: GisMapOverlayLayer): GeoJSON.FeatureCollection {
  if (!layer.geojson) return { type: "FeatureCollection", features: [] };
  return {
    type: "FeatureCollection",
    features: layer.geojson.features.map((feature) => ({
      ...feature,
      properties: {
        ...(feature.properties ?? {}),
        __overlayLayerKey: layer.layer_key,
        __overlayName: layer.name,
        __overlayColor: layer.color,
        __overlaySavedSelectionId: layer.saved_selection_id ?? null,
      },
    })),
  };
}

function buildLayerCentroidGeojson(layer: GisMapOverlayLayer): GeoJSON.FeatureCollection {
  return buildCentroidFeatureCollection(buildLayerGeojson(layer));
}

const OVERLAY_LAYER_PREFIX = "overlay-";
function overlayLayerIds(layerKey: string) {
  const safe = layerKey.replace(/[^a-zA-Z0-9_-]/g, "_");
  return {
    sourceId: `${OVERLAY_LAYER_PREFIX}${safe}-source`,
    centroidSourceId: `${OVERLAY_LAYER_PREFIX}${safe}-centroid-source`,
    fillId: `${OVERLAY_LAYER_PREFIX}${safe}-fill`,
    outlineId: `${OVERLAY_LAYER_PREFIX}${safe}-outline`,
    centroidId: `${OVERLAY_LAYER_PREFIX}${safe}-centroid`,
  };
}

function buildDistrettoColorExpression(colors: Record<string, string> | undefined): maplibregl.ExpressionSpecification | string {
  const entries = Object.entries(colors ?? {});
  if (entries.length === 0) return "#1D4E35";
  const expression: unknown[] = ["match", ["get", "num_distretto"]];
  for (const [num, color] of entries) {
    expression.push(num, color);
  }
  expression.push("#1D4E35");
  return expression as maplibregl.ExpressionSpecification;
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
  onParticellaClick,
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
  const handlersRef = useRef({ onGeometryDrawn, onSelectionCleared, onParticellaClick, token });
  const [mapError, setMapError] = useState<string | null>(null);
  const [mapReadyVersion, setMapReadyVersion] = useState(0);
  const resizeRafRef = useRef<number | null>(null);
  const overlayMapKeysRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    handlersRef.current = { onGeometryDrawn, onSelectionCleared, onParticellaClick, token };
  }, [onGeometryDrawn, onParticellaClick, onSelectionCleared, token]);

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

      map.addSource("distretti-boundaries-source", {
        type: "vector",
        tiles: [`${window.location.origin}/tiles/cat_distretti_boundaries/{z}/{x}/{y}`],
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
          "fill-color": "#1D4E35",
          "fill-opacity": 0.12,
        },
      });

      map.addLayer({
        id: "distretti-outline",
        type: "line",
        source: "distretti-boundaries-source",
        "source-layer": "cat_distretti_boundaries",
        minzoom: 7,
        paint: {
          "line-color": "#1D4E35",
          "line-width": [
            "interpolate",
            ["linear"],
            ["zoom"],
            7,
            1.6,
            11,
            2,
            15,
            2.6,
          ],
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
          "fill-color": [
            "case",
            ["==", ["get", "ha_anomalie"], true],
            "#EF4444",
            ["==", ["get", "ha_ruolo"], true],
            "#10B981",
            "#6366F1",
          ],
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

      map.on("click", async (event) => {
        const currentToken = handlersRef.current.token;
        if (!currentToken) return;

        const overlayFillIds = Array.from(overlayMapKeysRef.current).map(
          (key) => overlayLayerIds(key).fillId,
        );
        const clickableLayers = [...overlayFillIds, "particelle-fill"].filter(
          (l) => map.getLayer(l) != null,
        );
        const features = map.queryRenderedFeatures(event.point, { layers: clickableLayers });
        const id = features[0]?.properties?.id;
        popupRef.current?.remove();
        if (!id) {
          handlersRef.current.onParticellaClick?.(null);
          return;
        }
        try {
          const data = await catastoGisGetPopup(currentToken, String(id));
          if (handlersRef.current.onParticellaClick) {
            handlersRef.current.onParticellaClick(data);
          } else {
            popupRef.current = new maplibregl.Popup({ maxWidth: "320px" })
              .setLngLat(event.lngLat)
              .setHTML(buildPopupHtml(data))
              .addTo(map);
          }
        } catch {
          // Popup failures are non-blocking for the map interaction.
        }
      });

      for (const layerId of ["particelle-fill", "distretti-fill"]) {
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
    const distrettoColor = buildDistrettoColorExpression(mapLayers?.distrettoColors);

    if (map.getLayer("distretti-fill")) {
      map.setLayoutProperty("distretti-fill", "visibility", showDistretti && showDistrettiFill ? "visible" : "none");
      map.setPaintProperty("distretti-fill", "fill-color", distrettoColor);
      map.setPaintProperty("distretti-fill", "fill-opacity", distrettiOpacity);
    }
    if (map.getLayer("distretti-outline")) {
      map.setLayoutProperty("distretti-outline", "visibility", showDistretti ? "visible" : "none");
      map.setPaintProperty("distretti-outline", "line-color", distrettoColor);
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

    for (const stale of [
      "uploaded-particelle-fill",
      "uploaded-particelle-outline",
      "uploaded-particelle-centroids",
    ]) {
      if (map.getLayer(stale)) map.removeLayer(stale);
    }
    for (const staleSource of [
      "uploaded-particelle-source",
      "uploaded-particelle-centroids-source",
    ]) {
      if (map.getSource(staleSource)) map.removeSource(staleSource);
    }

    const overlays = overlayLayers ?? [];
    const expectedKeys = new Set(overlays.map((l) => l.layer_key));

    for (const key of Array.from(overlayMapKeysRef.current)) {
      if (!expectedKeys.has(key)) {
        const ids = overlayLayerIds(key);
        if (map.getLayer(ids.fillId)) map.removeLayer(ids.fillId);
        if (map.getLayer(ids.outlineId)) map.removeLayer(ids.outlineId);
        if (map.getLayer(ids.centroidId)) map.removeLayer(ids.centroidId);
        if (map.getSource(ids.sourceId)) map.removeSource(ids.sourceId);
        if (map.getSource(ids.centroidSourceId)) map.removeSource(ids.centroidSourceId);
        overlayMapKeysRef.current.delete(key);
      }
    }

    for (const layer of overlays) {
      const ids = overlayLayerIds(layer.layer_key);
      const layerData = buildLayerGeojson(layer);
      const centroidData = buildLayerCentroidGeojson(layer);
      const opacity = layer.opacity ?? 0.55;
      const color = layer.color ?? "#10B981";
      const showFill = layer.showFill ?? true;
      const isVisible = layer.visible !== false;

      const fillOpacityExpr: maplibregl.ExpressionSpecification = [
        "*",
        opacity,
        ["interpolate", ["linear"], ["zoom"], 8, 1, 11, 0.75, 14, 0.5],
      ];
      const lineOpacity = Math.min(1, opacity * 0.9);
      const circleOpacityExpr: maplibregl.ExpressionSpecification = [
        "*",
        opacity,
        ["interpolate", ["linear"], ["zoom"], 7, 1, 12, 0.85, 16, 0],
      ];
      const circleStrokeOpacity = Math.min(1, opacity * 0.95);

      if (!map.getSource(ids.sourceId)) {
        map.addSource(ids.sourceId, { type: "geojson", data: layerData });
      } else {
        (map.getSource(ids.sourceId) as maplibregl.GeoJSONSource).setData(layerData);
      }
      if (!map.getSource(ids.centroidSourceId)) {
        map.addSource(ids.centroidSourceId, { type: "geojson", data: centroidData });
      } else {
        (map.getSource(ids.centroidSourceId) as maplibregl.GeoJSONSource).setData(centroidData);
      }

      if (!map.getLayer(ids.fillId)) {
        map.addLayer({
          id: ids.fillId,
          type: "fill",
          source: ids.sourceId,
          paint: {
            "fill-color": color,
            "fill-opacity": fillOpacityExpr,
          },
        });
        map.on("mouseenter", ids.fillId, () => {
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", ids.fillId, () => {
          map.getCanvas().style.cursor = "";
        });
      } else {
        map.setPaintProperty(ids.fillId, "fill-color", color);
        map.setPaintProperty(ids.fillId, "fill-opacity", fillOpacityExpr);
      }

      if (!map.getLayer(ids.outlineId)) {
        map.addLayer({
          id: ids.outlineId,
          type: "line",
          source: ids.sourceId,
          paint: {
            "line-color": color,
            "line-opacity": lineOpacity,
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
      } else {
        map.setPaintProperty(ids.outlineId, "line-color", color);
        map.setPaintProperty(ids.outlineId, "line-opacity", lineOpacity);
      }

      if (!map.getLayer(ids.centroidId)) {
        map.addLayer({
          id: ids.centroidId,
          type: "circle",
          source: ids.centroidSourceId,
          paint: {
            "circle-color": color,
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
            "circle-opacity": circleOpacityExpr,
            "circle-stroke-color": "#FFFFFF",
            "circle-stroke-opacity": circleStrokeOpacity,
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
      } else {
        map.setPaintProperty(ids.centroidId, "circle-color", color);
        map.setPaintProperty(ids.centroidId, "circle-opacity", circleOpacityExpr);
        map.setPaintProperty(ids.centroidId, "circle-stroke-opacity", circleStrokeOpacity);
      }

      overlayMapKeysRef.current.add(layer.layer_key);

      map.setLayoutProperty(ids.fillId, "visibility", isVisible && showFill ? "visible" : "none");
      map.setLayoutProperty(ids.outlineId, "visibility", isVisible ? "visible" : "none");
      map.setLayoutProperty(ids.centroidId, "visibility", isVisible ? "visible" : "none");
    }
  }, [overlayLayers, mapReadyVersion]);

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
