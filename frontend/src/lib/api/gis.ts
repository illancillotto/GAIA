import { createQueryString, request, requestBlob } from "@/lib/api";
import type {
  GisAuditLogListResponse,
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
  GisCatalogLayerFeatureListResponse,
  GisCatalogLayer,
  GisCatalogLayerCreateInput,
  GisCatalogLayerExport,
  GisCatalogLayerExportInput,
  GisCatalogLayerExportListResponse,
  GisCatalogLayerFilters,
  GisCatalogLayerListResponse,
  GisCatalogLayerMetadataUpdateInput,
  GisCatalogLayerPermission,
  GisCatalogLayerPermissionUpsertInput,
  GisOgcPocResponse,
  GisQgisGovernanceResponse,
  GisRuntimeHealthResponse,
  GisShapefileImport,
  GisShapefileImportChangeRequestInput,
  GisShapefileImportChangeRequestResponse,
  GisShapefileImportCreateInput,
  GisShapefileImportListResponse,
  GisShapefileImportPreview,
  GisShapefileImportStatus,
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

export async function getGisCatalogLayer(
  token: string,
  layerId: string,
): Promise<GisCatalogLayer> {
  return request<GisCatalogLayer>(`/gis/layers/${layerId}`, {
    headers: authHeaders(token),
  });
}

export async function createGisCatalogLayer(
  token: string,
  input: GisCatalogLayerCreateInput,
): Promise<GisCatalogLayer> {
  return request<GisCatalogLayer>("/gis/layers", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({
      workspace: input.workspace,
      name: input.name,
      title: input.title,
      description: cleanQueryValue(input.description),
      domain_module: cleanQueryValue(input.domainModule),
      source_type: cleanQueryValue(input.sourceType) ?? "postgis",
      official_source: cleanQueryValue(input.officialSource) ?? "postgis",
      postgis_schema: cleanQueryValue(input.postgisSchema) ?? "public",
      postgis_table: cleanQueryValue(input.postgisTable),
      geometry_column: cleanQueryValue(input.geometryColumn) ?? "geometry",
      geometry_type: cleanQueryValue(input.geometryType),
      srid: input.srid,
      feature_id_column: cleanQueryValue(input.featureIdColumn) ?? "id",
      martin_layer_id: cleanQueryValue(input.martinLayerId),
      nas_export_root: cleanQueryValue(input.nasExportRoot),
    }),
  });
}

export async function updateGisCatalogLayerMetadata(
  token: string,
  layerId: string,
  input: GisCatalogLayerMetadataUpdateInput,
): Promise<GisCatalogLayer> {
  return request<GisCatalogLayer>(`/gis/layers/${layerId}/metadata`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify({
      title: cleanQueryValue(input.title),
      description: cleanQueryValue(input.description),
      ogc_service_url: cleanQueryValue(input.ogcServiceUrl),
      qgis_project_path: cleanQueryValue(input.qgisProjectPath),
      nas_export_root: cleanQueryValue(input.nasExportRoot),
    }),
  });
}

export async function setGisCatalogLayerActive(
  token: string,
  layerId: string,
  active: boolean,
): Promise<GisCatalogLayer> {
  return request<GisCatalogLayer>(
    `/gis/layers/${layerId}/${active ? "activate" : "deactivate"}`,
    {
      method: "POST",
      headers: authHeaders(token),
    },
  );
}

export async function requestGisCatalogLayerExport(
  token: string,
  layerId: string,
  input: GisCatalogLayerExportInput,
): Promise<GisCatalogLayerExport> {
  return request<GisCatalogLayerExport>(
    `/gis/layers/${layerId}/export-shapefile`,
    {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({
        version_label: cleanQueryValue(input.versionLabel),
        nas_path: cleanQueryValue(input.nasPath),
      }),
    },
  );
}

export async function listGisCatalogLayerExports(
  token: string,
  filters: {
    layerId?: string;
    status?: string;
    limit?: number;
    offset?: number;
  } = {},
): Promise<GisCatalogLayerExportListResponse> {
  const query = createQueryString({
    layer_id: cleanQueryValue(filters.layerId),
    status: cleanQueryValue(filters.status),
    limit: String(filters.limit ?? 25),
    offset: String(filters.offset ?? 0),
  });
  return request<GisCatalogLayerExportListResponse>(`/gis/exports${query}`, {
    headers: authHeaders(token),
  });
}

export async function listGisAuditLogs(
  token: string,
  filters: {
    layerId?: string;
    eventType?: string;
    limit?: number;
    offset?: number;
  } = {},
): Promise<GisAuditLogListResponse> {
  const query = createQueryString({
    layer_id: cleanQueryValue(filters.layerId),
    event_type: cleanQueryValue(filters.eventType),
    limit: String(filters.limit ?? 25),
    offset: String(filters.offset ?? 0),
  });
  return request<GisAuditLogListResponse>(`/gis/audit${query}`, {
    headers: authHeaders(token),
  });
}

export async function getGisQgisGovernance(
  token: string,
): Promise<GisQgisGovernanceResponse> {
  return request<GisQgisGovernanceResponse>("/gis/qgis/governance", {
    headers: authHeaders(token),
  });
}

export async function getGisCatalogDashboard(
  token: string,
): Promise<GisCatalogDashboardResponse> {
  return request<GisCatalogDashboardResponse>("/gis/catalog/dashboard", {
    headers: authHeaders(token),
  });
}

export async function getGisRuntimeHealth(
  token: string,
): Promise<GisRuntimeHealthResponse> {
  return request<GisRuntimeHealthResponse>("/gis/runtime-health", {
    headers: authHeaders(token),
  });
}

export async function listGisLayerFeatures(
  token: string,
  layerId: string,
  query?: string,
  limit = 20,
  offset = 0,
): Promise<GisCatalogLayerFeatureListResponse> {
  const queryString = createQueryString({
    query: cleanQueryValue(query),
    limit: String(limit),
    offset: String(offset),
  });
  return request<GisCatalogLayerFeatureListResponse>(
    `/gis/layers/${layerId}/features${queryString}`,
    {
      headers: authHeaders(token),
    },
  );
}

export async function downloadGisQgisProject(token: string): Promise<Blob> {
  return requestBlob("/gis/qgis/project", {
    headers: authHeaders(token),
  });
}

export async function getGisOgcPoc(token: string): Promise<GisOgcPocResponse> {
  return request<GisOgcPocResponse>("/gis/ogc/poc", {
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
  const sourceSrid =
    input.sourceSrid == null
      ? undefined
      : cleanQueryValue(String(input.sourceSrid));
  if (sourceSrid) formData.append("source_srid", sourceSrid);
  if (cleanQueryValue(input.domainModule))
    formData.append(
      "domain_module",
      cleanQueryValue(input.domainModule) as string,
    );
  if (cleanQueryValue(input.officialSource))
    formData.append(
      "official_source",
      cleanQueryValue(input.officialSource) as string,
    );
  if (input.encoding !== undefined)
    formData.append("encoding", cleanQueryValue(input.encoding) ?? "");

  return request<GisShapefileImport>("/gis/imports/shapefile", {
    method: "POST",
    headers: authHeaders(token),
    body: formData,
  });
}

export async function getGisShapefileImport(
  token: string,
  importId: string,
): Promise<GisShapefileImport> {
  return request<GisShapefileImport>(`/gis/imports/${importId}`, {
    headers: authHeaders(token),
  });
}

export async function listGisShapefileImports(
  token: string,
  filters: {
    status?: GisShapefileImportStatus;
    limit?: number;
    offset?: number;
  } = {},
): Promise<GisShapefileImportListResponse> {
  const query = createQueryString({
    status: filters.status,
    limit: String(filters.limit ?? 25),
    offset: String(filters.offset ?? 0),
  });
  return request<GisShapefileImportListResponse>(`/gis/imports${query}`, {
    headers: authHeaders(token),
  });
}

export async function previewGisShapefileImport(
  token: string,
  importId: string,
  limit = 5,
  offset = 0,
): Promise<GisShapefileImportPreview> {
  const query = createQueryString({
    limit: String(limit),
    offset: String(offset),
  });
  return request<GisShapefileImportPreview>(
    `/gis/imports/${importId}/preview${query}`,
    {
      headers: authHeaders(token),
    },
  );
}

export async function createGisShapefileImportChangeRequests(
  token: string,
  importId: string,
  input: GisShapefileImportChangeRequestInput,
): Promise<GisShapefileImportChangeRequestResponse> {
  return request<GisShapefileImportChangeRequestResponse>(
    `/gis/imports/${importId}/change-requests`,
    {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({
        target_layer_id: input.targetLayerId,
        justification: cleanQueryValue(input.justification),
        limit: input.limit,
        offset: input.offset,
      }),
    },
  );
}

export async function validateGisShapefileImport(
  token: string,
  importId: string,
): Promise<GisShapefileImport> {
  return request<GisShapefileImport>(`/gis/imports/${importId}/validate`, {
    method: "POST",
    headers: authHeaders(token),
  });
}

export async function rejectGisShapefileImport(
  token: string,
  importId: string,
): Promise<GisShapefileImport> {
  return request<GisShapefileImport>(`/gis/imports/${importId}/reject`, {
    method: "POST",
    headers: authHeaders(token),
  });
}

export async function publishGisShapefileImport(
  token: string,
  importId: string,
): Promise<GisShapefileImport> {
  return request<GisShapefileImport>(`/gis/imports/${importId}/publish`, {
    method: "POST",
    headers: authHeaders(token),
  });
}

export async function listGisLayerPermissions(
  token: string,
  layerId: string,
): Promise<GisCatalogLayerPermission[]> {
  return request<GisCatalogLayerPermission[]>(
    `/gis/layers/${layerId}/permissions`,
    {
      headers: authHeaders(token),
    },
  );
}

export async function upsertGisLayerPermission(
  token: string,
  layerId: string,
  input: GisCatalogLayerPermissionUpsertInput,
): Promise<GisCatalogLayerPermission> {
  return request<GisCatalogLayerPermission>(
    `/gis/layers/${layerId}/permissions`,
    {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({
        principal_type: input.principalType,
        principal_key: input.principalKey,
        access_level: input.accessLevel,
      }),
    },
  );
}

export async function revokeGisLayerPermission(
  token: string,
  layerId: string,
  permissionId: string,
): Promise<void> {
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

  return request<GisCatalogAnnotation[]>(
    `/gis/layers/${layerId}/annotations${query}`,
    {
      headers: authHeaders(token),
    },
  );
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
  return request<GisCatalogAnnotation>(
    `/gis/layers/${layerId}/annotations/${annotationId}`,
    {
      method: "PATCH",
      headers: authHeaders(token),
      body: JSON.stringify({
        title: input.title,
        body: input.body,
        geometry: input.geometry,
        attachment_refs: input.attachmentRefs,
      }),
    },
  );
}

export async function setGisLayerAnnotationStatus(
  token: string,
  layerId: string,
  annotationId: string,
  status: Exclude<GisCatalogAnnotationStatus, "open">,
): Promise<GisCatalogAnnotation> {
  const actionPath =
    status === "in_review"
      ? "in-review"
      : status === "closed"
        ? "close"
        : "reject";
  return request<GisCatalogAnnotation>(
    `/gis/layers/${layerId}/annotations/${annotationId}/${actionPath}`,
    {
      method: "POST",
      headers: authHeaders(token),
    },
  );
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
  return request<GisCatalogChangeRequest>(
    `/gis/layers/${layerId}/change-requests`,
    {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({
        feature_id: cleanQueryValue(input.featureId),
        change_type: input.changeType,
        payload: input.payload,
        justification: cleanQueryValue(input.justification),
      }),
    },
  );
}

export async function updateGisChangeRequest(
  token: string,
  changeRequestId: string,
  input: GisCatalogChangeRequestUpdateInput,
): Promise<GisCatalogChangeRequest> {
  return request<GisCatalogChangeRequest>(
    `/gis/change-requests/${changeRequestId}`,
    {
      method: "PATCH",
      headers: authHeaders(token),
      body: JSON.stringify({
        feature_id: cleanQueryValue(input.featureId),
        change_type: input.changeType,
        payload: input.payload,
        justification: cleanQueryValue(input.justification),
      }),
    },
  );
}

export async function setGisChangeRequestStatus(
  token: string,
  changeRequestId: string,
  status: Exclude<GisCatalogChangeRequestStatus, "submitted">,
  reviewNotes?: string,
): Promise<GisCatalogChangeRequest> {
  const actionPath =
    status === "needs_changes"
      ? "request-changes"
      : status === "approved"
        ? "approve"
        : status === "rejected"
          ? "reject"
          : "apply";
  const body =
    status === "applied"
      ? undefined
      : JSON.stringify({ review_notes: cleanQueryValue(reviewNotes) });
  return request<GisCatalogChangeRequest>(
    `/gis/change-requests/${changeRequestId}/${actionPath}`,
    {
      method: "POST",
      headers: authHeaders(token),
      body,
    },
  );
}
