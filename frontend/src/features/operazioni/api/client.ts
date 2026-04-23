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
    ...(options?.headers as Record<string, string>),
  };
  if (!(options?.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
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

export interface VehicleFuelLogItem {
  id: string;
  vehicle_id: string;
  usage_session_id: string | null;
  recorded_by_user_id: number;
  fueled_at: string;
  liters: string;
  total_cost: string | null;
  odometer_km: string | null;
  station_name: string | null;
  notes: string | null;
  created_at: string;
}

export async function getVehicleFuelLogs(
  vehicleId: string,
  params?: Record<string, string>,
): Promise<{ items: VehicleFuelLogItem[]; total: number; page: number; page_size: number; total_pages: number }> {
  const qs = params ? `?${new URLSearchParams(params).toString()}` : "";
  return fetchOperazioni(`/vehicles/${vehicleId}/fuel-logs${qs}`);
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

export async function getReportsDashboard(params?: Record<string, string>) {
  const qs = params ? `?${new URLSearchParams(params).toString()}` : "";
  return fetchOperazioni(`/reports/dashboard${qs}`);
}

export async function importWhiteReports(file: File): Promise<{
  imported: number;
  skipped: number;
  errors: string[];
  categories_created: string[];
  total_events_created: number;
}> {
  const formData = new FormData();
  formData.append("file", file);
  return fetchOperazioni("/reports/import-white", {
    method: "POST",
    body: formData,
  });
}

export interface UnresolvedRow {
  db_id: string | null;
  row_index: number;
  reason_type: "no_card_operator" | "no_vehicle";
  reason_detail: string;
  targa: string | null;
  identificativo: string | null;
  fueled_at_iso: string | null;
  liters: string | null;
  total_cost: string | null;
  odometer_km: string | null;
  operator_name: string | null;
  wc_operator_id: string | null;
  card_code: string | null;
  station_name: string | null;
  notes_extra: string | null;
}

export interface PersistedUnresolvedRow extends UnresolvedRow {
  id: string;
  import_ref: string;
  status: "pending" | "resolved" | "skipped";
  resolved_vehicle_id: string | null;
  resolved_at: string | null;
  created_at: string;
}

export async function importFleetTransactions(file: File): Promise<{
  imported: number;
  skipped: number;
  errors: string[];
  rows_read: number;
  import_ref: string;
  matched_white_refuels: number;
  unresolved: UnresolvedRow[];
}> {
  const formData = new FormData();
  formData.append("file", file);
  return fetchOperazioni("/vehicles/fuel-logs/import-fleet-transactions", {
    method: "POST",
    body: formData,
  });
}

export interface ResolvedTransactionPayload {
  vehicle_id: string;
  fueled_at_iso: string;
  liters: string;
  total_cost: string | null;
  odometer_km: string | null;
  card_code: string | null;
  station_name: string | null;
  notes_extra: string | null;
  unresolved_id: string | null;
}

export async function resolveFleetTransactions(
  resolutions: ResolvedTransactionPayload[],
): Promise<{ imported: number; skipped: number; errors: string[] }> {
  return fetchOperazioni("/vehicles/fuel-logs/resolve-fleet-transactions", {
    method: "POST",
    body: JSON.stringify(resolutions),
  });
}

export async function skipUnresolvedTransaction(id: string): Promise<void> {
  await fetchOperazioni(`/vehicles/fuel-logs/unresolved-transactions/${id}/skip`, {
    method: "POST",
  });
}

export async function getUnresolvedTransactions(params?: {
  status_filter?: string;
  page?: number;
  page_size?: number;
}): Promise<{
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: PersistedUnresolvedRow[];
}> {
  const p = new URLSearchParams();
  if (params?.status_filter) p.set("status_filter", params.status_filter);
  if (params?.page) p.set("page", String(params.page));
  if (params?.page_size) p.set("page_size", String(params.page_size));
  const qs = p.toString() ? `?${p.toString()}` : "";
  return fetchOperazioni(`/vehicles/fuel-logs/unresolved-transactions${qs}`);
}

export interface UnresolvedAnomalies {
  high_volume: { id: string; card_code: string | null; targa: string | null; operator_name: string | null; fueled_at_iso: string | null; liters: number; total_cost: number; station_name: string | null }[];
  same_day_multiple: { card_code: string | null; day: string; count: number; tot_liters: number; operator_name: string | null }[];
  top_operators: { operator_name: string; count: number; tot_liters: number; tot_cost: number }[];
  no_operator_cards: { card_code: string | null; count: number; tot_liters: number }[];
  thresholds: { liters_threshold: number; same_day_min: number };
}

export async function getUnresolvedAnomalies(params?: { liters_threshold?: number; same_day_min?: number }): Promise<UnresolvedAnomalies> {
  const p = new URLSearchParams();
  if (params?.liters_threshold) p.set("liters_threshold", String(params.liters_threshold));
  if (params?.same_day_min) p.set("same_day_min", String(params.same_day_min));
  const qs = p.toString() ? `?${p.toString()}` : "";
  return fetchOperazioni(`/vehicles/fuel-logs/unresolved-transactions/anomalies${qs}`);
}

export async function getWhiteRefuelEvents(params?: Record<string, string>) {
  const qs = params ? `?${new URLSearchParams(params).toString()}` : "";
  return fetchOperazioni(`/vehicles/refuel-events${qs}`);
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

// --- Operators ---

export async function getOperators(params?: Record<string, string>) {
  const qs = params ? `?${new URLSearchParams(params).toString()}` : "";
  return fetchOperazioni(`/operators${qs}`);
}

export async function getOperator(id: string) {
  return fetchOperazioni(`/operators/${id}`);
}

export interface OperatorFuelCardSummary {
  id: string;
  codice: string | null;
  pan: string;
  is_blocked: boolean;
  expires_at: string | null;
}

export interface OperatorVehicleUsageSummary {
  vehicle_id: string;
  vehicle_label: string;
  usage_count: number;
  km_travelled: string | null;
}

export interface OperatorFuelLogSummary {
  id: string;
  vehicle_id: string;
  vehicle_label: string;
  fueled_at: string;
  liters: string;
  total_cost: string | null;
  odometer_km: string | null;
  station_name: string | null;
}

export interface OperatorUsageSessionSummary {
  id: string;
  vehicle_id: string;
  vehicle_label: string;
  started_at: string;
  ended_at: string | null;
  status: string;
  km_travelled: string | null;
}

export interface OperatorDetailStats {
  fuel_cards_count: number;
  fuel_logs_count: number;
  usage_sessions_count: number;
  total_liters: string;
  total_fuel_cost: string | null;
  total_km_travelled: string;
  most_used_vehicle: OperatorVehicleUsageSummary | null;
  last_used_vehicle_label: string | null;
}

export interface OperatorDetailResponse {
  operator: {
    id: string;
    wc_id: number;
    username: string | null;
    email: string | null;
    first_name: string | null;
    last_name: string | null;
    tax: string | null;
    role: string | null;
    enabled: boolean;
    gaia_user_id: number | null;
    wc_synced_at: string | null;
    created_at: string;
    updated_at: string;
    current_fuel_cards: OperatorFuelCardSummary[];
  };
  stats: OperatorDetailStats;
  current_fuel_cards: OperatorFuelCardSummary[];
  recent_fuel_logs: OperatorFuelLogSummary[];
  recent_usage_sessions: OperatorUsageSessionSummary[];
}

export async function getOperatorDetail(id: string): Promise<OperatorDetailResponse> {
  return fetchOperazioni(`/operators/${id}/detail`);
}

export async function getUnlinkedOperators() {
  return fetchOperazioni("/operators/unlinked");
}

export async function getGaiaUsersForLinking(search?: string) {
  const qs = search ? `?${new URLSearchParams({ search }).toString()}` : "";
  return fetchOperazioni(`/operators/gaia-users${qs}`);
}

export async function autoLinkGaiaOperators(): Promise<{ linked: number; already_linked: number; skipped: number }> {
  return fetchOperazioni("/operators/auto-link-gaia", { method: "POST" });
}

export async function linkGaiaUser(operatorId: string, gaiaUserId: number): Promise<unknown> {
  return fetchOperazioni(`/operators/${operatorId}/link-gaia`, {
    method: "POST",
    body: JSON.stringify({ gaia_user_id: gaiaUserId }),
  });
}

export async function unlinkGaiaUser(operatorId: string): Promise<unknown> {
  return fetchOperazioni(`/operators/${operatorId}/unlink-gaia`, { method: "POST" });
}

export async function inviteOperator(wcOperatorId: string): Promise<{
  token: string;
  expires_at: string;
  activation_url_path: string;
  already_activated: boolean;
}> {
  return fetchOperazioni(`/operators/${wcOperatorId}/invite`, { method: "POST" });
}

export async function getInvitationStatus(wcOperatorId: string): Promise<{
  has_pending: boolean;
  has_activated: boolean;
  token: string | null;
  expires_at: string | null;
  activated_at: string | null;
  gaia_user_id: number | null;
}> {
  return fetchOperazioni(`/operators/${wcOperatorId}/invitation-status`);
}

export interface BulkImportedOperator {
  wc_operator_id: string;
  full_name: string;
  username: string;
  temp_password: string;
  skipped: boolean;
  skip_reason: string | null;
}

export interface BulkImportResult {
  created: number;
  skipped: number;
  operators: BulkImportedOperator[];
}

export async function bulkImportOperatorsAsGaiaUsers(): Promise<BulkImportResult> {
  return fetchOperazioni("/operators/bulk-import-gaia", { method: "POST" });
}

// --- Areas ---

export async function getAreas(params?: Record<string, string>) {
  const qs = params ? `?${new URLSearchParams(params).toString()}` : "";
  return fetchOperazioni(`/areas${qs}`);
}

export async function getArea(id: string) {
  return fetchOperazioni(`/areas/${id}`);
}

// --- Fuel cards ---

export async function getFuelCards(params?: Record<string, string>) {
  const qs = params ? `?${new URLSearchParams(params).toString()}` : "";
  return fetchOperazioni(`/fuel-cards${qs}`);
}

export async function getFuelCardAssignments(cardId: string) {
  return fetchOperazioni(`/fuel-cards/${cardId}/assignments`);
}

export async function importFuelCards(file: File): Promise<{
  imported: number;
  updated: number;
  skipped: number;
  assignments_created: number;
  assignments_closed: number;
  rows_read: number;
  unmatched_drivers: number;
  errors: string[];
}> {
  const formData = new FormData();
  formData.append("file", file);
  return fetchOperazioni("/fuel-cards/import-excel", {
    method: "POST",
    body: formData,
  });
}

export async function getUnmatchedFuelCards(params?: Record<string, string>) {
  const qs = params ? `?${new URLSearchParams(params).toString()}` : "";
  return fetchOperazioni(`/fuel-cards/unmatched${qs}`);
}

export async function assignFuelCard(
  cardId: string,
  data: { wc_operator_id: string; driver_raw?: string | null; note?: string | null },
) {
  return fetchOperazioni(`/fuel-cards/${cardId}/assign`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function ignoreFuelCardDriver(cardId: string, note?: string | null) {
  const qs = note ? `?${new URLSearchParams({ note }).toString()}` : "";
  return fetchOperazioni(`/fuel-cards/${cardId}/ignore${qs}`, {
    method: "POST",
  });
}

// ─── Analytics ───────────────────────────────────────────────────────────────

export interface AnalyticsParams {
  from_date?: string;
  to_date?: string;
  granularity?: "day" | "week" | "month";
}

export async function getAnalyticsAvailablePeriods() {
  return fetchOperazioni(`/analytics/available-periods`);
}

export async function getAnalyticsSummary(params?: Omit<AnalyticsParams, "granularity">) {
  const qs = params ? `?${new URLSearchParams(params as Record<string, string>).toString()}` : "";
  return fetchOperazioni(`/analytics/summary${qs}`);
}

export async function getAnalyticsFuel(params?: AnalyticsParams) {
  const qs = params ? `?${new URLSearchParams(params as Record<string, string>).toString()}` : "";
  return fetchOperazioni(`/analytics/fuel${qs}`);
}

export async function getAnalyticsKm(params?: AnalyticsParams) {
  const qs = params ? `?${new URLSearchParams(params as Record<string, string>).toString()}` : "";
  return fetchOperazioni(`/analytics/km${qs}`);
}

export async function getAnalyticsWorkHours(params?: AnalyticsParams) {
  const qs = params ? `?${new URLSearchParams(params as Record<string, string>).toString()}` : "";
  return fetchOperazioni(`/analytics/work-hours${qs}`);
}

export async function getAnalyticsAnomalies(params?: AnalyticsParams & { type?: string }) {
  const qs = params ? `?${new URLSearchParams(params as Record<string, string>).toString()}` : "";
  return fetchOperazioni(`/analytics/anomalies${qs}`);
}
