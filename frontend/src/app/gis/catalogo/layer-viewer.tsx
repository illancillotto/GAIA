"use client";

import { useEffect, useRef, useState } from "react";
import { Map as MapLibreMap, NavigationControl, ScaleControl } from "maplibre-gl";
import type { LayerSpecification, StyleSpecification } from "@maplibre/maplibre-gl-style-spec";

import { listGisLayerFeatures } from "@/lib/api/gis";
import {
  WEBGL2_REQUIRED_MESSAGE,
  canCreateWebGL2Context,
  mapInitializationErrorMessage,
  registerMapGPUErrorHandler,
} from "@/lib/maplibre-support";
import type { GisCatalogLayer, GisCatalogLayerFeature } from "@/types/gis";

const SOURCE_ID = "gaia-catalog-layer";
const PAGE_SIZE = 50;
const MAX_FALLBACK_FEATURES = 1000;
const DEFAULT_MIN_ZOOM = 7;
const DEFAULT_MAX_ZOOM = 22;
const CBO_MAP_CENTER: [number, number] = [8.6, 39.85];
const GPU_RESTORE_ERROR = "Impossibile ripristinare la mappa WebGL2.";

export type GisLayerMapData = {
  featureCollection: GeoJSON.FeatureCollection;
  truncated: boolean;
};

export function getMartinZoomRange(metadata: Record<string, unknown>): {
  minzoom: number;
  maxzoom: number;
} {
  const tiles = metadata.tiles;
  if (typeof tiles !== "object" || tiles === null || Array.isArray(tiles)) {
    return { minzoom: DEFAULT_MIN_ZOOM, maxzoom: DEFAULT_MAX_ZOOM };
  }
  const tileMetadata = tiles as Record<string, unknown>;
  return {
    minzoom:
      typeof tileMetadata.minzoom === "number"
        ? tileMetadata.minzoom
        : DEFAULT_MIN_ZOOM,
    maxzoom:
      typeof tileMetadata.maxzoom === "number"
        ? tileMetadata.maxzoom
        : DEFAULT_MAX_ZOOM,
  };
}

export function buildGisLayerStyleLayers(
  geometryType: string | null | undefined,
  sourceLayer?: string,
): LayerSpecification[] {
  const normalizedType = String(geometryType ?? "").toUpperCase();
  const sourceLayerProperty = sourceLayer
    ? { "source-layer": sourceLayer }
    : {};

  if (normalizedType.includes("POINT")) {
    return [
      {
        id: "gaia-catalog-points",
        type: "circle",
        source: SOURCE_ID,
        ...sourceLayerProperty,
        paint: {
          "circle-color": "#d96f32",
          "circle-radius": 6,
          "circle-stroke-color": "#fff8e8",
          "circle-stroke-width": 2,
        },
      },
    ];
  }

  if (normalizedType.includes("LINE")) {
    return [
      {
        id: "gaia-catalog-lines",
        type: "line",
        source: SOURCE_ID,
        ...sourceLayerProperty,
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": "#147a72", "line-width": 4 },
      },
    ];
  }

  return [
    {
      id: "gaia-catalog-polygons",
      type: "fill",
      source: SOURCE_ID,
      ...sourceLayerProperty,
      paint: { "fill-color": "#8fbf68", "fill-opacity": 0.45 },
    },
    {
      id: "gaia-catalog-polygon-borders",
      type: "line",
      source: SOURCE_ID,
      ...sourceLayerProperty,
      paint: { "line-color": "#315d3a", "line-width": 1.5 },
    },
  ];
}

function toMapFeature(
  feature: GisCatalogLayerFeature,
): GeoJSON.Feature | null {
  if (!feature.geometry) return null;
  return {
    type: "Feature",
    id: feature.feature_id,
    geometry: feature.geometry,
    properties: {
      feature_id: feature.feature_id,
      label: feature.label,
    },
  };
}

export async function loadGisLayerMapData(
  token: string,
  layerId: string,
  maxFeatures = MAX_FALLBACK_FEATURES,
): Promise<GisLayerMapData> {
  const items: GisCatalogLayerFeature[] = [];
  let offset = 0;
  let hasMore = true;

  while (hasMore && items.length < maxFeatures) {
    const response = await listGisLayerFeatures(
      token,
      layerId,
      undefined,
      PAGE_SIZE,
      offset,
    );
    items.push(...response.items);
    hasMore = response.has_more;
    if (response.items.length === 0) break;
    offset = response.offset + response.items.length;
  }

  return {
    featureCollection: {
      type: "FeatureCollection",
      features: items.slice(0, maxFeatures).map(toMapFeature).filter(Boolean) as GeoJSON.Feature[],
    },
    truncated: hasMore,
  };
}

const mapStyle: StyleSpecification = {
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

type LayerMapLifecycle = {
  container: HTMLDivElement;
  token: string;
  layer: GisCatalogLayer;
  isCancelled: () => boolean;
  setStatus: (status: "loading" | "ready" | "error") => void;
  setError: (error: string | null) => void;
  setTruncated: (truncated: boolean) => void;
};

async function openGisLayerMap({
  container,
  token,
  layer,
  isCancelled,
  setStatus,
  setError,
  setTruncated,
}: LayerMapLifecycle): Promise<MapLibreMap | null> {
  setStatus("loading");
  setError(null);
  setTruncated(false);
  try {
    if (!canCreateWebGL2Context()) throw new Error(WEBGL2_REQUIRED_MESSAGE);
    const martinZoom = getMartinZoomRange(layer.metadata);
    const mapData = layer.martin_layer_id ? null : await loadGisLayerMapData(token, layer.id);
    if (isCancelled()) return null;
    setTruncated(mapData?.truncated ?? false);

    const map = new MapLibreMap({
      container,
      style: mapStyle,
      center: CBO_MAP_CENTER,
      zoom: layer.martin_layer_id ? martinZoom.minzoom : DEFAULT_MIN_ZOOM,
      attributionControl: {},
    });
    map.addControl(new NavigationControl(), "top-right");
    map.addControl(new ScaleControl({ unit: "metric" }), "bottom-right");
    registerMapGPUErrorHandler(map, (message) => { setError(message); setStatus("error"); }, GPU_RESTORE_ERROR);
    map.on("load", () => {
      if (isCancelled()) return;
      map.addSource(SOURCE_ID, layer.martin_layer_id ? {
        type: "vector",
        tiles: [`${window.location.origin}/tiles/${encodeURIComponent(layer.martin_layer_id)}/{z}/{x}/{y}`],
        minzoom: martinZoom.minzoom,
        maxzoom: martinZoom.maxzoom,
      } : {
        type: "geojson",
        data: mapData!.featureCollection,
      });
      for (const styleLayer of buildGisLayerStyleLayers(layer.geometry_type, layer.martin_layer_id ?? undefined)) {
        map.addLayer(styleLayer);
      }
      setStatus("ready");
    });
    return map;
  } catch (loadError) {
    if (isCancelled()) return null;
    setError(mapInitializationErrorMessage(loadError, "Mappa temporaneamente non disponibile"));
    setStatus("error");
    return null;
  }
}

export function GisLayerViewer({
  token,
  layer,
}: {
  token: string;
  layer: GisCatalogLayer;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [error, setError] = useState<string | null>(null);
  const [truncated, setTruncated] = useState(false);

  useEffect(function synchronizeLayerMap() {
    let cancelled = false;
    let map: MapLibreMap | null = null;
    void openGisLayerMap({
      container: containerRef.current as HTMLDivElement,
      token,
      layer,
      isCancelled: () => cancelled,
      setStatus,
      setError,
      setTruncated,
    }).then((createdMap) => {
      if (cancelled) createdMap?.remove();
      else map = createdMap;
    });
    return () => {
      cancelled = true;
      map?.remove();
    };
  }, [layer.geometry_type, layer.id, layer.martin_layer_id, token]);

  return (
    <div className="relative min-h-[28rem] overflow-hidden rounded-[26px] border border-[#cbd9ce] bg-[#edf4ee] shadow-inner sm:min-h-[38rem]">
      <div ref={containerRef} className="absolute inset-0" aria-label={`Mappa ${layer.title}`} />
      {status === "loading" ? (
        <p className="absolute left-4 top-4 rounded-xl bg-white/95 px-4 py-3 text-sm font-semibold text-[#1D4E35] shadow" role="status">
          Caricamento mappa...
        </p>
      ) : null}
      {status === "error" ? (
        <p className="absolute inset-x-4 top-4 rounded-xl bg-red-50 px-4 py-3 text-sm font-semibold text-red-700 shadow" role="alert">
          {error}
        </p>
      ) : null}
      {status === "ready" && truncated ? (
        <p className="absolute bottom-4 left-4 max-w-md rounded-xl bg-[#fff8dc]/95 px-4 py-3 text-sm text-[#6d5715] shadow" role="status">
          Vista rapida limitata ai primi {MAX_FALLBACK_FEATURES} elementi. Per il dataset completo usa QGIS.
        </p>
      ) : null}
    </div>
  );
}
