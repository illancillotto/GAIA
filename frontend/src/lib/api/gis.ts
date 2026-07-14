import { createQueryString, request } from "@/lib/api";
import type {
  GisCatalogAnnotation,
  GisCatalogAnnotationFilters,
  GisCatalogAnnotationSaveInput,
  GisCatalogAnnotationStatus,
  GisCatalogAnnotationUpdateInput,
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

export async function listGisLayerAnnotations(
  token: string,
  layerId: string,
  filters: GisCatalogAnnotationFilters = {},
): Promise<GisCatalogAnnotation[]> {
  const query = createQueryString({
    status: filters.status,
    feature_id: cleanQueryValue(filters.featureId),
  });

  return request<GisCatalogAnnotation[]>(`/gis/layers/${layerId}/annotations${query}`, {
    headers: authHeaders(token),
  });
}

export async function createGisLayerAnnotation(
  token: string,
  layerId: string,
  input: GisCatalogAnnotationSaveInput,
): Promise<GisCatalogAnnotation> {
  return request<GisCatalogAnnotation>(`/gis/layers/${layerId}/annotations`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({
      feature_id: cleanQueryValue(input.featureId),
      title: input.title,
      body: input.body,
      geometry: input.geometry,
      attachment_refs: input.attachmentRefs ?? [],
    }),
  });
}

export async function updateGisLayerAnnotation(
  token: string,
  layerId: string,
  annotationId: string,
  input: GisCatalogAnnotationUpdateInput,
): Promise<GisCatalogAnnotation> {
  return request<GisCatalogAnnotation>(`/gis/layers/${layerId}/annotations/${annotationId}`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify({
      title: input.title,
      body: input.body,
      geometry: input.geometry,
      attachment_refs: input.attachmentRefs,
    }),
  });
}

export async function setGisLayerAnnotationStatus(
  token: string,
  layerId: string,
  annotationId: string,
  status: Exclude<GisCatalogAnnotationStatus, "open">,
): Promise<GisCatalogAnnotation> {
  const actionPath = status === "in_review" ? "in-review" : status === "closed" ? "close" : "reject";
  return request<GisCatalogAnnotation>(`/gis/layers/${layerId}/annotations/${annotationId}/${actionPath}`, {
    method: "POST",
    headers: authHeaders(token),
  });
}
