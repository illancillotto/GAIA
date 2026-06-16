import type {
  AnagraficaCsvImportResult,
  AnagraficaDocument,
  UtenzeAuditLog,
  XlsxImportBatch,
  XlsxImportStartResult,
  AnagraficaDocumentSummary,
  AnagraficaImportJob,
  AnagraficaImportPreview,
  AnagraficaImportRunResult,
  AnagraficaNasFolderCandidate,
  AnagraficaPaymentNotice,
  AnagraficaResetResult,
  AnagraficaSearchResult,
  AnagraficaStats,
  AnagraficaSubjectCreateInput,
  AnagraficaSubjectDetail,
  AnagraficaSubjectNasImportStatus,
  AnagraficaSubjectImportResult,
  AnagraficaSubjectListResponse,
  AnagraficaSubjectUpdateInput,
  AnagraficaVisuraRoutingAnomaly,
  AnagraficaVisuraRoutingAnomalyListResponse,
  AnprJobTriggerResult,
  AnprPreviewLookupResponse,
  AnprSubjectStatus,
  AnprSyncConfig,
  AnprSyncConfigUpdateInput,
  AnprSyncResult,
  ApplicationUser,
  ApplicationUserCreateInput,
  ApplicationUserListResponse,
  ApplicationUserUpdateInput,
  CatastoDocument,
  CatastoComune,
  ElaborazioneBatch,
  ElaborazioneAnprSummary,
  ElaborazioneBatchDetail,
  ElaborazioneCaptchaSummary,
  ElaborazioneCredential,
  ElaborazioneCredentialStatus,
  ElaborazioneCredentialTestResult,
  ElaborazioneOperationResponse,
  ElaborazioneRuoloAutoSyncConfig,
  ElaborazioneRuoloAutoSyncConfigUpdateInput,
  ElaborazioneRuoloAutoSyncStatus,
  ElaborazioneRuntimeMetrics,
  GateMobileSyncRunTriggerResponse,
  GateMobileSyncStatusResponse,
  ElaborazioneRichiesta,
  ElaborazioneRichiestaCreateInput,
  CapacitasCredential,
  CapacitasCredentialCreateInput,
  CapacitasCredentialTestResult as CapacitasCredentialProbeResult,
  CapacitasCredentialUpdateInput,
  CapacitasAnagraficaHistoryImportInput,
  CapacitasAnagraficaHistoryImportJob,
  CapacitasAnagraficaHistoryImportResult,
  CapacitasInCassSyncJob,
  CapacitasInCassRuoloHarvestInput,
  CapacitasInCassRuoloHarvestResult,
  CapacitasInCassSyncJobCreateInput,
  CapacitasLookupOption,
  CapacitasParticellaAnomalia,
  CapacitasParticelleSyncJob,
  CapacitasParticelleSyncJobCreateInput,
  CapacitasRefetchCertificatiInput,
  CapacitasRefetchCertificatiResult,
  CapacitasResolveFragioneInput,
  CapacitasResolveFragioneResult,
  CapacitasSearchInput,
  CapacitasSearchResult,
  CapacitasTerreniJob,
  CapacitasTerreniJobCreateInput,
  CapacitasTerreniSearchInput,
  CapacitasTerreniSearchResult,
  BonificaOristaneseCredential,
  BonificaOristaneseCredentialCreateInput,
  BonificaOristaneseCredentialTestResult as BonificaOristaneseCredentialProbeResult,
  BonificaOristaneseCredentialUpdateInput,
  BonificaSyncRunRequest,
  BonificaSyncRunResponse,
  BonificaSyncStatusResponse,
  BonificaUserStaging,
  BonificaUserStagingBulkApproveResponse,
  BonificaUserStagingListResponse,
  CurrentUser,
  DashboardSummary,
  EffectivePermission,
  EffectivePermissionPreview,
  InazCollaborator,
  InazAccessContext,
  InazCollaboratorScheduleAssignment,
  InazCollaboratorScheduleAssignmentCreateInput,
  InazCollaboratorCalendarResponse,
  InazCollaboratorListResponse,
  InazCollaboratorSummaryResponse,
  InazCredential,
  InazCredentialCreateInput,
  InazCredentialTestResult,
  InazCredentialUpdateInput,
  InazDashboardSummaryResponse,
  InazDailyRecord,
  InazDailyRecordManualUpdateInput,
  InazDailyRecordListResponse,
  InazRecoveryAdjustment,
  InazRecoveryAdjustmentCreateInput,
  InazRecoveryAdjustmentReviewInput,
  InazRecoveryAdjustmentUpdateInput,
  InazRecoveryDashboardResponse,
  InazAutoSyncConfig,
  InazAutoSyncConfigUpdateInput,
  InazHoliday,
  InazHolidayCreateInput,
  InazHolidayUpdateInput,
  InazImportJob,
  InazImportJobListResponse,
  InazImportJsonResponse,
  InazImportPreviewResponse,
  InazScheduleRule,
  InazScheduleBootstrapApplyRequest,
  InazScheduleBootstrapApplyResponse,
  InazScheduleBootstrapPreviewResponse,
  InazScheduleRuleCreateInput,
  InazScheduleRuleUpdateInput,
  InazScheduleTemplate,
  InazScheduleTemplateCreateInput,
  InazScheduleTemplateUpdateInput,
  InazSupervisorAssignment,
  InazSyncJob,
  InazSyncJobCreateInput,
  InazSyncJobListResponse,
  LoginResponse,
  MeInazStatusResponse,
  MeInazSummaryResponse,
  MeModuleStatusResponse,
  MeOperazioniActivityListResponse,
  MeOperazioniCaseListResponse,
  MeOperazioniReportListResponse,
  MeOperazioniSummaryResponse,
  MeSummaryResponse,
  MeAssignedDeviceListResponse,
  MeVehicleAssignmentListResponse,
  MeVehicleUsageSessionListResponse,
  MyPermissionsResponse,
  OrgStructureAssignment,
  OrgStructureAssignmentUpdateInput,
  OrgStructureBootstrapResult,
  OrgStructureWorkspace,
  UserPermissionsAdminView,
  OrganigrammaImportResponse,
  OrganigrammaSnapshot,
  OrgAssignment,
  OrgAssignmentCreateInput,
  OrgAssignmentUpdateInput,
  OrgStructureKind,
  OrgImportMode,
  OrgUnit,
  OrgUnitCreateInput,
  OrgUnitDetail,
  OrgUnitTreeNode,
  OrgUnitUpdateInput,
  OrgVisibilityOverride,
  OrgVisibilityOverrideCreateInput,
  OrgVisibilityOverrideUpdateInput,
  OrgVisibilityResult,
  OrgWhiteCompanySyncResult,
  NetworkAlert,
  NetworkAlertUpdateInput,
  NetworkDashboardSummary,
  NetworkDetectionWatchlistRule,
  NetworkDetectionWatchlistRuleCreateInput,
  NetworkDetectionWatchlistRuleUpdateInput,
  NetworkAssignedUserSummary,
  NetworkDevice,
  NetworkDeviceBulkUpdateInput,
  NetworkDeviceBulkUpdateResponse,
  NetworkDeviceListResponse,
  NetworkStatisticsSummary,
  NetworkDeviceUpdateInput,
  NetworkFirewall,
  NetworkFirewallEvent,
  NetworkFirewallLogCoverageSummary,
  NetworkFirewallMetric,
  NetworkIpWhois,
  NetworkTrackedSubject,
  NetworkTrackedSubjectActivitySummary,
  NetworkTrackedSubjectCreateInput,
  NetworkTrackedSubjectUpdateInput,
  NetworkArpTimelineItem,
  NetworkVpnBypassSummary,
  DevicePositionUpdateInput,
  DevicePosition,
  NetworkFloorPlan,
  NetworkFloorPlanCreateInput,
  NetworkFloorPlanDevice,
  NetworkFloorPlanDetail,
  NetworkScan,
  NetworkScanDetail,
  NetworkScanDiff,
  NetworkScanTriggerInput,
  NetworkScanTriggerResponse,
  NasGroup,
  NasUser,
  PermissionEntryInput,
  PermissionUserInput,
  Review,
  SectionResponse,
  Share,
  SyncApplyResult,
  SyncCapabilities,
  SyncJob,
  SyncPreview,
  SyncPreviewRequest,
  SyncRun,
  WikiRequest,
  WikiRequestAssignee,
  WikiRequestArtifact,
  WikiRequestArtifactCreateInput,
  WikiSupportClustersResponse,
  WikiSupportInsightsResponse,
  WikiSupportAnalyticsSeriesResponse,
  WikiSupportAnalyticsSummary,
  WikiRequestDuplicateCandidate,
  WikiRequestCreateInput,
  WikiRequestEvent,
  WikiRequestFeedbackInput,
  WikiRequestFamily,
  WikiRequestMakeCanonicalInput,
  WikiRequestMarkDuplicateInput,
  WikiMyRequestsSummary,
  WikiRequestReopenInput,
  WikiRequestUpdateInput,
  WikiToolAuditLogListResponse,
  WikiToolAuditLogDetailResponse,
  WikiToolAuditLogRelatedResponse,
  WikiToolAuditSummary,
  WikiTelemetryPruneResponse,
  WikiTelemetryRefreshResponse,
  WikiTelemetryRetention,
  WikiTelemetrySchedule,
  WikiTelemetrySeriesResponse,
  WikiTelemetrySummary,
  WikiConversationMetricsSeriesResponse,
  WikiConversationMetricsSummary,
  WikiConversationContextLink,
  WikiConversationGovernanceConfig,
  WikiConversationMetricsBackfillJob,
  WikiConversationMetricsBackfillJobChainDetail,
  WikiConversationMetricsBackfillJobChainListResponse,
  WikiConversationMetricsBackfillJobChainSummary,
  WikiConversationMetricsBackfillJobPruneResponse,
} from "@/types/api";
import type {
  WikiArticleGroup,
  WikiConversation,
  WikiConversationSummary,
  WikiConversationSummaryMetrics,
} from "@/features/wiki/types";

const DEFAULT_API_BASE_URL = "/api";
const ELABORAZIONE_BATCH_DETAIL_CACHE_TTL_MS = 1000;

type ElaborazioneBatchDetailCacheEntry = {
  expiresAt: number;
  promise: Promise<ElaborazioneBatchDetail>;
};

const elaborazioneBatchDetailCache = new Map<string, ElaborazioneBatchDetailCacheEntry>();

export class ApiError extends Error {
  status?: number;
  detailData: unknown;

  constructor(message: string, detailData?: unknown, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detailData = detailData;
  }
}

export function isAuthError(error: unknown): error is ApiError {
  return error instanceof ApiError && (error.status === 401 || error.status === 403);
}

export function getApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL;
  const value = raw.replace(/\/+$/, "");

  // Always keep a non-empty base URL.
  if (!value) {
    return DEFAULT_API_BASE_URL;
  }

  // In browser we require a relative base (e.g. "/api") so nginx can proxy correctly.
  // If a previous build/runtime leaks an absolute URL (e.g. "http://localhost"),
  // fall back to the safe default.
  if (typeof window !== "undefined" && !value.startsWith("/")) {
    return DEFAULT_API_BASE_URL;
  }

  return value;
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = typeof FormData !== "undefined" && init?.body instanceof FormData;

  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
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

  return (await response.json()) as T;
}

export async function requestBlob(path: string, init?: RequestInit): Promise<Blob> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
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

  return response.blob();
}

export async function requestFormDataWithUploadProgress<T>(
  path: string,
  formData: FormData,
  token: string,
  onProgress?: (percent: number) => void,
): Promise<T> {
  return await new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${getApiBaseUrl()}${path}`);
    xhr.responseType = "json";
    xhr.setRequestHeader("Authorization", `Bearer ${token}`);

    xhr.upload.addEventListener("progress", (event) => {
      if (!event.lengthComputable) {
        return;
      }
      const percent = Math.min(100, Math.max(0, Math.round((event.loaded / event.total) * 100)));
      onProgress?.(percent);
    });

    xhr.addEventListener("load", () => {
      const responseData = xhr.response;
      if (xhr.status >= 200 && xhr.status < 300) {
        onProgress?.(100);
        resolve(responseData as T);
        return;
      }

      const payload = typeof responseData === "object" && responseData !== null ? (responseData as { detail?: unknown }) : undefined;
      let detail = "Request failed";
      const detailData: unknown = payload?.detail;

      if (typeof payload?.detail === "string") {
        detail = payload.detail;
      } else if (
        payload?.detail &&
        typeof payload.detail === "object" &&
        "message" in payload.detail &&
        typeof payload.detail.message === "string"
      ) {
        detail = payload.detail.message;
      } else if (payload?.detail != null) {
        detail = JSON.stringify(payload.detail);
      } else if (xhr.statusText) {
        detail = xhr.statusText;
      }

      reject(new ApiError(detail, detailData, xhr.status));
    });

    xhr.addEventListener("error", () => {
      reject(new ApiError("Errore di rete durante upload CSV"));
    });

    xhr.send(formData);
  });
}

export function createQueryString(params: Record<string, string | undefined>): string {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value && value.trim().length > 0) {
      searchParams.set(key, value.trim());
    }
  });

  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

export function getWebSocketBaseUrl(): string {
  const apiBaseUrl = getApiBaseUrl();

  if (apiBaseUrl.startsWith("https://")) {
    return apiBaseUrl.replace("https://", "wss://");
  }

  if (apiBaseUrl.startsWith("http://")) {
    return apiBaseUrl.replace("http://", "ws://");
  }

  if (typeof window === "undefined") {
    return apiBaseUrl;
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${apiBaseUrl}`;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function getCurrentUser(token: string): Promise<CurrentUser> {
  return request<CurrentUser>("/auth/me", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiArticles(token: string): Promise<WikiArticleGroup[]> {
  return request<WikiArticleGroup[]>("/wiki/articles", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getMeStatus(token: string): Promise<MeModuleStatusResponse> {
  return request<MeModuleStatusResponse>("/me", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getMeInazStatus(token: string): Promise<MeInazStatusResponse> {
  return request<MeInazStatusResponse>("/me/inaz", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listMeInazDailyRecords(
  token: string,
  params: {
    collaboratorId?: string;
    dateFrom?: string;
    dateTo?: string;
    q?: string;
    page?: number;
    pageSize?: number;
  } = {},
): Promise<InazDailyRecordListResponse> {
  const query = new URLSearchParams();
  if (params.collaboratorId) {
    query.set("collaborator_id", params.collaboratorId);
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
  return request<InazDailyRecordListResponse>(`/me/inaz/daily-records${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getMeInazDailyRecord(token: string, recordId: string): Promise<import("@/types/api").InazDailyRecord> {
  return request<import("@/types/api").InazDailyRecord>(`/me/inaz/daily-records/${recordId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getMeInazSummary(token: string, periodStart: string, periodEnd: string): Promise<MeInazSummaryResponse> {
  const query = new URLSearchParams({ period_start: periodStart, period_end: periodEnd });
  return request<MeInazSummaryResponse>(`/me/inaz/summary?${query.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getMeSummary(
  token: string,
  params?: { periodStart?: string; periodEnd?: string },
): Promise<MeSummaryResponse> {
  const query = new URLSearchParams();
  if (params?.periodStart) query.set("period_start", params.periodStart);
  if (params?.periodEnd) query.set("period_end", params.periodEnd);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<MeSummaryResponse>(`/me/summary${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getMeOperazioniSummary(
  token: string,
  params?: { periodStart?: string; periodEnd?: string },
): Promise<MeOperazioniSummaryResponse> {
  const query = new URLSearchParams();
  if (params?.periodStart) query.set("period_start", params.periodStart);
  if (params?.periodEnd) query.set("period_end", params.periodEnd);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<MeOperazioniSummaryResponse>(`/me/operazioni/summary${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listMeOperazioniActivities(
  token: string,
  params?: { periodStart?: string; periodEnd?: string; page?: number; pageSize?: number },
): Promise<MeOperazioniActivityListResponse> {
  const query = new URLSearchParams();
  if (params?.periodStart) query.set("period_start", params.periodStart);
  if (params?.periodEnd) query.set("period_end", params.periodEnd);
  if (params?.page) query.set("page", String(params.page));
  if (params?.pageSize) query.set("page_size", String(params.pageSize));
  return request<MeOperazioniActivityListResponse>(`/me/operazioni/activities?${query.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listMeOperazioniReports(
  token: string,
  params?: { periodStart?: string; periodEnd?: string; page?: number; pageSize?: number },
): Promise<MeOperazioniReportListResponse> {
  const query = new URLSearchParams();
  if (params?.periodStart) query.set("period_start", params.periodStart);
  if (params?.periodEnd) query.set("period_end", params.periodEnd);
  if (params?.page) query.set("page", String(params.page));
  if (params?.pageSize) query.set("page_size", String(params.pageSize));
  return request<MeOperazioniReportListResponse>(`/me/operazioni/reports?${query.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listMeOperazioniCases(
  token: string,
  params?: { periodStart?: string; periodEnd?: string; page?: number; pageSize?: number },
): Promise<MeOperazioniCaseListResponse> {
  const query = new URLSearchParams();
  if (params?.periodStart) query.set("period_start", params.periodStart);
  if (params?.periodEnd) query.set("period_end", params.periodEnd);
  if (params?.page) query.set("page", String(params.page));
  if (params?.pageSize) query.set("page_size", String(params.pageSize));
  return request<MeOperazioniCaseListResponse>(`/me/operazioni/cases?${query.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listMeVehicleSessions(
  token: string,
  params?: { periodStart?: string; periodEnd?: string; page?: number; pageSize?: number },
): Promise<MeVehicleUsageSessionListResponse> {
  const query = new URLSearchParams();
  if (params?.periodStart) query.set("period_start", params.periodStart);
  if (params?.periodEnd) query.set("period_end", params.periodEnd);
  if (params?.page) query.set("page", String(params.page));
  if (params?.pageSize) query.set("page_size", String(params.pageSize));
  return request<MeVehicleUsageSessionListResponse>(`/me/operazioni/vehicle-sessions?${query.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listMeAssignedDevices(token: string): Promise<MeAssignedDeviceListResponse> {
  return request<MeAssignedDeviceListResponse>("/me/assets/devices", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listMeVehicleAssignments(token: string): Promise<MeVehicleAssignmentListResponse> {
  return request<MeVehicleAssignmentListResponse>("/me/assets/vehicle-assignments", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getMyPermissions(token: string): Promise<MyPermissionsResponse> {
  return request<MyPermissionsResponse>("/auth/my-permissions", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getDashboardSummary(token: string): Promise<DashboardSummary> {
  return request<DashboardSummary>("/dashboard/summary", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getShares(token: string): Promise<Share[]> {
  return request<Share[]>("/shares", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNasUsers(token: string): Promise<NasUser[]> {
  return request<NasUser[]>("/nas-users", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNasUsersForUsersSection(token: string): Promise<NasUser[]> {
  return request<NasUser[]>("/nas-users/section", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listApplicationUsers(
  token: string,
  params: { skip?: number; limit?: number; role?: string; isActive?: boolean } = {},
): Promise<ApplicationUserListResponse> {
  const query = new URLSearchParams();
  if (params.skip != null) {
    query.set("skip", String(params.skip));
  }
  if (params.limit != null) {
    query.set("limit", String(params.limit));
  }
  if (params.role) {
    query.set("role", params.role);
  }
  if (params.isActive != null) {
    query.set("is_active", String(params.isActive));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<ApplicationUserListResponse>(`/admin/users${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listAllApplicationUsers(token: string): Promise<ApplicationUser[]> {
  const pageSize = 200;
  let skip = 0;
  const items: ApplicationUser[] = [];

  while (true) {
    const response = await listApplicationUsers(token, { skip, limit: pageSize });
    items.push(...response.items);
    if (items.length >= response.total || response.items.length === 0) {
      return items;
    }
    skip += pageSize;
  }
}

export async function getApplicationUserPermissions(token: string, userId: number): Promise<UserPermissionsAdminView> {
  return request<UserPermissionsAdminView>(`/admin/users/${userId}/permissions`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listSectionCatalog(token: string, params: { module?: string; activeOnly?: boolean } = {}): Promise<SectionResponse[]> {
  const query = new URLSearchParams();
  if (params.module) query.set("module", params.module);
  if (params.activeOnly) query.set("active_only", "true");
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<SectionResponse[]>(`/sections${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updateApplicationUserPermissions(
  token: string,
  userId: number,
  permissions: Array<{ section_id: number; is_granted: boolean }>,
): Promise<UserPermissionsAdminView> {
  await request(`/admin/users/${userId}/permissions`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ permissions }),
  });
  return getApplicationUserPermissions(token, userId);
}

export async function deleteApplicationUserPermissionOverride(token: string, userId: number, sectionId: number): Promise<void> {
  await request(`/admin/users/${userId}/permissions/${sectionId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getOrgStructureWorkspace(token: string): Promise<OrgStructureWorkspace> {
  return request<OrgStructureWorkspace>("/admin/org-structure", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function bootstrapOrgStructureFromWhiteCompany(token: string): Promise<OrgStructureBootstrapResult> {
  return request<OrgStructureBootstrapResult>("/admin/org-structure/bootstrap", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function upsertOrgStructureAssignment(
  token: string,
  userId: number,
  payload: OrgStructureAssignmentUpdateInput,
): Promise<OrgStructureAssignment> {
  return request<OrgStructureAssignment>(`/admin/org-structure/users/${userId}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function deleteOrgStructureAssignment(token: string, userId: number): Promise<void> {
  await request<void>(`/admin/org-structure/users/${userId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

// --- Organigramma (canonical layer) ---------------------------------------
function authHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

export async function getOrgUnits(
  token: string,
  params: { parentId?: string; structureKind?: OrgStructureKind } = {},
): Promise<OrgUnit[]> {
  const query = new URLSearchParams();
  if (params.parentId) query.set("parent_id", params.parentId);
  if (params.structureKind) query.set("structure_kind", params.structureKind);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<OrgUnit[]>(`/organigramma/units${suffix}`, { headers: authHeaders(token) });
}

export async function getOrgTree(token: string, structureKind: OrgStructureKind = "organigramma"): Promise<OrgUnitTreeNode[]> {
  return request<OrgUnitTreeNode[]>(`/organigramma/units/tree?structure_kind=${structureKind}`, { headers: authHeaders(token) });
}

export async function getOrgUnit(
  token: string,
  unitId: string,
  structureKind: OrgStructureKind = "organigramma",
): Promise<OrgUnitDetail> {
  return request<OrgUnitDetail>(`/organigramma/units/${unitId}?structure_kind=${structureKind}`, { headers: authHeaders(token) });
}

export async function createOrgUnit(
  token: string,
  payload: OrgUnitCreateInput,
  structureKind: OrgStructureKind = "organigramma",
): Promise<OrgUnit> {
  return request<OrgUnit>(`/organigramma/units?structure_kind=${structureKind}`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function updateOrgUnit(
  token: string,
  unitId: string,
  payload: OrgUnitUpdateInput,
  structureKind: OrgStructureKind = "organigramma",
): Promise<OrgUnit> {
  return request<OrgUnit>(`/organigramma/units/${unitId}?structure_kind=${structureKind}`, {
    method: "PUT",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function deleteOrgUnit(
  token: string,
  unitId: string,
  structureKind: OrgStructureKind = "organigramma",
): Promise<void> {
  await request<void>(`/organigramma/units/${unitId}?structure_kind=${structureKind}`, { method: "DELETE", headers: authHeaders(token) });
}

export async function getOrgAssignments(
  token: string,
  params: { unitId?: string; userId?: number; structureKind?: OrgStructureKind } = {},
): Promise<OrgAssignment[]> {
  const query = new URLSearchParams();
  if (params.unitId) query.set("unit_id", params.unitId);
  if (params.userId != null) query.set("user_id", String(params.userId));
  if (params.structureKind) query.set("structure_kind", params.structureKind);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<OrgAssignment[]>(`/organigramma/assignments${suffix}`, { headers: authHeaders(token) });
}

export async function createOrgAssignment(
  token: string,
  payload: OrgAssignmentCreateInput,
  structureKind: OrgStructureKind = "organigramma",
): Promise<OrgAssignment> {
  return request<OrgAssignment>(`/organigramma/assignments?structure_kind=${structureKind}`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function updateOrgAssignment(
  token: string,
  assignmentId: string,
  payload: OrgAssignmentUpdateInput,
  structureKind: OrgStructureKind = "organigramma",
): Promise<OrgAssignment> {
  return request<OrgAssignment>(`/organigramma/assignments/${assignmentId}?structure_kind=${structureKind}`, {
    method: "PUT",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function deleteOrgAssignment(
  token: string,
  assignmentId: string,
  structureKind: OrgStructureKind = "organigramma",
): Promise<void> {
  await request<void>(`/organigramma/assignments/${assignmentId}?structure_kind=${structureKind}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
}

export async function getOrgOverrides(
  token: string,
  structureKind: OrgStructureKind = "organigramma",
): Promise<OrgVisibilityOverride[]> {
  return request<OrgVisibilityOverride[]>(`/organigramma/overrides?structure_kind=${structureKind}`, { headers: authHeaders(token) });
}

export async function createOrgOverride(
  token: string,
  payload: OrgVisibilityOverrideCreateInput,
  structureKind: OrgStructureKind = "organigramma",
): Promise<OrgVisibilityOverride> {
  return request<OrgVisibilityOverride>(`/organigramma/overrides?structure_kind=${structureKind}`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function updateOrgOverride(
  token: string,
  overrideId: string,
  payload: OrgVisibilityOverrideUpdateInput,
  structureKind: OrgStructureKind = "organigramma",
): Promise<OrgVisibilityOverride> {
  return request<OrgVisibilityOverride>(`/organigramma/overrides/${overrideId}?structure_kind=${structureKind}`, {
    method: "PUT",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function deleteOrgOverride(
  token: string,
  overrideId: string,
  structureKind: OrgStructureKind = "organigramma",
): Promise<void> {
  await request<void>(`/organigramma/overrides/${overrideId}?structure_kind=${structureKind}`, { method: "DELETE", headers: authHeaders(token) });
}

export async function getOrgVisibility(
  token: string,
  userId: number,
  structureKind: OrgStructureKind = "organigramma",
): Promise<OrgVisibilityResult> {
  return request<OrgVisibilityResult>(`/organigramma/visibility/${userId}?structure_kind=${structureKind}`, { headers: authHeaders(token) });
}

export async function syncOrgWhiteCompany(token: string): Promise<OrgWhiteCompanySyncResult> {
  return request<OrgWhiteCompanySyncResult>("/organigramma/sync/whitecompany", {
    method: "POST",
    headers: authHeaders(token),
  });
}

export async function exportOrganigrammaSnapshot(
  token: string,
  structureKind: OrgStructureKind = "organigramma",
): Promise<OrganigrammaSnapshot> {
  return request<OrganigrammaSnapshot>(`/organigramma/io/export?structure_kind=${structureKind}`, {
    headers: authHeaders(token),
  });
}

export async function importOrganigrammaSnapshot(
  token: string,
  snapshot: OrganigrammaSnapshot,
  mode: OrgImportMode = "merge",
  structureKind: OrgStructureKind = "organigramma",
): Promise<OrganigrammaImportResponse> {
  return request<OrganigrammaImportResponse>(`/organigramma/io/import?mode=${mode}&structure_kind=${structureKind}`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(snapshot),
  });
}

export async function listInazCollaborators(
  token: string,
  params: {
    q?: string;
    mappedOnly?: boolean | null;
    page?: number;
    pageSize?: number;
  } = {},
): Promise<InazCollaboratorListResponse> {
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
  return request<InazCollaboratorListResponse>(`/inaz/collaborators${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listAllInazCollaborators(token: string): Promise<InazCollaborator[]> {
  const pageSize = 200;
  let page = 1;
  const items: InazCollaborator[] = [];

  while (true) {
    const response = await listInazCollaborators(token, { page, pageSize });
    items.push(...response.items);
    if (items.length >= response.total || response.items.length === 0) {
      return items;
    }
    page += 1;
  }
}

export async function listInazApplicationUsers(token: string): Promise<ApplicationUser[]> {
  return request<ApplicationUser[]>("/inaz/application-users", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listInazCredentials(token: string): Promise<InazCredential[]> {
  return request<InazCredential[]>("/inaz/credentials", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getInazAccessContext(token: string): Promise<InazAccessContext> {
  return request<InazAccessContext>("/inaz/access-context", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listInazSupervisorAssignments(
  token: string,
  supervisorUserId?: number,
): Promise<InazSupervisorAssignment[]> {
  const suffix = supervisorUserId != null ? `?supervisor_user_id=${supervisorUserId}` : "";
  return request<InazSupervisorAssignment[]>(`/inaz/supervisor-assignments${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updateInazSupervisorAssignment(
  token: string,
  collaboratorId: string,
  supervisorUserId: number | null,
): Promise<InazSupervisorAssignment | null> {
  return request<InazSupervisorAssignment | null>(`/inaz/supervisor-assignments/${collaboratorId}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ supervisor_user_id: supervisorUserId }),
  });
}

export async function createInazCredential(token: string, payload: InazCredentialCreateInput): Promise<InazCredential> {
  return request<InazCredential>("/inaz/credentials", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function updateInazCredential(
  token: string,
  credentialId: number,
  payload: InazCredentialUpdateInput,
): Promise<InazCredential> {
  return request<InazCredential>(`/inaz/credentials/${credentialId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function deleteInazCredential(token: string, credentialId: number): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/inaz/credentials/${credentialId}`, {
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

export async function testInazCredential(token: string, credentialId: number): Promise<InazCredentialTestResult> {
  return request<InazCredentialTestResult>(`/inaz/credentials/${credentialId}/test`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function mapInazCollaboratorApplicationUser(
  token: string,
  collaboratorId: string,
  applicationUserId: number | null,
): Promise<InazCollaborator> {
  return request<InazCollaborator>(`/inaz/collaborators/${collaboratorId}/application-user`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ application_user_id: applicationUserId }),
  });
}

export async function getInazCollaboratorCalendar(
  token: string,
  collaboratorId: string,
  dateFrom: string,
  dateTo: string,
): Promise<InazCollaboratorCalendarResponse> {
  const query = new URLSearchParams({ date_from: dateFrom, date_to: dateTo });
  return request<InazCollaboratorCalendarResponse>(`/inaz/collaborators/${collaboratorId}/calendar?${query.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getInazCollaboratorSummary(
  token: string,
  collaboratorId: string,
  periodStart: string,
  periodEnd: string,
): Promise<InazCollaboratorSummaryResponse> {
  const query = new URLSearchParams({ period_start: periodStart, period_end: periodEnd });
  return request<InazCollaboratorSummaryResponse>(`/inaz/collaborators/${collaboratorId}/summary?${query.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listInazDailyRecords(
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
): Promise<InazDailyRecordListResponse> {
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
  return request<InazDailyRecordListResponse>(`/inaz/giornaliere${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listInazDailyMatrixRecords(
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
): Promise<InazDailyRecordListResponse> {
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
  return request<InazDailyRecordListResponse>(`/inaz/giornaliere/matrix${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getInazDailyRecord(token: string, recordId: string): Promise<InazDailyRecord> {
  return request<InazDailyRecord>(`/inaz/giornaliere/${recordId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getInazDashboardSummary(
  token: string,
  params: { periodStart: string; periodEnd: string },
): Promise<InazDashboardSummaryResponse> {
  const query = new URLSearchParams({
    period_start: params.periodStart,
    period_end: params.periodEnd,
  });
  return request<InazDashboardSummaryResponse>(`/inaz/dashboard/summary?${query.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updateInazDailyRecord(
  token: string,
  recordId: string,
  payload: InazDailyRecordManualUpdateInput,
): Promise<import("@/types/api").InazDailyRecord> {
  return request(`/inaz/giornaliere/${recordId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getInazRecoveryDashboard(
  token: string,
  params: {
    dateFrom?: string;
    dateTo?: string;
    q?: string;
    negativeOnly?: boolean;
    pendingValidationOnly?: boolean;
    pendingAdjustmentsOnly?: boolean;
    manualAdjustmentsOnly?: boolean;
  } = {},
): Promise<InazRecoveryDashboardResponse> {
  const query = new URLSearchParams();
  if (params.dateFrom) query.set("date_from", params.dateFrom);
  if (params.dateTo) query.set("date_to", params.dateTo);
  if (params.q) query.set("q", params.q);
  if (params.negativeOnly) query.set("negative_only", "true");
  if (params.pendingValidationOnly) query.set("pending_validation_only", "true");
  if (params.pendingAdjustmentsOnly) query.set("pending_adjustments_only", "true");
  if (params.manualAdjustmentsOnly) query.set("manual_adjustments_only", "true");
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<InazRecoveryDashboardResponse>(`/inaz/recovery/dashboard${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listInazRecoveryAdjustments(
  token: string,
  collaboratorId?: string,
  approvalStatus?: "pending" | "approved" | "rejected",
): Promise<InazRecoveryAdjustment[]> {
  const query = new URLSearchParams();
  if (collaboratorId) query.set("collaborator_id", collaboratorId);
  if (approvalStatus) query.set("approval_status", approvalStatus);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<InazRecoveryAdjustment[]>(`/inaz/recovery/adjustments${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createInazRecoveryAdjustment(
  token: string,
  payload: InazRecoveryAdjustmentCreateInput,
): Promise<InazRecoveryAdjustment> {
  return request<InazRecoveryAdjustment>("/inaz/recovery/adjustments", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function updateInazRecoveryAdjustment(
  token: string,
  adjustmentId: string,
  payload: InazRecoveryAdjustmentUpdateInput,
): Promise<InazRecoveryAdjustment> {
  return request<InazRecoveryAdjustment>(`/inaz/recovery/adjustments/${adjustmentId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function deleteInazRecoveryAdjustment(token: string, adjustmentId: string): Promise<void> {
  await request<void>(`/inaz/recovery/adjustments/${adjustmentId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function reviewInazRecoveryAdjustment(
  token: string,
  adjustmentId: string,
  payload: InazRecoveryAdjustmentReviewInput,
): Promise<InazRecoveryAdjustment> {
  return request<InazRecoveryAdjustment>(`/inaz/recovery/adjustments/${adjustmentId}/review`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function listInazHolidays(token: string, year?: number): Promise<InazHoliday[]> {
  const query = year != null ? `?year=${year}` : "";
  return request<InazHoliday[]>(`/inaz/holidays${query}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function bootstrapInazHolidays(token: string, year: number): Promise<{ year: number; created: number; items: InazHoliday[] }> {
  return request(`/inaz/holidays/bootstrap?year=${year}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createInazHoliday(token: string, payload: InazHolidayCreateInput): Promise<InazHoliday> {
  return request<InazHoliday>("/inaz/holidays", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function updateInazHoliday(token: string, holidayId: number, payload: InazHolidayUpdateInput): Promise<InazHoliday> {
  return request<InazHoliday>(`/inaz/holidays/${holidayId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function deleteInazHoliday(token: string, holidayId: number): Promise<void> {
  await request<void>(`/inaz/holidays/${holidayId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listInazScheduleTemplates(token: string): Promise<InazScheduleTemplate[]> {
  return request<InazScheduleTemplate[]>("/inaz/schedule/templates", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createInazScheduleTemplate(token: string, payload: InazScheduleTemplateCreateInput): Promise<InazScheduleTemplate> {
  return request<InazScheduleTemplate>("/inaz/schedule/templates", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function updateInazScheduleTemplate(token: string, templateId: number, payload: InazScheduleTemplateUpdateInput): Promise<InazScheduleTemplate> {
  return request<InazScheduleTemplate>(`/inaz/schedule/templates/${templateId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function deleteInazScheduleTemplate(token: string, templateId: number): Promise<void> {
  await request<void>(`/inaz/schedule/templates/${templateId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createInazScheduleRule(token: string, templateId: number, payload: InazScheduleRuleCreateInput): Promise<InazScheduleRule> {
  return request<InazScheduleRule>(`/inaz/schedule/templates/${templateId}/rules`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function updateInazScheduleRule(token: string, ruleId: number, payload: InazScheduleRuleUpdateInput): Promise<InazScheduleRule> {
  return request<InazScheduleRule>(`/inaz/schedule/rules/${ruleId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function deleteInazScheduleRule(token: string, ruleId: number): Promise<void> {
  await request<void>(`/inaz/schedule/rules/${ruleId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listInazCollaboratorScheduleAssignments(token: string, collaboratorId: string): Promise<InazCollaboratorScheduleAssignment[]> {
  return request<InazCollaboratorScheduleAssignment[]>(`/inaz/collaborators/${collaboratorId}/schedule-assignments`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createInazCollaboratorScheduleAssignment(
  token: string,
  collaboratorId: string,
  payload: InazCollaboratorScheduleAssignmentCreateInput,
): Promise<InazCollaboratorScheduleAssignment> {
  return request<InazCollaboratorScheduleAssignment>(`/inaz/collaborators/${collaboratorId}/schedule-assignments`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function deleteInazCollaboratorScheduleAssignment(token: string, assignmentId: number): Promise<void> {
  await request<void>(`/inaz/schedule-assignments/${assignmentId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function deleteInazScheduleAssignment(token: string, assignmentId: number): Promise<void> {
  await deleteInazCollaboratorScheduleAssignment(token, assignmentId);
}

export async function getInazScheduleBootstrapPreview(token: string): Promise<InazScheduleBootstrapPreviewResponse> {
  return request<InazScheduleBootstrapPreviewResponse>("/inaz/configuration/schedule-bootstrap-preview", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function applyInazScheduleBootstrap(
  token: string,
  payload: InazScheduleBootstrapApplyRequest = {},
): Promise<InazScheduleBootstrapApplyResponse> {
  return request<InazScheduleBootstrapApplyResponse>("/inaz/configuration/schedule-bootstrap-apply", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function previewInazImport(
  token: string,
  file: File,
): Promise<InazImportPreviewResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return request<InazImportPreviewResponse>("/inaz/import/preview", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });
}

export async function importInazJson(
  token: string,
  file: File,
): Promise<InazImportJsonResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return request<InazImportJsonResponse>("/inaz/import/json", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });
}

export async function listInazImportJobs(token: string): Promise<InazImportJob[]> {
  const response = await request<InazImportJobListResponse>("/inaz/import/jobs", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return response.items;
}

export async function getInazImportJob(token: string, jobId: string): Promise<InazImportJob> {
  return request<InazImportJob>(`/inaz/import/jobs/${jobId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createInazSyncJob(token: string, payload: InazSyncJobCreateInput): Promise<InazSyncJob> {
  return request<InazSyncJob>("/inaz/sync/jobs", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getInazAutoSyncConfig(token: string): Promise<InazAutoSyncConfig> {
  return request<InazAutoSyncConfig>("/inaz/sync/config", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updateInazAutoSyncConfig(
  token: string,
  payload: InazAutoSyncConfigUpdateInput,
): Promise<InazAutoSyncConfig> {
  return request<InazAutoSyncConfig>("/inaz/sync/config", {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function listInazSyncJobs(token: string, params: { limit?: number } = {}): Promise<InazSyncJob[]> {
  const query = new URLSearchParams();
  if (params.limit != null) {
    query.set("limit", String(params.limit));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  const response = await request<InazSyncJobListResponse>(`/inaz/sync/jobs${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return response.items;
}

export async function getInazSyncJob(token: string, jobId: string): Promise<InazSyncJob> {
  return request<InazSyncJob>(`/inaz/sync/jobs/${jobId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function retryInazSyncJob(token: string, jobId: string): Promise<InazSyncJob> {
  return request<InazSyncJob>(`/inaz/sync/jobs/${jobId}/retry`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function cancelInazSyncJob(token: string, jobId: string): Promise<InazSyncJob> {
  return request<InazSyncJob>(`/inaz/sync/jobs/${jobId}/cancel`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function deleteInazSyncJob(token: string, jobId: string): Promise<void> {
  await request<void>(`/inaz/sync/jobs/${jobId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function downloadInazSyncArtifact(
  token: string,
  jobId: string,
  artifactName: "json" | "log" | "summary" | "progress" | "events",
): Promise<Blob> {
  return requestBlob(`/inaz/sync/jobs/${jobId}/artifacts/${artifactName}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function exportInazXlsm(
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
  return requestBlob(`/inaz/export/giornaliere.xlsm?${query.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiToolAuditLogs(
  token: string,
  params: {
    page?: number;
    pageSize?: number;
    toolName?: string;
    moduleKey?: string;
    conversationId?: string;
    username?: string;
    intent?: string;
    mode?: string;
    success?: boolean | null;
  } = {},
): Promise<WikiToolAuditLogListResponse> {
  const query = new URLSearchParams();
  if (params.page) {
    query.set("page", String(params.page));
  }
  if (params.pageSize) {
    query.set("page_size", String(params.pageSize));
  }
  if (params.toolName) {
    query.set("tool_name", params.toolName);
  }
  if (params.moduleKey) {
    query.set("module_key", params.moduleKey);
  }
  if (params.conversationId) {
    query.set("conversation_id", params.conversationId);
  }
  if (params.username) {
    query.set("username", params.username);
  }
  if (params.intent) {
    query.set("intent", params.intent);
  }
  if (params.mode) {
    query.set("mode", params.mode);
  }
  if (params.success != null) {
    query.set("success", String(params.success));
  }

  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiToolAuditLogListResponse>(`/wiki/audit/tool-calls${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiRequests(token: string): Promise<WikiRequest[]> {
  return request<WikiRequest[]>("/wiki/requests", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiRequest(token: string, requestId: string): Promise<WikiRequest> {
  return request<WikiRequest>(`/wiki/requests/${requestId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiRequestArtifacts(token: string, requestId: string): Promise<WikiRequestArtifact[]> {
  return request<WikiRequestArtifact[]>(`/wiki/requests/${requestId}/artifacts`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function downloadWikiRequestArtifact(token: string, requestId: string, artifactId: string): Promise<Blob> {
  const response = await fetch(`${getApiBaseUrl()}/wiki/requests/${requestId}/artifacts/${artifactId}/download`, {
    method: "GET",
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
    throw new ApiError(detail, null, response.status);
  }

  return response.blob();
}

export async function getWikiRequestAssignees(token: string): Promise<WikiRequestAssignee[]> {
  return request<WikiRequestAssignee[]>("/wiki/requests/assignees", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiRequestEvents(token: string, requestId: string): Promise<WikiRequestEvent[]> {
  return request<WikiRequestEvent[]>(`/wiki/requests/${requestId}/events`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiRequestDuplicates(token: string, requestId: string): Promise<WikiRequestDuplicateCandidate[]> {
  return request<WikiRequestDuplicateCandidate[]>(`/wiki/requests/${requestId}/duplicates`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiRequestLinkedDuplicates(token: string, requestId: string): Promise<WikiRequestDuplicateCandidate[]> {
  return request<WikiRequestDuplicateCandidate[]>(`/wiki/requests/${requestId}/linked-duplicates`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiRequestFamily(token: string, requestId: string): Promise<WikiRequestFamily> {
  return request<WikiRequestFamily>(`/wiki/requests/${requestId}/family`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getMyWikiRequests(token: string): Promise<WikiRequest[]> {
  return request<WikiRequest[]>("/wiki/requests/mine", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getMyWikiRequestsSummary(token: string): Promise<WikiMyRequestsSummary> {
  return request<WikiMyRequestsSummary>("/wiki/requests/mine/summary", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function markWikiRequestViewed(token: string, requestId: string): Promise<WikiRequest> {
  return request<WikiRequest>(`/wiki/requests/${requestId}/mark-viewed`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function reopenWikiRequest(
  token: string,
  requestId: string,
  payload: WikiRequestReopenInput,
): Promise<WikiRequest> {
  return request<WikiRequest>(`/wiki/requests/${requestId}/reopen`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function createWikiRequest(token: string, payload: WikiRequestCreateInput): Promise<WikiRequest> {
  return request<WikiRequest>("/wiki/requests", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function createWikiRequestWithArtifacts(
  token: string,
  payload: WikiRequestCreateInput,
  artifacts: WikiRequestArtifactCreateInput,
): Promise<WikiRequest> {
  const formData = new FormData();
  formData.set("payload_json", JSON.stringify(payload));
  if (artifacts.screenshotMeta) {
    formData.set("screenshot_meta_json", JSON.stringify(artifacts.screenshotMeta));
  }
  if (artifacts.uiSnapshot) {
    formData.set("ui_snapshot_json", JSON.stringify(artifacts.uiSnapshot));
  }
  if (artifacts.screenshotFile) {
    formData.set("screenshot", artifacts.screenshotFile);
  }
  return request<WikiRequest>("/wiki/requests/with-artifacts", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });
}

export async function updateWikiRequest(
  token: string,
  requestId: string,
  payload: WikiRequestUpdateInput,
): Promise<WikiRequest> {
  return request<WikiRequest>(`/wiki/requests/${requestId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function markWikiRequestDuplicate(
  token: string,
  requestId: string,
  payload: WikiRequestMarkDuplicateInput,
): Promise<WikiRequest> {
  return request<WikiRequest>(`/wiki/requests/${requestId}/mark-duplicate`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function unlinkWikiRequestDuplicate(token: string, requestId: string): Promise<WikiRequest> {
  return request<WikiRequest>(`/wiki/requests/${requestId}/unlink-duplicate`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function makeWikiRequestCanonical(
  token: string,
  requestId: string,
  payload: WikiRequestMakeCanonicalInput = {},
): Promise<WikiRequestFamily> {
  return request<WikiRequestFamily>(`/wiki/requests/${requestId}/make-canonical`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function updateWikiRequestFeedback(
  token: string,
  requestId: string,
  payload: WikiRequestFeedbackInput,
): Promise<WikiRequest> {
  return request<WikiRequest>(`/wiki/requests/${requestId}/feedback`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getWikiSupportAnalyticsSummary(
  token: string,
  params: { days?: number | null; deliveryStatus?: string | null; ticketLinked?: boolean | null } = {},
): Promise<WikiSupportAnalyticsSummary> {
  const query = new URLSearchParams();
  if (params.days != null) {
    query.set("days", String(params.days));
  }
  if (params.deliveryStatus) {
    query.set("delivery_status", params.deliveryStatus);
  }
  if (params.ticketLinked != null) {
    query.set("ticket_linked", String(params.ticketLinked));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiSupportAnalyticsSummary>(`/wiki/support/analytics/summary${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiSupportAnalyticsSeries(
  token: string,
  params: { days?: number | null; deliveryStatus?: string | null; ticketLinked?: boolean | null } = {},
): Promise<WikiSupportAnalyticsSeriesResponse> {
  const query = new URLSearchParams();
  if (params.days != null) {
    query.set("days", String(params.days));
  }
  if (params.deliveryStatus) {
    query.set("delivery_status", params.deliveryStatus);
  }
  if (params.ticketLinked != null) {
    query.set("ticket_linked", String(params.ticketLinked));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiSupportAnalyticsSeriesResponse>(`/wiki/support/analytics/series${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiSupportAnalyticsClusters(
  token: string,
  params: { days?: number | null; limit?: number | null; deliveryStatus?: string | null; ticketLinked?: boolean | null } = {},
): Promise<WikiSupportClustersResponse> {
  const query = new URLSearchParams();
  if (params.days != null) {
    query.set("days", String(params.days));
  }
  if (params.limit != null) {
    query.set("limit", String(params.limit));
  }
  if (params.deliveryStatus) {
    query.set("delivery_status", params.deliveryStatus);
  }
  if (params.ticketLinked != null) {
    query.set("ticket_linked", String(params.ticketLinked));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiSupportClustersResponse>(`/wiki/support/analytics/clusters${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiSupportAnalyticsInsights(
  token: string,
  params: { days?: number | null; deliveryStatus?: string | null; ticketLinked?: boolean | null } = {},
): Promise<WikiSupportInsightsResponse> {
  const query = new URLSearchParams();
  if (params.days != null) {
    query.set("days", String(params.days));
  }
  if (params.deliveryStatus) {
    query.set("delivery_status", params.deliveryStatus);
  }
  if (params.ticketLinked != null) {
    query.set("ticket_linked", String(params.ticketLinked));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiSupportInsightsResponse>(`/wiki/support/analytics/insights${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiToolAuditSummary(
  token: string,
  params: {
    toolName?: string;
    moduleKey?: string;
    conversationId?: string;
    username?: string;
    intent?: string;
    mode?: string;
    success?: boolean | null;
  } = {},
): Promise<WikiToolAuditSummary> {
  const query = new URLSearchParams();
  if (params.toolName) {
    query.set("tool_name", params.toolName);
  }
  if (params.moduleKey) {
    query.set("module_key", params.moduleKey);
  }
  if (params.conversationId) {
    query.set("conversation_id", params.conversationId);
  }
  if (params.username) {
    query.set("username", params.username);
  }
  if (params.intent) {
    query.set("intent", params.intent);
  }
  if (params.mode) {
    query.set("mode", params.mode);
  }
  if (params.success != null) {
    query.set("success", String(params.success));
  }

  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiToolAuditSummary>(`/wiki/audit/tool-calls/summary${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiToolAuditLogDetail(
  token: string,
  auditId: string,
): Promise<WikiToolAuditLogDetailResponse> {
  return request<WikiToolAuditLogDetailResponse>(`/wiki/audit/tool-calls/${auditId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiToolAuditRelatedLogs(
  token: string,
  auditId: string,
  params: { limit?: number | null } = {},
): Promise<WikiToolAuditLogRelatedResponse> {
  const query = new URLSearchParams();
  if (params.limit != null) {
    query.set("limit", String(params.limit));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiToolAuditLogRelatedResponse>(`/wiki/audit/tool-calls/${auditId}/related${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function exportWikiToolAuditLogs(
  token: string,
  params: {
    toolName?: string;
    moduleKey?: string;
    conversationId?: string;
    username?: string;
    intent?: string;
    mode?: string;
    success?: boolean | null;
  } = {},
): Promise<Blob> {
  const query = new URLSearchParams();
  if (params.toolName) {
    query.set("tool_name", params.toolName);
  }
  if (params.moduleKey) {
    query.set("module_key", params.moduleKey);
  }
  if (params.conversationId) {
    query.set("conversation_id", params.conversationId);
  }
  if (params.username) {
    query.set("username", params.username);
  }
  if (params.intent) {
    query.set("intent", params.intent);
  }
  if (params.mode) {
    query.set("mode", params.mode);
  }
  if (params.success != null) {
    query.set("success", String(params.success));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return requestBlob(`/wiki/audit/tool-calls/export${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiTelemetrySummary(
  token: string,
  params: { days?: number | null } = {},
): Promise<WikiTelemetrySummary> {
  const query = new URLSearchParams();
  if (params.days != null) {
    query.set("days", String(params.days));
  }

  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiTelemetrySummary>(`/wiki/telemetry/summary${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiTelemetrySeries(
  token: string,
  params: {
    dimensionType?: string | null;
    dimensionKey?: string | null;
    days?: number | null;
    granularity?: string | null;
  } = {},
): Promise<WikiTelemetrySeriesResponse> {
  const query = new URLSearchParams();
  if (params.dimensionType) {
    query.set("dimension_type", params.dimensionType);
  }
  if (params.dimensionKey) {
    query.set("dimension_key", params.dimensionKey);
  }
  if (params.days != null) {
    query.set("days", String(params.days));
  }
  if (params.granularity) {
    query.set("granularity", params.granularity);
  }

  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiTelemetrySeriesResponse>(`/wiki/telemetry/series${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function refreshWikiTelemetry(
  token: string,
  params: { days?: number | null } = {},
): Promise<WikiTelemetryRefreshResponse> {
  const query = new URLSearchParams();
  if (params.days != null) {
    query.set("days", String(params.days));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiTelemetryRefreshResponse>(`/wiki/telemetry/refresh${suffix}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiTelemetrySchedule(token: string): Promise<WikiTelemetrySchedule> {
  return request<WikiTelemetrySchedule>("/wiki/telemetry/schedule", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiTelemetryRetention(token: string): Promise<WikiTelemetryRetention> {
  return request<WikiTelemetryRetention>("/wiki/telemetry/retention", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function pruneWikiTelemetry(token: string): Promise<WikiTelemetryPruneResponse> {
  return request<WikiTelemetryPruneResponse>("/wiki/telemetry/prune", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function exportWikiTelemetrySeries(
  token: string,
  params: {
    dimensionType?: string | null;
    dimensionKey?: string | null;
    days?: number | null;
    granularity?: string | null;
  } = {},
): Promise<Blob> {
  const query = new URLSearchParams();
  if (params.dimensionType) {
    query.set("dimension_type", params.dimensionType);
  }
  if (params.dimensionKey) {
    query.set("dimension_key", params.dimensionKey);
  }
  if (params.days != null) {
    query.set("days", String(params.days));
  }
  if (params.granularity) {
    query.set("granularity", params.granularity);
  }

  const suffix = query.toString() ? `?${query.toString()}` : "";
  return requestBlob(`/wiki/telemetry/series/export${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiConversationMetricsSummary(
  token: string,
  params: { days?: number | null } = {},
): Promise<WikiConversationMetricsSummary> {
  const query = new URLSearchParams();
  if (params.days != null) {
    query.set("days", String(params.days));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiConversationMetricsSummary>(`/wiki/conversations/metrics/summary${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiConversationMetricsSeries(
  token: string,
  params: {
    dimensionType?: string | null;
    dimensionKey?: string | null;
    days?: number | null;
    granularity?: string | null;
  } = {},
): Promise<WikiConversationMetricsSeriesResponse> {
  const query = new URLSearchParams();
  if (params.dimensionType) {
    query.set("dimension_type", params.dimensionType);
  }
  if (params.dimensionKey) {
    query.set("dimension_key", params.dimensionKey);
  }
  if (params.days != null) {
    query.set("days", String(params.days));
  }
  if (params.granularity) {
    query.set("granularity", params.granularity);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiConversationMetricsSeriesResponse>(`/wiki/conversations/metrics/series${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiConversations(
  token: string,
  params: {
    limit?: number;
    search?: string | null;
    status?: string | null;
    priority?: string | null;
    assignedTo?: string | null;
    reviewReason?: string | null;
    needsReview?: boolean | null;
    createdBy?: string | null;
    contextArticle?: string | null;
  } = {},
): Promise<WikiConversationSummary[]> {
  const query = new URLSearchParams();
  if (params.limit != null) {
    query.set("limit", String(params.limit));
  }
  if (params.search) {
    query.set("search", params.search);
  }
  if (params.status) {
    query.set("status", params.status);
  }
  if (params.priority) {
    query.set("priority", params.priority);
  }
  if (params.assignedTo) {
    query.set("assigned_to", params.assignedTo);
  }
  if (params.reviewReason) {
    query.set("review_reason", params.reviewReason);
  }
  if (params.needsReview != null) {
    query.set("needs_review", String(params.needsReview));
  }
  if (params.createdBy) {
    query.set("created_by", params.createdBy);
  }
  if (params.contextArticle) {
    query.set("context_article", params.contextArticle);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiConversationSummary[]>(`/wiki/conversations${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiConversationSummary(
  token: string,
): Promise<WikiConversationSummaryMetrics> {
  return request<WikiConversationSummaryMetrics>("/wiki/conversations/summary", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiConversationDetail(token: string, conversationId: string): Promise<WikiConversation> {
  return request<WikiConversation>(`/wiki/conversations/${conversationId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updateWikiConversation(
  token: string,
  conversationId: string,
  payload: Partial<Pick<WikiConversationSummary, "status" | "priority" | "assigned_to">>,
): Promise<WikiConversation> {
  return request<WikiConversation>(`/wiki/conversations/${conversationId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function resolveWikiConversationContextLink(
  token: string,
  params: {
    entityKey?: string | null;
    moduleKey?: string | null;
  } = {},
): Promise<WikiConversationContextLink> {
  const query = new URLSearchParams();
  if (params.entityKey) {
    query.set("entity_key", params.entityKey);
  }
  if (params.moduleKey) {
    query.set("module_key", params.moduleKey);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiConversationContextLink>(`/wiki/conversations/context-link${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiConversationGovernanceConfig(token: string): Promise<WikiConversationGovernanceConfig> {
  return request<WikiConversationGovernanceConfig>("/wiki/conversations/governance-config", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updateWikiConversationGovernanceConfig(
  token: string,
  payload: {
    fallback_heavy_threshold?: number;
    no_match_repeated_threshold?: number;
    high_latency_ms_threshold?: number;
  },
): Promise<WikiConversationGovernanceConfig> {
  return request<WikiConversationGovernanceConfig>("/wiki/conversations/governance-config", {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function backfillWikiConversationMetrics(
  token: string,
  payload: {
    start_date: string;
    end_date: string;
    data_complete_from?: string | null;
  },
): Promise<WikiConversationGovernanceConfig> {
  return request<WikiConversationGovernanceConfig>("/wiki/conversations/metrics/backfill", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function enqueueWikiConversationMetricsBackfill(
  token: string,
  payload: {
    start_date: string;
    end_date: string;
    data_complete_from?: string | null;
  },
): Promise<WikiConversationMetricsBackfillJob> {
  return request<WikiConversationMetricsBackfillJob>("/wiki/conversations/metrics/backfill-jobs", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getLatestWikiConversationMetricsBackfillJob(
  token: string,
): Promise<WikiConversationMetricsBackfillJob | null> {
  return request<WikiConversationMetricsBackfillJob | null>("/wiki/conversations/metrics/backfill-jobs/latest", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listWikiConversationMetricsBackfillJobChains(
  token: string,
  limit = 10,
  filters: {
    latestStatus?: string;
    requestedBy?: string;
    hasActiveRetry?: boolean;
    sortBy?: string;
  } = {},
): Promise<WikiConversationMetricsBackfillJobChainListResponse> {
  const query = new URLSearchParams();
  query.set("limit", String(limit));
  if (filters.latestStatus) {
    query.set("latest_status", filters.latestStatus);
  }
  if (filters.requestedBy) {
    query.set("requested_by", filters.requestedBy);
  }
  if (filters.hasActiveRetry != null) {
    query.set("has_active_retry", String(filters.hasActiveRetry));
  }
  if (filters.sortBy) {
    query.set("sort_by", filters.sortBy);
  }
  return request<WikiConversationMetricsBackfillJobChainListResponse>(
    `/wiki/conversations/metrics/backfill-job-chains?${query.toString()}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );
}

export async function getWikiConversationMetricsBackfillJobChainSummary(
  token: string,
  filters: {
    latestStatus?: string;
    requestedBy?: string;
    hasActiveRetry?: boolean;
    sortBy?: string;
  } = {},
): Promise<WikiConversationMetricsBackfillJobChainSummary> {
  const query = new URLSearchParams();
  if (filters.latestStatus) {
    query.set("latest_status", filters.latestStatus);
  }
  if (filters.requestedBy) {
    query.set("requested_by", filters.requestedBy);
  }
  if (filters.hasActiveRetry != null) {
    query.set("has_active_retry", String(filters.hasActiveRetry));
  }
  if (filters.sortBy) {
    query.set("sort_by", filters.sortBy);
  }
  const queryString = query.toString();
  return request<WikiConversationMetricsBackfillJobChainSummary>(
    `/wiki/conversations/metrics/backfill-job-chains/summary${queryString ? `?${queryString}` : ""}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );
}

export async function getWikiConversationMetricsBackfillJobChainDetail(
  token: string,
  rootJobId: string,
): Promise<WikiConversationMetricsBackfillJobChainDetail> {
  return request<WikiConversationMetricsBackfillJobChainDetail>(
    `/wiki/conversations/metrics/backfill-job-chains/${encodeURIComponent(rootJobId)}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );
}

export async function retryWikiConversationMetricsBackfillJob(
  token: string,
  jobId: string,
): Promise<WikiConversationMetricsBackfillJob> {
  return request<WikiConversationMetricsBackfillJob>(
    `/wiki/conversations/metrics/backfill-jobs/${encodeURIComponent(jobId)}/retry`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );
}

export async function clearWikiConversationMetricsBackfillJobHistory(
  token: string,
): Promise<WikiConversationMetricsBackfillJobPruneResponse> {
  return request<WikiConversationMetricsBackfillJobPruneResponse>("/wiki/conversations/metrics/backfill-jobs", {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createApplicationUser(token: string, payload: ApplicationUserCreateInput): Promise<ApplicationUser> {
  return request<ApplicationUser>("/admin/users", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function updateApplicationUser(
  token: string,
  userId: number,
  payload: ApplicationUserUpdateInput,
): Promise<ApplicationUser> {
  return request<ApplicationUser>(`/admin/users/${userId}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function deleteApplicationUser(token: string, userId: number): Promise<void> {
  await request<null>(`/admin/users/${userId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNasGroups(token: string): Promise<NasGroup[]> {
  return request<NasGroup[]>("/nas-groups", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkDashboard(token: string): Promise<NetworkDashboardSummary> {
  return request<NetworkDashboardSummary>("/network/dashboard", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkStatistics(
  token: string,
  params: { windowHours?: number } = {},
): Promise<NetworkStatisticsSummary> {
  const query = new URLSearchParams();
  if (params.windowHours != null) {
    query.set("window_hours", String(params.windowHours));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<NetworkStatisticsSummary>(`/network/statistics${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkDevices(
  token: string,
  params?: {
    search?: string;
    status?: string;
    lifecycle?: string;
    assignment?: string;
    known?: string;
    vendor?: string;
    deviceType?: string;
    page?: number;
    pageSize?: number;
  },
): Promise<NetworkDeviceListResponse> {
  const query = new URLSearchParams();
  if (params?.search) {
    query.set("search", params.search);
  }
  if (params?.status) {
    query.set("status", params.status);
  }
  if (params?.lifecycle) {
    query.set("lifecycle", params.lifecycle);
  }
  if (params?.assignment) {
    query.set("assignment", params.assignment);
  }
  if (params?.known) {
    query.set("known", params.known);
  }
  if (params?.vendor) {
    query.set("vendor", params.vendor);
  }
  if (params?.deviceType) {
    query.set("device_type", params.deviceType);
  }
  if (params?.page) {
    query.set("page", String(params.page));
  }
  if (params?.pageSize) {
    query.set("page_size", String(params.pageSize));
  }

  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<NetworkDeviceListResponse>(`/network/devices${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkDevice(token: string, deviceId: number): Promise<NetworkDevice> {
  return request<NetworkDevice>(`/network/devices/${deviceId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listNetworkDeviceAssignees(token: string): Promise<NetworkAssignedUserSummary[]> {
  return request<NetworkAssignedUserSummary[]>("/network/device-assignees", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listNetworkTrackedSubjects(
  token: string,
  params?: { includeInactive?: boolean; includeInferred?: boolean; windowHours?: number; search?: string; entityType?: string },
): Promise<NetworkTrackedSubject[]> {
  const query = new URLSearchParams();
  if (params?.includeInactive) {
    query.set("include_inactive", "true");
  }
  if (params?.includeInferred) {
    query.set("include_inferred", "true");
  }
  if (params?.windowHours != null) {
    query.set("window_hours", String(params.windowHours));
  }
  if (params?.search) {
    query.set("search", params.search);
  }
  if (params?.entityType) {
    query.set("entity_type", params.entityType);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<NetworkTrackedSubject[]>(`/network/tracking${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createNetworkTrackedSubject(
  token: string,
  payload: NetworkTrackedSubjectCreateInput,
): Promise<NetworkTrackedSubject> {
  return request<NetworkTrackedSubject>("/network/tracking", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function updateNetworkTrackedSubject(
  token: string,
  subjectId: number,
  payload: NetworkTrackedSubjectUpdateInput,
): Promise<NetworkTrackedSubject> {
  return request<NetworkTrackedSubject>(`/network/tracking/${subjectId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getNetworkIpWhois(token: string, ipAddress: string): Promise<NetworkIpWhois> {
  return request<NetworkIpWhois>(`/network/ip-whois/${encodeURIComponent(ipAddress)}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkTrackedSubjectActivities(
  token: string,
  subjectId: number,
  params?: { windowHours?: number; limit?: number },
): Promise<NetworkTrackedSubjectActivitySummary> {
  const query = new URLSearchParams();
  if (params?.windowHours != null) {
    query.set("window_hours", String(params.windowHours));
  }
  if (params?.limit != null) {
    query.set("limit", String(params.limit));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<NetworkTrackedSubjectActivitySummary>(`/network/tracking/${subjectId}/activities${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkDetectionWatchlist(token: string): Promise<NetworkDetectionWatchlistRule[]> {
  return request<NetworkDetectionWatchlistRule[]>("/network/detection-watchlist", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createNetworkDetectionWatchlistRule(
  token: string,
  payload: NetworkDetectionWatchlistRuleCreateInput,
): Promise<NetworkDetectionWatchlistRule> {
  return request<NetworkDetectionWatchlistRule>("/network/detection-watchlist", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function updateNetworkDetectionWatchlistRule(
  token: string,
  ruleId: number,
  payload: NetworkDetectionWatchlistRuleUpdateInput,
): Promise<NetworkDetectionWatchlistRule> {
  return request<NetworkDetectionWatchlistRule>(`/network/detection-watchlist/${ruleId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getNetworkVpnBypassSummary(
  token: string,
  params?: { windowHours?: number },
): Promise<NetworkVpnBypassSummary> {
  const query = new URLSearchParams();
  if (params?.windowHours != null) {
    query.set("window_hours", String(params.windowHours));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<NetworkVpnBypassSummary>(`/network/vpn-bypass/summary${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkVpnBypassArpTimeline(
  token: string,
  params?: { windowHours?: number; limit?: number },
): Promise<NetworkArpTimelineItem[]> {
  const query = new URLSearchParams();
  if (params?.windowHours != null) {
    query.set("window_hours", String(params.windowHours));
  }
  if (params?.limit != null) {
    query.set("limit", String(params.limit));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<NetworkArpTimelineItem[]>(`/network/vpn-bypass/arp-timeline${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updateNetworkDevice(
  token: string,
  deviceId: number,
  payload: NetworkDeviceUpdateInput,
): Promise<NetworkDevice> {
  return request<NetworkDevice>(`/network/devices/${deviceId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function bulkUpdateNetworkDevices(
  token: string,
  payload: NetworkDeviceBulkUpdateInput,
): Promise<NetworkDeviceBulkUpdateResponse> {
  return request<NetworkDeviceBulkUpdateResponse>("/network/devices/bulk-update", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getNetworkAlerts(token: string): Promise<NetworkAlert[]> {
  return request<NetworkAlert[]>("/network/alerts", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkFirewalls(token: string): Promise<NetworkFirewall[]> {
  return request<NetworkFirewall[]>("/network/firewalls", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkFirewallEvents(
  token: string,
  firewallId: number,
  params?: { severity?: string; limit?: number },
): Promise<NetworkFirewallEvent[]> {
  const query = new URLSearchParams();
  if (params?.severity) {
    query.set("severity", params.severity);
  }
  if (params?.limit) {
    query.set("limit", String(params.limit));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<NetworkFirewallEvent[]>(`/network/firewalls/${firewallId}/events${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkFirewallLogCoverage(
  token: string,
  firewallId: number,
  params: { windowHours?: number } = {},
): Promise<NetworkFirewallLogCoverageSummary> {
  const query = new URLSearchParams();
  if (params.windowHours) {
    query.set("window_hours", String(params.windowHours));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<NetworkFirewallLogCoverageSummary>(`/network/firewalls/${firewallId}/log-coverage${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkFirewallMetrics(
  token: string,
  firewallId: number,
  params?: { metricKey?: string; limit?: number },
): Promise<NetworkFirewallMetric[]> {
  const query = new URLSearchParams();
  if (params?.metricKey) {
    query.set("metric_key", params.metricKey);
  }
  if (params?.limit) {
    query.set("limit", String(params.limit));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<NetworkFirewallMetric[]>(`/network/firewalls/${firewallId}/metrics${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function pollNetworkFirewallMetrics(token: string, firewallId: number): Promise<NetworkFirewallMetric[]> {
  return request<NetworkFirewallMetric[]>(`/network/firewalls/${firewallId}/metrics/poll`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updateNetworkAlert(
  token: string,
  alertId: number,
  payload: NetworkAlertUpdateInput,
): Promise<NetworkAlert> {
  return request<NetworkAlert>(`/network/alerts/${alertId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getNetworkScans(token: string): Promise<NetworkScan[]> {
  return request<NetworkScan[]>("/network/scans", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkScan(token: string, scanId: number): Promise<NetworkScanDetail> {
  return request<NetworkScanDetail>(`/network/scans/${scanId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkScanDiff(token: string, scanId: number, otherScanId: number): Promise<NetworkScanDiff> {
  return request<NetworkScanDiff>(`/network/scans/${scanId}/diff/${otherScanId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function triggerNetworkScan(
  token: string,
  payload?: NetworkScanTriggerInput,
): Promise<NetworkScanTriggerResponse> {
  return request<NetworkScanTriggerResponse>("/network/scans", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: payload ? JSON.stringify(payload) : undefined,
  });
}

export async function getNetworkFloorPlans(token: string): Promise<NetworkFloorPlan[]> {
  return request<NetworkFloorPlan[]>("/network/floor-plans", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createNetworkFloorPlan(
  token: string,
  payload: NetworkFloorPlanCreateInput,
): Promise<NetworkFloorPlan> {
  return request<NetworkFloorPlan>("/network/floor-plans", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getNetworkFloorPlan(token: string, floorPlanId: number): Promise<NetworkFloorPlanDetail> {
  return request<NetworkFloorPlanDetail>(`/network/floor-plans/${floorPlanId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkFloorPlanDevices(
  token: string,
  floorPlanId: number,
): Promise<NetworkFloorPlanDevice[]> {
  return request<NetworkFloorPlanDevice[]>(`/network/floor-plans/${floorPlanId}/devices`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updateNetworkDevicePosition(
  token: string,
  deviceId: number,
  payload: DevicePositionUpdateInput,
): Promise<DevicePosition> {
  return request<DevicePosition>(`/network/devices/${deviceId}/position`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getAnagraficaStats(token: string): Promise<AnagraficaStats> {
  return request<AnagraficaStats>("/utenze/stats", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const getUtenzeStats = getAnagraficaStats;

export async function getAnagraficaDocumentSummary(token: string): Promise<AnagraficaDocumentSummary> {
  return request<AnagraficaDocumentSummary>("/utenze/documents/summary", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const getUtenzeDocumentSummary = getAnagraficaDocumentSummary;

export async function getAnagraficaSubjects(
  token: string,
  params?: {
    page?: number;
    pageSize?: number;
    search?: string;
    subjectType?: string;
    status?: string;
    letter?: string;
    requiresReview?: boolean;
  },
): Promise<AnagraficaSubjectListResponse> {
  const query = new URLSearchParams();
  if (params?.page) query.set("page", String(params.page));
  if (params?.pageSize) query.set("page_size", String(params.pageSize));
  if (params?.search) query.set("search", params.search);
  if (params?.subjectType) query.set("subject_type", params.subjectType);
  if (params?.status) query.set("status", params.status);
  if (params?.letter) query.set("letter", params.letter);
  if (typeof params?.requiresReview === "boolean") query.set("requires_review", String(params.requiresReview));
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<AnagraficaSubjectListResponse>(`/utenze/subjects${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const getUtenzeSubjects = getAnagraficaSubjects;

export async function getAnagraficaSubject(token: string, subjectId: string): Promise<AnagraficaSubjectDetail> {
  return request<AnagraficaSubjectDetail>(`/utenze/subjects/${subjectId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const getUtenzeSubject = getAnagraficaSubject;

export async function createAnagraficaSubject(
  token: string,
  payload: AnagraficaSubjectCreateInput,
): Promise<AnagraficaSubjectDetail> {
  return request<AnagraficaSubjectDetail>("/utenze/subjects", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export const createUtenzeSubject = createAnagraficaSubject;

export async function importAnagraficaSubjectsCsv(
  token: string,
  file: File,
  onProgress?: (percent: number) => void,
): Promise<AnagraficaCsvImportResult> {
  const formData = new FormData();
  formData.append("file", file);

  return requestFormDataWithUploadProgress<AnagraficaCsvImportResult>(
    "/utenze/subjects/import-csv",
    formData,
    token,
    onProgress,
  );
}

export const importUtenzeSubjectsCsv = importAnagraficaSubjectsCsv;

export async function importUtenzeSubjectsXlsx(
  token: string,
  file: File,
  onProgress?: (percent: number) => void,
): Promise<XlsxImportStartResult> {
  const formData = new FormData();
  formData.append("file", file);

  return requestFormDataWithUploadProgress<XlsxImportStartResult>(
    "/utenze/subjects/import-xlsx",
    formData,
    token,
    onProgress,
  );
}

export async function getUtenzeXlsxImportBatch(token: string, batchId: string): Promise<XlsxImportBatch> {
  return request<XlsxImportBatch>(`/utenze/xlsx-import-batches/${batchId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getUtenzeXlsxImportBatches(token: string): Promise<XlsxImportBatch[]> {
  return request<XlsxImportBatch[]>("/utenze/xlsx-import-batches", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getUtenzeSubjectAuditLog(token: string, subjectId: string): Promise<UtenzeAuditLog[]> {
  return request<UtenzeAuditLog[]>(`/utenze/subjects/${subjectId}/audit-log`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getUtenzeSubjectPaymentNotices(token: string, subjectId: string): Promise<AnagraficaPaymentNotice[]> {
  return request<AnagraficaPaymentNotice[]>(`/utenze/subjects/${subjectId}/payment-notices`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getUtenzeAnprStatus(token: string, subjectId: string): Promise<AnprSubjectStatus> {
  return request<AnprSubjectStatus>(`/utenze/anpr/sync/${subjectId}/status`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function syncUtenzeAnprSubject(token: string, subjectId: string): Promise<AnprSyncResult> {
  return request<AnprSyncResult>(`/utenze/anpr/sync/${subjectId}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function previewLookupUtenzeAnprByCf(token: string, codiceFiscale: string): Promise<AnprPreviewLookupResponse> {
  return request<AnprPreviewLookupResponse>("/utenze/anpr/preview-lookup", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ codice_fiscale: codiceFiscale.trim() }),
  });
}

export async function getUtenzeAnprConfig(token: string): Promise<AnprSyncConfig> {
  return request<AnprSyncConfig>("/utenze/anpr/config", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function updateUtenzeAnprConfig(
  token: string,
  payload: AnprSyncConfigUpdateInput,
): Promise<AnprSyncConfig> {
  return request<AnprSyncConfig>("/utenze/anpr/config", {
    method: "PUT",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export async function getUtenzeAnprJobStatus(token: string): Promise<AnprJobTriggerResult> {
  return request<AnprJobTriggerResult>("/utenze/anpr/job/status", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function triggerUtenzeAnprJob(token: string): Promise<AnprJobTriggerResult> {
  return request<AnprJobTriggerResult>("/utenze/anpr/job/trigger", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function updateAnagraficaSubject(
  token: string,
  subjectId: string,
  payload: AnagraficaSubjectUpdateInput,
): Promise<AnagraficaSubjectDetail> {
  return request<AnagraficaSubjectDetail>(`/utenze/subjects/${subjectId}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export const updateUtenzeSubject = updateAnagraficaSubject;

export async function deactivateAnagraficaSubject(token: string, subjectId: string): Promise<AnagraficaSubjectDetail> {
  return request<AnagraficaSubjectDetail>(`/utenze/subjects/${subjectId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const deactivateUtenzeSubject = deactivateAnagraficaSubject;

export async function getAnagraficaSubjectDocuments(token: string, subjectId: string): Promise<AnagraficaDocument[]> {
  return request<AnagraficaDocument[]>(`/utenze/subjects/${subjectId}/documents`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const getUtenzeSubjectDocuments = getAnagraficaSubjectDocuments;

export async function updateAnagraficaDocument(
  token: string,
  documentId: string,
  payload: { doc_type?: string; notes?: string },
): Promise<AnagraficaDocument> {
  return request<AnagraficaDocument>(`/utenze/documents/${documentId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export const updateUtenzeDocument = updateAnagraficaDocument;

export async function deleteAnagraficaDocument(token: string, documentId: string, deletePassword?: string): Promise<void> {
  await fetch(`${getApiBaseUrl()}/utenze/documents/${documentId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
      ...(deletePassword ? { "X-GAIA-Delete-Password": deletePassword } : {}),
    },
    cache: "no-store",
  }).then(async (response) => {
    if (!response.ok) {
      let detail = response.statusText || "Request failed";
      try {
        const payload = (await response.json()) as { detail?: unknown };
        if (typeof payload.detail === "string") detail = payload.detail;
      } catch {}
      throw new ApiError(detail, undefined, response.status);
    }
  });
}

export const deleteUtenzeDocument = deleteAnagraficaDocument;

export async function downloadAnagraficaDocumentBlob(token: string, documentId: string): Promise<Blob> {
  return requestBlob(`/utenze/documents/${documentId}/download`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const downloadUtenzeDocumentBlob = downloadAnagraficaDocumentBlob;

export async function downloadAnagraficaExportBlob(
  token: string,
  params?: {
    format?: "csv" | "xlsx";
    search?: string;
    subjectType?: string;
    status?: string;
    letter?: string;
    requiresReview?: boolean;
  },
): Promise<Blob> {
  const query = new URLSearchParams();
  query.set("format", params?.format ?? "csv");
  if (params?.search) query.set("search", params.search);
  if (params?.subjectType) query.set("subject_type", params.subjectType);
  if (params?.status) query.set("status", params.status);
  if (params?.letter) query.set("letter", params.letter);
  if (typeof params?.requiresReview === "boolean") query.set("requires_review", String(params.requiresReview));
  return requestBlob(`/utenze/export?${query.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const downloadUtenzeExportBlob = downloadAnagraficaExportBlob;

export async function previewAnagraficaImport(token: string, letter?: string): Promise<AnagraficaImportPreview> {
  return request<AnagraficaImportPreview>("/utenze/import/preview", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(letter ? { letter } : {}),
  });
}

export const previewUtenzeImport = previewAnagraficaImport;

export async function runAnagraficaImport(token: string, letter?: string): Promise<AnagraficaImportRunResult> {
  return request<AnagraficaImportRunResult>("/utenze/import/run", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(letter ? { letter } : {}),
  });
}

export const runUtenzeImport = runAnagraficaImport;

export async function runAnagraficaImportFromSubjects(token: string): Promise<AnagraficaImportRunResult> {
  return request<AnagraficaImportRunResult>("/utenze/import/run-from-subjects", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const runUtenzeImportFromSubjects = runAnagraficaImportFromSubjects;

export async function getAnagraficaImportJobs(token: string): Promise<AnagraficaImportJob[]> {
  return request<AnagraficaImportJob[]>("/utenze/import/jobs", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const getUtenzeImportJobs = getAnagraficaImportJobs;

export async function getUtenzeVisureRoutingAnomalies(
  token: string,
  params?: {
    resolved?: boolean;
    search?: string;
    page?: number;
    pageSize?: number;
  },
): Promise<AnagraficaVisuraRoutingAnomalyListResponse> {
  const query = new URLSearchParams();
  if (typeof params?.resolved === "boolean") query.set("resolved", String(params.resolved));
  if (params?.search) query.set("search", params.search);
  if (params?.page) query.set("page", String(params.page));
  if (params?.pageSize) query.set("page_size", String(params.pageSize));
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<AnagraficaVisuraRoutingAnomalyListResponse>(`/utenze/visure-routing-anomalies${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getAnagraficaImportJob(token: string, jobId: string): Promise<AnagraficaImportJob> {
  return request<AnagraficaImportJob>(`/utenze/import/jobs/${jobId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const getUtenzeImportJob = getAnagraficaImportJob;

export async function resolveUtenzeVisureRoutingAnomaly(
  token: string,
  anomalyId: string,
): Promise<AnagraficaVisuraRoutingAnomaly> {
  return request<AnagraficaVisuraRoutingAnomaly>(`/utenze/visure-routing-anomalies/${anomalyId}/resolve`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function abortUtenzeRegistryImportJob(token: string, jobId: string): Promise<AnagraficaImportJob> {
  return request<AnagraficaImportJob>(`/utenze/import/jobs/${jobId}/abort-registry`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function resumeUtenzeRegistryImportJob(token: string, jobId: string): Promise<AnagraficaImportRunResult> {
  return request<AnagraficaImportRunResult>(`/utenze/import/jobs/${jobId}/resume-registry`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export type RegistryImportJobDeletedResponse = { deleted: boolean };

export async function deleteUtenzeRegistryImportJob(token: string, jobId: string): Promise<RegistryImportJobDeletedResponse> {
  return request<RegistryImportJobDeletedResponse>(`/utenze/import/jobs/${jobId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function resumeAnagraficaImportJob(token: string, jobId: string): Promise<AnagraficaImportRunResult> {
  return request<AnagraficaImportRunResult>(`/utenze/import/jobs/${jobId}/resume`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const resumeUtenzeImportJob = resumeAnagraficaImportJob;

export async function searchAnagraficaSubjects(token: string, queryText: string, limit = 20): Promise<AnagraficaSearchResult> {
  const query = new URLSearchParams({ q: queryText, limit: String(limit) });
  return request<AnagraficaSearchResult>(`/utenze/search?${query.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const searchUtenzeSubjects = searchAnagraficaSubjects;

export async function importAnagraficaSubjectFromNas(token: string, subjectId: string): Promise<AnagraficaSubjectImportResult> {
  return request<AnagraficaSubjectImportResult>(`/utenze/subjects/${subjectId}/import-from-nas`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const importUtenzeSubjectFromNas = importAnagraficaSubjectFromNas;

export async function getAnagraficaSubjectNasCandidates(
  token: string,
  subjectId: string,
  limit = 20,
): Promise<AnagraficaNasFolderCandidate[]> {
  const query = new URLSearchParams({ limit: String(limit) });
  return request<AnagraficaNasFolderCandidate[]>(`/utenze/subjects/${subjectId}/nas-candidates?${query.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const getUtenzeSubjectNasCandidates = getAnagraficaSubjectNasCandidates;

export async function getAnagraficaSubjectNasImportStatus(token: string, subjectId: string): Promise<AnagraficaSubjectNasImportStatus> {
  return request<AnagraficaSubjectNasImportStatus>(`/utenze/subjects/${subjectId}/nas-import-status`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const getUtenzeSubjectNasImportStatus = getAnagraficaSubjectNasImportStatus;

export async function uploadAnagraficaSubjectDocument(
  token: string,
  subjectId: string,
  file: File,
  docType: string,
  notes?: string,
): Promise<AnagraficaDocument> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("doc_type", docType);
  if (notes) {
    formData.append("notes", notes);
  }
  return request<AnagraficaDocument>(`/utenze/subjects/${subjectId}/documents/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });
}

export const uploadUtenzeSubjectDocument = uploadAnagraficaSubjectDocument;

export async function resetAnagraficaData(token: string, confirm = "RESET ANAGRAFICA"): Promise<AnagraficaResetResult> {
  return request<AnagraficaResetResult>("/utenze/reset", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ confirm }),
  });
}

export const resetUtenzeData = resetAnagraficaData;

export async function getReviews(token: string): Promise<Review[]> {
  return request<Review[]>("/reviews", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getSyncCapabilities(token: string): Promise<SyncCapabilities> {
  return request<SyncCapabilities>("/sync/capabilities", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function previewSync(
  token: string,
  payload: SyncPreviewRequest,
): Promise<SyncPreview> {
  return request<SyncPreview>("/sync/preview", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function applySync(
  token: string,
  payload: SyncPreviewRequest,
): Promise<SyncApplyResult> {
  return request<SyncApplyResult>("/sync/apply", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function createSyncJob(
  token: string,
  profile: "quick" | "full" = "quick",
): Promise<SyncJob> {
  return request<SyncJob>("/sync/jobs", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ profile }),
  });
}

export async function getSyncRuns(token: string): Promise<SyncRun[]> {
  return request<SyncRun[]>("/sync-runs", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getSyncJobs(token: string): Promise<SyncJob[]> {
  return request<SyncJob[]>("/sync/jobs", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function retrySyncJob(token: string, jobId: number): Promise<SyncJob> {
  return request<SyncJob>(`/sync/jobs/${jobId}/retry`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function cancelSyncJob(token: string, jobId: number): Promise<SyncJob> {
  return request<SyncJob>(`/sync/jobs/${jobId}/cancel`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getEffectivePermissions(token: string): Promise<EffectivePermission[]> {
  return request<EffectivePermission[]>("/effective-permissions", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function calculatePermissionPreview(
  token: string,
  users: PermissionUserInput[],
  permissionEntries: PermissionEntryInput[],
): Promise<EffectivePermissionPreview[]> {
  return request<EffectivePermissionPreview[]>("/permissions/calculate-preview", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      users,
      permission_entries: permissionEntries,
    }),
  });
}

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

export async function listCapacitasInCassSyncJobs(token: string): Promise<CapacitasInCassSyncJob[]> {
  return request<CapacitasInCassSyncJob[]>("/elaborazioni/capacitas/incass/avvisi/jobs", {
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

export async function createElaborazioneBatch(
  token: string,
  file: File,
  name?: string,
): Promise<ElaborazioneBatchDetail> {
  const formData = new FormData();
  formData.append("file", file);
  if (name) {
    formData.append("name", name);
  }

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
