import { ApiError, getApiBaseUrl } from "@/lib/api";
import type {
  RiordinoAppeal,
  RiordinoAppealCreateInput,
  RiordinoAppealResolveInput,
  RiordinoDashboardResponse,
  RiordinoDocument,
  RiordinoDocumentTypeConfig,
  RiordinoDocumentTypeConfigInput,
  RiordinoDocumentListResponse,
  RiordinoDocumentUploadInput,
  RiordinoEvent,
  RiordinoGisCreateInput,
  RiordinoGisLink,
  RiordinoGisUpdateInput,
  RiordinoIssue,
  RiordinoIssueTypeConfig,
  RiordinoIssueTypeConfigInput,
  RiordinoIssueCloseInput,
  RiordinoIssueCreateInput,
  RiordinoNotification,
  RiordinoPhase,
  RiordinoPhaseCompleteInput,
  RiordinoPracticeDetail,
  RiordinoPracticeListResponse,
  RiordinoStep,
  RiordinoStepAdvanceInput,
  RiordinoStepSkipInput,
} from "@/types/riordino";

async function extractError(response: Response): Promise<never> {
  let detail = "Request failed";
  let detailData: unknown;

  try {
    const payload = (await response.json()) as { detail?: unknown };
    detailData = payload.detail;

    if (typeof payload.detail === "string") {
      detail = payload.detail;
    } else if (
      payload.detail &&
      typeof payload.detail === "object" &&
      "message" in payload.detail &&
      typeof payload.detail.message === "string"
    ) {
      detail = payload.detail.message;
    } else if (payload.detail != null) {
      detail = JSON.stringify(payload.detail);
    }
  } catch {
    detail = response.statusText || detail;
  }

  throw new ApiError(detail, detailData, response.status);
}

async function riordinoRequest<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const isFormData = typeof FormData !== "undefined" && init?.body instanceof FormData;
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      Authorization: `Bearer ${token}`,
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    return extractError(response);
  }

  return (await response.json()) as T;
}

async function riordinoBlobRequest(path: string, token: string, init?: RequestInit): Promise<Blob> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    return extractError(response);
  }

  return response.blob();
}

function createQueryString(params: Record<string, string | undefined>): string {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value && value.trim()) {
      searchParams.set(key, value.trim());
    }
  });
  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

export async function getRiordinoDashboard(token: string): Promise<RiordinoDashboardResponse> {
  return riordinoRequest<RiordinoDashboardResponse>("/api/riordino/dashboard", token);
}

export async function listRiordinoPractices(
  token: string,
  params: {
    status?: string;
    municipality?: string;
    phase?: string;
    owner?: string;
    page?: string;
    per_page?: string;
  } = {},
): Promise<RiordinoPracticeListResponse> {
  const query = createQueryString(params);
  return riordinoRequest<RiordinoPracticeListResponse>(`/api/riordino/practices${query}`, token);
}

export async function getRiordinoPractice(token: string, practiceId: string): Promise<RiordinoPracticeDetail> {
  return riordinoRequest<RiordinoPracticeDetail>(`/api/riordino/practices/${practiceId}`, token);
}

export async function listRiordinoEvents(token: string, practiceId: string): Promise<RiordinoEvent[]> {
  return riordinoRequest<RiordinoEvent[]>(`/api/riordino/practices/${practiceId}/events`, token);
}

export async function listRiordinoAppeals(token: string, practiceId: string, status?: string): Promise<RiordinoAppeal[]> {
  const query = createQueryString({ status });
  return riordinoRequest<RiordinoAppeal[]>(`/api/riordino/practices/${practiceId}/appeals${query}`, token);
}

export async function createRiordinoAppeal(token: string, practiceId: string, payload: RiordinoAppealCreateInput): Promise<RiordinoAppeal> {
  return riordinoRequest<RiordinoAppeal>(`/api/riordino/practices/${practiceId}/appeals`, token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function resolveRiordinoAppeal(
  token: string,
  practiceId: string,
  appealId: string,
  payload: RiordinoAppealResolveInput,
): Promise<RiordinoAppeal> {
  return riordinoRequest<RiordinoAppeal>(`/api/riordino/practices/${practiceId}/appeals/${appealId}/resolve`, token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listRiordinoIssues(
  token: string,
  practiceId: string,
  params: { severity?: string; status_filter?: string; category?: string } = {},
): Promise<RiordinoIssue[]> {
  const query = createQueryString(params);
  return riordinoRequest<RiordinoIssue[]>(`/api/riordino/practices/${practiceId}/issues${query}`, token);
}

export async function createRiordinoIssue(token: string, practiceId: string, payload: RiordinoIssueCreateInput): Promise<RiordinoIssue> {
  return riordinoRequest<RiordinoIssue>(`/api/riordino/practices/${practiceId}/issues`, token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function closeRiordinoIssue(
  token: string,
  practiceId: string,
  issueId: string,
  payload: RiordinoIssueCloseInput,
): Promise<RiordinoIssue> {
  return riordinoRequest<RiordinoIssue>(`/api/riordino/practices/${practiceId}/issues/${issueId}/close`, token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listRiordinoDocuments(
  token: string,
  practiceId: string,
  params: { phase_id?: string; step_id?: string; document_type?: string; appeal_id?: string } = {},
): Promise<RiordinoDocumentListResponse> {
  const query = createQueryString(params);
  return riordinoRequest<RiordinoDocumentListResponse>(`/api/riordino/practices/${practiceId}/documents${query}`, token);
}

export async function uploadRiordinoDocument(
  token: string,
  practiceId: string,
  payload: RiordinoDocumentUploadInput,
): Promise<RiordinoDocument> {
  const formData = new FormData();
  formData.append("file", payload.file);
  formData.append("document_type", payload.document_type);

  if (payload.phase_id) formData.append("phase_id", payload.phase_id);
  if (payload.step_id) formData.append("step_id", payload.step_id);
  if (payload.appeal_id) formData.append("appeal_id", payload.appeal_id);
  if (payload.issue_id) formData.append("issue_id", payload.issue_id);
  if (payload.notes) formData.append("notes", payload.notes);

  return riordinoRequest<RiordinoDocument>(`/api/riordino/practices/${practiceId}/documents`, token, {
    method: "POST",
    body: formData,
  });
}

export async function deleteRiordinoDocument(token: string, documentId: string): Promise<RiordinoDocument> {
  return riordinoRequest<RiordinoDocument>(`/api/riordino/practices/documents/${documentId}`, token, {
    method: "DELETE",
  });
}

export async function downloadRiordinoDocument(token: string, documentId: string): Promise<Blob> {
  return riordinoBlobRequest(`/api/riordino/practices/documents/${documentId}/download`, token);
}

export async function downloadRiordinoPracticeSummary(token: string, practiceId: string): Promise<Blob> {
  return riordinoBlobRequest(`/api/riordino/practices/${practiceId}/export/summary`, token);
}

export async function downloadRiordinoPracticeDossier(token: string, practiceId: string): Promise<Blob> {
  return riordinoBlobRequest(`/api/riordino/practices/${practiceId}/export/dossier`, token);
}

export async function listRiordinoGisLinks(token: string, practiceId: string): Promise<RiordinoGisLink[]> {
  return riordinoRequest<RiordinoGisLink[]>(`/api/riordino/practices/${practiceId}/gis-links`, token);
}

export async function createRiordinoGisLink(token: string, practiceId: string, payload: RiordinoGisCreateInput): Promise<RiordinoGisLink> {
  return riordinoRequest<RiordinoGisLink>(`/api/riordino/practices/${practiceId}/gis-links`, token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateRiordinoGisLink(
  token: string,
  practiceId: string,
  linkId: string,
  payload: RiordinoGisUpdateInput,
): Promise<RiordinoGisLink> {
  return riordinoRequest<RiordinoGisLink>(`/api/riordino/practices/${practiceId}/gis-links/${linkId}`, token, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function advanceRiordinoStep(
  token: string,
  practiceId: string,
  stepId: string,
  payload: RiordinoStepAdvanceInput = {},
): Promise<RiordinoStep> {
  return riordinoRequest<RiordinoStep>(`/api/riordino/practices/${practiceId}/steps/${stepId}/advance`, token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function skipRiordinoStep(
  token: string,
  practiceId: string,
  stepId: string,
  payload: RiordinoStepSkipInput,
): Promise<RiordinoStep> {
  return riordinoRequest<RiordinoStep>(`/api/riordino/practices/${practiceId}/steps/${stepId}/skip`, token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function reopenRiordinoStep(token: string, practiceId: string, stepId: string): Promise<RiordinoStep> {
  return riordinoRequest<RiordinoStep>(`/api/riordino/practices/${practiceId}/steps/${stepId}/reopen`, token, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function startRiordinoPhase(token: string, practiceId: string, phaseId: string): Promise<RiordinoPhase> {
  return riordinoRequest<RiordinoPhase>(`/api/riordino/practices/${practiceId}/phases/${phaseId}/start`, token, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function completeRiordinoPhase(
  token: string,
  practiceId: string,
  phaseId: string,
  payload: RiordinoPhaseCompleteInput = {},
): Promise<RiordinoPhase> {
  return riordinoRequest<RiordinoPhase>(`/api/riordino/practices/${practiceId}/phases/${phaseId}/complete`, token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listRiordinoNotifications(token: string): Promise<RiordinoNotification[]> {
  return riordinoRequest<RiordinoNotification[]>("/api/riordino/notifications", token);
}

export async function markRiordinoNotificationRead(token: string, notificationId: string): Promise<RiordinoNotification> {
  return riordinoRequest<RiordinoNotification>(`/api/riordino/notifications/${notificationId}/read`, token, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function checkRiordinoDeadlines(token: string): Promise<RiordinoNotification[]> {
  return riordinoRequest<RiordinoNotification[]>("/api/riordino/notifications/check-deadlines", token, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function listRiordinoDocumentTypes(token: string): Promise<RiordinoDocumentTypeConfig[]> {
  return riordinoRequest<RiordinoDocumentTypeConfig[]>("/api/riordino/config/document-types", token);
}

export async function createRiordinoDocumentType(token: string, payload: RiordinoDocumentTypeConfigInput): Promise<RiordinoDocumentTypeConfig> {
  return riordinoRequest<RiordinoDocumentTypeConfig>("/api/riordino/config/document-types", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateRiordinoDocumentType(
  token: string,
  configId: string,
  payload: Partial<RiordinoDocumentTypeConfigInput>,
): Promise<RiordinoDocumentTypeConfig> {
  return riordinoRequest<RiordinoDocumentTypeConfig>(`/api/riordino/config/document-types/${configId}`, token, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteRiordinoDocumentType(token: string, configId: string): Promise<RiordinoDocumentTypeConfig> {
  return riordinoRequest<RiordinoDocumentTypeConfig>(`/api/riordino/config/document-types/${configId}`, token, {
    method: "DELETE",
  });
}

export async function listRiordinoIssueTypes(token: string): Promise<RiordinoIssueTypeConfig[]> {
  return riordinoRequest<RiordinoIssueTypeConfig[]>("/api/riordino/config/issue-types", token);
}

export async function createRiordinoIssueType(token: string, payload: RiordinoIssueTypeConfigInput): Promise<RiordinoIssueTypeConfig> {
  return riordinoRequest<RiordinoIssueTypeConfig>("/api/riordino/config/issue-types", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateRiordinoIssueType(
  token: string,
  configId: string,
  payload: Partial<RiordinoIssueTypeConfigInput>,
): Promise<RiordinoIssueTypeConfig> {
  return riordinoRequest<RiordinoIssueTypeConfig>(`/api/riordino/config/issue-types/${configId}`, token, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteRiordinoIssueType(token: string, configId: string): Promise<RiordinoIssueTypeConfig> {
  return riordinoRequest<RiordinoIssueTypeConfig>(`/api/riordino/config/issue-types/${configId}`, token, {
    method: "DELETE",
  });
}

export async function listRiordinoMunicipalities(token: string): Promise<string[]> {
  return riordinoRequest<string[]>("/api/riordino/config/municipalities", token);
}
