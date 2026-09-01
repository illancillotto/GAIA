"use client";

import { useState } from "react";
import type maplibregl from "maplibre-gl";

import {
  catastoGetDistrettoGeojson,
  catastoGisGetDeliveryPointPopup,
  catastoGisSearch,
  catastoListDistretti,
} from "@/lib/api/catasto";
import { getGisTerritorioMunicipalities, type GisTerritorioLayer } from "@/lib/api/territorio";
import {
  formatCatastoGisCoordinateLabel,
  parseCatastoGisCoordinateSearch,
} from "@/lib/catasto-gis-coordinate-search";
import {
  deliveryPointResults,
  districtResults,
  geometryBbox,
  isInGaiaComprensorio,
  municipalityResults,
  parcelResults,
  type TerritorioSearchResult,
} from "./territorio-unified-search";

type SearchMap = Pick<maplibregl.Map, "fitBounds" | "flyTo" | "querySourceFeatures">;

type SearchInput = {
  token: string;
  value: string;
  map: SearchMap | null;
  municipalityLayer: GisTerritorioLayer | null;
};

function loadedDeliveryPoints(map: SearchMap | null): GeoJSON.Feature[] {
  if (!map) return [];
  try {
    return map.querySourceFeatures("delivery-points-source", { sourceLayer: "cat_delivery_points_current" }) as GeoJSON.Feature[];
  } catch {
    return [];
  }
}

async function searchAll({ token, value, map, municipalityLayer }: SearchInput): Promise<TerritorioSearchResult[]> {
  const coordinate = parseCatastoGisCoordinateSearch(value);
  const [parcels, districts, municipalities] = await Promise.all([
    catastoGisSearch(token, { query: value, mode: "auto", limit: 8 }),
    catastoListDistretti(token),
    municipalityLayer
      ? getGisTerritorioMunicipalities(token, municipalityLayer.id)
      : Promise.resolve<GeoJSON.FeatureCollection>({ type: "FeatureCollection", features: [] }),
  ]);
  const coordinateResult: TerritorioSearchResult[] = coordinate ? [{
    id: `coordinata:${coordinate.lat}:${coordinate.lon}`,
    kind: "coordinata",
    label: formatCatastoGisCoordinateLabel(coordinate),
    detail: coordinate.source === "dms" ? "Coordinate DMS" : "Coordinate decimali",
    source: "Coordinate GAIA",
    center: [coordinate.lon, coordinate.lat],
  }] : [];
  return [
    ...coordinateResult,
    ...parcelResults(parcels),
    ...districtResults(districts, value),
    ...deliveryPointResults(loadedDeliveryPoints(map), value),
    ...municipalityResults(municipalities, value),
  ];
}

async function focusResult(map: SearchMap, token: string, result: TerritorioSearchResult): Promise<string | null> {
  let target = result;
  if (result.kind === "distretto") {
    const feature = await catastoGetDistrettoGeojson(token, result.id.slice("distretto:".length));
    target = { ...result, bbox: geometryBbox(feature.geometry as GeoJSON.Geometry) ?? undefined };
  }
  if (result.kind === "pdc") {
    await catastoGisGetDeliveryPointPopup(token, result.id.slice("pdc:".length));
  }
  if (!isInGaiaComprensorio(target)) {
    return "Risultato fuori dal comprensorio GAIA. La mappa non viene spostata.";
  }
  if (target.center) {
    map.flyTo({ center: target.center, zoom: 16 });
  } else {
    const bbox = target.bbox as [number, number, number, number];
    map.fitBounds([[bbox[0], bbox[1]], [bbox[2], bbox[3]]], {
      padding: 48,
      maxZoom: 17,
      duration: 700,
    });
  }
  return null;
}

export function useTerritorioUnifiedSearch({
  token,
  map,
  municipalityLayer,
}: {
  token: string | null;
  map: SearchMap | null;
  municipalityLayer: GisTerritorioLayer | null;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<TerritorioSearchResult[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function runSearch(): Promise<void> {
    const value = query.trim();
    if (!token || !value) {
      setMessage(!token ? "Sessione non disponibile." : "Inserisci un criterio di ricerca.");
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const next = await searchAll({ token, value, map, municipalityLayer });
      setResults(next);
      setMessage(next.length ? null : `Nessun risultato nel comprensorio per “${value}”.`);
    } catch (error) {
      setResults([]);
      setMessage(error instanceof Error ? error.message : "Ricerca GIS non disponibile.");
    } finally {
      setBusy(false);
    }
  }

  async function selectResult(result: TerritorioSearchResult): Promise<void> {
    if (!map || !token) return;
    setMessage(await focusResult(map, token, result));
  }

  function clear(): void {
    setQuery("");
    setResults([]);
    setMessage(null);
  }

  return { query, setQuery, results, busy, message, runSearch, selectResult, clear };
}
