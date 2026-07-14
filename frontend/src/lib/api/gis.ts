import { createQueryString, request } from "@/lib/api";
import type {
  GisCatalogLayerFilters,
  GisCatalogLayerListResponse,
  GisCatalogLayerPermission,
  GisCatalogLayerPermissionUpsertInput,
} from "@/types/gis";

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

export async function listGisLayerPermissions(token: string, layerId: string): Promise<GisCatalogLayerPermission[]> {
  return request<GisCatalogLayerPermission[]>(`/gis/layers/${layerId}/permissions`, {
    headers: authHeaders(token),
  });
}

export async function upsertGisLayerPermission(
  token: string,
  layerId: string,
  input: GisCatalogLayerPermissionUpsertInput,
): Promise<GisCatalogLayerPermission> {
  return request<GisCatalogLayerPermission>(`/gis/layers/${layerId}/permissions`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({
      principal_type: input.principalType,
      principal_key: input.principalKey,
      access_level: input.accessLevel,
    }),
  });
}

export async function revokeGisLayerPermission(token: string, layerId: string, permissionId: string): Promise<void> {
  await request<void>(`/gis/layers/${layerId}/permissions/${permissionId}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
}
