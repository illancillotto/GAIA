import type { ApplicationUser, PresenzeCredential, PresenzeCredentialCreateInput, PresenzeCredentialTestResult, PresenzeCredentialUpdateInput, PresenzeSupervisorAssignment, PresenzeSyncJob, PresenzeAccessContext, PresenzeAnomalyListResponse, PresenzeAnomalyMonthSummaryResponse, PresenzeCollaborator, PresenzeCollaboratorContractProfileUpdateInput, PresenzeCollaboratorCalendarResponse, PresenzeCollaboratorListResponse, PresenzeCollaboratorSummaryResponse, PresenzeDailyRecord, PresenzeDailyRecordListResponse } from "@/types/api";
import { ApiError, getApiBaseUrl, request } from "./core";

const PRESENZE_API_BASE = "/presenze";
export async function listPresenzeCollaborators(
  token: string,
  params: {
    q?: string;
    mappedOnly?: boolean | null;
    page?: number;
    pageSize?: number;
  } = {},
): Promise<PresenzeCollaboratorListResponse> {
  const query = new URLSearchParams();
  if (params.q) {
    query.set("q", params.q);
  }
  if (params.mappedOnly != null) {
    query.set("mapped_only", String(params.mappedOnly));
  }
  if (params.page) {
    query.set("page", String(params.page));
  }
  if (params.pageSize) {
    query.set("page_size", String(params.pageSize));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<PresenzeCollaboratorListResponse>(`${PRESENZE_API_BASE}/collaborators${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listAllPresenzeCollaborators(token: string): Promise<PresenzeCollaborator[]> {
  const pageSize = 200;
  let page = 1;
  const items: PresenzeCollaborator[] = [];

  while (true) {
    const response = await listPresenzeCollaborators(token, { page, pageSize });
    items.push(...response.items);
    if (items.length >= response.total || response.items.length === 0) {
      return items;
    }
    page += 1;
  }
}

export async function listPresenzeApplicationUsers(token: string): Promise<ApplicationUser[]> {
  return request<ApplicationUser[]>(`${PRESENZE_API_BASE}/application-users`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listPresenzeCredentials(token: string): Promise<PresenzeCredential[]> {
  return request<PresenzeCredential[]>(`${PRESENZE_API_BASE}/credentials`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getPresenzeAccessContext(token: string): Promise<PresenzeAccessContext> {
  return request<PresenzeAccessContext>(`${PRESENZE_API_BASE}/access-context`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listPresenzeSupervisorAssignments(
  token: string,
  supervisorUserId?: number,
): Promise<PresenzeSupervisorAssignment[]> {
  const suffix = supervisorUserId != null ? `?supervisor_user_id=${supervisorUserId}` : "";
  return request<PresenzeSupervisorAssignment[]>(`${PRESENZE_API_BASE}/supervisor-assignments${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updatePresenzeSupervisorAssignment(
  token: string,
  collaboratorId: string,
  supervisorUserId: number | null,
): Promise<PresenzeSupervisorAssignment | null> {
  return request<PresenzeSupervisorAssignment | null>(`${PRESENZE_API_BASE}/supervisor-assignments/${collaboratorId}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ supervisor_user_id: supervisorUserId }),
  });
}

export async function createPresenzeCredential(token: string, payload: PresenzeCredentialCreateInput): Promise<PresenzeCredential> {
  return request<PresenzeCredential>(`${PRESENZE_API_BASE}/credentials`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function updatePresenzeCredential(
  token: string,
  credentialId: number,
  payload: PresenzeCredentialUpdateInput,
): Promise<PresenzeCredential> {
  return request<PresenzeCredential>(`${PRESENZE_API_BASE}/credentials/${credentialId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function deletePresenzeCredential(token: string, credentialId: number): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}${PRESENZE_API_BASE}/credentials/${credentialId}`, {
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

export async function testPresenzeCredential(token: string, credentialId: number): Promise<PresenzeCredentialTestResult> {
  return request<PresenzeCredentialTestResult>(`${PRESENZE_API_BASE}/credentials/${credentialId}/test`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function mapPresenzeCollaboratorApplicationUser(
  token: string,
  collaboratorId: string,
  applicationUserId: number | null,
): Promise<PresenzeCollaborator> {
  return request<PresenzeCollaborator>(`${PRESENZE_API_BASE}/collaborators/${collaboratorId}/application-user`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ application_user_id: applicationUserId }),
  });
}

export async function updatePresenzeCollaboratorContractProfile(
  token: string,
  collaboratorId: string,
  payload: PresenzeCollaboratorContractProfileUpdateInput,
): Promise<PresenzeCollaborator> {
  return request<PresenzeCollaborator>(`${PRESENZE_API_BASE}/collaborators/${collaboratorId}/contract-profile`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getPresenzeCollaboratorCalendar(
  token: string,
  collaboratorId: string,
  dateFrom: string,
  dateTo: string,
): Promise<PresenzeCollaboratorCalendarResponse> {
  const query = new URLSearchParams({ date_from: dateFrom, date_to: dateTo });
  return request<PresenzeCollaboratorCalendarResponse>(`${PRESENZE_API_BASE}/collaborators/${collaboratorId}/calendar?${query.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getPresenzeCollaboratorSummary(
  token: string,
  collaboratorId: string,
  periodStart: string,
  periodEnd: string,
): Promise<PresenzeCollaboratorSummaryResponse> {
  const query = new URLSearchParams({ period_start: periodStart, period_end: periodEnd });
  return request<PresenzeCollaboratorSummaryResponse>(`${PRESENZE_API_BASE}/collaborators/${collaboratorId}/summary?${query.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listPresenzeDailyRecords(
  token: string,
  params: {
    collaboratorId?: string;
    applicationUserId?: number;
    dateFrom?: string;
    dateTo?: string;
    q?: string;
    includePunches?: boolean;
    includeRawPayload?: boolean;
    page?: number;
    pageSize?: number;
  } = {},
): Promise<PresenzeDailyRecordListResponse> {
  const query = new URLSearchParams();
  if (params.collaboratorId) {
    query.set("collaborator_id", params.collaboratorId);
  }
  if (params.applicationUserId != null) {
    query.set("application_user_id", String(params.applicationUserId));
  }
  if (params.dateFrom) {
    query.set("date_from", params.dateFrom);
  }
  if (params.dateTo) {
    query.set("date_to", params.dateTo);
  }
  if (params.q) {
    query.set("q", params.q);
  }
  if (params.includePunches != null) {
    query.set("include_punches", String(params.includePunches));
  }
  if (params.includeRawPayload != null) {
    query.set("include_raw_payload", String(params.includeRawPayload));
  }
  if (params.page) {
    query.set("page", String(params.page));
  }
  if (params.pageSize) {
    query.set("page_size", String(params.pageSize));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<PresenzeDailyRecordListResponse>(`${PRESENZE_API_BASE}/giornaliere${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listPresenzeAnomalyRecords(
  token: string,
  params: {
    collaboratorId?: string;
    applicationUserId?: number;
    dateFrom?: string;
    dateTo?: string;
    q?: string;
    onlyAnomalies?: boolean;
    onlyRequests?: boolean;
    page?: number;
    pageSize?: number;
  } = {},
): Promise<PresenzeAnomalyListResponse> {
  const query = new URLSearchParams();
  if (params.collaboratorId) {
    query.set("collaborator_id", params.collaboratorId);
  }
  if (params.applicationUserId != null) {
    query.set("application_user_id", String(params.applicationUserId));
  }
  if (params.dateFrom) {
    query.set("date_from", params.dateFrom);
  }
  if (params.dateTo) {
    query.set("date_to", params.dateTo);
  }
  if (params.q) {
    query.set("q", params.q);
  }
  if (params.onlyAnomalies != null) {
    query.set("only_anomalies", String(params.onlyAnomalies));
  }
  if (params.onlyRequests != null) {
    query.set("only_requests", String(params.onlyRequests));
  }
  if (params.page) {
    query.set("page", String(params.page));
  }
  if (params.pageSize) {
    query.set("page_size", String(params.pageSize));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<PresenzeAnomalyListResponse>(`${PRESENZE_API_BASE}/anomalie${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getPresenzeAnomalyMonthSummary(
  token: string,
  params: {
    collaboratorId?: string;
    applicationUserId?: number;
    months?: number;
    anchorMonth?: string;
  } = {},
): Promise<PresenzeAnomalyMonthSummaryResponse> {
  const query = new URLSearchParams();
  if (params.collaboratorId) {
    query.set("collaborator_id", params.collaboratorId);
  }
  if (params.applicationUserId != null) {
    query.set("application_user_id", String(params.applicationUserId));
  }
  if (params.months != null) {
    query.set("months", String(params.months));
  }
  if (params.anchorMonth) {
    query.set("anchor_month", params.anchorMonth);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<PresenzeAnomalyMonthSummaryResponse>(`${PRESENZE_API_BASE}/anomalie/month-summary${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listPresenzeDailyMatrixRecords(
  token: string,
  params: {
    collaboratorId?: string;
    applicationUserId?: number;
    dateFrom?: string;
    dateTo?: string;
    q?: string;
    page?: number;
    pageSize?: number;
  } = {},
): Promise<PresenzeDailyRecordListResponse> {
  const query = new URLSearchParams();
  if (params.collaboratorId) {
    query.set("collaborator_id", params.collaboratorId);
  }
  if (params.applicationUserId != null) {
    query.set("application_user_id", String(params.applicationUserId));
  }
  if (params.dateFrom) {
    query.set("date_from", params.dateFrom);
  }
  if (params.dateTo) {
    query.set("date_to", params.dateTo);
  }
  if (params.q) {
    query.set("q", params.q);
  }
  if (params.page) {
    query.set("page", String(params.page));
  }
  if (params.pageSize) {
    query.set("page_size", String(params.pageSize));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<PresenzeDailyRecordListResponse>(`${PRESENZE_API_BASE}/giornaliere/matrix${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getPresenzeDailyRecord(token: string, recordId: string): Promise<PresenzeDailyRecord> {
  return request<PresenzeDailyRecord>(`${PRESENZE_API_BASE}/giornaliere/${recordId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function refreshPresenzeDailyRecordFromInaz(token: string, recordId: string): Promise<PresenzeSyncJob> {
  return request<PresenzeSyncJob>(`${PRESENZE_API_BASE}/giornaliere/${recordId}/refresh-from-inaz`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}
