import type { ElaborazioneCredential, ElaborazioneCredentialStatus, ElaborazioneCredentialTestResult, ElaborazioneOperationResponse, CapacitasCredential, CapacitasCredentialCreateInput, CapacitasCredentialTestResult as CapacitasCredentialProbeResult, CapacitasCredentialUpdateInput, BonificaOristaneseCredential, BonificaOristaneseCredentialCreateInput, BonificaOristaneseCredentialTestResult as BonificaOristaneseCredentialProbeResult, BonificaOristaneseCredentialUpdateInput, BonificaSyncRunRequest, BonificaSyncRunResponse, BonificaSyncStatusResponse, PostaOnlineCredential, PostaOnlineCredentialCreateInput, PostaOnlineCredentialTestInput, PostaOnlineCredentialUpdateInput, PostaOnlineRegisteredMailSyncJob, PostaOnlineRegisteredMailSyncJobCreateInput, BonificaUserStaging, BonificaUserStagingBulkApproveResponse, BonificaUserStagingListResponse } from "@/types/api";
import { ApiError, getApiBaseUrl, getWebSocketBaseUrl, request } from "./core";

export async function getElaborazioneCredentials(token: string): Promise<ElaborazioneCredentialStatus> {
  return request<ElaborazioneCredentialStatus>("/elaborazioni/credentials", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function saveElaborazioneCredentials(
  token: string,
  payload: {
    label?: string;
    sister_username: string;
    sister_password: string;
    convenzione?: string;
    codice_richiesta?: string;
    ufficio_provinciale?: string;
    active?: boolean;
    is_default?: boolean;
    schedule_enabled?: boolean;
    availability_schedule?: ElaborazioneCredential["availability_schedule"];
  },
): Promise<ElaborazioneCredential> {
  return request<ElaborazioneCredential>("/elaborazioni/credentials", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function updateElaborazioneCredential(
  token: string,
  credentialId: string,
  payload: {
    label?: string;
    sister_username?: string;
    sister_password?: string;
    convenzione?: string | null;
    codice_richiesta?: string | null;
    ufficio_provinciale?: string;
    active?: boolean;
    is_default?: boolean;
    schedule_enabled?: boolean;
    availability_schedule?: ElaborazioneCredential["availability_schedule"];
  },
): Promise<ElaborazioneCredential> {
  return request<ElaborazioneCredential>(`/elaborazioni/credentials/${credentialId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function deleteElaborazioneCredentials(token: string): Promise<ElaborazioneOperationResponse> {
  return request<ElaborazioneOperationResponse>("/elaborazioni/credentials", {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function deleteElaborazioneCredential(
  token: string,
  credentialId: string,
): Promise<ElaborazioneOperationResponse> {
  return request<ElaborazioneOperationResponse>(`/elaborazioni/credentials/${credentialId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function releaseElaborazioneCredentials(token: string): Promise<ElaborazioneOperationResponse> {
  return request<ElaborazioneOperationResponse>("/elaborazioni/credentials/release", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function testElaborazioneCredentials(
  token: string,
  payload?: {
    credential_id?: string;
    sister_username: string;
    sister_password: string;
    convenzione?: string;
    codice_richiesta?: string;
    ufficio_provinciale?: string;
  } | {
    credential_id: string;
  },
): Promise<ElaborazioneCredentialTestResult> {
  return request<ElaborazioneCredentialTestResult>("/elaborazioni/credentials/test", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: payload ? JSON.stringify(payload) : undefined,
  });
}

export async function getElaborazioneCredentialTest(
  token: string,
  testId: string,
): Promise<ElaborazioneCredentialTestResult> {
  return request<ElaborazioneCredentialTestResult>(`/elaborazioni/credentials/test/${testId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export function createElaborazioneCredentialTestWebSocket(testId: string, token: string): WebSocket | null {
  if (typeof window === "undefined") {
    return null;
  }

  const url = new URL(`${getWebSocketBaseUrl()}/elaborazioni/ws/credentials-test/${testId}`);
  url.searchParams.set("token", token);
  return new WebSocket(url.toString());
}

export async function listCapacitasCredentials(token: string): Promise<CapacitasCredential[]> {
  return request<CapacitasCredential[]>("/elaborazioni/capacitas/credentials", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createCapacitasCredential(
  token: string,
  payload: CapacitasCredentialCreateInput,
): Promise<CapacitasCredential> {
  return request<CapacitasCredential>("/elaborazioni/capacitas/credentials", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function updateCapacitasCredential(
  token: string,
  credentialId: number,
  payload: CapacitasCredentialUpdateInput,
): Promise<CapacitasCredential> {
  return request<CapacitasCredential>(`/elaborazioni/capacitas/credentials/${credentialId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function deleteCapacitasCredential(token: string, credentialId: number): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/elaborazioni/capacitas/credentials/${credentialId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let detail = "Request failed";

    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") {
        detail = payload.detail;
      }
    } catch {
      detail = response.statusText || detail;
    }

    throw new ApiError(detail, undefined, response.status);
  }
}

export async function testCapacitasCredential(
  token: string,
  credentialId: number,
): Promise<CapacitasCredentialProbeResult> {
  return request<CapacitasCredentialProbeResult>(`/elaborazioni/capacitas/credentials/${credentialId}/test`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listBonificaOristaneseCredentials(token: string): Promise<BonificaOristaneseCredential[]> {
  return request<BonificaOristaneseCredential[]>("/elaborazioni/bonifica/credentials", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createBonificaOristaneseCredential(
  token: string,
  payload: BonificaOristaneseCredentialCreateInput,
): Promise<BonificaOristaneseCredential> {
  return request<BonificaOristaneseCredential>("/elaborazioni/bonifica/credentials", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function updateBonificaOristaneseCredential(
  token: string,
  credentialId: number,
  payload: BonificaOristaneseCredentialUpdateInput,
): Promise<BonificaOristaneseCredential> {
  return request<BonificaOristaneseCredential>(`/elaborazioni/bonifica/credentials/${credentialId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function deleteBonificaOristaneseCredential(token: string, credentialId: number): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/elaborazioni/bonifica/credentials/${credentialId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let detail = "Request failed";

    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") {
        detail = payload.detail;
      }
    } catch {
      detail = response.statusText || detail;
    }

    throw new ApiError(detail, undefined, response.status);
  }
}

export async function testBonificaOristaneseCredential(
  token: string,
  credentialId: number,
): Promise<BonificaOristaneseCredentialProbeResult> {
  return request<BonificaOristaneseCredentialProbeResult>(
    `/elaborazioni/bonifica/credentials/${credentialId}/test`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );
}

export async function listPostaOnlineCredentials(token: string): Promise<PostaOnlineCredential[]> {
  return request<PostaOnlineCredential[]>("/elaborazioni/posta-online/credentials", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createPostaOnlineCredential(
  token: string,
  payload: PostaOnlineCredentialCreateInput,
): Promise<PostaOnlineCredential> {
  return request<PostaOnlineCredential>("/elaborazioni/posta-online/credentials", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function updatePostaOnlineCredential(
  token: string,
  credentialId: number,
  payload: PostaOnlineCredentialUpdateInput,
): Promise<PostaOnlineCredential> {
  return request<PostaOnlineCredential>(`/elaborazioni/posta-online/credentials/${credentialId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function deletePostaOnlineCredential(token: string, credentialId: number): Promise<void> {
  await request<null>(`/elaborazioni/posta-online/credentials/${credentialId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function testPostaOnlineCredential(
  token: string,
  credentialId: number,
  payload: PostaOnlineCredentialTestInput = {},
): Promise<PostaOnlineRegisteredMailSyncJob> {
  return request<PostaOnlineRegisteredMailSyncJob>(`/elaborazioni/posta-online/credentials/${credentialId}/test`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function listPostaOnlineRegisteredMailJobs(token: string): Promise<PostaOnlineRegisteredMailSyncJob[]> {
  return request<PostaOnlineRegisteredMailSyncJob[]>("/elaborazioni/posta-online/raccomandate/jobs", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createPostaOnlineRegisteredMailJob(
  token: string,
  payload: PostaOnlineRegisteredMailSyncJobCreateInput,
): Promise<PostaOnlineRegisteredMailSyncJob> {
  return request<PostaOnlineRegisteredMailSyncJob>("/elaborazioni/posta-online/raccomandate/jobs", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function rerunPostaOnlineRegisteredMailJob(
  token: string,
  jobId: number,
): Promise<PostaOnlineRegisteredMailSyncJob> {
  return request<PostaOnlineRegisteredMailSyncJob>(`/elaborazioni/posta-online/raccomandate/jobs/${jobId}/run`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function deletePostaOnlineRegisteredMailJob(token: string, jobId: number): Promise<void> {
  await request<null>(`/elaborazioni/posta-online/raccomandate/jobs/${jobId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getBonificaSyncStatus(token: string): Promise<BonificaSyncStatusResponse> {
  return request<BonificaSyncStatusResponse>("/elaborazioni/bonifica/sync/status", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function runBonificaSync(token: string, payload: BonificaSyncRunRequest): Promise<BonificaSyncRunResponse> {
  return request<BonificaSyncRunResponse>("/elaborazioni/bonifica/sync/run", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function deleteBonificaSyncJob(token: string, jobId: string): Promise<void> {
  await request<null>(`/elaborazioni/bonifica/sync/jobs/${jobId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getUtenzeBonificaStaging(
  token: string,
  params: { page?: number; page_size?: number } = {},
): Promise<BonificaUserStagingListResponse> {
  const search = new URLSearchParams();
  if (params.page != null) search.set("page", String(params.page));
  if (params.page_size != null) search.set("page_size", String(params.page_size));
  const suffix = search.toString();

  return request<BonificaUserStagingListResponse>(`/utenze/bonifica-staging${suffix ? `?${suffix}` : ""}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getUtenzeBonificaStagingItem(token: string, stagingId: string): Promise<BonificaUserStaging> {
  return request<BonificaUserStaging>(`/utenze/bonifica-staging/${stagingId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function approveUtenzeBonificaStagingItem(token: string, stagingId: string): Promise<BonificaUserStaging> {
  return request<BonificaUserStaging>(`/utenze/bonifica-staging/${stagingId}/approve`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function rejectUtenzeBonificaStagingItem(token: string, stagingId: string): Promise<BonificaUserStaging> {
  return request<BonificaUserStaging>(`/utenze/bonifica-staging/${stagingId}/reject`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function bulkApproveUtenzeBonificaStaging(
  token: string,
  ids: string[],
): Promise<BonificaUserStagingBulkApproveResponse> {
  return request<BonificaUserStagingBulkApproveResponse>("/utenze/bonifica-staging/bulk-approve", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ ids }),
  });
}
