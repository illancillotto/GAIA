import type { CatDistretto } from "@/types/catasto";
import type { GisSearchResponse } from "@/types/gis";

export type TerritorioSearchKind = "particella" | "distretto" | "pdc" | "comune" | "coordinata";
export type TerritorioSearchBbox = [number, number, number, number];

export type TerritorioSearchResult = {
  id: string;
  kind: TerritorioSearchKind;
  label: string;
  detail: string;
  source: string;
  bbox?: TerritorioSearchBbox;
  center?: [number, number];
  feature?: GeoJSON.Feature;
};

export const GAIA_COMPRENSORIO_BBOX: TerritorioSearchBbox = [8.39, 39.62, 8.93, 40.13];

function visitCoordinates(value: unknown, visit: (lon: number, lat: number) => void): void {
  if (!Array.isArray(value)) return;
  if (value.length >= 2 && typeof value[0] === "number" && typeof value[1] === "number") {
    visit(value[0], value[1]);
    return;
  }
  for (const child of value) visitCoordinates(child, visit);
}

export function geometryBbox(geometry: GeoJSON.Geometry | null | undefined): TerritorioSearchBbox | null {
  if (!geometry || geometry.type === "GeometryCollection") {
    if (geometry?.type !== "GeometryCollection") return null;
    const boxes = geometry.geometries.map(geometryBbox).filter((box): box is TerritorioSearchBbox => box !== null);
    return boxes.length ? mergeBboxes(boxes) : null;
  }
  let minLon = Infinity;
  let minLat = Infinity;
  let maxLon = -Infinity;
  let maxLat = -Infinity;
  visitCoordinates(geometry.coordinates, (lon, lat) => {
    minLon = Math.min(minLon, lon);
    minLat = Math.min(minLat, lat);
    maxLon = Math.max(maxLon, lon);
    maxLat = Math.max(maxLat, lat);
  });
  return Number.isFinite(minLon) ? [minLon, minLat, maxLon, maxLat] : null;
}

function mergeBboxes(boxes: TerritorioSearchBbox[]): TerritorioSearchBbox {
  return boxes.reduce<TerritorioSearchBbox>(
    (merged, box) => [
      Math.min(merged[0], box[0]),
      Math.min(merged[1], box[1]),
      Math.max(merged[2], box[2]),
      Math.max(merged[3], box[3]),
    ],
    boxes[0],
  );
}

export function isInGaiaComprensorio(result: TerritorioSearchResult): boolean {
  const bbox = result.bbox ?? (result.center
    ? [result.center[0], result.center[1], result.center[0], result.center[1]]
    : null);
  if (!bbox) return false;
  return bbox[2] >= GAIA_COMPRENSORIO_BBOX[0]
    && bbox[0] <= GAIA_COMPRENSORIO_BBOX[2]
    && bbox[3] >= GAIA_COMPRENSORIO_BBOX[1]
    && bbox[1] <= GAIA_COMPRENSORIO_BBOX[3];
}

export function parcelResults(response: GisSearchResponse): TerritorioSearchResult[] {
  return response.results.map((item) => {
    const feature = response.geojson?.features.find((entry) => String(entry.properties?.id ?? "") === item.id);
    return {
      id: `particella:${item.id}`,
      kind: "particella",
      label: `${item.nome_comune ?? item.codice_catastale ?? "Comune ND"} - Fg. ${item.foglio ?? "-"}, Part. ${item.particella ?? "-"}`,
      detail: item.utenza_denominazione ?? item.utenza_cf ?? "Particella catastale GAIA",
      source: "GAIA Catasto",
      feature,
      bbox: geometryBbox(feature?.geometry) ?? undefined,
    };
  });
}

export function districtResults(districts: CatDistretto[], query: string): TerritorioSearchResult[] {
  const normalized = query.trim().toLocaleLowerCase("it");
  return districts
    .filter((item) => `${item.num_distretto} ${item.nome_distretto ?? ""}`.toLocaleLowerCase("it").includes(normalized))
    .slice(0, 8)
    .map((item) => ({
      id: `distretto:${item.id}`,
      kind: "distretto",
      label: `Distretto ${item.num_distretto}`,
      detail: item.nome_distretto ?? "Distretto irriguo GAIA",
      source: "GAIA Distretti",
    }));
}

const MUNICIPALITY_FIELDS = ["comune", "nome_comune", "denominazione", "nome", "name"];

function propertyText(properties: GeoJSON.GeoJsonProperties, fields: string[]): string | null {
  if (!properties) return null;
  const entries = Object.entries(properties);
  for (const field of fields) {
    const entry = entries.find(([key]) => key.toLocaleLowerCase("it") === field);
    if (entry && entry[1] != null && String(entry[1]).trim()) return String(entry[1]).trim();
  }
  return null;
}

export function municipalityResults(collection: GeoJSON.FeatureCollection, query: string): TerritorioSearchResult[] {
  const normalized = query.trim().toLocaleLowerCase("it");
  return collection.features.flatMap((feature, index) => {
    const label = propertyText(feature.properties, MUNICIPALITY_FIELDS);
    if (!label?.toLocaleLowerCase("it").includes(normalized)) return [];
    const bbox = geometryBbox(feature.geometry);
    if (!bbox) return [];
    return [{
      id: `comune:${String(feature.id ?? index)}`,
      kind: "comune" as const,
      label,
      detail: "Limite amministrativo comunale",
      source: "RAS SITR",
      bbox,
    }];
  }).slice(0, 8);
}

export function deliveryPointResults(features: GeoJSON.Feature[], query: string): TerritorioSearchResult[] {
  const normalized = query.trim().toLocaleLowerCase("it");
  const seen = new Set<string>();
  return features.flatMap((feature) => {
    const id = String(feature.properties?.id ?? feature.id ?? "");
    const code = propertyText(feature.properties, ["punto_consegna_code", "punto_consegna", "code"]);
    const district = propertyText(feature.properties, ["distretto_code", "distretto"]);
    const haystack = `${code ?? ""} ${district ?? ""}`.toLocaleLowerCase("it");
    const bbox = geometryBbox(feature.geometry);
    if (!id || !code || seen.has(id) || !haystack.includes(normalized) || !bbox) return [];
    seen.add(id);
    return [{
      id: `pdc:${id}`,
      kind: "pdc" as const,
      label: `PdC ${code}`,
      detail: district ? `Distretto ${district}` : "Punto di consegna GAIA",
      source: "GAIA PdC",
      bbox,
      feature,
    }];
  }).slice(0, 8);
}
