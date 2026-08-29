"use client";

import {
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";

import {
  getGisTerritorioLegend,
  listGisTerritorioLayers,
  type GisTerritorioLayer,
  type GisTerritorioLayerGroup,
} from "@/lib/api/territorio";

type MapErrorEvent = {
  error?: Error;
  sourceId?: string;
};

export type TerritorioMapAdapter = {
  addSource: (id: string, source: object) => void;
  getSource: (id: string) => unknown;
  removeSource: (id: string) => void;
  addLayer: (layer: object, beforeId?: string) => void;
  getLayer: (id: string) => unknown;
  removeLayer: (id: string) => void;
  setPaintProperty: (layerId: string, name: string, value: number) => void;
  setTransformRequest: (transform: (url: string) => object) => unknown;
  on: (event: "error", listener: (event: MapErrorEvent) => void) => void;
  off: (event: "error", listener: (event: MapErrorEvent) => void) => void;
};

const SOURCE_PREFIX = "territorio-source-";
const LAYER_PREFIX = "territorio-layer-";
const GAIA_LAYER_ANCHORS = [
  "distretti-fill",
  "distretti-boundaries",
  "particelle-fill",
  "delivery-points",
  "irrigation-canals",
  "dui-2026-fill",
];

function sourceId(layerId: string): string {
  return `${SOURCE_PREFIX}${layerId}`;
}

function mapLayerId(layerId: string): string {
  return `${LAYER_PREFIX}${layerId}`;
}

function wmsTileUrl(layer: GisTerritorioLayer): string {
  const query = new URLSearchParams({
    request: "GetMap",
    crs: "EPSG:3857",
    bbox: "{bbox-epsg-3857}",
    width: "256",
    height: "256",
    format: "image/png",
    transparent: "true",
  });
  return `${layer.proxy_wms_url}?${query.toString()}`;
}

function firstGaiaLayer(map: TerritorioMapAdapter): string | undefined {
  return GAIA_LAYER_ANCHORS.find((candidate) => map.getLayer(candidate));
}

function removeLayer(map: TerritorioMapAdapter, id: string): void {
  const renderedLayerId = mapLayerId(id);
  const renderedSourceId = sourceId(id);
  if (map.getLayer(renderedLayerId)) map.removeLayer(renderedLayerId);
  if (map.getSource(renderedSourceId)) map.removeSource(renderedSourceId);
}

function registerLayer(
  map: TerritorioMapAdapter,
  layer: GisTerritorioLayer,
  opacity: number,
): void {
  const renderedSourceId = sourceId(layer.id);
  const renderedLayerId = mapLayerId(layer.id);
  if (!map.getSource(renderedSourceId)) {
    map.addSource(renderedSourceId, {
      type: "raster",
      tiles: [wmsTileUrl(layer)],
      tileSize: 256,
      attribution: layer.attribution,
    });
  }
  if (!map.getLayer(renderedLayerId)) {
    map.addLayer(
      {
        id: renderedLayerId,
        type: "raster",
        source: renderedSourceId,
        paint: { "raster-opacity": opacity },
      },
      firstGaiaLayer(map),
    );
  } else {
    map.setPaintProperty(renderedLayerId, "raster-opacity", opacity);
  }
}

export type TerritorioLayerState = {
  groups: GisTerritorioLayerGroup[];
  loading: boolean;
  catalogError: string | null;
  enabled: Record<string, boolean>;
  opacity: Record<string, number>;
  layerErrors: Record<string, string>;
  legendUrls: Record<string, string>;
  toggleLayer: (layerId: string) => void;
  setLayerOpacity: (layerId: string, opacity: number) => void;
};

type LayerErrors = Record<string, string>;
type ErrorSetter = Dispatch<SetStateAction<LayerErrors>>;

function useExternalRequestAuth(
  map: TerritorioMapAdapter | null,
  token: string | null,
): void {
  useEffect(() => {
    if (!map) return;
    map.setTransformRequest((url) => {
      const path = new URL(url, window.location.origin).pathname;
      if (!token || !path.startsWith("/gis/external/")) return { url };
      return { url, headers: { Authorization: `Bearer ${token}` } };
    });
  }, [map, token]);
}

function useTerritorioCatalog(token: string | null) {
  const [groups, setGroups] = useState<GisTerritorioLayerGroup[]>([]);
  const [loading, setLoading] = useState(Boolean(token));
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [opacity, setOpacity] = useState<Record<string, number>>({});
  useEffect(() => {
    let active = true;
    if (!token) {
      setGroups([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setCatalogError(null);
    listGisTerritorioLayers(token)
      .then((response) => {
        if (!active) return;
        setGroups(response.groups);
        setOpacity(Object.fromEntries(response.groups.flatMap(
          (group) => group.layers.map((layer) => [layer.id, layer.default_opacity]),
        )));
      })
      .catch((error: unknown) => {
        if (!active) return;
        setCatalogError(error instanceof Error ? error.message : "Catalogo territoriale non disponibile");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [token]);
  return { groups, loading, catalogError, opacity, setOpacity };
}

function useMapLayerSynchronization(
  map: TerritorioMapAdapter | null,
  groups: GisTerritorioLayerGroup[],
  enabled: Record<string, boolean>,
  opacity: Record<string, number>,
  setLayerErrors: ErrorSetter,
): void {
  useEffect(() => {
    if (!map) return;
    for (const layer of groups.flatMap((group) => group.layers)) {
      try {
        if (enabled[layer.id]) {
          registerLayer(map, layer, opacity[layer.id] ?? layer.default_opacity);
        } else {
          removeLayer(map, layer.id);
        }
      } catch (error) {
        setLayerErrors((current) => ({
          ...current,
          [layer.id]: error instanceof Error ? error.message : "Sorgente non disponibile",
        }));
      }
    }
  }, [enabled, groups, map, opacity, setLayerErrors]);
}

function useMapErrorIsolation(
  map: TerritorioMapAdapter | null,
  setLayerErrors: ErrorSetter,
): void {
  useEffect(() => {
    if (!map) return;
    const handleError = (event: MapErrorEvent) => {
      const layerId = event.sourceId?.startsWith(SOURCE_PREFIX)
        ? event.sourceId.slice(SOURCE_PREFIX.length)
        : null;
      if (!layerId) return;
      setLayerErrors((current) => ({
        ...current,
        [layerId]: event.error?.message || "Sorgente non disponibile",
      }));
    };
    map.on("error", handleError);
    return () => map.off("error", handleError);
  }, [map, setLayerErrors]);
}

function useLegendImages(
  token: string | null,
  groups: GisTerritorioLayerGroup[],
  enabled: Record<string, boolean>,
  setLayerErrors: ErrorSetter,
): Record<string, string> {
  const [legendUrls, setLegendUrls] = useState<Record<string, string>>({});
  const legendUrlsRef = useRef(legendUrls);
  legendUrlsRef.current = legendUrls;
  useEffect(() => {
    if (!token) return;
    const layers = groups.flatMap((group) => group.layers)
      .filter((layer) => enabled[layer.id] && !legendUrls[layer.id]);
    for (const layer of layers) {
      getGisTerritorioLegend(token, layer.legend_url)
        .then((blob) => setLegendUrls((current) => ({
          ...current,
          [layer.id]: URL.createObjectURL(blob),
        })))
        .catch((error: unknown) => setLayerErrors((current) => ({
          ...current,
          [layer.id]: error instanceof Error ? error.message : "Legenda non disponibile",
        })));
    }
  }, [enabled, groups, legendUrls, setLayerErrors, token]);
  useEffect(() => () => {
    for (const url of Object.values(legendUrlsRef.current)) URL.revokeObjectURL(url);
  }, []);
  return legendUrls;
}

function useMapLayerCleanup(
  map: TerritorioMapAdapter | null,
  groups: GisTerritorioLayerGroup[],
): void {
  useEffect(() => () => {
    if (!map) return;
    for (const group of groups) {
      for (const layer of group.layers) removeLayer(map, layer.id);
    }
  }, [groups, map]);
}

export function useTerritorioLayers(
  map: TerritorioMapAdapter | null,
  token: string | null,
): TerritorioLayerState {
  const catalog = useTerritorioCatalog(token);
  const [enabled, setEnabled] = useState<Record<string, boolean>>({});
  const [layerErrors, setLayerErrors] = useState<LayerErrors>({});
  useExternalRequestAuth(map, token);
  useMapLayerSynchronization(map, catalog.groups, enabled, catalog.opacity, setLayerErrors);
  useMapErrorIsolation(map, setLayerErrors);
  const legendUrls = useLegendImages(token, catalog.groups, enabled, setLayerErrors);
  useMapLayerCleanup(map, catalog.groups);

  return {
    groups: catalog.groups,
    loading: catalog.loading,
    catalogError: catalog.catalogError,
    enabled,
    opacity: catalog.opacity,
    layerErrors,
    legendUrls,
    toggleLayer: (layerId) => {
      setLayerErrors((current) => ({ ...current, [layerId]: "" }));
      setEnabled((current) => ({ ...current, [layerId]: !current[layerId] }));
    },
    setLayerOpacity: (layerId, value) => {
      catalog.setOpacity((current) => ({ ...current, [layerId]: value }));
    },
  };
}
