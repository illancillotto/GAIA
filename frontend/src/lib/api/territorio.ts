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

export function getGisTerritorioLegend(
  token: string,
  legendUrl: string,
): Promise<Blob> {
  return requestBlob(legendUrl, { headers: authHeaders(token) });
}
