/** Operazioni API client. */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";
const OPERAZIONI_PREFIX = "/api/operazioni";

async function fetchOperazioni(path: string, options?: RequestInit) {
  const token = typeof window !== "undefined" ? localStorage.getItem("gaia_token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${BASE_URL}${OPERAZIONI_PREFIX}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: { message: response.statusText } }));
    throw new Error(error.error?.message || response.statusText);
  }

  return response.json();
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

// --- Cases ---

export async function getCases(params?: Record<string, string>) {
  const qs = params ? `?${new URLSearchParams(params).toString()}` : "";
  return fetchOperazioni(`/cases${qs}`);
}

export async function getCase(id: string) {
  return fetchOperazioni(`/cases/${id}`);
}

export async function assignCase(caseId: string, data: Record<string, unknown>) {
  return fetchOperazioni(`/cases/${caseId}/assign`, {
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

export async function getCaseEvents(caseId: string) {
  return fetchOperazioni(`/cases/${caseId}/events`);
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
