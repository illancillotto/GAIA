import { createQueryString, request } from "@/lib/api";
import type { GisCatalogLayerFilters, GisCatalogLayerListResponse } from "@/types/gis";

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

function cleanQueryValue(value: string | undefined): string | undefined {
  const cleaned = value?.trim();
  return cleaned || undefined;
}

export async function listGisCatalogLayers(
  token: string,
  filters: GisCatalogLayerFilters = {},
): Promise<GisCatalogLayerListResponse> {
  const query = createQueryString({
    workspace: cleanQueryValue(filters.workspace),
    domain_module: cleanQueryValue(filters.domainModule),
    source_type: cleanQueryValue(filters.sourceType),
    official_source: cleanQueryValue(filters.officialSource),
    is_active: filters.isActive == null ? undefined : String(filters.isActive),
  });

  return request<GisCatalogLayerListResponse>(`/gis/layers${query}`, {
    headers: authHeaders(token),
  });
}
