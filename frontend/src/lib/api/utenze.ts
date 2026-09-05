import type { AnagraficaCsvImportResult, AnagraficaDocument, UtenzeAuditLog, XlsxImportBatch, XlsxImportStartResult, AnagraficaDocumentSummary, AnagraficaImportJob, AnagraficaImportPreview, AnagraficaImportRunResult, AnagraficaNasFolderCandidate, AnagraficaPaymentNotice, AnagraficaResetResult, AnagraficaSearchResult, AnagraficaStats, AnagraficaSubjectCreateInput, AnagraficaSubjectDetail, AnagraficaSubjectNasImportStatus, AnagraficaSubjectImportResult, AnagraficaSubjectListResponse, AnagraficaSubjectUpdateInput, AnagraficaVisuraRoutingAnomaly, AnagraficaVisuraRoutingAnomalyListResponse, AnprJobTriggerResult, AnprPreviewLookupResponse, AnprSubjectStatus, AnprSyncConfig, AnprSyncConfigUpdateInput, AnprSyncResult } from "@/types/api";
import { ApiError, getApiBaseUrl, request, requestBlob, requestFormDataWithUploadProgress } from "./core";

export async function getAnagraficaStats(token: string): Promise<AnagraficaStats> {
  return request<AnagraficaStats>("/utenze/stats", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const getUtenzeStats = getAnagraficaStats;

export async function getAnagraficaDocumentSummary(token: string): Promise<AnagraficaDocumentSummary> {
  return request<AnagraficaDocumentSummary>("/utenze/documents/summary", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const getUtenzeDocumentSummary = getAnagraficaDocumentSummary;

export async function getAnagraficaSubjects(
  token: string,
  params?: {
    page?: number;
    pageSize?: number;
    search?: string;
    subjectType?: string;
    status?: string;
    letter?: string;
    requiresReview?: boolean;
  },
): Promise<AnagraficaSubjectListResponse> {
  const query = new URLSearchParams();
  if (params?.page) query.set("page", String(params.page));
  if (params?.pageSize) query.set("page_size", String(params.pageSize));
  if (params?.search) query.set("search", params.search);
  if (params?.subjectType) query.set("subject_type", params.subjectType);
  if (params?.status) query.set("status", params.status);
  if (params?.letter) query.set("letter", params.letter);
  if (typeof params?.requiresReview === "boolean") query.set("requires_review", String(params.requiresReview));
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<AnagraficaSubjectListResponse>(`/utenze/subjects${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const getUtenzeSubjects = getAnagraficaSubjects;

export async function getAnagraficaSubject(token: string, subjectId: string): Promise<AnagraficaSubjectDetail> {
  return request<AnagraficaSubjectDetail>(`/utenze/subjects/${subjectId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const getUtenzeSubject = getAnagraficaSubject;

export async function createAnagraficaSubject(
  token: string,
  payload: AnagraficaSubjectCreateInput,
): Promise<AnagraficaSubjectDetail> {
  return request<AnagraficaSubjectDetail>("/utenze/subjects", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export const createUtenzeSubject = createAnagraficaSubject;

export async function importAnagraficaSubjectsCsv(
  token: string,
  file: File,
  onProgress?: (percent: number) => void,
): Promise<AnagraficaCsvImportResult> {
  const formData = new FormData();
  formData.append("file", file);

  return requestFormDataWithUploadProgress<AnagraficaCsvImportResult>(
    "/utenze/subjects/import-csv",
    formData,
    token,
    onProgress,
  );
}

export const importUtenzeSubjectsCsv = importAnagraficaSubjectsCsv;

export async function importUtenzeSubjectsXlsx(
  token: string,
  file: File,
  onProgress?: (percent: number) => void,
): Promise<XlsxImportStartResult> {
  const formData = new FormData();
  formData.append("file", file);

  return requestFormDataWithUploadProgress<XlsxImportStartResult>(
    "/utenze/subjects/import-xlsx",
    formData,
    token,
    onProgress,
  );
}

export async function getUtenzeXlsxImportBatch(token: string, batchId: string): Promise<XlsxImportBatch> {
  return request<XlsxImportBatch>(`/utenze/xlsx-import-batches/${batchId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getUtenzeXlsxImportBatches(token: string): Promise<XlsxImportBatch[]> {
  return request<XlsxImportBatch[]>("/utenze/xlsx-import-batches", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getUtenzeSubjectAuditLog(token: string, subjectId: string): Promise<UtenzeAuditLog[]> {
  return request<UtenzeAuditLog[]>(`/utenze/subjects/${subjectId}/audit-log`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getUtenzeSubjectPaymentNotices(token: string, subjectId: string): Promise<AnagraficaPaymentNotice[]> {
  return request<AnagraficaPaymentNotice[]>(`/utenze/subjects/${subjectId}/payment-notices`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getUtenzeAnprStatus(token: string, subjectId: string): Promise<AnprSubjectStatus> {
  return request<AnprSubjectStatus>(`/utenze/anpr/sync/${subjectId}/status`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function syncUtenzeAnprSubject(token: string, subjectId: string): Promise<AnprSyncResult> {
  return request<AnprSyncResult>(`/utenze/anpr/sync/${subjectId}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function verifyUtenzeAnprAlive(token: string, subjectId: string): Promise<AnprSyncResult> {
  return request<AnprSyncResult>(`/utenze/anpr/sync/${subjectId}/verify-alive`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function verifyUtenzeAnprDeathDate(token: string, subjectId: string): Promise<AnprSyncResult> {
  return request<AnprSyncResult>(`/utenze/anpr/sync/${subjectId}/verify-death-date`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function previewLookupUtenzeAnprByCf(token: string, codiceFiscale: string): Promise<AnprPreviewLookupResponse> {
  return request<AnprPreviewLookupResponse>("/utenze/anpr/preview-lookup", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ codice_fiscale: codiceFiscale.trim() }),
  });
}

export async function getUtenzeAnprConfig(token: string): Promise<AnprSyncConfig> {
  return request<AnprSyncConfig>("/utenze/anpr/config", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function updateUtenzeAnprConfig(
  token: string,
  payload: AnprSyncConfigUpdateInput,
): Promise<AnprSyncConfig> {
  return request<AnprSyncConfig>("/utenze/anpr/config", {
    method: "PUT",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export async function getUtenzeAnprJobStatus(token: string): Promise<AnprJobTriggerResult> {
  return request<AnprJobTriggerResult>("/utenze/anpr/job/status", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function triggerUtenzeAnprJob(token: string): Promise<AnprJobTriggerResult> {
  return request<AnprJobTriggerResult>("/utenze/anpr/job/trigger", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function updateAnagraficaSubject(
  token: string,
  subjectId: string,
  payload: AnagraficaSubjectUpdateInput,
): Promise<AnagraficaSubjectDetail> {
  return request<AnagraficaSubjectDetail>(`/utenze/subjects/${subjectId}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export const updateUtenzeSubject = updateAnagraficaSubject;

export async function deactivateAnagraficaSubject(token: string, subjectId: string): Promise<AnagraficaSubjectDetail> {
  return request<AnagraficaSubjectDetail>(`/utenze/subjects/${subjectId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const deactivateUtenzeSubject = deactivateAnagraficaSubject;

export async function getAnagraficaSubjectDocuments(token: string, subjectId: string): Promise<AnagraficaDocument[]> {
  return request<AnagraficaDocument[]>(`/utenze/subjects/${subjectId}/documents`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const getUtenzeSubjectDocuments = getAnagraficaSubjectDocuments;

export async function updateAnagraficaDocument(
  token: string,
  documentId: string,
  payload: { doc_type?: string; notes?: string },
): Promise<AnagraficaDocument> {
  return request<AnagraficaDocument>(`/utenze/documents/${documentId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export const updateUtenzeDocument = updateAnagraficaDocument;

export async function classifyAnagraficaDocumentContent(token: string, documentId: string, text?: string): Promise<AnagraficaDocument> {
  return request<AnagraficaDocument>(`/utenze/documents/${documentId}/content-classification`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(text == null ? {} : { text }),
  });
}

export const classifyUtenzeDocumentContent = classifyAnagraficaDocumentContent;

export async function deleteAnagraficaDocument(token: string, documentId: string, deletePassword?: string): Promise<void> {
  await fetch(`${getApiBaseUrl()}/utenze/documents/${documentId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
      ...(deletePassword ? { "X-GAIA-Delete-Password": deletePassword } : {}),
    },
    cache: "no-store",
  }).then(async (response) => {
    if (!response.ok) {
      let detail = response.statusText || "Request failed";
      try {
        const payload = (await response.json()) as { detail?: unknown };
        if (typeof payload.detail === "string") detail = payload.detail;
      } catch {}
      throw new ApiError(detail, undefined, response.status);
    }
  });
}

export const deleteUtenzeDocument = deleteAnagraficaDocument;

export async function downloadAnagraficaDocumentBlob(token: string, documentId: string): Promise<Blob> {
  return requestBlob(`/utenze/documents/${documentId}/download`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const downloadUtenzeDocumentBlob = downloadAnagraficaDocumentBlob;

export async function downloadAnagraficaExportBlob(
  token: string,
  params?: {
    format?: "csv" | "xlsx";
    search?: string;
    subjectType?: string;
    status?: string;
    letter?: string;
    requiresReview?: boolean;
  },
): Promise<Blob> {
  const query = new URLSearchParams();
  query.set("format", params?.format ?? "csv");
  if (params?.search) query.set("search", params.search);
  if (params?.subjectType) query.set("subject_type", params.subjectType);
  if (params?.status) query.set("status", params.status);
  if (params?.letter) query.set("letter", params.letter);
  if (typeof params?.requiresReview === "boolean") query.set("requires_review", String(params.requiresReview));
  return requestBlob(`/utenze/export?${query.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const downloadUtenzeExportBlob = downloadAnagraficaExportBlob;

export async function previewAnagraficaImport(token: string, letter?: string): Promise<AnagraficaImportPreview> {
  return request<AnagraficaImportPreview>("/utenze/import/preview", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(letter ? { letter } : {}),
  });
}

export const previewUtenzeImport = previewAnagraficaImport;

export async function runAnagraficaImport(token: string, letter?: string): Promise<AnagraficaImportRunResult> {
  return request<AnagraficaImportRunResult>("/utenze/import/run", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(letter ? { letter } : {}),
  });
}

export const runUtenzeImport = runAnagraficaImport;

export async function runAnagraficaImportFromSubjects(token: string): Promise<AnagraficaImportRunResult> {
  return request<AnagraficaImportRunResult>("/utenze/import/run-from-subjects", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const runUtenzeImportFromSubjects = runAnagraficaImportFromSubjects;

export async function getAnagraficaImportJobs(token: string): Promise<AnagraficaImportJob[]> {
  return request<AnagraficaImportJob[]>("/utenze/import/jobs", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const getUtenzeImportJobs = getAnagraficaImportJobs;

export async function getUtenzeVisureRoutingAnomalies(
  token: string,
  params?: {
    resolved?: boolean;
    search?: string;
    page?: number;
    pageSize?: number;
  },
): Promise<AnagraficaVisuraRoutingAnomalyListResponse> {
  const query = new URLSearchParams();
  if (typeof params?.resolved === "boolean") query.set("resolved", String(params.resolved));
  if (params?.search) query.set("search", params.search);
  if (params?.page) query.set("page", String(params.page));
  if (params?.pageSize) query.set("page_size", String(params.pageSize));
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<AnagraficaVisuraRoutingAnomalyListResponse>(`/utenze/visure-routing-anomalies${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getAnagraficaImportJob(token: string, jobId: string): Promise<AnagraficaImportJob> {
  return request<AnagraficaImportJob>(`/utenze/import/jobs/${jobId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const getUtenzeImportJob = getAnagraficaImportJob;

export async function resolveUtenzeVisureRoutingAnomaly(
  token: string,
  anomalyId: string,
): Promise<AnagraficaVisuraRoutingAnomaly> {
  return request<AnagraficaVisuraRoutingAnomaly>(`/utenze/visure-routing-anomalies/${anomalyId}/resolve`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function abortUtenzeRegistryImportJob(token: string, jobId: string): Promise<AnagraficaImportJob> {
  return request<AnagraficaImportJob>(`/utenze/import/jobs/${jobId}/abort-registry`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function resumeUtenzeRegistryImportJob(token: string, jobId: string): Promise<AnagraficaImportRunResult> {
  return request<AnagraficaImportRunResult>(`/utenze/import/jobs/${jobId}/resume-registry`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export type RegistryImportJobDeletedResponse = { deleted: boolean };

export async function deleteUtenzeRegistryImportJob(token: string, jobId: string): Promise<RegistryImportJobDeletedResponse> {
  return request<RegistryImportJobDeletedResponse>(`/utenze/import/jobs/${jobId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function resumeAnagraficaImportJob(token: string, jobId: string): Promise<AnagraficaImportRunResult> {
  return request<AnagraficaImportRunResult>(`/utenze/import/jobs/${jobId}/resume`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const resumeUtenzeImportJob = resumeAnagraficaImportJob;

export async function searchAnagraficaSubjects(token: string, queryText: string, limit = 20): Promise<AnagraficaSearchResult> {
  const query = new URLSearchParams({ q: queryText, limit: String(limit) });
  return request<AnagraficaSearchResult>(`/utenze/search?${query.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const searchUtenzeSubjects = searchAnagraficaSubjects;

export async function importAnagraficaSubjectFromNas(token: string, subjectId: string): Promise<AnagraficaSubjectImportResult> {
  return request<AnagraficaSubjectImportResult>(`/utenze/subjects/${subjectId}/import-from-nas`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const importUtenzeSubjectFromNas = importAnagraficaSubjectFromNas;

export async function getAnagraficaSubjectNasCandidates(
  token: string,
  subjectId: string,
  limit = 20,
): Promise<AnagraficaNasFolderCandidate[]> {
  const query = new URLSearchParams({ limit: String(limit) });
  return request<AnagraficaNasFolderCandidate[]>(`/utenze/subjects/${subjectId}/nas-candidates?${query.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const getUtenzeSubjectNasCandidates = getAnagraficaSubjectNasCandidates;

export async function getAnagraficaSubjectNasImportStatus(token: string, subjectId: string): Promise<AnagraficaSubjectNasImportStatus> {
  return request<AnagraficaSubjectNasImportStatus>(`/utenze/subjects/${subjectId}/nas-import-status`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const getUtenzeSubjectNasImportStatus = getAnagraficaSubjectNasImportStatus;

export async function uploadAnagraficaSubjectDocument(
  token: string,
  subjectId: string,
  file: File,
  docType: string,
  notes?: string,
): Promise<AnagraficaDocument> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("doc_type", docType);
  if (notes) {
    formData.append("notes", notes);
  }
  return request<AnagraficaDocument>(`/utenze/subjects/${subjectId}/documents/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });
}

export const uploadUtenzeSubjectDocument = uploadAnagraficaSubjectDocument;

export async function resetAnagraficaData(token: string, confirm = "RESET ANAGRAFICA"): Promise<AnagraficaResetResult> {
  return request<AnagraficaResetResult>("/utenze/reset", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ confirm }),
  });
}

export const resetUtenzeData = resetAnagraficaData;
