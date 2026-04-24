import { createQueryString, request, requestFormDataWithUploadProgress } from "@/lib/api";
import type {
  CatAnomaliaListResponse,
  CatAnomalia,
  CatAnagraficaBulkSearchRequest,
  CatAnagraficaBulkSearchResponse,
  CatDistretto,
  CatDistrettoKpi,
  CatImportBatch,
  CatImportStartResponse,
  CatImportSummary,
  CatParticella,
  CatParticellaConsorzio,
  CatParticellaDetail,
  CatParticellaHistory,
  CatSchemaContributo,
  CatUtenzaIrrigua,
  GeoJSONFeature,
  UUID,
} from "@/types/catasto";

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
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

export async function catastoListParticelle(
  token: string,
  filters?: {
    comune?: number;
    codiceCatastale?: string;
    nomeComune?: string;
    foglio?: string;
    particella?: string;
    distretto?: string;
    anno?: number;
    cf?: string;
    intestatario?: string;
    haAnomalie?: boolean;
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
  if (filters?.anno != null) query.set("anno", String(filters.anno));
  if (filters?.cf) query.set("cf", filters.cf);
  if (filters?.intestatario) query.set("intestatario", filters.intestatario);
  if (filters?.haAnomalie != null) query.set("ha_anomalie", filters.haAnomalie ? "true" : "false");
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
  payload: { status?: string; note_operatore?: string; assigned_to?: number },
): Promise<CatAnomalia> {
  return request<CatAnomalia>(`/catasto/anomalie/${id}`, {
    method: "PATCH",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
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

export async function capacitasGetRptCertificatoLink(token: string, cco: string): Promise<{ url: string }> {
  const query = new URLSearchParams({ cco });
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
