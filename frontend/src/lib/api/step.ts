import type {
  StepAvvisoLink,
  StepContribuenteDetail,
  StepContribuenteRow,
  StepCredential,
  StepCredentialCreateInput,
  StepCredentialUpdateInput,
  StepLinkAnomaly,
  StepLinkStatus,
  StepOverview,
  StepPage,
  StepSyncJob,
  StepSyncJobCreateInput,
} from "@/types/step";

import { request, requestBlob } from "./core";

const STEP_API_BASE = "/elaborazioni/step";

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

function query(params: Record<string, string | number | boolean | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

export function listStepCredentials(token: string): Promise<StepCredential[]> {
  return request<StepCredential[]>(`${STEP_API_BASE}/credentials`, { headers: authHeaders(token) });
}

export function createStepCredential(token: string, payload: StepCredentialCreateInput): Promise<StepCredential> {
  return request<StepCredential>(`${STEP_API_BASE}/credentials`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export function updateStepCredential(
  token: string,
  credentialId: number,
  payload: StepCredentialUpdateInput,
): Promise<StepCredential> {
  return request<StepCredential>(`${STEP_API_BASE}/credentials/${credentialId}`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function deleteStepCredential(token: string, credentialId: number): Promise<void> {
  await request<null>(`${STEP_API_BASE}/credentials/${credentialId}`, { method: "DELETE", headers: authHeaders(token) });
}

export function testStepCredential(token: string, credentialId: number): Promise<StepSyncJob> {
  return request<StepSyncJob>(`${STEP_API_BASE}/credentials/${credentialId}/test`, {
    method: "POST",
    headers: authHeaders(token),
  });
}

export function listStepJobs(token: string): Promise<StepSyncJob[]> {
  return request<StepSyncJob[]>(`${STEP_API_BASE}/jobs`, { headers: authHeaders(token) });
}

export function createStepJob(token: string, payload: StepSyncJobCreateInput): Promise<StepSyncJob> {
  return request<StepSyncJob>(`${STEP_API_BASE}/jobs`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export function cancelStepJob(token: string, jobId: number): Promise<StepSyncJob> {
  return request<StepSyncJob>(`${STEP_API_BASE}/jobs/${jobId}/cancel`, { method: "POST", headers: authHeaders(token) });
}

export async function deleteStepJob(token: string, jobId: number): Promise<void> {
  await request<null>(`${STEP_API_BASE}/jobs/${jobId}`, { method: "DELETE", headers: authHeaders(token) });
}

export function getStepOverview(token: string): Promise<StepOverview> {
  return request<StepOverview>(`${STEP_API_BASE}/overview`, { headers: authHeaders(token) });
}

export function listStepContribuenti(
  token: string,
  params: { q?: string; onlyResiduo?: boolean; page?: number; pageSize?: number } = {},
): Promise<StepPage<StepContribuenteRow>> {
  const search = query({ q: params.q, only_residuo: params.onlyResiduo || null, page: params.page, page_size: params.pageSize });
  return request<StepPage<StepContribuenteRow>>(`${STEP_API_BASE}/contribuenti${search}`, { headers: authHeaders(token) });
}

export function getStepContribuente(token: string, contribuenteId: string): Promise<StepContribuenteDetail> {
  return request<StepContribuenteDetail>(`${STEP_API_BASE}/contribuenti/${contribuenteId}`, { headers: authHeaders(token) });
}

export function downloadStepDocumentoPdf(token: string, documentoId: string): Promise<Blob> {
  return requestBlob(`${STEP_API_BASE}/documenti/${documentoId}/pdf`, { headers: authHeaders(token) });
}

export function listStepLinkAnomalies(
  token: string,
  params: { status?: StepLinkStatus | ""; page?: number; pageSize?: number } = {},
): Promise<StepPage<StepLinkAnomaly>> {
  const search = query({ status: params.status, page: params.page, page_size: params.pageSize });
  return request<StepPage<StepLinkAnomaly>>(`${STEP_API_BASE}/ruolo-links${search}`, { headers: authHeaders(token) });
}

export function listStepLinksForAvviso(token: string, avvisoId: string): Promise<StepAvvisoLink[]> {
  return request<StepAvvisoLink[]>(`${STEP_API_BASE}/ruolo-avvisi/${avvisoId}`, { headers: authHeaders(token) });
}
