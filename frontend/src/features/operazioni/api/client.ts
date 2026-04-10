/** Operazioni API client — same base URL as @/lib/api (NEXT_PUBLIC_API_BASE_URL, default /api). */

import { getApiBaseUrl } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";

function operazioniErrorMessage(payload: unknown, fallback: string): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          item && typeof item === "object" && "msg" in item
            ? String((item as { msg: unknown }).msg)
            : JSON.stringify(item),
        )
        .join(", ");
    }
  }
  if (payload && typeof payload === "object" && "error" in payload) {
    const err = (payload as { error?: { message?: string } }).error;
    if (err?.message) {
      return err.message;
    }
  }
  return fallback;
}

async function fetchOperazioni(path: string, options?: RequestInit) {
  const token = getStoredAccessToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = `${getApiBaseUrl()}/operazioni${path}`;
  const response = await fetch(url, {
    ...options,
    headers,
    cache: "no-store",
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(operazioniErrorMessage(payload, response.statusText || "Request failed"));
  }

  return response.json();
}

async function fetchOperazioniBlob(path: string): Promise<{ blob: Blob; filename?: string }> {
  const token = getStoredAccessToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = `${getApiBaseUrl()}/operazioni${path}`;
  const response = await fetch(url, {
    method: "GET",
    headers,
    cache: "no-store",
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(operazioniErrorMessage(payload, response.statusText || "Request failed"));
  }

  const disposition = response.headers.get("content-disposition") ?? "";
  const filenameMatch = disposition.match(/filename="?([^"]+)"?/i);
  return {
    blob: await response.blob(),
    filename: filenameMatch?.[1],
  };
}

// --- Vehicles ---

export async function getVehicles(params?: Record<string, string>) {
  const qs = params ? `?${new URLSearchParams(params).toString()}` : "";
  return fetchOperazioni(`/vehicles${qs}`);
}

export async function getVehicle(id: string) {
  return fetchOperazioni(`/vehicles/${id}`);
}

export async function createVehicle(data: Record<string, unknown>) {
  return fetchOperazioni("/vehicles", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function startVehicleUsageSession(data: Record<string, unknown>) {
  return fetchOperazioni("/vehicles/usage-sessions/start", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function stopVehicleUsageSession(sessionId: string, data: Record<string, unknown>) {
  return fetchOperazioni(`/vehicles/usage-sessions/${sessionId}/stop`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// --- Activities ---

export async function getActivityCatalog() {
  return fetchOperazioni("/activities/catalog");
}

export async function getActivities(params?: Record<string, string>) {
  const qs = params ? `?${new URLSearchParams(params).toString()}` : "";
  return fetchOperazioni(`/activities${qs}`);
}

export async function getActivity(id: string) {
  return fetchOperazioni(`/activities/${id}`);
}

export async function getActivityAttachments(id: string) {
  return fetchOperazioni(`/activities/${id}/attachments`);
}

export async function getActivityGpsSummary(id: string) {
  return fetchOperazioni(`/activities/${id}/gps-summary`);
}

export async function getActivityGpsViewer(id: string) {
  return fetchOperazioni(`/activities/${id}/gps-viewer`);
}

export async function startActivity(data: Record<string, unknown>) {
  return fetchOperazioni("/activities/start", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function stopActivity(activityId: string, data: Record<string, unknown>) {
  return fetchOperazioni(`/activities/${activityId}/stop`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function approveActivity(activityId: string, data: Record<string, unknown>) {
  return fetchOperazioni(`/activities/${activityId}/approve`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// --- Reports ---

export async function getReports(params?: Record<string, string>) {
  const qs = params ? `?${new URLSearchParams(params).toString()}` : "";
  return fetchOperazioni(`/reports${qs}`);
}

export async function createReport(data: Record<string, unknown>) {
  return fetchOperazioni("/reports", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getReport(id: string) {
  return fetchOperazioni(`/reports/${id}`);
}

export async function getReportAttachments(id: string) {
  return fetchOperazioni(`/reports/${id}/attachments`);
}

// --- Cases ---

export async function getCases(params?: Record<string, string>) {
  const qs = params ? `?${new URLSearchParams(params).toString()}` : "";
  return fetchOperazioni(`/cases${qs}`);
}

export async function getCase(id: string) {
  return fetchOperazioni(`/cases/${id}`);
}

export async function getCaseAttachments(id: string) {
  return fetchOperazioni(`/cases/${id}/attachments`);
}

export async function getAttachmentPreviewData(
  attachmentId: string,
): Promise<{ blob: Blob; filename?: string; mimeType: string; textContent?: string | null }> {
  const { blob, filename } = await fetchOperazioniBlob(`/attachments/${attachmentId}/download`);
  const mimeType = blob.type || "application/octet-stream";
  const isTextLike =
    mimeType.startsWith("text/") ||
    mimeType === "application/json" ||
    mimeType === "application/ld+json" ||
    mimeType === "application/xml" ||
    mimeType === "text/csv";
  return {
    blob,
    filename,
    mimeType,
    textContent: isTextLike ? await blob.text().catch(() => null) : null,
  };
}

export async function downloadAttachment(attachmentId: string, preferredFilename?: string): Promise<void> {
  const { blob, filename } = await fetchOperazioniBlob(`/attachments/${attachmentId}/download`);
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = preferredFilename ?? filename ?? `attachment-${attachmentId}`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export async function assignCase(caseId: string, data: Record<string, unknown>) {
  return fetchOperazioni(`/cases/${caseId}/assign`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function acknowledgeCase(caseId: string, data: Record<string, unknown>) {
  return fetchOperazioni(`/cases/${caseId}/acknowledge`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function startCase(caseId: string, data: Record<string, unknown>) {
  return fetchOperazioni(`/cases/${caseId}/start`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function resolveCase(caseId: string, data: Record<string, unknown>) {
  return fetchOperazioni(`/cases/${caseId}/resolve`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function closeCase(caseId: string, data: Record<string, unknown>) {
  return fetchOperazioni(`/cases/${caseId}/close`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function reopenCase(caseId: string, data: Record<string, unknown>) {
  return fetchOperazioni(`/cases/${caseId}/reopen`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getCaseEvents(caseId: string) {
  return fetchOperazioni(`/cases/${caseId}/events`);
}

// --- Storage ---

export async function getStorageLatestMetric() {
  return fetchOperazioni("/storage/metrics/latest");
}

export async function getStorageAlerts() {
  return fetchOperazioni("/storage/alerts");
}

export async function recalculateStorage() {
  return fetchOperazioni("/storage/recalculate", {
    method: "POST",
  });
}

// --- Lookups ---

export async function getReportCategories() {
  return fetchOperazioni("/lookups/report-categories");
}

export async function getReportSeverities() {
  return fetchOperazioni("/lookups/report-severities");
}

export async function getTeams() {
  return fetchOperazioni("/lookups/teams");
}

export async function getMaintenanceTypes() {
  return fetchOperazioni("/lookups/maintenance-types");
}
