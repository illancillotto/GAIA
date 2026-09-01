import { request, requestBlob } from "@/lib/api";

export type GisTerritorioLayer = {
  id: string;
  name: string;
  title: string;
  description: string | null;
  theme: string;
  source: string;
  proxy_wms_url: string;
  legend_url: string;
  default_opacity: number;
  render_order: number;
  queryable: "wfs_queryable" | "wms_infoable" | "wms_visual_only";
  attribution: string;
};

export type GisTerritorioLayerGroup = {
  theme: string;
  label: string;
  layers: GisTerritorioLayer[];
};

export type GisTerritorioLayerListResponse = {
  groups: GisTerritorioLayerGroup[];
  total: number;
};

export type GisInterrogazioneStatus = "ok" | "empty" | "failed" | "skipped";

export type GisInterrogazioneSource = {
  source_id: string;
  title: string;
  status: GisInterrogazioneStatus;
  duration_ms: number;
  data: Array<Record<string, unknown>>;
  message: string | null;
};

export type GisInterrogazioneLevel = {
  key: "gaia" | "catasto_ufficiale" | "territorio";
  sources: GisInterrogazioneSource[];
};

export type GisInterrogazioneResponse = {
  lon: number;
  lat: number;
  srid: number;
  radius_m: number;
  gaia: GisInterrogazioneLevel;
  catasto_ufficiale: GisInterrogazioneLevel;
  territorio: GisInterrogazioneLevel;
};

export type GisSchedaTerritoriale = {
  id: string;
  particella_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  artifact_path: string | null;
  checksum_sha256: string | null;
  source_snapshot: Record<string, unknown>;
  error_message: string | null;
};

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

export function listGisTerritorioLayers(
  token: string,
): Promise<GisTerritorioLayerListResponse> {
  return request<GisTerritorioLayerListResponse>("/gis/territorio/layers", {
    headers: authHeaders(token),
  });
}

export function getGisTerritorioMunicipalities(
  token: string,
  layerId: string,
): Promise<GeoJSON.FeatureCollection> {
  const query = new URLSearchParams({
    request: "GetFeature",
    count: "500",
    srsname: "EPSG:4326",
    outputformat: "application/json",
  });
  return request<GeoJSON.FeatureCollection>(`/gis/external/${layerId}/wfs?${query.toString()}`, {
    headers: authHeaders(token),
  });
}

export function interrogaGisTerritorio(
  token: string,
  body: { lon: number; lat: number; layer_ids: string[] },
): Promise<GisInterrogazioneResponse> {
  return request<GisInterrogazioneResponse>("/gis/interroga", {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function createGisSchedaTerritoriale(
  token: string,
  particellaId: string,
): Promise<GisSchedaTerritoriale> {
  return request<GisSchedaTerritoriale>("/gis/scheda-territoriale", {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ particella_id: particellaId }),
  });
}

export function getGisSchedaTerritoriale(
  token: string,
  sheetId: string,
): Promise<GisSchedaTerritoriale> {
  return request<GisSchedaTerritoriale>(`/gis/scheda-territoriale/${sheetId}`, {
    headers: authHeaders(token),
  });
}

export function downloadGisSchedaTerritoriale(
  token: string,
  sheetId: string,
): Promise<Blob> {
  return requestBlob(`/gis/scheda-territoriale/${sheetId}/pdf`, {
    headers: authHeaders(token),
  });
}

export function getGisTerritorioLegend(
  token: string,
  legendUrl: string,
): Promise<Blob> {
  return requestBlob(legendUrl, { headers: authHeaders(token) });
}
