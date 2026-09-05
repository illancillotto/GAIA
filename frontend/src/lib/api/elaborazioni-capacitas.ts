import type { CatastoComune, CapacitasAnagraficaHistoryImportInput, CapacitasAnagraficaHistoryImportJob, CapacitasAnagraficaHistoryImportResult, CapacitasDomandeIrrigueSyncJob, CapacitasDomandeIrrigueSyncJobCreateInput, CapacitasInCassSyncJob, CapacitasInCassSyncJobListItem, CapacitasInCassSyncJobListParams, CapacitasInCassRuoloHarvestInput, CapacitasInCassRuoloHarvestResult, CapacitasInCassSyncJobCreateInput, CapacitasLookupOption, CapacitasParticellaAnomalia, CapacitasParticelleSyncJob, CapacitasParticelleSyncJobCreateInput, CapacitasRefetchCertificatiInput, CapacitasRefetchCertificatiResult, CapacitasResolveFragioneInput, CapacitasResolveFragioneResult, CapacitasSearchInput, CapacitasSearchResult, CapacitasTerreniJob, CapacitasTerreniJobCreateInput, CapacitasTerreniSearchInput, CapacitasTerreniSearchResult } from "@/types/api";
import { ApiError, createQueryString, getApiBaseUrl, request } from "./core";

export async function searchCapacitasInvolture(
  token: string,
  payload: CapacitasSearchInput,
): Promise<CapacitasSearchResult> {
  return request<CapacitasSearchResult>("/elaborazioni/capacitas/involture/search", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function importCapacitasAnagraficaHistory(
  token: string,
  payload: CapacitasAnagraficaHistoryImportInput,
): Promise<CapacitasAnagraficaHistoryImportResult> {
  return request<CapacitasAnagraficaHistoryImportResult>("/elaborazioni/capacitas/involture/anagrafica/storico/import", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function createCapacitasAnagraficaHistoryJob(
  token: string,
  payload: CapacitasAnagraficaHistoryImportInput,
): Promise<CapacitasAnagraficaHistoryImportJob> {
  return request<CapacitasAnagraficaHistoryImportJob>("/elaborazioni/capacitas/involture/anagrafica/storico/jobs", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function listCapacitasAnagraficaHistoryJobs(token: string): Promise<CapacitasAnagraficaHistoryImportJob[]> {
  return request<CapacitasAnagraficaHistoryImportJob[]>("/elaborazioni/capacitas/involture/anagrafica/storico/jobs", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createCapacitasDomandeIrrigueSyncJob(
  token: string,
  payload: CapacitasDomandeIrrigueSyncJobCreateInput,
): Promise<CapacitasDomandeIrrigueSyncJob> {
  return request<CapacitasDomandeIrrigueSyncJob>("/elaborazioni/capacitas/involture/domande-irrigue/jobs", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function listCapacitasDomandeIrrigueSyncJobs(token: string): Promise<CapacitasDomandeIrrigueSyncJob[]> {
  return request<CapacitasDomandeIrrigueSyncJob[]>("/elaborazioni/capacitas/involture/domande-irrigue/jobs", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function rerunCapacitasDomandeIrrigueSyncJob(
  token: string,
  jobId: number,
): Promise<CapacitasDomandeIrrigueSyncJob> {
  return request<CapacitasDomandeIrrigueSyncJob>(`/elaborazioni/capacitas/involture/domande-irrigue/jobs/${jobId}/run`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function deleteCapacitasDomandeIrrigueSyncJob(token: string, jobId: number): Promise<void> {
  await request<null>(`/elaborazioni/capacitas/involture/domande-irrigue/jobs/${jobId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createCapacitasInCassSyncJob(
  token: string,
  payload: CapacitasInCassSyncJobCreateInput,
): Promise<CapacitasInCassSyncJob> {
  return request<CapacitasInCassSyncJob>("/elaborazioni/capacitas/incass/avvisi/jobs", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function createCapacitasInCassRuoloHarvest(
  token: string,
  payload: CapacitasInCassRuoloHarvestInput,
): Promise<CapacitasInCassRuoloHarvestResult> {
  return request<CapacitasInCassRuoloHarvestResult>("/elaborazioni/capacitas/incass/avvisi/jobs/ruolo-harvest", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function listCapacitasInCassSyncJobs(
  token: string,
  params: CapacitasInCassSyncJobListParams = {},
): Promise<CapacitasInCassSyncJobListItem[]> {
  const query = new URLSearchParams();
  if (params.limit != null) {
    query.set("limit", String(params.limit));
  }
  if (params.status) {
    query.set("status", params.status);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<CapacitasInCassSyncJobListItem[]>(`/elaborazioni/capacitas/incass/avvisi/jobs${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function rerunCapacitasInCassSyncJob(token: string, jobId: number): Promise<CapacitasInCassSyncJob> {
  return request<CapacitasInCassSyncJob>(`/elaborazioni/capacitas/incass/avvisi/jobs/${jobId}/run`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function deleteCapacitasInCassSyncJob(token: string, jobId: number): Promise<void> {
  await request<null>(`/elaborazioni/capacitas/incass/avvisi/jobs/${jobId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function rerunCapacitasAnagraficaHistoryJob(
  token: string,
  jobId: number,
): Promise<CapacitasAnagraficaHistoryImportJob> {
  return request<CapacitasAnagraficaHistoryImportJob>(
    `/elaborazioni/capacitas/involture/anagrafica/storico/jobs/${jobId}/run`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );
}

export async function deleteCapacitasAnagraficaHistoryJob(token: string, jobId: number): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/elaborazioni/capacitas/involture/anagrafica/storico/jobs/${jobId}`, {
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

export async function importCapacitasAnagraficaHistoryFile(
  token: string,
  file: File,
  options?: { credentialId?: number | null; continueOnError?: boolean },
): Promise<CapacitasAnagraficaHistoryImportResult> {
  const formData = new FormData();
  formData.append("file", file);
  if (options?.credentialId != null) {
    formData.append("credential_id", String(options.credentialId));
  }
  if (options?.continueOnError != null) {
    formData.append("continue_on_error", String(options.continueOnError));
  }
  return request<CapacitasAnagraficaHistoryImportResult>("/elaborazioni/capacitas/involture/anagrafica/storico/import-file", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });
}

export async function searchCapacitasFrazioni(
  token: string,
  query: string,
  credentialId?: number | null,
): Promise<CapacitasLookupOption[]> {
  const qs = createQueryString({
    q: query,
    credential_id: credentialId != null ? String(credentialId) : undefined,
  });
  return request<CapacitasLookupOption[]>(`/elaborazioni/capacitas/involture/frazioni${qs}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getCapacitasSezioni(
  token: string,
  frazioneId: string,
  credentialId?: number | null,
): Promise<CapacitasLookupOption[]> {
  const qs = createQueryString({
    frazione_id: frazioneId,
    credential_id: credentialId != null ? String(credentialId) : undefined,
  });
  return request<CapacitasLookupOption[]>(`/elaborazioni/capacitas/involture/sezioni${qs}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getCapacitasFogli(
  token: string,
  frazioneId: string,
  sezione?: string,
  credentialId?: number | null,
): Promise<CapacitasLookupOption[]> {
  const qs = createQueryString({
    frazione_id: frazioneId,
    sezione,
    credential_id: credentialId != null ? String(credentialId) : undefined,
  });
  return request<CapacitasLookupOption[]>(`/elaborazioni/capacitas/involture/fogli${qs}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function searchCapacitasTerreni(
  token: string,
  payload: CapacitasTerreniSearchInput,
): Promise<CapacitasTerreniSearchResult> {
  return request<CapacitasTerreniSearchResult>("/elaborazioni/capacitas/involture/terreni/search", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function createCapacitasTerreniJob(
  token: string,
  payload: CapacitasTerreniJobCreateInput,
): Promise<CapacitasTerreniJob> {
  return request<CapacitasTerreniJob>("/elaborazioni/capacitas/involture/terreni/jobs", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function listCapacitasTerreniJobs(token: string): Promise<CapacitasTerreniJob[]> {
  return request<CapacitasTerreniJob[]>("/elaborazioni/capacitas/involture/terreni/jobs", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function rerunCapacitasTerreniJob(token: string, jobId: number): Promise<CapacitasTerreniJob> {
  return request<CapacitasTerreniJob>(`/elaborazioni/capacitas/involture/terreni/jobs/${jobId}/run`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function deleteCapacitasTerreniJob(token: string, jobId: number): Promise<void> {
  await request<null>(`/elaborazioni/capacitas/involture/terreni/jobs/${jobId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createCapacitasParticelleSyncJob(
  token: string,
  payload: CapacitasParticelleSyncJobCreateInput,
): Promise<CapacitasParticelleSyncJob> {
  return request<CapacitasParticelleSyncJob>("/elaborazioni/capacitas/involture/particelle/jobs", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function listCapacitasParticelleSyncJobs(token: string): Promise<CapacitasParticelleSyncJob[]> {
  return request<CapacitasParticelleSyncJob[]>("/elaborazioni/capacitas/involture/particelle/jobs", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function rerunCapacitasParticelleSyncJob(token: string, jobId: number): Promise<CapacitasParticelleSyncJob> {
  return request<CapacitasParticelleSyncJob>(`/elaborazioni/capacitas/involture/particelle/jobs/${jobId}/run`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function deleteCapacitasParticelleSyncJob(token: string, jobId: number): Promise<void> {
  await request<null>(`/elaborazioni/capacitas/involture/particelle/jobs/${jobId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function stopCapacitasParticelleSyncJob(token: string, jobId: number): Promise<CapacitasParticelleSyncJob> {
  return request<CapacitasParticelleSyncJob>(`/elaborazioni/capacitas/involture/particelle/jobs/${jobId}/stop`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function patchCapacitasParticelleSyncJobSpeed(
  token: string,
  jobId: number,
  doubleSpeed: boolean,
): Promise<CapacitasParticelleSyncJob> {
  return request<CapacitasParticelleSyncJob>(
    `/elaborazioni/capacitas/involture/particelle/jobs/${jobId}/speed`,
    {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ double_speed: doubleSpeed }),
    },
  );
}

export async function refetchCapacitasCertificatiEmpty(
  token: string,
  payload: CapacitasRefetchCertificatiInput,
): Promise<CapacitasRefetchCertificatiResult> {
  return request<CapacitasRefetchCertificatiResult>(
    "/elaborazioni/capacitas/involture/certificati/refetch-empty",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    },
  );
}

export async function listCapacitasParticelleAnomalie(
  token: string,
  params?: { limit?: number; offset?: number },
): Promise<CapacitasParticellaAnomalia[]> {
  const query = createQueryString({
    limit: params?.limit?.toString(),
    offset: params?.offset?.toString(),
  });
  return request<CapacitasParticellaAnomalia[]>(
    `/elaborazioni/capacitas/involture/particelle/anomalie${query}`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
}

export async function resolveCapacitasParticellaFrazione(
  token: string,
  particellaId: string,
  payload: CapacitasResolveFragioneInput,
): Promise<CapacitasResolveFragioneResult> {
  return request<CapacitasResolveFragioneResult>(
    `/elaborazioni/capacitas/involture/particelle/${particellaId}/resolve-frazione`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload),
    },
  );
}

export async function getCatastoComuni(token: string, search?: string): Promise<CatastoComune[]> {
  const query = createQueryString({ search });
  return request<CatastoComune[]>(`/catasto/comuni${query}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}
