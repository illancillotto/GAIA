"use client";

import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import MapboxDraw from "maplibre-gl-draw";

import {
  PARTICELLA_INCOMPLETE_KEY_EXPRESSION,
  buildDeliveryPointFilter,
  buildMeterVisibilityFilter,
  buildParticelleFillOpacity,
  buildParticelleFilter,
  buildParticelleOutlineColor,
  shouldShowDeliveryPointLayer,
} from "@/components/catasto/gis/map-filters";
import type { ParticelleQuickFilter } from "@/components/catasto/gis/map-filters";
import { catastoGisGetDeliveryPointPopup, catastoGisGetPopup } from "@/lib/api/catasto";
import {
  DELIVERY_POINTS_TILE_REVISION_STORAGE_KEY,
  getStoredDeliveryPointsTileRevision,
} from "@/lib/catasto-gis-cache";
import type { DeliveryPointPopupData, GisBasemap, GisFilters, GisMapOverlayLayer, GisOverlayFeatureClick, ParticellaPopupData } from "@/types/gis";

interface MapContainerProps {
  token: string | null;
  onGeometryDrawn: (geometry: GeoJSON.Geometry) => void;
  onSelectionCleared: () => void;
  onParticellaClick?: (particella: ParticellaPopupData | null) => void;
  onDeliveryPointClick?: (deliveryPoint: DeliveryPointPopupData | null) => void;
  onOverlayFeatureClick?: (overlay: GisOverlayFeatureClick | null) => void;
  selectedIds: string[];
  filters: GisFilters;
  mapLayers?: {
    showDistretti: boolean;
    showDistrettiFill?: boolean;
    showParticelleFill?: boolean;
    distrettiOpacity?: number;
    particelleOpacity?: number;
    distretto?: string | null;
    highlightSelected?: boolean;
    distrettoColors?: Record<string, string>;
    particelleQuickFilter?: "all" | "ruolo" | "ruolo_inferito";
    showDeliveryPoints?: boolean;
    deliveryPointsQuickFilter?: "all" | "with_meter" | "without_meter";
  };
  overlayLayers?: GisMapOverlayLayer[];
  focusGeojson?: GeoJSON.FeatureCollection | null;
  focusSignal?: number;
  focusOptions?: {
    maxZoom?: number;
    padding?: number;
    duration?: number;
  };
  drawSignal: number;
  clearSignal: number;
  resizeSignal?: number;
  basemap?: GisBasemap;
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
const PARTICELLE_MIN_ZOOM = 13;
const GOOGLE_MAP_TILES_API_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY?.trim() ?? "";

type GoogleTilesSession = {
  session?: string;
  expiry?: string;
};

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
        __overlayOutlineColor: layer.outlineColor ?? layer.color,
        __overlayPulse: layer.pulse === true,
        __overlayPulseUntil: layer.pulseUntil ?? null,
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

function buildParticelleTilesUrl(revision: string): string {
  return `${window.location.origin}/tiles/cat_particelle_current/{z}/{x}/{y}?v=${encodeURIComponent(revision)}`;
}

function buildDeliveryPointsTilesUrl(revision: string): string {
  return `${window.location.origin}/tiles/cat_delivery_points_current/{z}/{x}/{y}?v=${encodeURIComponent(revision)}`;
}

function buildIrrigationCanalsTilesUrl(revision: string): string {
  return `${window.location.origin}/tiles/cat_irrigation_canals_current/{z}/{x}/{y}?v=${encodeURIComponent(revision)}`;
}

function fitCollectionBounds(
  map: maplibregl.Map,
  collection: GeoJSON.FeatureCollection | null | undefined,
  options?: {
    maxZoom?: number;
    padding?: number;
    duration?: number;
  },
): void {
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
      map.fitBounds(bounds, {
        padding: options?.padding ?? 40,
        duration: options?.duration ?? 600,
        maxZoom: options?.maxZoom ?? 16,
      });
    }
  } catch {
    // Fit bounds is best-effort.
  }
}

async function ensureGoogleSatelliteLayer(map: maplibregl.Map): Promise<boolean> {
  if (map.getLayer("google-satellite-tiles")) return true;
  if (!GOOGLE_MAP_TILES_API_KEY) return false;

  const response = await fetch(
    `https://tile.googleapis.com/v1/createSession?key=${encodeURIComponent(GOOGLE_MAP_TILES_API_KEY)}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mapType: "satellite",
        language: "it-IT",
        region: "IT",
      }),
    },
  );
  if (!response.ok) return false;

  const payload = (await response.json()) as GoogleTilesSession;
  if (!payload.session) return false;

  if (!map.getSource("google-satellite")) {
    map.addSource("google-satellite", {
      type: "raster",
      tiles: [
        `https://tile.googleapis.com/v1/2dtiles/{z}/{x}/{y}?session=${encodeURIComponent(payload.session)}&key=${encodeURIComponent(GOOGLE_MAP_TILES_API_KEY)}`,
      ],
      tileSize: 256,
      attribution: "Google",
    });
  }
  map.addLayer(
    {
      id: "google-satellite-tiles",
      type: "raster",
      source: "google-satellite",
      minzoom: 0,
      maxzoom: 20,
      layout: { visibility: "none" },
    },
    map.getLayer("distretti-fill") ? "distretti-fill" : undefined,
  );
  return true;
}

export default function MapContainer({
  token,
  onGeometryDrawn,
  onSelectionCleared,
  onParticellaClick,
  onDeliveryPointClick,
  onOverlayFeatureClick,
  selectedIds,
  filters,
  mapLayers,
  overlayLayers,
  focusGeojson,
  focusSignal,
  focusOptions,
  drawSignal,
  clearSignal,
  resizeSignal,
  basemap,
  className,
}: MapContainerProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const drawRef = useRef<DrawControl | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const handlersRef = useRef({
    onGeometryDrawn,
    onSelectionCleared,
    onParticellaClick,
    onDeliveryPointClick,
    onOverlayFeatureClick,
    token,
  });
  const [mapError, setMapError] = useState<string | null>(null);
  const [mapReadyVersion, setMapReadyVersion] = useState(0);
  const resizeRafRef = useRef<number | null>(null);
  const overlayMapKeysRef = useRef<Set<string>>(new Set());
  const lastParticelleQuickFilterRef = useRef<ParticelleQuickFilter>("all");
  const particelleTilesRevisionRef = useRef<string>(Date.now().toString());
  const deliveryPointsTilesRevisionRef = useRef<string>(getStoredDeliveryPointsTileRevision());
  const [deliveryPointsTilesRevision, setDeliveryPointsTilesRevision] = useState(deliveryPointsTilesRevisionRef.current);

  useEffect(() => {
    handlersRef.current = {
      onGeometryDrawn,
      onSelectionCleared,
      onParticellaClick,
      onDeliveryPointClick,
      onOverlayFeatureClick,
      token,
    };
  }, [onDeliveryPointClick, onGeometryDrawn, onOverlayFeatureClick, onParticellaClick, onSelectionCleared, token]);

  useEffect(() => {
    const nextRevision = getStoredDeliveryPointsTileRevision();
    deliveryPointsTilesRevisionRef.current = nextRevision;
    setDeliveryPointsTilesRevision(nextRevision);

    const handleStorage = (event: StorageEvent) => {
      if (event.key !== DELIVERY_POINTS_TILE_REVISION_STORAGE_KEY) return;
      const storedRevision = getStoredDeliveryPointsTileRevision();
      deliveryPointsTilesRevisionRef.current = storedRevision;
      setDeliveryPointsTilesRevision(storedRevision);
    };

    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || mapReadyVersion === 0) return;

    const source = map.getSource("delivery-points-source") as
      | (maplibregl.Source & { setTiles?: (tiles: string[]) => void })
      | undefined;
    source?.setTiles?.([buildDeliveryPointsTilesUrl(deliveryPointsTilesRevision)]);
    const canalsSource = map.getSource("irrigation-canals-source") as
      | (maplibregl.Source & { setTiles?: (tiles: string[]) => void })
      | undefined;
    canalsSource?.setTiles?.([buildIrrigationCanalsTilesUrl(deliveryPointsTilesRevision)]);
    map.triggerRepaint();
  }, [deliveryPointsTilesRevision, mapReadyVersion]);

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
            satellite: {
              type: "raster",
              tiles: ["https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
              tileSize: 256,
              attribution: "Esri, Maxar, Earthstar Geographics, and the GIS User Community",
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
            {
              id: "satellite-tiles",
              type: "raster",
              source: "satellite",
              minzoom: 0,
              maxzoom: 19,
              layout: { visibility: "none" },
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

    const refreshParticelleTiles = () => {
      const nextRevision = Date.now().toString();
      particelleTilesRevisionRef.current = nextRevision;
      const source = map.getSource("particelle-source") as
        | (maplibregl.Source & { setTiles?: (tiles: string[]) => void })
        | undefined;
      source?.setTiles?.([buildParticelleTilesUrl(nextRevision)]);
      map.triggerRepaint();
    };

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
          // Keep district boundaries understated so parcel outlines remain dominant.
          "line-color": "#64748B",
          "line-width": [
            "interpolate",
            ["linear"],
            ["zoom"],
            7,
            0.8,
            11,
            1,
            15,
            1.4,
          ],
          "line-opacity": 0.22,
        },
      });

      map.addSource("particelle-source", {
        type: "vector",
        tiles: [buildParticelleTilesUrl(particelleTilesRevisionRef.current)],
        minzoom: 13,
        maxzoom: 20,
      });

      map.addSource("delivery-points-source", {
        type: "vector",
        tiles: [buildDeliveryPointsTilesUrl(deliveryPointsTilesRevisionRef.current)],
        minzoom: 11,
        maxzoom: 20,
      });

      map.addSource("irrigation-canals-source", {
        type: "vector",
        tiles: [buildIrrigationCanalsTilesUrl(deliveryPointsTilesRevisionRef.current)],
        minzoom: 10,
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
            PARTICELLA_INCOMPLETE_KEY_EXPRESSION,
            "#F000B8",
            ["==", ["get", "ha_anomalie"], true],
            "#EF4444",
            ["==", ["get", "ha_ruolo"], true],
            "#10B981",
            ["==", ["get", "ha_ruolo_inferito"], true],
            "#F59E0B",
            "#6366F1",
          ],
          "fill-opacity": buildParticelleFillOpacity(0.5, "all"),
        },
      });

      map.addLayer({
        id: "particelle-outline",
        type: "line",
        source: "particelle-source",
        "source-layer": "cat_particelle_current",
        minzoom: 14,
        paint: {
          "line-color": buildParticelleOutlineColor(basemap),
          "line-width": [
            "case",
            PARTICELLA_INCOMPLETE_KEY_EXPRESSION,
            0.9,
            0.35,
          ],
        },
      });

      map.addLayer({
        id: "particelle-hitbox",
        type: "fill",
        source: "particelle-source",
        "source-layer": "cat_particelle_current",
        minzoom: 13,
        paint: {
          "fill-color": "#000000",
          "fill-opacity": 0.001,
        },
      });

      map.addLayer({
        id: "irrigation-canals-line",
        type: "line",
        source: "irrigation-canals-source",
        "source-layer": "cat_irrigation_canals_current",
        minzoom: 10,
        paint: {
          "line-color": "#0F766E",
          "line-width": [
            "interpolate",
            ["linear"],
            ["zoom"],
            10,
            1.1,
            13,
            1.8,
            16,
            2.4,
          ],
          "line-opacity": 0.75,
        },
      });

      map.addLayer({
        id: "delivery-points-with-meter",
        type: "circle",
        source: "delivery-points-source",
        "source-layer": "cat_delivery_points_current",
        minzoom: 11,
        filter: [
          "any",
          ["==", ["get", "has_meter"], true],
          ["==", ["get", "has_meter"], 1],
          ["==", ["get", "has_meter"], "true"],
        ],
        paint: {
          "circle-color": "#14532D",
          "circle-radius": [
            "interpolate",
            ["linear"],
            ["zoom"],
            11,
            2.5,
            14,
            4,
            17,
            5.5,
          ],
          "circle-opacity": 0.92,
          "circle-stroke-color": "#DCFCE7",
          "circle-stroke-width": 1.1,
        },
      });

      map.addLayer({
        id: "delivery-points-without-meter",
        type: "circle",
        source: "delivery-points-source",
        "source-layer": "cat_delivery_points_current",
        minzoom: 11,
        filter: [
          "any",
          ["==", ["get", "has_meter"], false],
          ["==", ["get", "has_meter"], 0],
          ["==", ["get", "has_meter"], "false"],
        ],
        paint: {
          "circle-color": "#B45309",
          "circle-radius": [
            "interpolate",
            ["linear"],
            ["zoom"],
            11,
            2,
            14,
            3.2,
            17,
            4.5,
          ],
          "circle-opacity": 0.88,
          "circle-stroke-color": "#FEF3C7",
          "circle-stroke-width": 1,
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
        const clickableLayers = [
          ...overlayFillIds,
          "delivery-points-with-meter",
          "delivery-points-without-meter",
          "particelle-hitbox",
        ].filter(
          (l) => map.getLayer(l) != null,
        );
        const clickPadding = 6;
        const features = map.queryRenderedFeatures(
          [
            [event.point.x - clickPadding, event.point.y - clickPadding],
            [event.point.x + clickPadding, event.point.y + clickPadding],
          ],
          { layers: clickableLayers },
        );
        const clickableFeature = features.find((feature) => {
          const featureId = feature.properties?.id ?? feature.id;
          return featureId != null && String(featureId).trim().length > 0;
        });
        const id = clickableFeature?.properties?.id ?? clickableFeature?.id;
        popupRef.current?.remove();
        if (!id) {
          handlersRef.current.onParticellaClick?.(null);
          if (clickableFeature?.properties?.__overlayLayerKey) {
            handlersRef.current.onOverlayFeatureClick?.({
              layer_key: String(clickableFeature.properties.__overlayLayerKey),
              layer_name: typeof clickableFeature.properties.__overlayName === "string" ? clickableFeature.properties.__overlayName : null,
              properties: { ...(clickableFeature.properties ?? {}) } as Record<string, unknown>,
              geometry: (clickableFeature.geometry as GeoJSON.Geometry | undefined) ?? null,
            });
            return;
          }
          handlersRef.current.onOverlayFeatureClick?.(null);
          handlersRef.current.onDeliveryPointClick?.(null);
          return;
        }
        const layerId = clickableFeature?.layer?.id ?? null;
        const isDeliveryPointLayer = layerId === "delivery-points-with-meter" || layerId === "delivery-points-without-meter";
        if (isDeliveryPointLayer) {
          handlersRef.current.onOverlayFeatureClick?.(null);
          handlersRef.current.onParticellaClick?.(null);
          try {
            const data = await catastoGisGetDeliveryPointPopup(currentToken, String(id));
            handlersRef.current.onDeliveryPointClick?.(data);
          } catch {
            handlersRef.current.onDeliveryPointClick?.(null);
          }
          return;
        }
        handlersRef.current.onDeliveryPointClick?.(null);
        handlersRef.current.onOverlayFeatureClick?.(null);
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
          handlersRef.current.onParticellaClick?.(null);
        }
      });

      for (const layerId of [
        "particelle-hitbox",
        "particelle-fill",
        "distretti-fill",
        "delivery-points-with-meter",
        "delivery-points-without-meter",
      ]) {
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

    const handleWindowFocus = () => {
      refreshParticelleTiles();
    };
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        refreshParticelleTiles();
      }
    };
    window.addEventListener("focus", handleWindowFocus);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    mapRef.current = map;

    return () => {
      window.removeEventListener("focus", handleWindowFocus);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
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

    const selectedBasemap = basemap ?? "osm";
    const applyVisibility = (activeBasemap: GisBasemap) => {
      if (map.getLayer("osm-tiles")) {
        map.setLayoutProperty("osm-tiles", "visibility", activeBasemap === "osm" ? "visible" : "none");
      }
      if (map.getLayer("satellite-tiles")) {
        map.setLayoutProperty("satellite-tiles", "visibility", activeBasemap === "satellite" ? "visible" : "none");
      }
      if (map.getLayer("google-satellite-tiles")) {
        map.setLayoutProperty("google-satellite-tiles", "visibility", activeBasemap === "google_satellite" ? "visible" : "none");
      }
    };

    if (selectedBasemap !== "google_satellite") {
      applyVisibility(selectedBasemap);
      return;
    }

    let cancelled = false;
    void ensureGoogleSatelliteLayer(map)
      .then((available) => {
        if (cancelled) return;
        applyVisibility(available ? "google_satellite" : "osm");
      })
      .catch(() => {
        if (!cancelled) applyVisibility("osm");
      });
    return () => {
      cancelled = true;
    };
  }, [basemap, mapReadyVersion]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || mapReadyVersion === 0) return;

    const showDistretti = mapLayers?.showDistretti ?? true;
    const showDistrettiFill = mapLayers?.showDistrettiFill ?? false;
    const showParticelleFill = mapLayers?.showParticelleFill ?? true;
    const showDeliveryPoints = mapLayers?.showDeliveryPoints ?? true;
    const deliveryPointsQuickFilter = mapLayers?.deliveryPointsQuickFilter ?? "all";
    const distrettiOpacity = mapLayers?.distrettiOpacity ?? 0.3;
    const particelleOpacity = mapLayers?.particelleOpacity ?? 0.5;
    const distrettoColor = buildDistrettoColorExpression(mapLayers?.distrettoColors);
    const particelleQuickFilter = mapLayers?.particelleQuickFilter ?? "all";

    if (map.getLayer("distretti-fill")) {
      map.setLayoutProperty("distretti-fill", "visibility", showDistretti && showDistrettiFill ? "visible" : "none");
      map.setPaintProperty("distretti-fill", "fill-color", distrettoColor);
      map.setPaintProperty("distretti-fill", "fill-opacity", distrettiOpacity);
    }
    if (map.getLayer("distretti-outline")) {
      map.setLayoutProperty("distretti-outline", "visibility", showDistretti && !showDistrettiFill ? "visible" : "none");
      map.setPaintProperty("distretti-outline", "line-color", "#64748B");
      map.setPaintProperty("distretti-outline", "line-opacity", Math.min(0.32, distrettiOpacity * 0.55 + 0.08));
    }
    if (map.getLayer("particelle-fill")) {
      map.setLayoutProperty("particelle-fill", "visibility", showParticelleFill ? "visible" : "none");
      map.setPaintProperty("particelle-fill", "fill-opacity", buildParticelleFillOpacity(particelleOpacity, particelleQuickFilter));
    }
    if (map.getLayer("particelle-outline")) {
      map.setLayoutProperty("particelle-outline", "visibility", "visible");
      map.setPaintProperty("particelle-outline", "line-color", buildParticelleOutlineColor(basemap));
      map.setPaintProperty("particelle-outline", "line-opacity", Math.min(0.65, particelleOpacity * 0.7 + 0.08));
    }
    if (map.getLayer("particelle-hitbox")) {
      // Keep the transparent hitbox queryable even when the visual parcel layer is disabled.
      map.setLayoutProperty("particelle-hitbox", "visibility", "visible");
    }
    if (map.getLayer("irrigation-canals-line")) {
      map.setLayoutProperty("irrigation-canals-line", "visibility", "visible");
    }
    if (map.getLayer("delivery-points-with-meter")) {
      map.setLayoutProperty(
        "delivery-points-with-meter",
        "visibility",
        showDeliveryPoints && shouldShowDeliveryPointLayer(deliveryPointsQuickFilter, true) ? "visible" : "none",
      );
    }
    if (map.getLayer("delivery-points-without-meter")) {
      map.setLayoutProperty(
        "delivery-points-without-meter",
        "visibility",
        showDeliveryPoints && shouldShowDeliveryPointLayer(deliveryPointsQuickFilter, false) ? "visible" : "none",
      );
    }

    const distretto = (mapLayers?.distretto ?? filters.num_distretto ?? null) || null;
    if (map.getLayer("distretti-fill")) {
      map.setFilter("distretti-fill", distretto ? ["==", ["get", "num_distretto"], distretto] : null);
      map.setFilter("distretti-outline", distretto ? ["==", ["get", "num_distretto"], distretto] : null);
    }

    if (map.getLayer("particelle-fill")) {
      const particelleFilter = buildParticelleFilter(distretto, particelleQuickFilter);
      map.setFilter("particelle-fill", particelleFilter);
      map.setFilter("particelle-outline", particelleFilter);
      map.setFilter("particelle-hitbox", particelleFilter);
    }
    const deliveryPointFilter = buildDeliveryPointFilter(distretto);
    if (map.getLayer("delivery-points-with-meter")) {
      map.setFilter("delivery-points-with-meter", buildMeterVisibilityFilter(distretto, true));
    }
    if (map.getLayer("delivery-points-without-meter")) {
      map.setFilter("delivery-points-without-meter", buildMeterVisibilityFilter(distretto, false));
    }
    if (map.getLayer("irrigation-canals-line")) {
      map.setFilter("irrigation-canals-line", deliveryPointFilter);
    }

    if (
      particelleQuickFilter !== "all" &&
      lastParticelleQuickFilterRef.current !== particelleQuickFilter &&
      map.getZoom() < PARTICELLE_MIN_ZOOM
    ) {
      map.easeTo({ zoom: PARTICELLE_MIN_ZOOM, duration: 650 });
    }
    lastParticelleQuickFilterRef.current = particelleQuickFilter;

    const highlight = mapLayers?.highlightSelected ?? true;
    if (map.getLayer("particelle-selected-outline")) {
      map.setLayoutProperty("particelle-selected-outline", "visibility", highlight ? "visible" : "none");
      map.setFilter(
        "particelle-selected-outline",
        selectedIds.length > 0 ? ["in", ["get", "id"], ["literal", selectedIds]] : ["in", ["get", "id"], ["literal", []]],
      );
    }
  }, [basemap, filters.num_distretto, mapLayers, mapReadyVersion, selectedIds]);

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
      const outlineColor = layer.outlineColor ?? color;
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
            "fill-color": ["coalesce", ["get", "__overlayColor"], color],
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
        map.setPaintProperty(ids.fillId, "fill-color", ["coalesce", ["get", "__overlayColor"], color]);
        map.setPaintProperty(ids.fillId, "fill-opacity", fillOpacityExpr);
      }

      if (!map.getLayer(ids.outlineId)) {
        map.addLayer({
          id: ids.outlineId,
          type: "line",
          source: ids.sourceId,
          paint: {
            "line-color": ["coalesce", ["get", "__overlayOutlineColor"], outlineColor],
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
        map.setPaintProperty(ids.outlineId, "line-color", ["coalesce", ["get", "__overlayOutlineColor"], outlineColor]);
        map.setPaintProperty(ids.outlineId, "line-opacity", lineOpacity);
      }

      if (!map.getLayer(ids.centroidId)) {
        map.addLayer({
          id: ids.centroidId,
          type: "circle",
          source: ids.centroidSourceId,
          paint: {
            "circle-color": ["coalesce", ["get", "__overlayColor"], color],
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
        map.setPaintProperty(ids.centroidId, "circle-color", ["coalesce", ["get", "__overlayColor"], color]);
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
    if (!map || mapReadyVersion === 0) return;

    const resetLayerStyle = (layer: GisMapOverlayLayer) => {
      const ids = overlayLayerIds(layer.layer_key);
      const baseOpacity = layer.opacity ?? 0.82;
      const lineOpacity = Math.min(1, baseOpacity * 0.9);
      const circleStrokeOpacity = Math.min(1, baseOpacity * 0.95);
      const fillOpacityExpr: maplibregl.ExpressionSpecification = [
        "*",
        baseOpacity,
        ["interpolate", ["linear"], ["zoom"], 8, 1, 11, 0.75, 14, 0.5],
      ];
      const circleOpacityExpr: maplibregl.ExpressionSpecification = [
        "*",
        baseOpacity,
        ["interpolate", ["linear"], ["zoom"], 7, 1, 12, 0.85, 16, 0],
      ];
      if (map.getLayer(ids.fillId)) map.setPaintProperty(ids.fillId, "fill-opacity", fillOpacityExpr);
      if (map.getLayer(ids.outlineId)) {
        map.setPaintProperty(ids.outlineId, "line-opacity", lineOpacity);
        map.setPaintProperty(
          ids.outlineId,
          "line-width",
          ["interpolate", ["linear"], ["zoom"], 8, 2.5, 12, 2, 16, 1.25],
        );
      }
      if (map.getLayer(ids.centroidId)) {
        map.setPaintProperty(ids.centroidId, "circle-opacity", circleOpacityExpr);
        map.setPaintProperty(ids.centroidId, "circle-stroke-opacity", circleStrokeOpacity);
      }
    };

    const pulsingLayers = (overlayLayers ?? []).filter(
      (layer) => layer.visible !== false && layer.pulse && (layer.pulseUntil ?? 0) > Date.now(),
    );
    if (pulsingLayers.length === 0) return;

    let frameId = 0;
    const tick = () => {
      const now = Date.now();
      const activeLayers = pulsingLayers.filter((layer) => (layer.pulseUntil ?? 0) > now);
      if (activeLayers.length === 0) {
        for (const layer of pulsingLayers) resetLayerStyle(layer);
        return;
      }
      const phase = (Math.sin(now / 260) + 1) / 2;
      for (const layer of activeLayers) {
        const ids = overlayLayerIds(layer.layer_key);
        const baseOpacity = layer.opacity ?? 0.82;
        const fillOpacity = Math.max(0.22, Math.min(0.98, 0.18 + phase * baseOpacity * 0.95));
        const lineOpacity = Math.max(0.78, Math.min(1, 0.82 + phase * 0.18));
        const lineWidth = 2.8 + phase * 2.8;
        const circleOpacity = Math.max(0.8, Math.min(1, 0.84 + phase * 0.16));

        if (map.getLayer(ids.fillId)) {
          map.setPaintProperty(ids.fillId, "fill-opacity", fillOpacity);
        }
        if (map.getLayer(ids.outlineId)) {
          map.setPaintProperty(ids.outlineId, "line-opacity", lineOpacity);
          map.setPaintProperty(ids.outlineId, "line-width", lineWidth);
        }
        if (map.getLayer(ids.centroidId)) {
          map.setPaintProperty(ids.centroidId, "circle-opacity", circleOpacity);
          map.setPaintProperty(ids.centroidId, "circle-stroke-opacity", circleOpacity);
        }
      }
      frameId = window.requestAnimationFrame(tick);
    };

    frameId = window.requestAnimationFrame(tick);
    return () => {
      window.cancelAnimationFrame(frameId);
      for (const layer of pulsingLayers) resetLayerStyle(layer);
    };
  }, [overlayLayers, mapReadyVersion]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || mapReadyVersion === 0 || !focusSignal) return;
    fitCollectionBounds(map, focusGeojson, focusOptions);
  }, [focusGeojson, focusOptions, focusSignal, mapReadyVersion]);

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
  const swapped = data.swapped_capacitas;
  const swappedHtml = swapped
    ? `
      <div style="margin-top:8px;border:1px solid #FDBA74;background:#FFF7ED;border-radius:10px;padding:8px;color:#9A3412">
        <div style="font-size:11px;font-weight:800;letter-spacing:.06em;text-transform:uppercase">Comune Capacitas diverso</div>
        <div style="margin-top:3px">
          In GAIA: <strong>${escapeHtml(data.nome_comune || data.codice_catastale || "-")}</strong> ·
          Capacitas/Ruolo: <strong>${escapeHtml(swapped.source_comune_nome || swapped.source_codice_catastale || "-")}</strong>
        </div>
        <div style="font-size:12px">
          Rif. sorgente ${escapeHtml(swapped.source_foglio || "-")}/${escapeHtml(swapped.source_particella || "-")}${swapped.source_subalterno ? `/${escapeHtml(swapped.source_subalterno)}` : ""}
          ${swapped.anno_tributario_latest ? ` · anno ${escapeHtml(String(swapped.anno_tributario_latest))}` : ""}
        </div>
      </div>
    `
    : "";

  return `
    <div style="font-family:system-ui,sans-serif;font-size:13px;line-height:1.5;color:#111827">
      <div style="font-weight:700;margin-bottom:4px">${escapeHtml(data.cfm || "Particella")}</div>
      <div>Comune: ${escapeHtml(data.nome_comune || data.codice_catastale || "-")}</div>
      <div>Foglio: ${escapeHtml(data.foglio || "-")} - Part.: ${escapeHtml(data.particella || "-")}${data.subalterno ? ` - Sub: ${escapeHtml(data.subalterno)}` : ""}</div>
      <div>Superficie: ${escapeHtml(superficieText)}</div>
      <div>Distretto: ${escapeHtml(data.num_distretto || "-")}${data.nome_distretto ? ` (${escapeHtml(data.nome_distretto)})` : ""}</div>
      <div style="margin-top:4px">${anomalie}</div>
      ${swappedHtml}
      <div style="margin-top:8px">
        <a href="/catasto/particelle/${encodeURIComponent(data.id)}" target="_blank" rel="noopener noreferrer" style="color:#4F46E5;font-weight:600;text-decoration:none">
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
