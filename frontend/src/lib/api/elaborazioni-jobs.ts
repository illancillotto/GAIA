import type { CatastoDocument, ElaborazioneBatch, ElaborazioneAutoJobControl, ElaborazioneAnprSummary, ElaborazioneBatchDetail, ElaborazioneCaptchaSummary, ElaborazioneOperationResponse, ElaborazioneRuoloAutoSyncConfig, ElaborazioneRuoloAutoSyncConfigUpdateInput, ElaborazioneRuoloAutoSyncStatus, ElaborazioneRuntimeMetrics, GateMobileSyncRunTriggerResponse, GateMobileSyncStatusResponse, ElaborazioneRichiesta, ElaborazioneRichiestaCreateInput } from "@/types/api";
import { createQueryString, getWebSocketBaseUrl, request, requestBlob } from "./core";

const ELABORAZIONE_BATCH_DETAIL_CACHE_TTL_MS = 1000;
type ElaborazioneBatchDetailCacheEntry = {
  expiresAt: number;
  promise: Promise<ElaborazioneBatchDetail>;
};

const elaborazioneBatchDetailCache = new Map<string, ElaborazioneBatchDetailCacheEntry>();
export async function createElaborazioneBatch(
  token: string,
  file: File,
  name?: string,
  credentialIds: string[] = [],
): Promise<ElaborazioneBatchDetail> {
  const formData = new FormData();
  formData.append("file", file);
  if (name) formData.append("name", name);
  credentialIds.forEach((credentialId) => formData.append("credential_ids", credentialId));

  return request<ElaborazioneBatchDetail>("/elaborazioni/batches", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });
}

export async function getElaborazioneBatches(token: string, status?: string): Promise<ElaborazioneBatch[]> {
  const query = createQueryString({ status });
  return request<ElaborazioneBatch[]>(`/elaborazioni/batches${query}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getElaborazioneBatch(
  token: string,
  batchId: string,
  options?: { bustCache?: boolean },
): Promise<ElaborazioneBatchDetail> {
  const cacheKey = `${token}:${batchId}`;
  const now = Date.now();

  if (options?.bustCache) {
    elaborazioneBatchDetailCache.delete(cacheKey);
  } else {
    const cached = elaborazioneBatchDetailCache.get(cacheKey);
    if (cached && cached.expiresAt > now) {
      return cached.promise;
    }
  }

  const promise = request<ElaborazioneBatchDetail>(`/elaborazioni/batches/${batchId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  }).finally(() => {
    globalThis.setTimeout(() => {
      const current = elaborazioneBatchDetailCache.get(cacheKey);
      if (current?.promise === promise && current.expiresAt <= Date.now()) {
        elaborazioneBatchDetailCache.delete(cacheKey);
      }
    }, ELABORAZIONE_BATCH_DETAIL_CACHE_TTL_MS);
  });

  elaborazioneBatchDetailCache.set(cacheKey, {
    expiresAt: now + ELABORAZIONE_BATCH_DETAIL_CACHE_TTL_MS,
    promise,
  });
  return promise;
}

export async function startElaborazioneBatch(token: string, batchId: string): Promise<ElaborazioneBatch> {
  return request<ElaborazioneBatch>(`/elaborazioni/batches/${batchId}/start`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function cancelElaborazioneBatch(token: string, batchId: string): Promise<ElaborazioneBatch> {
  return request<ElaborazioneBatch>(`/elaborazioni/batches/${batchId}/cancel`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function retryFailedElaborazioneBatch(token: string, batchId: string): Promise<ElaborazioneBatch> {
  return request<ElaborazioneBatch>(`/elaborazioni/batches/${batchId}/retry-failed`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createElaborazioneRichiesta(
  token: string,
  payload: ElaborazioneRichiestaCreateInput,
): Promise<ElaborazioneBatchDetail> {
  return request<ElaborazioneBatchDetail>("/elaborazioni/requests", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getPendingElaborazioneCaptcha(token: string): Promise<ElaborazioneRichiesta[]> {
  return request<ElaborazioneRichiesta[]>("/elaborazioni/captcha/pending", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getElaborazioneCaptchaSummary(token: string): Promise<ElaborazioneCaptchaSummary> {
  return request<ElaborazioneCaptchaSummary>("/elaborazioni/captcha/summary", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getElaborazioneAnprSummary(token: string): Promise<ElaborazioneAnprSummary> {
  return request<ElaborazioneAnprSummary>("/elaborazioni/utenze-anpr/summary", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getElaborazioneRuntimeMetrics(token: string): Promise<ElaborazioneRuntimeMetrics> {
  return request<ElaborazioneRuntimeMetrics>("/elaborazioni/metrics", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getElaborazioneAutoJobControls(token: string): Promise<ElaborazioneAutoJobControl[]> {
  return request<ElaborazioneAutoJobControl[]>("/elaborazioni/auto-job-controls", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updateElaborazioneAutoJobControl(
  token: string,
  controlKey: string,
  payload: { enabled: boolean },
): Promise<ElaborazioneAutoJobControl> {
  return request<ElaborazioneAutoJobControl>(`/elaborazioni/auto-job-controls/${controlKey}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getElaborazioneRuoloAutoSyncStatus(token: string): Promise<ElaborazioneRuoloAutoSyncStatus> {
  return request<ElaborazioneRuoloAutoSyncStatus>("/elaborazioni/ruolo-autosync/status", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getElaborazioneRuoloAutoSyncConfig(token: string): Promise<ElaborazioneRuoloAutoSyncConfig> {
  return request<ElaborazioneRuoloAutoSyncConfig>("/elaborazioni/ruolo-autosync/config", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updateElaborazioneRuoloAutoSyncConfig(
  token: string,
  payload: ElaborazioneRuoloAutoSyncConfigUpdateInput,
): Promise<ElaborazioneRuoloAutoSyncConfig> {
  return request<ElaborazioneRuoloAutoSyncConfig>("/elaborazioni/ruolo-autosync/config", {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function refreshElaborazioneRuoloAutoSyncSource(token: string): Promise<ElaborazioneOperationResponse> {
  return request<ElaborazioneOperationResponse>("/elaborazioni/ruolo-autosync/refresh-source", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function runElaborazioneRuoloAutoSyncNow(token: string): Promise<ElaborazioneOperationResponse> {
  return request<ElaborazioneOperationResponse>("/elaborazioni/ruolo-autosync/run-now", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getGateMobileSyncStatus(token: string): Promise<GateMobileSyncStatusResponse> {
  return request<GateMobileSyncStatusResponse>("/operazioni/mobile-gateway-sync/status", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function triggerGateMobileSyncRun(token: string): Promise<GateMobileSyncRunTriggerResponse> {
  return request<GateMobileSyncRunTriggerResponse>("/operazioni/mobile-gateway-sync/run", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function solveElaborazioneCaptcha(
  token: string,
  requestId: string,
  text: string,
): Promise<ElaborazioneRichiesta> {
  return request<ElaborazioneRichiesta>(`/elaborazioni/captcha/${requestId}/solve`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ text }),
  });
}

export async function skipElaborazioneCaptcha(token: string, requestId: string): Promise<ElaborazioneRichiesta> {
  return request<ElaborazioneRichiesta>(`/elaborazioni/captcha/${requestId}/skip`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getCatastoDocuments(
  token: string,
  filters?: {
    q?: string;
    comune?: string;
    foglio?: string;
    particella?: string;
    created_from?: string;
    created_to?: string;
  },
): Promise<CatastoDocument[]> {
  const query = createQueryString(filters ?? {});
  return request<CatastoDocument[]>(`/catasto/documents${query}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function searchCatastoDocuments(
  token: string,
  filters?: {
    q?: string;
    comune?: string;
    foglio?: string;
    particella?: string;
    created_from?: string;
    created_to?: string;
  },
): Promise<CatastoDocument[]> {
  const query = createQueryString(filters ?? {});
  return request<CatastoDocument[]>(`/catasto/documents/search${query}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getCatastoDocument(token: string, documentId: string): Promise<CatastoDocument> {
  return request<CatastoDocument>(`/catasto/documents/${documentId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function fetchElaborazioneCaptchaImageBlob(token: string, requestId: string): Promise<Blob> {
  return requestBlob(`/elaborazioni/captcha/${requestId}/image`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function downloadCatastoDocumentBlob(token: string, documentId: string): Promise<Blob> {
  return requestBlob(`/catasto/documents/${documentId}/download`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function downloadElaborazioneBatchZipBlob(token: string, batchId: string): Promise<Blob> {
  return requestBlob(`/elaborazioni/batches/${batchId}/download`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function downloadElaborazioneBatchReportJsonBlob(token: string, batchId: string): Promise<Blob> {
  return requestBlob(`/elaborazioni/batches/${batchId}/report.json`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function downloadElaborazioneBatchReportMarkdownBlob(token: string, batchId: string): Promise<Blob> {
  return requestBlob(`/elaborazioni/batches/${batchId}/report.md`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function downloadElaborazioneRequestArtifactsBlob(token: string, requestId: string): Promise<Blob> {
  return requestBlob(`/elaborazioni/requests/${requestId}/artifacts/download`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function fetchElaborazioneRequestArtifactPreviewBlob(token: string, requestId: string): Promise<Blob> {
  return requestBlob(`/elaborazioni/requests/${requestId}/artifacts/preview`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function downloadSelectedCatastoDocumentsZipBlob(
  token: string,
  documentIds: string[],
): Promise<Blob> {
  return requestBlob("/catasto/documents/download", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ document_ids: documentIds }),
  });
}

export function createElaborazioneBatchWebSocket(batchId: string, token: string): WebSocket | null {
  if (typeof window === "undefined") {
    return null;
  }

  const url = new URL(`${getWebSocketBaseUrl()}/elaborazioni/ws/${batchId}`);
  url.searchParams.set("token", token);
  return new WebSocket(url.toString());
}

export type {
  ElaborazioneBatch,
  ElaborazioneBatchDetail,
  ElaborazioneBatchWebSocketEvent,
  ElaborazioneCaptchaSummary,
  ElaborazioneCredential,
  ElaborazioneCredentialStatus,
  ElaborazioneCredentialTestResult,
  ElaborazioneCredentialTestWebSocketEvent,
  ElaborazioneOperationResponse,
  ElaborazioneRuntimeMetrics,
  ElaborazioneRichiesta,
  ElaborazioneRichiestaCreateInput,
  GateMobileSyncRunTriggerResponse,
  GateMobileSyncStatusResponse,
} from "@/types/api";
