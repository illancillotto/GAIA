import { ApiError, getApiBaseUrl } from "@/lib/api";
import type {
  RuoloAvvisoDetailResponse,
  RuoloAvvisoListResponse,
  RuoloCapacitasCalculationDetailResponse,
  RuoloCapacitasCheckResponse,
  RuoloCapacitasCheckComuneResponse,
  RuoloCapacitasCheckStatus,
  RuoloGaiaCalculationResponse,
  RuoloImportJobListResponse,
  RuoloImportJobResponse,
  RuoloParticellaResponse,
  RuoloParticelleSummaryResponse,
  RuoloStatsAnalyticsResponse,
  RuoloStatsResponse,
  RuoloStatsComuneResponse,
  RuoloTributiAvvisoDetailResponse,
  RuoloTributiAvvisoListResponse,
  RuoloTributiAvvisoStatusUpdateRequest,
  RuoloTributiNoteCreateRequest,
  RuoloTributiNoteResponse,
  RuoloTributiPaymentCreateRequest,
  RuoloTributiPaymentResponse,
  RuoloTributiReminderBatchCreateRequest,
  RuoloTributiReminderBatchListResponse,
  RuoloTributiReminderBatchResponse,
  RuoloTributiReminderCandidateListResponse,
  RuoloTributiReminderCreateRequest,
  RuoloTributiReminderResponse,
} from "@/types/ruolo";

async function extractError(response: Response): Promise<never> {
  let detail = "Request failed";
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      detail = payload.detail;
    } else if (payload.detail != null) {
      detail = JSON.stringify(payload.detail);
    }
  } catch {
    detail = response.statusText || detail;
  }
  throw new ApiError(detail, undefined, response.status);
}

async function ruoloRequest<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const isFormData = typeof FormData !== "undefined" && init?.body instanceof FormData;
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers: {
      /* c8 ignore next -- Current ruolo API exports are JSON/blob-only; this keeps the helper ready for future upload endpoints. */
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      Authorization: `Bearer ${token}`,
      ...init?.headers,
    },
  });
  if (!response.ok) return extractError(response);
  return response.json() as Promise<T>;
}

export function formatRuoloCapacitasCheckStatus(status: RuoloCapacitasCheckStatus): string {
  switch (status) {
    case "amount_mismatch":
      return "Importi non allineati";
    case "only_in_ruolo":
      return "Presente solo nel ruolo";
    case "only_in_capacitas":
      return "Presente solo in Capacitas";
    case "matched":
      return "Allineato";
    default:
      return status;
  }
}

export function getRuoloCapacitasCheckStatusBadgeClassName(status: RuoloCapacitasCheckStatus): string {
  switch (status) {
    case "amount_mismatch":
      return "bg-amber-50 text-amber-800 border border-amber-200";
    case "only_in_ruolo":
      return "bg-sky-50 text-sky-800 border border-sky-200";
    case "only_in_capacitas":
      return "bg-fuchsia-50 text-fuchsia-800 border border-fuchsia-200";
    case "matched":
      return "bg-emerald-50 text-emerald-800 border border-emerald-200";
    default:
      return "bg-gray-100 text-gray-700 border border-gray-200";
  }
}

// ── Import Jobs ───────────────────────────────────────────────────────────────

export async function listImportJobs(
  token: string,
  anno?: number,
  page = 1,
  pageSize = 20,
): Promise<RuoloImportJobListResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (anno != null) params.set("anno", String(anno));
  return ruoloRequest<RuoloImportJobListResponse>(`/ruolo/import/jobs?${params}`, token);
}

export async function getImportJob(token: string, jobId: string): Promise<RuoloImportJobResponse> {
  return ruoloRequest<RuoloImportJobResponse>(`/ruolo/import/jobs/${jobId}`, token);
}

// ── Avvisi ────────────────────────────────────────────────────────────────────

export type ListAvvisiParams = {
  anno?: number;
  subject_id?: string;
  q?: string;
  codice_fiscale?: string;
  comune?: string;
  codice_utenza?: string;
  unlinked?: boolean;
  page?: number;
  page_size?: number;
};

export async function listAvvisi(
  token: string,
  params: ListAvvisiParams = {},
): Promise<RuoloAvvisoListResponse> {
  const qs = new URLSearchParams();
  if (params.anno != null) qs.set("anno", String(params.anno));
  if (params.subject_id) qs.set("subject_id", params.subject_id);
  if (params.q) qs.set("q", params.q);
  if (params.codice_fiscale) qs.set("codice_fiscale", params.codice_fiscale);
  if (params.comune) qs.set("comune", params.comune);
  if (params.codice_utenza) qs.set("codice_utenza", params.codice_utenza);
  if (params.unlinked) qs.set("unlinked", "true");
  qs.set("page", String(params.page ?? 1));
  qs.set("page_size", String(params.page_size ?? 20));
  return ruoloRequest<RuoloAvvisoListResponse>(`/ruolo/avvisi?${qs}`, token);
}

export async function getAvviso(token: string, avvisoId: string): Promise<RuoloAvvisoDetailResponse> {
  return ruoloRequest<RuoloAvvisoDetailResponse>(`/ruolo/avvisi/${avvisoId}`, token);
}

export async function getAvvisiBySubject(
  token: string,
  subjectId: string,
): Promise<RuoloAvvisoDetailResponse[]> {
  return ruoloRequest<RuoloAvvisoDetailResponse[]>(`/ruolo/soggetti/${subjectId}/avvisi`, token);
}

export type ListRuoloParticelleParams = {
  anno?: number;
  foglio?: string;
  particella?: string;
  comune?: string;
  match_status?: string;
  match_reason?: string;
  unmatched_only?: boolean;
  page?: number;
  page_size?: number;
};

export async function listRuoloParticelle(
  token: string,
  params: ListRuoloParticelleParams = {},
): Promise<RuoloParticellaResponse[]> {
  const qs = new URLSearchParams();
  if (params.anno != null) qs.set("anno", String(params.anno));
  if (params.foglio) qs.set("foglio", params.foglio);
  if (params.particella) qs.set("particella", params.particella);
  if (params.comune) qs.set("comune", params.comune);
  if (params.match_status) qs.set("match_status", params.match_status);
  if (params.match_reason) qs.set("match_reason", params.match_reason);
  if (params.unmatched_only) qs.set("unmatched_only", "true");
  qs.set("page", String(params.page ?? 1));
  qs.set("page_size", String(params.page_size ?? 50));
  return ruoloRequest<RuoloParticellaResponse[]>(`/ruolo/particelle?${qs}`, token);
}

export function buildExportCsvUrl(params: ListAvvisiParams): string {
  const qs = new URLSearchParams();
  if (params.anno != null) qs.set("anno", String(params.anno));
  if (params.subject_id) qs.set("subject_id", params.subject_id);
  if (params.q) qs.set("q", params.q);
  if (params.codice_fiscale) qs.set("codice_fiscale", params.codice_fiscale);
  if (params.comune) qs.set("comune", params.comune);
  if (params.codice_utenza) qs.set("codice_utenza", params.codice_utenza);
  if (params.unlinked) qs.set("unlinked", "true");
  return `${getApiBaseUrl()}/ruolo/avvisi/export?${qs}`;
}

// ── Tributi ──────────────────────────────────────────────────────────────────

export type ListTributiAvvisiParams = ListAvvisiParams & {
  payment_status?: string;
  workflow_status?: string;
  open_only?: boolean;
};

export async function listTributiAvvisi(
  token: string,
  params: ListTributiAvvisiParams = {},
): Promise<RuoloTributiAvvisoListResponse> {
  const qs = new URLSearchParams();
  if (params.anno != null) qs.set("anno", String(params.anno));
  if (params.subject_id) qs.set("subject_id", params.subject_id);
  if (params.q) qs.set("q", params.q);
  if (params.codice_fiscale) qs.set("codice_fiscale", params.codice_fiscale);
  if (params.comune) qs.set("comune", params.comune);
  if (params.codice_utenza) qs.set("codice_utenza", params.codice_utenza);
  if (params.unlinked) qs.set("unlinked", "true");
  if (params.payment_status) qs.set("payment_status", params.payment_status);
  if (params.workflow_status) qs.set("workflow_status", params.workflow_status);
  if (params.open_only) qs.set("open_only", "true");
  qs.set("page", String(params.page ?? 1));
  qs.set("page_size", String(params.page_size ?? 20));
  return ruoloRequest<RuoloTributiAvvisoListResponse>(`/ruolo/tributi/avvisi?${qs}`, token);
}

export async function getTributiAvviso(
  token: string,
  avvisoId: string,
): Promise<RuoloTributiAvvisoDetailResponse> {
  return ruoloRequest<RuoloTributiAvvisoDetailResponse>(`/ruolo/tributi/avvisi/${avvisoId}`, token);
}

export async function createTributiPayment(
  token: string,
  avvisoId: string,
  payload: RuoloTributiPaymentCreateRequest,
): Promise<RuoloTributiPaymentResponse> {
  return ruoloRequest<RuoloTributiPaymentResponse>(`/ruolo/tributi/avvisi/${avvisoId}/payments`, token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateTributiAvvisoStatus(
  token: string,
  avvisoId: string,
  payload: RuoloTributiAvvisoStatusUpdateRequest,
): Promise<void> {
  await ruoloRequest(`/ruolo/tributi/avvisi/${avvisoId}/status`, token, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function addTributiNote(
  token: string,
  avvisoId: string,
  payload: RuoloTributiNoteCreateRequest,
): Promise<RuoloTributiNoteResponse> {
  return ruoloRequest<RuoloTributiNoteResponse>(`/ruolo/tributi/avvisi/${avvisoId}/notes`, token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listTributiReminders(
  token: string,
  avvisoId: string,
): Promise<RuoloTributiReminderResponse[]> {
  return ruoloRequest<RuoloTributiReminderResponse[]>(`/ruolo/tributi/avvisi/${avvisoId}/reminders`, token);
}

export async function createTributiReminder(
  token: string,
  avvisoId: string,
  payload: RuoloTributiReminderCreateRequest = {},
): Promise<RuoloTributiReminderResponse> {
  return ruoloRequest<RuoloTributiReminderResponse>(`/ruolo/tributi/avvisi/${avvisoId}/reminders`, token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export type ListTributiReminderCandidatesParams = {
  anno_from?: number;
  anno_to?: number;
  q?: string;
  comune?: string;
  codice_fiscale?: string[];
  page?: number;
  page_size?: number;
};

export async function listTributiReminderCandidates(
  token: string,
  params: ListTributiReminderCandidatesParams = {},
): Promise<RuoloTributiReminderCandidateListResponse> {
  const qs = new URLSearchParams();
  if (params.anno_from != null) qs.set("anno_from", String(params.anno_from));
  if (params.anno_to != null) qs.set("anno_to", String(params.anno_to));
  if (params.q) qs.set("q", params.q);
  if (params.comune) qs.set("comune", params.comune);
  for (const taxCode of params.codice_fiscale ?? []) qs.append("codice_fiscale", taxCode);
  qs.set("page", String(params.page ?? 1));
  qs.set("page_size", String(params.page_size ?? 50));
  return ruoloRequest<RuoloTributiReminderCandidateListResponse>(`/ruolo/tributi/solleciti/candidates?${qs}`, token);
}

export async function createTributiReminderBatch(
  token: string,
  payload: RuoloTributiReminderBatchCreateRequest,
): Promise<RuoloTributiReminderBatchResponse> {
  return ruoloRequest<RuoloTributiReminderBatchResponse>("/ruolo/tributi/solleciti/batches", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listTributiReminderBatches(
  token: string,
  page = 1,
  pageSize = 20,
): Promise<RuoloTributiReminderBatchListResponse> {
  const qs = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  return ruoloRequest<RuoloTributiReminderBatchListResponse>(`/ruolo/tributi/solleciti/batches?${qs}`, token);
}

export async function getTributiReminderBatch(
  token: string,
  batchId: string,
): Promise<RuoloTributiReminderBatchResponse> {
  return ruoloRequest<RuoloTributiReminderBatchResponse>(`/ruolo/tributi/solleciti/batches/${batchId}`, token);
}

export async function downloadTributiReminderDocument(
  token: string,
  downloadUrl: string,
): Promise<Blob> {
  const response = await fetch(`${getApiBaseUrl()}${downloadUrl}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) return extractError(response);
  return response.blob();
}

// ── Stats ─────────────────────────────────────────────────────────────────────

export async function getRuoloStats(token: string, anno?: number): Promise<RuoloStatsResponse> {
  const qs = new URLSearchParams();
  if (anno != null) qs.set("anno", String(anno));
  return ruoloRequest<RuoloStatsResponse>(`/ruolo/stats?${qs}`, token);
}

export async function getRuoloParticelleSummary(
  token: string,
  anno?: number,
): Promise<RuoloParticelleSummaryResponse> {
  const qs = new URLSearchParams();
  if (anno != null) qs.set("anno", String(anno));
  return ruoloRequest<RuoloParticelleSummaryResponse>(`/ruolo/stats/particelle?${qs}`, token);
}

export async function getRuoloStatsComuni(
  token: string,
  anno: number,
): Promise<RuoloStatsComuneResponse> {
  return ruoloRequest<RuoloStatsComuneResponse>(`/ruolo/stats/comuni?anno=${anno}`, token);
}

export async function getRuoloStatsAnalytics(
  token: string,
  anno: number,
): Promise<RuoloStatsAnalyticsResponse> {
  return ruoloRequest<RuoloStatsAnalyticsResponse>(`/ruolo/stats/analytics?anno=${anno}`, token);
}

export async function getRuoloCapacitasCheck(
  token: string,
  anno: number,
  minDelta = 0.01,
  limit = 25,
): Promise<RuoloCapacitasCheckResponse> {
  const qs = new URLSearchParams({
    anno: String(anno),
    min_delta: String(minDelta),
    limit: String(limit),
  });
  return ruoloRequest<RuoloCapacitasCheckResponse>(`/ruolo/stats/capacitas-check?${qs}`, token);
}

export async function getRuoloCapacitasCheckComuni(
  token: string,
  anno: number,
  limit = 8,
): Promise<RuoloCapacitasCheckComuneResponse> {
  const qs = new URLSearchParams({
    anno: String(anno),
    limit: String(limit),
  });
  return ruoloRequest<RuoloCapacitasCheckComuneResponse>(`/ruolo/stats/capacitas-check/comuni?${qs}`, token);
}

export async function getRuoloCapacitasCalculationDetail(
  token: string,
  anno: number,
  taxCode: string,
): Promise<RuoloCapacitasCalculationDetailResponse> {
  const qs = new URLSearchParams({
    anno: String(anno),
    tax_code: taxCode,
  });
  return ruoloRequest<RuoloCapacitasCalculationDetailResponse>(`/ruolo/stats/capacitas-check/detail?${qs}`, token);
}

export async function getRuoloGaiaCalculation(
  token: string,
  anno: number,
  options: { limit?: number; taxCode?: string; anomalousOnly?: boolean } = {},
): Promise<RuoloGaiaCalculationResponse> {
  const qs = new URLSearchParams({
    anno: String(anno),
    limit: String(options.limit ?? 100),
  });
  if (options.taxCode) qs.set("tax_code", options.taxCode);
  if (options.anomalousOnly) qs.set("anomalous_only", "true");
  return ruoloRequest<RuoloGaiaCalculationResponse>(`/ruolo/stats/calcolo-gaia?${qs}`, token);
}

export function buildRuoloGaiaCalculationExportUrl(
  anno: number,
  options: { limit?: number; taxCode?: string; anomalousOnly?: boolean } = {},
): string {
  const qs = new URLSearchParams({
    anno: String(anno),
    limit: String(options.limit ?? 100000),
  });
  if (options.taxCode) qs.set("tax_code", options.taxCode);
  if (options.anomalousOnly) qs.set("anomalous_only", "true");
  return `${getApiBaseUrl()}/ruolo/stats/calcolo-gaia/export?${qs}`;
}

export function buildRuoloCapacitasCheckExportUrl(anno: number, minDelta = 0.01): string {
  const qs = new URLSearchParams({
    anno: String(anno),
    min_delta: String(minDelta),
  });
  return `${getApiBaseUrl()}/ruolo/stats/capacitas-check/export?${qs}`;
}
