import { createQueryString, request, requestBlob, requestFormDataWithUploadProgress } from "@/lib/api";
import type {
  CatAnomaliaListResponse,
  CatAnomalia,
  CatAdeStatusScanCandidateListResponse,
  CatAdeStatusScanRunResponse,
  CatAdeStatusScanSummary,
  CatAnagraficaBulkSearchRequest,
  CatAnagraficaBulkSearchResponse,
  CatAnagraficaBulkJobDetail,
  CatAnagraficaBulkJobListResponse,
  CatDashboardAdeAlignmentSummary,
  CatDashboardSummary,
  CatColturaOverview,
  CatIndiceRuoloExcludedParticelleResponse,
  CatIndiceRuoloAssignDistrettoRequest,
  CatIndiceRuoloAssignDistrettoResponse,
  CatIndiceOverview,
  CatAnomaliaComuneWizardApplyResponse,
  CatAnomaliaComuneWizardListResponse,
  CatAnomaliaCfWizardApplyResponse,
  CatAnomaliaCfWizardListResponse,
  CatAnomaliaParticellaWizardApplyResponse,
  CatAnomaliaParticellaWizardListResponse,
  CatDistrettiExcelAnalysisResponse,
  CatDistretto,
  CatDistrettoKpi,
  CatImportBatch,
  CatImportStartResponse,
  CatImportSummary,
  CatMeterReading,
  CatMeterReadingImport,
  CatMeterReadingImportPreview,
  CatMeterReadingImportRunResponse,
  CatMeterReadingListResponse,
  CatAnomaliaSummary,
  CatCapacitasImportPreview,
  CatDeliveryPointsImportConfig,
  CatDeliveryPointsGisCacheRefreshResponse,
  CatDeliveryPointsImportRunResponse,
  CatParticella,
  CatParticellaCapacitasSyncResponse,
  CatParticellaConsorzio,
  CatParticellaDetail,
  CatParticellaHistory,
  CatSchemaContributo,
  CatUtenzaIrrigua,
  GeoJSONFeature,
  UUID,
} from "@/types/catasto";
import type {
  AdeAlignmentApplyRequest,
  AdeAlignmentApplyPreviewRequest,
  AdeAlignmentApplyPreviewResponse,
  AdeAlignmentApplyResponse,
  AdeAlignmentReportResponse,
  AdeWfsSyncBboxRequest,
  AdeWfsSyncBboxResponse,
  AdeWfsRunStatusResponse,
  DeliveryPointPopupData,
  Dui2026DomandaDetailResponse,
  Dui2026LayerResponse,
  DuiDomandaDetailResponse,
  DuiLayerResponse,
  GisFilters,
  GisSearchRequest,
  GisSearchResponse,
  GisParticellaRef,
  GisResolveRefsResponse,
  GisSavedSelectionCreate,
  GisSavedSelectionDetail,
  GisSavedSelectionSummary,
  GisSavedSelectionUpdate,
  GisSelectResult,
  ParticellaPopupData,
} from "@/types/gis";

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

export async function catastoGisSelect(
  token: string,
  geometry: GeoJSON.Geometry,
  filters?: GisFilters,
): Promise<GisSelectResult> {
  return request<GisSelectResult>("/catasto/gis/select", {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ geometry, filters }),
  });
}

export async function catastoGisSearch(
  token: string,
  payload: GisSearchRequest,
): Promise<GisSearchResponse> {
  return request<GisSearchResponse>("/catasto/gis/search", {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function catastoGisGetPopup(token: string, id: string): Promise<ParticellaPopupData> {
  return request<ParticellaPopupData>(`/catasto/gis/particella/${id}/popup`, {
    headers: authHeaders(token),
  });
}

export async function catastoGisGetDeliveryPointPopup(token: string, id: string): Promise<DeliveryPointPopupData> {
  return request<DeliveryPointPopupData>(`/catasto/gis/delivery-points/${id}`, {
    headers: authHeaders(token),
  });
}

export async function catastoGisGetDuiLatestLayer(token: string): Promise<DuiLayerResponse> {
  return request<DuiLayerResponse>("/catasto/gis/dui/latest-layer", {
    headers: authHeaders(token),
  });
}

export async function catastoGisGetDuiDomandaDetail(
  token: string,
  domandaIrrigua: string,
): Promise<DuiDomandaDetailResponse> {
  return request<DuiDomandaDetailResponse>(`/catasto/gis/dui/domande/${encodeURIComponent(domandaIrrigua)}`, {
    headers: authHeaders(token),
  });
}

export async function catastoGisGetDui2026LatestLayer(token: string): Promise<Dui2026LayerResponse> {
  return catastoGisGetDuiLatestLayer(token);
}

export async function catastoGisGetDui2026DomandaDetail(
  token: string,
  domandaIrrigua: string,
): Promise<Dui2026DomandaDetailResponse> {
  return catastoGisGetDuiDomandaDetail(token, domandaIrrigua);
}

export async function catastoGisSyncAdeWfsBbox(
  token: string,
  payload: AdeWfsSyncBboxRequest,
): Promise<AdeWfsSyncBboxResponse> {
  return request<AdeWfsSyncBboxResponse>("/catasto/gis/ade-wfs/sync-bbox", {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function catastoGisSyncAdeWfsBboxAsync(
  token: string,
  payload: AdeWfsSyncBboxRequest,
): Promise<AdeWfsSyncBboxResponse> {
  return request<AdeWfsSyncBboxResponse>("/catasto/gis/ade-wfs/sync-bbox-async", {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function catastoGisGetAdeWfsRunStatus(
  token: string,
  runId: string,
): Promise<AdeWfsRunStatusResponse> {
  return request<AdeWfsRunStatusResponse>(`/catasto/gis/ade-wfs/runs/${runId}`, {
    headers: authHeaders(token),
  });
}

export async function catastoGisGetLatestAdeWfsRunStatus(
  token: string,
): Promise<AdeWfsRunStatusResponse> {
  return request<AdeWfsRunStatusResponse>("/catasto/gis/ade-wfs/runs/latest", {
    headers: authHeaders(token),
  });
}

export async function catastoGisMarkAdeWfsRunFailed(
  token: string,
  runId: string,
): Promise<AdeWfsRunStatusResponse> {
  return request<AdeWfsRunStatusResponse>(`/catasto/gis/ade-wfs/runs/${runId}/mark-failed`, {
    method: "POST",
    headers: authHeaders(token),
  });
}

export async function catastoGisGetAdeAlignmentReport(
  token: string,
  runId: string,
  params?: { geometryThresholdM?: number },
): Promise<AdeAlignmentReportResponse> {
  const query = createQueryString({
    geometry_threshold_m: params?.geometryThresholdM != null ? String(params.geometryThresholdM) : undefined,
  });
  return request<AdeAlignmentReportResponse>(`/catasto/gis/ade-wfs/alignment-report/${runId}${query}`, {
    headers: authHeaders(token),
  });
}

export async function catastoGisPreviewAdeAlignmentApply(
  token: string,
  runId: string,
  payload: AdeAlignmentApplyPreviewRequest,
): Promise<AdeAlignmentApplyPreviewResponse> {
  return request<AdeAlignmentApplyPreviewResponse>(`/catasto/gis/ade-wfs/alignment-apply-preview/${runId}`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function catastoGisApplyAdeAlignment(
  token: string,
  runId: string,
  payload: AdeAlignmentApplyRequest,
): Promise<AdeAlignmentApplyResponse> {
  return request<AdeAlignmentApplyResponse>(`/catasto/gis/ade-wfs/alignment-apply/${runId}`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function catastoGisExport(
  token: string,
  ids: string[],
  format: "csv" | "geojson" | "xlsx",
): Promise<Blob> {
  const query = new URLSearchParams({ ids: ids.join(","), format });
  return requestBlob(`/catasto/gis/export?${query.toString()}`, {
    headers: authHeaders(token),
  });
}

export async function catastoGisResolveRefs(
  token: string,
  items: GisParticellaRef[],
  params?: { includeGeometry?: boolean },
): Promise<GisResolveRefsResponse> {
  return request<GisResolveRefsResponse>("/catasto/gis/resolve-refs", {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({
      items,
      include_geometry: params?.includeGeometry ?? true,
    }),
  });
}

export async function catastoGisListSavedSelections(token: string): Promise<GisSavedSelectionSummary[]> {
  return request<GisSavedSelectionSummary[]>("/catasto/gis/saved-selections", {
    headers: authHeaders(token),
  });
}

export async function catastoGisGetSavedSelection(token: string, id: string): Promise<GisSavedSelectionDetail> {
  return request<GisSavedSelectionDetail>(`/catasto/gis/saved-selections/${id}`, {
    headers: authHeaders(token),
  });
}

export async function catastoGisCreateSavedSelection(
  token: string,
  payload: GisSavedSelectionCreate,
): Promise<GisSavedSelectionDetail> {
  return request<GisSavedSelectionDetail>("/catasto/gis/saved-selections", {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function catastoGisUpdateSavedSelection(
  token: string,
  id: string,
  payload: GisSavedSelectionUpdate,
): Promise<GisSavedSelectionSummary> {
  return request<GisSavedSelectionSummary>(`/catasto/gis/saved-selections/${id}`, {
    method: "PATCH",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function catastoGisDeleteSavedSelection(token: string, id: string): Promise<void> {
  await request<void>(`/catasto/gis/saved-selections/${id}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
}

export async function catastoUploadShapefile(
  token: string,
  file: File,
  params?: { sourceSrid?: number; onProgress?: (percent: number) => void },
): Promise<CatImportStartResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const query = new URLSearchParams();
  if (params?.sourceSrid != null) query.set("source_srid", String(params.sourceSrid));
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return requestFormDataWithUploadProgress<CatImportStartResponse>(
    `/catasto/import/shapefile/upload${suffix}`,
    formData,
    token,
    params?.onProgress,
  );
}

export async function catastoUploadDistrettiShapefile(
  token: string,
  file: File,
  params?: { sourceSrid?: number; onProgress?: (percent: number) => void },
): Promise<CatImportStartResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const query = new URLSearchParams();
  if (params?.sourceSrid != null) query.set("source_srid", String(params.sourceSrid));
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return requestFormDataWithUploadProgress<CatImportStartResponse>(
    `/catasto/import/distretti/upload${suffix}`,
    formData,
    token,
    params?.onProgress,
  );
}

export async function catastoUploadCapacitas(
  token: string,
  file: File,
  params?: { force?: boolean; onProgress?: (percent: number) => void },
): Promise<CatImportStartResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const forceQuery = params?.force ? "?force=true" : "";
  return requestFormDataWithUploadProgress<CatImportStartResponse>(
    `/catasto/import/capacitas${forceQuery}`,
    formData,
    token,
    params?.onProgress,
  );
}

export async function catastoPreviewCapacitas(
  token: string,
  file: File,
  params?: { onProgress?: (percent: number) => void },
): Promise<CatCapacitasImportPreview> {
  const formData = new FormData();
  formData.append("file", file);
  return requestFormDataWithUploadProgress<CatCapacitasImportPreview>(
    "/catasto/import/capacitas/preview",
    formData,
    token,
    params?.onProgress,
  );
}

export async function catastoUploadDistrettiExcel(
  token: string,
  file: File,
  params?: { onProgress?: (percent: number) => void },
): Promise<CatImportStartResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return requestFormDataWithUploadProgress<CatImportStartResponse>(
    "/catasto/import/distretti/excel",
    formData,
    token,
    params?.onProgress,
  );
}

export async function catastoExportDistrettiExcelBatch(
  token: string,
  batchId: UUID,
  scope: "all" | "matched" | "without_match" | "unresolved" = "all",
): Promise<Blob> {
  return requestBlob(`/catasto/import/${batchId}/distretti-excel/export?scope=${scope}`, {
    headers: authHeaders(token),
  });
}

export async function catastoCreateDistrettiExcelGisLayer(
  token: string,
  batchId: UUID,
): Promise<GisSavedSelectionDetail> {
  return request<GisSavedSelectionDetail>(`/catasto/import/${batchId}/distretti-excel/gis-layer`, {
    method: "POST",
    headers: authHeaders(token),
  });
}

export async function catastoGetDistrettiExcelAnalysis(
  token: string,
  batchId: UUID,
  params?: { tipo?: string; page?: number; pageSize?: number },
): Promise<CatDistrettiExcelAnalysisResponse> {
  const query = new URLSearchParams();
  if (params?.tipo) query.set("tipo", params.tipo);
  if (params?.page) query.set("page", String(params.page));
  if (params?.pageSize) query.set("page_size", String(params.pageSize));
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<CatDistrettiExcelAnalysisResponse>(`/catasto/import/${batchId}/distretti-excel/analysis${suffix}`, {
    headers: authHeaders(token),
  });
}

export async function catastoGetImportStatus(token: string, batchId: UUID): Promise<CatImportBatch> {
  return request<CatImportBatch>(`/catasto/import/${batchId}/status`, {
    headers: authHeaders(token),
  });
}

export async function catastoGetImportHistory(
  token: string,
  params?: { status?: string; tipo?: string; limit?: number },
): Promise<CatImportBatch[]> {
  const query = createQueryString({
    status: params?.status || undefined,
    tipo: params?.tipo || undefined,
    limit: params?.limit != null ? String(params.limit) : undefined,
  });
  return request<CatImportBatch[]>("/catasto/import/history" + query, {
    headers: authHeaders(token),
  });
}

export async function catastoGetImportSummary(
  token: string,
  params?: { tipo?: string },
): Promise<CatImportSummary> {
  const query = createQueryString({
    tipo: params?.tipo || undefined,
  });
  return request<CatImportSummary>("/catasto/import/summary" + query, {
    headers: authHeaders(token),
  });
}

export async function catastoValidateMeterReadingsImport(
  token: string,
  file: File,
  params?: { anno?: number; distrettoId?: UUID; onProgress?: (percent: number) => void },
): Promise<CatMeterReadingImportPreview> {
  const formData = new FormData();
  formData.append("file", file);
  const query = new URLSearchParams();
  if (params?.anno != null) query.set("anno", String(params.anno));
  if (params?.distrettoId) query.set("distretto_id", params.distrettoId);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return requestFormDataWithUploadProgress<CatMeterReadingImportPreview>(
    `/catasto/meter-readings/import/validate${suffix}`,
    formData,
    token,
    params?.onProgress,
  );
}

export async function catastoImportMeterReadings(
  token: string,
  file: File,
  params?: {
    anno?: number;
    distrettoId?: UUID;
    mode?: "import" | "upsert" | "replace";
    onProgress?: (percent: number) => void;
  },
): Promise<CatMeterReadingImportRunResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const query = new URLSearchParams();
  if (params?.anno != null) query.set("anno", String(params.anno));
  if (params?.distrettoId) query.set("distretto_id", params.distrettoId);
  if (params?.mode) query.set("mode", params.mode);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return requestFormDataWithUploadProgress<CatMeterReadingImportRunResponse>(
    `/catasto/meter-readings/import${suffix}`,
    formData,
    token,
    params?.onProgress,
  );
}

export async function catastoListMeterReadingImports(token: string): Promise<CatMeterReadingImport[]> {
  return request<CatMeterReadingImport[]>("/catasto/meter-readings/imports", {
    headers: authHeaders(token),
  });
}

export async function catastoGetMeterReadingImport(token: string, importId: UUID): Promise<CatMeterReadingImport> {
  return request<CatMeterReadingImport>(`/catasto/meter-readings/imports/${importId}`, {
    headers: authHeaders(token),
  });
}

export async function catastoListMeterReadings(
  token: string,
  params?: {
    anno?: number;
    distrettoId?: UUID;
    codiceFiscale?: string;
    puntoConsegna?: string;
    matricola?: string;
    subjectId?: UUID;
    hasWarnings?: boolean;
    interventoDaEseguire?: boolean;
    source?: string;
    recordTab?: "meter" | "other";
    operationalFilter?: "all" | "unlinked" | "activities" | "dismissed" | "lowBattery";
    validationFilter?: "all" | "valid" | "warning" | "error";
    page?: number;
    pageSize?: number;
  },
): Promise<CatMeterReadingListResponse> {
  const query = createQueryString({
    anno: params?.anno != null ? String(params.anno) : undefined,
    distretto_id: params?.distrettoId,
    codice_fiscale: params?.codiceFiscale || undefined,
    punto_consegna: params?.puntoConsegna || undefined,
    matricola: params?.matricola || undefined,
    subject_id: params?.subjectId,
    has_warnings: params?.hasWarnings ? "true" : undefined,
    intervento_da_eseguire: params?.interventoDaEseguire ? "true" : undefined,
    source: params?.source || undefined,
    record_tab: params?.recordTab || undefined,
    operational_filter: params?.operationalFilter || undefined,
    validation_filter: params?.validationFilter || undefined,
    page: params?.page != null ? String(params.page) : undefined,
    page_size: params?.pageSize != null ? String(params.pageSize) : undefined,
  });
  return request<CatMeterReadingListResponse>(`/catasto/meter-readings${query}`, {
    headers: authHeaders(token),
  });
}

export async function catastoGetMeterReading(token: string, id: UUID): Promise<CatMeterReading> {
  return request<CatMeterReading>(`/catasto/meter-readings/${id}`, {
    headers: authHeaders(token),
  });
}

export async function catastoPatchMeterReading(
  token: string,
  id: UUID,
  payload: {
    punto_consegna?: string | null;
    matricola?: string | null;
    record_type?: string | null;
    tipologia_idrante?: string | null;
    codice_fiscale?: string | null;
    note?: string | null;
    intervento_da_eseguire?: string | null;
    change_note?: string | null;
  },
): Promise<CatMeterReading> {
  return request<CatMeterReading>(`/catasto/meter-readings/${id}`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function catastoValidateMeterReading(
  token: string,
  id: UUID,
  payload?: { change_note?: string | null },
): Promise<CatMeterReading> {
  return request<CatMeterReading>(`/catasto/meter-readings/${id}/validate`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload ?? {}),
  });
}

export async function catastoGetMeterReadingsBySubject(token: string, subjectId: UUID): Promise<CatMeterReading[]> {
  return request<CatMeterReading[]>(`/catasto/meter-readings/by-subject/${subjectId}`, {
    headers: authHeaders(token),
  });
}

export async function catastoGetDeliveryPointsImportConfig(token: string): Promise<CatDeliveryPointsImportConfig> {
  return request<CatDeliveryPointsImportConfig>("/catasto/delivery-points/import-config", {
    headers: authHeaders(token),
  });
}

export async function catastoUpdateDeliveryPointsImportConfig(
  token: string,
  payload: { root_path: string | null },
): Promise<CatDeliveryPointsImportConfig> {
  return request<CatDeliveryPointsImportConfig>("/catasto/delivery-points/import-config", {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function catastoImportDeliveryPointsFromConfig(token: string): Promise<CatDeliveryPointsImportRunResponse> {
  return request<CatDeliveryPointsImportRunResponse>("/catasto/delivery-points/import-from-config", {
    method: "POST",
    headers: authHeaders(token),
  });
}

export async function catastoGetDeliveryPointsImportJob(
  token: string,
  jobId: UUID,
): Promise<CatDeliveryPointsImportRunResponse> {
  return request<CatDeliveryPointsImportRunResponse>(`/catasto/delivery-points/import-jobs/${jobId}`, {
    headers: authHeaders(token),
  });
}

export async function catastoRefreshDeliveryPointsGisCache(
  token: string,
): Promise<CatDeliveryPointsGisCacheRefreshResponse> {
  return request<CatDeliveryPointsGisCacheRefreshResponse>("/catasto/delivery-points/gis-cache/refresh", {
    method: "POST",
    headers: authHeaders(token),
  });
}

export async function catastoGetImportReport(
  token: string,
  batchId: UUID,
  params?: { tipo?: string; page?: number; pageSize?: number },
): Promise<CatAnomaliaListResponse> {
  const query = new URLSearchParams();
  if (params?.tipo) query.set("tipo", params.tipo);
  if (params?.page) query.set("page", String(params.page));
  if (params?.pageSize) query.set("page_size", String(params.pageSize));
  const suffix = query.toString() ? `?${query.toString()}` : "";

  return request<CatAnomaliaListResponse>(`/catasto/import/${batchId}/report${suffix}`, {
    headers: authHeaders(token),
  });
}

export async function catastoListDistretti(token: string): Promise<CatDistretto[]> {
  return request<CatDistretto[]>("/catasto/distretti", {
    headers: authHeaders(token),
  });
}

export async function catastoGetDistretto(token: string, id: UUID): Promise<CatDistretto> {
  return request<CatDistretto>(`/catasto/distretti/${id}`, {
    headers: authHeaders(token),
  });
}

export async function catastoGetDistrettoKpi(token: string, id: UUID, anno?: number): Promise<CatDistrettoKpi> {
  const query = createQueryString({ anno: anno != null ? String(anno) : undefined });
  return request<CatDistrettoKpi>(`/catasto/distretti/${id}/kpi${query}`, {
    headers: authHeaders(token),
  });
}

export async function catastoGetDistrettoGeojson(token: string, id: UUID): Promise<GeoJSONFeature> {
  return request<GeoJSONFeature>(`/catasto/distretti/${id}/geojson`, {
    headers: authHeaders(token),
  });
}

export async function catastoGetDashboardSummary(token: string, params?: { anno?: number }): Promise<CatDashboardSummary> {
  const query = createQueryString({ anno: params?.anno != null ? String(params.anno) : undefined });
  return request<CatDashboardSummary>(`/catasto/dashboard/summary${query}`, {
    headers: authHeaders(token),
  });
}

export async function catastoGetDashboardAdeAlignment(token: string): Promise<CatDashboardAdeAlignmentSummary> {
  return request<CatDashboardAdeAlignmentSummary>("/catasto/dashboard/ade-alignment", {
    headers: authHeaders(token),
  });
}

export async function catastoGetIndiciOverview(token: string, anno?: number): Promise<CatIndiceOverview> {
  const query = createQueryString({ anno: anno != null ? String(anno) : undefined });
  return request<CatIndiceOverview>(`/catasto/indici/overview${query}`, {
    headers: authHeaders(token),
  });
}

export async function catastoGetIndiciRuoloEsclusi(
  token: string,
  anno?: number,
): Promise<CatIndiceRuoloExcludedParticelleResponse> {
  const query = createQueryString({ anno: anno != null ? String(anno) : undefined });
  return request<CatIndiceRuoloExcludedParticelleResponse>(`/catasto/indici/ruolo-esclusi${query}`, {
    headers: authHeaders(token),
  });
}

export async function catastoAssignIndiciRuoloEsclusoDistretto(
  token: string,
  payload: CatIndiceRuoloAssignDistrettoRequest,
): Promise<CatIndiceRuoloAssignDistrettoResponse> {
  return request<CatIndiceRuoloAssignDistrettoResponse>("/catasto/indici/ruolo-esclusi/assegna-distretto", {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function catastoGetColtureOverview(token: string, anno?: number): Promise<CatColturaOverview> {
  const query = createQueryString({ anno: anno != null ? String(anno) : undefined });
  return request<CatColturaOverview>(`/catasto/colture/overview${query}`, {
    headers: authHeaders(token),
  });
}

export async function catastoListParticelle(
  token: string,
  filters?: {
    comune?: number;
    codiceCatastale?: string;
    nomeComune?: string;
    foglio?: string;
    particella?: string;
    distretto?: string;
    indice?: string;
    anno?: number;
    search?: string;
    coltura?: string;
    cf?: string;
    intestatario?: string;
    haAnomalie?: boolean;
    soloConAnagrafica?: boolean;
    soloARuolo?: boolean;
    limit?: number;
  },
): Promise<CatParticella[]> {
  const query = new URLSearchParams();
  if (filters?.comune != null && Number.isFinite(filters.comune)) query.set("comune", String(filters.comune));
  if (filters?.codiceCatastale) query.set("codice_catastale", filters.codiceCatastale);
  if (filters?.nomeComune) query.set("nome_comune", filters.nomeComune);
  if (filters?.foglio) query.set("foglio", filters.foglio);
  if (filters?.particella) query.set("particella", filters.particella);
  if (filters?.distretto) query.set("distretto", filters.distretto);
  if (filters?.indice) query.set("indice", filters.indice);
  if (filters?.anno != null) query.set("anno", String(filters.anno));
  if (filters?.search) query.set("search", filters.search);
  if (filters?.coltura) query.set("coltura", filters.coltura);
  if (filters?.cf) query.set("cf", filters.cf);
  if (filters?.intestatario) query.set("intestatario", filters.intestatario);
  if (filters?.haAnomalie != null) query.set("ha_anomalie", filters.haAnomalie ? "true" : "false");
  if (filters?.soloConAnagrafica != null) query.set("solo_con_anagrafica", filters.soloConAnagrafica ? "true" : "false");
  if (filters?.soloARuolo != null) query.set("solo_a_ruolo", filters.soloARuolo ? "true" : "false");
  if (filters?.limit != null) query.set("limit", String(filters.limit));
  const suffix = query.toString() ? `?${query.toString()}` : "";

  return request<CatParticella[]>(`/catasto/particelle${suffix}`, {
    headers: authHeaders(token),
  });
}

export async function catastoGetParticella(token: string, id: UUID): Promise<CatParticellaDetail> {
  return request<CatParticellaDetail>(`/catasto/particelle/${id}`, {
    headers: authHeaders(token),
  });
}

export async function catastoSyncParticellaCapacitas(
  token: string,
  id: UUID,
  options?: { credentialId?: number | null; fetchCertificati?: boolean; fetchDetails?: boolean },
): Promise<CatParticellaCapacitasSyncResponse> {
  return request<CatParticellaCapacitasSyncResponse>(`/catasto/particelle/${id}/capacitas-sync`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({
      credential_id: options?.credentialId ?? null,
      fetch_certificati: options?.fetchCertificati ?? true,
      fetch_details: options?.fetchDetails ?? true,
    }),
  });
}

export async function catastoGetParticellaConsorzio(token: string, id: UUID): Promise<CatParticellaConsorzio> {
  return request<CatParticellaConsorzio>(`/catasto/particelle/${id}/consorzio`, {
    headers: authHeaders(token),
  });
}

export async function catastoGetParticellaGeojson(token: string, id: UUID): Promise<GeoJSONFeature> {
  return request<GeoJSONFeature>(`/catasto/particelle/${id}/geojson`, {
    headers: authHeaders(token),
  });
}

export async function catastoGetParticellaHistory(token: string, id: UUID): Promise<CatParticellaHistory[]> {
  return request<CatParticellaHistory[]>(`/catasto/particelle/${id}/history`, {
    headers: authHeaders(token),
  });
}

export async function catastoListAnomalie(
  token: string,
  params?: {
    tipo?: string;
    status?: string;
    severita?: string;
    anno?: number;
    distretto?: string;
    q?: string;
    sortBy?: string;
    sortDir?: "asc" | "desc";
    page?: number;
    pageSize?: number;
  },
): Promise<CatAnomaliaListResponse> {
  const query = new URLSearchParams();
  if (params?.tipo) query.set("tipo", params.tipo);
  if (params?.status) query.set("status", params.status);
  if (params?.severita) query.set("severita", params.severita);
  if (params?.anno != null) query.set("anno", String(params.anno));
  if (params?.distretto) query.set("distretto", params.distretto);
  if (params?.q) query.set("q", params.q);
  if (params?.sortBy) query.set("sort_by", params.sortBy);
  if (params?.sortDir) query.set("sort_dir", params.sortDir);
  if (params?.page != null) query.set("page", String(params.page));
  if (params?.pageSize != null) query.set("page_size", String(params.pageSize));
  const suffix = query.toString() ? `?${query.toString()}` : "";

  return request<CatAnomaliaListResponse>(`/catasto/anomalie${suffix}`, {
    headers: authHeaders(token),
  });
}

export async function catastoUpdateAnomalia(
  token: string,
  id: UUID,
  payload: { status?: string; note_operatore?: string | null; assigned_to?: number; segnalazione_id?: UUID },
): Promise<CatAnomalia> {
  return request<CatAnomalia>(`/catasto/anomalie/${id}`, {
    method: "PATCH",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function catastoGetAnomalieSummary(
  token: string,
  params?: { status?: string; severita?: string; anno?: number; distretto?: string },
): Promise<CatAnomaliaSummary> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.severita) query.set("severita", params.severita);
  if (params?.anno != null) query.set("anno", String(params.anno));
  if (params?.distretto) query.set("distretto", params.distretto);
  const suffix = query.toString() ? `?${query.toString()}` : "";

  return request<CatAnomaliaSummary>(`/catasto/anomalie/summary${suffix}`, {
    headers: authHeaders(token),
  });
}

export async function catastoGetAdeStatusScanSummary(token: string): Promise<CatAdeStatusScanSummary> {
  return request<CatAdeStatusScanSummary>("/catasto/anomalie/ade-scan/summary", {
    headers: authHeaders(token),
  });
}

export async function catastoGetAdeStatusScanCandidates(
  token: string,
  params?: { limit?: number },
): Promise<CatAdeStatusScanCandidateListResponse> {
  const query = new URLSearchParams();
  if (params?.limit != null) query.set("limit", String(params.limit));
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<CatAdeStatusScanCandidateListResponse>(`/catasto/anomalie/ade-scan/candidates${suffix}`, {
    headers: authHeaders(token),
  });
}

export async function catastoRunAdeStatusScan(
  token: string,
  payload: { limit?: number | null; match_reasons?: string[] | null },
): Promise<CatAdeStatusScanRunResponse> {
  return request<CatAdeStatusScanRunResponse>("/catasto/anomalie/ade-scan/run", {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function catastoGetCfWizardItems(
  token: string,
  params?: { status?: string; anno?: number; distretto?: string; page?: number; pageSize?: number },
): Promise<CatAnomaliaCfWizardListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.anno != null) query.set("anno", String(params.anno));
  if (params?.distretto) query.set("distretto", params.distretto);
  if (params?.page != null) query.set("page", String(params.page));
  if (params?.pageSize != null) query.set("page_size", String(params.pageSize));
  const suffix = query.toString() ? `?${query.toString()}` : "";

  return request<CatAnomaliaCfWizardListResponse>(`/catasto/anomalie/wizard/cf/items${suffix}`, {
    headers: authHeaders(token),
  });
}

export async function catastoApplyCfWizard(
  token: string,
  items: Array<{ anomalia_id: string; codice_fiscale: string; note_operatore?: string }>,
): Promise<CatAnomaliaCfWizardApplyResponse> {
  return request<CatAnomaliaCfWizardApplyResponse>("/catasto/anomalie/wizard/cf/apply", {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ items }),
  });
}

export async function catastoGetComuneWizardItems(
  token: string,
  params?: { status?: string; anno?: number; distretto?: string; page?: number; pageSize?: number },
): Promise<CatAnomaliaComuneWizardListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.anno != null) query.set("anno", String(params.anno));
  if (params?.distretto) query.set("distretto", params.distretto);
  if (params?.page != null) query.set("page", String(params.page));
  if (params?.pageSize != null) query.set("page_size", String(params.pageSize));
  const suffix = query.toString() ? `?${query.toString()}` : "";

  return request<CatAnomaliaComuneWizardListResponse>(`/catasto/anomalie/wizard/comune/items${suffix}`, {
    headers: authHeaders(token),
  });
}

export async function catastoApplyComuneWizard(
  token: string,
  items: Array<{ anomalia_id: string; comune_id: string; note_operatore?: string }>,
): Promise<CatAnomaliaComuneWizardApplyResponse> {
  return request<CatAnomaliaComuneWizardApplyResponse>("/catasto/anomalie/wizard/comune/apply", {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ items }),
  });
}

export async function catastoGetParticellaWizardItems(
  token: string,
  params?: { status?: string; anno?: number; distretto?: string; page?: number; pageSize?: number },
): Promise<CatAnomaliaParticellaWizardListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.anno != null) query.set("anno", String(params.anno));
  if (params?.distretto) query.set("distretto", params.distretto);
  if (params?.page != null) query.set("page", String(params.page));
  if (params?.pageSize != null) query.set("page_size", String(params.pageSize));
  const suffix = query.toString() ? `?${query.toString()}` : "";

  return request<CatAnomaliaParticellaWizardListResponse>(`/catasto/anomalie/wizard/particella/items${suffix}`, {
    headers: authHeaders(token),
  });
}

export async function catastoApplyParticellaWizard(
  token: string,
  items: Array<{ anomalia_id: string; particella_id: string; note_operatore?: string }>,
): Promise<CatAnomaliaParticellaWizardApplyResponse> {
  return request<CatAnomaliaParticellaWizardApplyResponse>("/catasto/anomalie/wizard/particella/apply", {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ items }),
  });
}

export async function catastoGetParticellaUtenze(
  token: string,
  id: UUID,
  params?: { anno?: number },
): Promise<CatUtenzaIrrigua[]> {
  const query = createQueryString({ anno: params?.anno != null ? String(params.anno) : undefined });
  return request<CatUtenzaIrrigua[]>(`/catasto/particelle/${id}/utenze${query}`, {
    headers: authHeaders(token),
  });
}

export async function catastoGetParticellaAnomalie(
  token: string,
  id: UUID,
  params?: { anno?: number },
): Promise<CatAnomalia[]> {
  const query = createQueryString({ anno: params?.anno != null ? String(params.anno) : undefined });
  return request<CatAnomalia[]>(`/catasto/particelle/${id}/anomalie${query}`, {
    headers: authHeaders(token),
  });
}

export async function catastoListSchemi(token: string): Promise<CatSchemaContributo[]> {
  return request<CatSchemaContributo[]>("/catasto/schemi", {
    headers: authHeaders(token),
  });
}

export async function capacitasGetRptCertificatoLink(
  token: string,
  cco: string,
  params?: { com?: string | null; pvc?: string | null; fra?: string | null; ccs?: string | null },
): Promise<{ url: string }> {
  const query = new URLSearchParams({ cco });
  if (params?.com) query.set("com", params.com);
  if (params?.pvc) query.set("pvc", params.pvc);
  if (params?.fra) query.set("fra", params.fra);
  if (params?.ccs) query.set("ccs", params.ccs);
  return request<{ url: string }>(`/elaborazioni/capacitas/involture/link/rpt-certificato?${query.toString()}`, {
    headers: authHeaders(token),
  });
}

export async function catastoBulkSearchAnagrafica(
  token: string,
  payload: CatAnagraficaBulkSearchRequest,
): Promise<CatAnagraficaBulkSearchResponse> {
  return request<CatAnagraficaBulkSearchResponse>("/catasto/elaborazioni-massive/particelle", {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function catastoCreateElaborazioneMassivaJob(
  token: string,
  payload: { source_filename?: string | null; skipped_rows?: number; payload: CatAnagraficaBulkSearchRequest },
): Promise<CatAnagraficaBulkJobDetail> {
  return request<CatAnagraficaBulkJobDetail>("/catasto/elaborazioni-massive/particelle/jobs", {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function catastoUploadElaborazioneMassivaJob(
  token: string,
  file: File,
  onProgress?: (percent: number) => void,
): Promise<CatAnagraficaBulkJobDetail> {
  const formData = new FormData();
  formData.append("file", file);
  return requestFormDataWithUploadProgress<CatAnagraficaBulkJobDetail>(
    "/catasto/elaborazioni-massive/particelle/jobs/upload",
    formData,
    token,
    onProgress,
  );
}

export async function catastoSaveElaborazioneMassivaJob(
  token: string,
  payload: { source_filename?: string | null; skipped_rows?: number; payload: CatAnagraficaBulkSearchRequest; results: CatAnagraficaBulkSearchResponse["results"] },
): Promise<CatAnagraficaBulkJobDetail> {
  return request<CatAnagraficaBulkJobDetail>("/catasto/elaborazioni-massive/particelle/jobs/save", {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function catastoListElaborazioniMassiveJobs(
  token: string,
  params?: { limit?: number },
): Promise<CatAnagraficaBulkJobListResponse> {
  const query = createQueryString({ limit: params?.limit != null ? String(params.limit) : undefined });
  return request<CatAnagraficaBulkJobListResponse>(`/catasto/elaborazioni-massive/particelle/jobs${query}`, {
    headers: authHeaders(token),
  });
}

export async function catastoGetElaborazioneMassivaJob(token: string, jobId: UUID): Promise<CatAnagraficaBulkJobDetail> {
  return request<CatAnagraficaBulkJobDetail>(`/catasto/elaborazioni-massive/particelle/jobs/${jobId}`, {
    headers: authHeaders(token),
  });
}

export async function catastoDownloadElaborazioneMassivaJobExport(
  token: string,
  jobId: UUID,
  format: "csv" | "xlsx",
): Promise<Blob> {
  return requestBlob(`/catasto/elaborazioni-massive/particelle/jobs/${jobId}/export?format=${format}`, {
    headers: authHeaders(token),
  });
}

export async function catastoDeleteElaborazioniMassiveJobs(token: string): Promise<{ deleted: number }> {
  return request<{ deleted: number }>("/catasto/elaborazioni-massive/particelle/jobs", {
    method: "DELETE",
    headers: authHeaders(token),
  });
}
