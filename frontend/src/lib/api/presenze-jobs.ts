import type { PresenzeAutoSyncConfig, PresenzeAutoSyncConfigUpdateInput, PresenzeBankHoursGuidanceConfig, PresenzeBankHoursGuidanceConfigRevision, PresenzeBankHoursGuidanceConfigUpdateInput, PresenzeImportJob, PresenzeImportJobListResponse, PresenzeImportJsonResponse, PresenzeImportPreviewResponse, PresenzeScheduleBootstrapApplyRequest, PresenzeScheduleBootstrapApplyResponse, PresenzeScheduleBootstrapPreviewResponse, PresenzeSyncJob, PresenzeSyncJobCreateInput, PresenzeSyncJobListResponse, PresenzeSyncJobRetrySelectedInput, PresenzeStraordinariExportJobCreateInput, PresenzeStraordinariPreviewResponse, PresenzeXlsmExportJobCreateInput } from "@/types/api";
import { request, requestBlob } from "./core";

const PRESENZE_API_BASE = "/presenze";
export async function getPresenzeScheduleBootstrapPreview(token: string): Promise<PresenzeScheduleBootstrapPreviewResponse> {
  return request<PresenzeScheduleBootstrapPreviewResponse>(`${PRESENZE_API_BASE}/configuration/schedule-bootstrap-preview`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function applyPresenzeScheduleBootstrap(
  token: string,
  payload: PresenzeScheduleBootstrapApplyRequest = {},
): Promise<PresenzeScheduleBootstrapApplyResponse> {
  return request<PresenzeScheduleBootstrapApplyResponse>(`${PRESENZE_API_BASE}/configuration/schedule-bootstrap-apply`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function previewPresenzeImport(
  token: string,
  file: File,
): Promise<PresenzeImportPreviewResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return request<PresenzeImportPreviewResponse>(`${PRESENZE_API_BASE}/import/preview`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });
}

export async function importPresenzeJson(
  token: string,
  file: File,
): Promise<PresenzeImportJsonResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return request<PresenzeImportJsonResponse>(`${PRESENZE_API_BASE}/import/json`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });
}

export async function listPresenzeImportJobs(token: string): Promise<PresenzeImportJob[]> {
  const response = await request<PresenzeImportJobListResponse>(`${PRESENZE_API_BASE}/import/jobs`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return response.items;
}

export async function getPresenzeImportJob(token: string, jobId: string): Promise<PresenzeImportJob> {
  return request<PresenzeImportJob>(`${PRESENZE_API_BASE}/import/jobs/${jobId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createPresenzeSyncJob(token: string, payload: PresenzeSyncJobCreateInput): Promise<PresenzeSyncJob> {
  return request<PresenzeSyncJob>(`${PRESENZE_API_BASE}/sync/jobs`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function createPresenzeXlsmExportJob(token: string, payload: PresenzeXlsmExportJobCreateInput): Promise<PresenzeSyncJob> {
  return request<PresenzeSyncJob>(`${PRESENZE_API_BASE}/export/jobs/xlsm`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function previewPresenzeStraordinariExport(
  token: string,
  params: { collaboratorId?: string | null } = {},
): Promise<PresenzeStraordinariPreviewResponse> {
  const query = new URLSearchParams();
  if (params.collaboratorId) {
    query.set("collaborator_id", params.collaboratorId);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<PresenzeStraordinariPreviewResponse>(`${PRESENZE_API_BASE}/export/straordinari/preview${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createPresenzeStraordinariExportJob(
  token: string,
  payload: PresenzeStraordinariExportJobCreateInput,
): Promise<PresenzeSyncJob> {
  return request<PresenzeSyncJob>(`${PRESENZE_API_BASE}/export/jobs/straordinari`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getPresenzeAutoSyncConfig(token: string): Promise<PresenzeAutoSyncConfig> {
  return request<PresenzeAutoSyncConfig>(`${PRESENZE_API_BASE}/sync/config`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updatePresenzeAutoSyncConfig(
  token: string,
  payload: PresenzeAutoSyncConfigUpdateInput,
): Promise<PresenzeAutoSyncConfig> {
  return request<PresenzeAutoSyncConfig>(`${PRESENZE_API_BASE}/sync/config`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getPresenzeBankHoursGuidanceConfig(token: string): Promise<PresenzeBankHoursGuidanceConfig> {
  return request<PresenzeBankHoursGuidanceConfig>(`${PRESENZE_API_BASE}/bank-hours/guidance-config`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updatePresenzeBankHoursGuidanceConfig(
  token: string,
  payload: PresenzeBankHoursGuidanceConfigUpdateInput,
): Promise<PresenzeBankHoursGuidanceConfig> {
  return request<PresenzeBankHoursGuidanceConfig>(`${PRESENZE_API_BASE}/bank-hours/guidance-config`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function listPresenzeBankHoursGuidanceConfigHistory(token: string): Promise<PresenzeBankHoursGuidanceConfigRevision[]> {
  return request<PresenzeBankHoursGuidanceConfigRevision[]>(`${PRESENZE_API_BASE}/bank-hours/guidance-config/history`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listPresenzeSyncJobs(token: string, params: { limit?: number } = {}): Promise<PresenzeSyncJob[]> {
  const query = new URLSearchParams();
  if (params.limit != null) {
    query.set("limit", String(params.limit));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  const response = await request<PresenzeSyncJobListResponse>(`${PRESENZE_API_BASE}/sync/jobs${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return response.items;
}

export async function getPresenzeSyncJob(token: string, jobId: string): Promise<PresenzeSyncJob> {
  return request<PresenzeSyncJob>(`${PRESENZE_API_BASE}/sync/jobs/${jobId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listPresenzeXlsmExportJobs(token: string, params: { limit?: number } = {}): Promise<PresenzeSyncJob[]> {
  const query = new URLSearchParams();
  if (params.limit != null) {
    query.set("limit", String(params.limit));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  const response = await request<PresenzeSyncJobListResponse>(`${PRESENZE_API_BASE}/export/jobs/xlsm${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return response.items;
}

export async function getPresenzeXlsmExportJob(token: string, jobId: string): Promise<PresenzeSyncJob> {
  return request<PresenzeSyncJob>(`${PRESENZE_API_BASE}/export/jobs/xlsm/${jobId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listPresenzeStraordinariExportJobs(token: string, params: { limit?: number } = {}): Promise<PresenzeSyncJob[]> {
  const query = new URLSearchParams();
  if (params.limit != null) {
    query.set("limit", String(params.limit));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  const response = await request<PresenzeSyncJobListResponse>(`${PRESENZE_API_BASE}/export/jobs/straordinari${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return response.items;
}

export async function getPresenzeStraordinariExportJob(token: string, jobId: string): Promise<PresenzeSyncJob> {
  return request<PresenzeSyncJob>(`${PRESENZE_API_BASE}/export/jobs/straordinari/${jobId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function deletePresenzeStraordinariExportJob(token: string, jobId: string): Promise<void> {
  await request<void>(`${PRESENZE_API_BASE}/export/jobs/straordinari/${jobId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function downloadPresenzeStraordinariExportArtifact(
  token: string,
  jobId: string,
  artifactName: "xlsx" | "log" | "summary" | "progress",
): Promise<Blob> {
  return requestBlob(`${PRESENZE_API_BASE}/export/jobs/straordinari/${jobId}/artifacts/${artifactName}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function deletePresenzeXlsmExportJob(token: string, jobId: string): Promise<void> {
  await request<void>(`${PRESENZE_API_BASE}/export/jobs/xlsm/${jobId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function downloadPresenzeXlsmExportArtifact(
  token: string,
  jobId: string,
  artifactName: "xlsm" | "log" | "summary" | "progress",
): Promise<Blob> {
  return requestBlob(`${PRESENZE_API_BASE}/export/jobs/xlsm/${jobId}/artifacts/${artifactName}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function retryPresenzeSyncJob(token: string, jobId: string): Promise<PresenzeSyncJob> {
  return request<PresenzeSyncJob>(`${PRESENZE_API_BASE}/sync/jobs/${jobId}/retry`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function retrySelectedPresenzeSyncJob(
  token: string,
  jobId: string,
  payload: PresenzeSyncJobRetrySelectedInput,
): Promise<PresenzeSyncJob> {
  return request<PresenzeSyncJob>(`${PRESENZE_API_BASE}/sync/jobs/${jobId}/retry-selected`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function cancelPresenzeSyncJob(token: string, jobId: string): Promise<PresenzeSyncJob> {
  return request<PresenzeSyncJob>(`${PRESENZE_API_BASE}/sync/jobs/${jobId}/cancel`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function deletePresenzeSyncJob(token: string, jobId: string): Promise<void> {
  await request<void>(`${PRESENZE_API_BASE}/sync/jobs/${jobId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function downloadPresenzeSyncArtifact(
  token: string,
  jobId: string,
  artifactName: "json" | "log" | "summary" | "progress" | "events",
): Promise<Blob> {
  return requestBlob(`${PRESENZE_API_BASE}/sync/jobs/${jobId}/artifacts/${artifactName}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function exportPresenzeXlsm(
  token: string,
  params: {
    periodStart: string;
    collaboratorIds?: string[];
    employeeKind?: string;
    templatePath?: string;
  },
): Promise<Blob> {
  const query = new URLSearchParams({ period_start: params.periodStart });
  if (params.employeeKind) {
    query.set("employee_kind", params.employeeKind);
  }
  if (params.templatePath) {
    query.set("template_path", params.templatePath);
  }
  for (const collaboratorId of params.collaboratorIds ?? []) {
    query.append("collaborator_id", collaboratorId);
  }
  return requestBlob(`${PRESENZE_API_BASE}/export/giornaliere.xlsm?${query.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}
