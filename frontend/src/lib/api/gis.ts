import { createQueryString, request } from "@/lib/api";
import type {
  GisCatalogAnnotation,
  GisCatalogAnnotationFilters,
  GisCatalogAnnotationSaveInput,
  GisCatalogAnnotationStatus,
  GisCatalogAnnotationUpdateInput,
  GisCatalogChangeRequest,
  GisCatalogChangeRequestFilters,
  GisCatalogChangeRequestSaveInput,
  GisCatalogChangeRequestStatus,
  GisCatalogChangeRequestUpdateInput,
  GisCatalogDashboardResponse,
  GisCatalogLayerFilters,
  GisCatalogLayerListResponse,
  GisCatalogLayerPermission,
  GisCatalogLayerPermissionUpsertInput,
  GisShapefileImport,
  GisShapefileImportCreateInput,
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

export async function getGisCatalogDashboard(token: string): Promise<GisCatalogDashboardResponse> {
  return request<GisCatalogDashboardResponse>("/gis/catalog/dashboard", {
    headers: authHeaders(token),
  });
}

export async function createGisShapefileImport(
  token: string,
  input: GisShapefileImportCreateInput,
): Promise<GisShapefileImport> {
  const formData = new FormData();
  formData.append("file", input.file);
  formData.append("workspace", input.workspace);
  formData.append("target_layer_name", input.targetLayerName);
  formData.append("target_layer_title", input.targetLayerTitle);
  formData.append("source_srid", String(input.sourceSrid));
  if (cleanQueryValue(input.domainModule)) formData.append("domain_module", cleanQueryValue(input.domainModule) as string);
  if (cleanQueryValue(input.officialSource)) formData.append("official_source", cleanQueryValue(input.officialSource) as string);
  if (cleanQueryValue(input.encoding)) formData.append("encoding", cleanQueryValue(input.encoding) as string);

  return request<GisShapefileImport>("/gis/imports/shapefile", {
    method: "POST",
    headers: authHeaders(token),
    body: formData,
  });
}

export async function getGisShapefileImport(token: string, importId: string): Promise<GisShapefileImport> {
  return request<GisShapefileImport>(`/gis/imports/${importId}`, {
    headers: authHeaders(token),
  });
}

export async function validateGisShapefileImport(token: string, importId: string): Promise<GisShapefileImport> {
  return request<GisShapefileImport>(`/gis/imports/${importId}/validate`, {
    method: "POST",
    headers: authHeaders(token),
  });
}

export async function rejectGisShapefileImport(token: string, importId: string): Promise<GisShapefileImport> {
  return request<GisShapefileImport>(`/gis/imports/${importId}/reject`, {
    method: "POST",
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

export async function listGisChangeRequests(
  token: string,
  filters: GisCatalogChangeRequestFilters = {},
): Promise<GisCatalogChangeRequest[]> {
  const query = createQueryString({
    status: filters.status,
    layer_id: cleanQueryValue(filters.layerId),
  });

  return request<GisCatalogChangeRequest[]>(`/gis/change-requests${query}`, {
    headers: authHeaders(token),
  });
}

export async function createGisLayerChangeRequest(
  token: string,
  layerId: string,
  input: GisCatalogChangeRequestSaveInput,
): Promise<GisCatalogChangeRequest> {
  return request<GisCatalogChangeRequest>(`/gis/layers/${layerId}/change-requests`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({
      feature_id: cleanQueryValue(input.featureId),
      change_type: input.changeType,
      payload: input.payload,
      justification: cleanQueryValue(input.justification),
    }),
  });
}

export async function updateGisChangeRequest(
  token: string,
  changeRequestId: string,
  input: GisCatalogChangeRequestUpdateInput,
): Promise<GisCatalogChangeRequest> {
  return request<GisCatalogChangeRequest>(`/gis/change-requests/${changeRequestId}`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify({
      feature_id: cleanQueryValue(input.featureId),
      change_type: input.changeType,
      payload: input.payload,
      justification: cleanQueryValue(input.justification),
    }),
  });
}

export async function setGisChangeRequestStatus(
  token: string,
  changeRequestId: string,
  status: Exclude<GisCatalogChangeRequestStatus, "submitted">,
  reviewNotes?: string,
): Promise<GisCatalogChangeRequest> {
  const actionPath =
    status === "needs_changes" ? "request-changes" : status === "approved" ? "approve" : status === "rejected" ? "reject" : "apply";
  const body = status === "applied" ? undefined : JSON.stringify({ review_notes: cleanQueryValue(reviewNotes) });
  return request<GisCatalogChangeRequest>(`/gis/change-requests/${changeRequestId}/${actionPath}`, {
    method: "POST",
    headers: authHeaders(token),
    body,
  });
}
