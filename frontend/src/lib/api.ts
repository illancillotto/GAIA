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
  AnagraficaResetResult,
  AnagraficaSearchResult,
  AnagraficaStats,
  AnagraficaSubjectCreateInput,
  AnagraficaSubjectDetail,
  AnagraficaSubjectNasImportStatus,
  AnagraficaSubjectImportResult,
  AnagraficaSubjectListResponse,
  AnagraficaSubjectUpdateInput,
  AnprJobTriggerResult,
  AnprSyncConfig,
  AnprSyncConfigUpdateInput,
  AnprSubjectStatus,
  AnprSyncResult,
  ApplicationUser,
  ApplicationUserCreateInput,
  ApplicationUserListResponse,
  ApplicationUserUpdateInput,
  CatastoDocument,
  CatastoComune,
  ElaborazioneBatch,
  ElaborazioneBatchDetail,
  ElaborazioneCaptchaSummary,
  ElaborazioneCredential,
  ElaborazioneCredentialStatus,
  ElaborazioneCredentialTestResult,
  ElaborazioneOperationResponse,
  ElaborazioneRichiesta,
  ElaborazioneRichiestaCreateInput,
  CapacitasCredential,
  CapacitasCredentialCreateInput,
  CapacitasCredentialTestResult as CapacitasCredentialProbeResult,
  CapacitasCredentialUpdateInput,
  CapacitasAnagraficaHistoryImportInput,
  CapacitasAnagraficaHistoryImportJob,
  CapacitasAnagraficaHistoryImportResult,
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
  LoginResponse,
  MyPermissionsResponse,
  NetworkAlert,
  NetworkAlertUpdateInput,
  NetworkDashboardSummary,
  NetworkDevice,
  NetworkDeviceListResponse,
  NetworkDeviceUpdateInput,
  DevicePositionUpdateInput,
  DevicePosition,
  NetworkFloorPlan,
  NetworkFloorPlanCreateInput,
  NetworkFloorPlanDevice,
  NetworkFloorPlanDetail,
  NetworkScan,
  NetworkScanDetail,
  NetworkScanDiff,
  NetworkScanTriggerResponse,
  NasGroup,
  NasUser,
  PermissionEntryInput,
  PermissionUserInput,
  Review,
  Share,
  SyncApplyResult,
  SyncCapabilities,
  SyncLiveApplyResult,
  SyncPreview,
  SyncPreviewRequest,
  SyncRun,
} from "@/types/api";

const DEFAULT_API_BASE_URL = "/api";

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

export async function listApplicationUsers(token: string): Promise<ApplicationUserListResponse> {
  return request<ApplicationUserListResponse>("/admin/users", {
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

export async function getNetworkDevices(
  token: string,
  params?: { search?: string; status?: string; page?: number; pageSize?: number },
): Promise<NetworkDeviceListResponse> {
  const query = new URLSearchParams();
  if (params?.search) {
    query.set("search", params.search);
  }
  if (params?.status) {
    query.set("status", params.status);
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

export async function getNetworkAlerts(token: string): Promise<NetworkAlert[]> {
  return request<NetworkAlert[]>("/network/alerts", {
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

export async function triggerNetworkScan(token: string): Promise<NetworkScanTriggerResponse> {
  return request<NetworkScanTriggerResponse>("/network/scans", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
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

export async function getAnagraficaImportJob(token: string, jobId: string): Promise<AnagraficaImportJob> {
  return request<AnagraficaImportJob>(`/utenze/import/jobs/${jobId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const getUtenzeImportJob = getAnagraficaImportJob;

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

export async function applyLiveSync(
  token: string,
  profile: "quick" | "full" = "quick",
): Promise<SyncLiveApplyResult> {
  return request<SyncLiveApplyResult>(`/sync/live-apply?profile=${profile}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getSyncRuns(token: string): Promise<SyncRun[]> {
  return request<SyncRun[]>("/sync-runs", {
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

export async function getElaborazioneBatch(token: string, batchId: string): Promise<ElaborazioneBatchDetail> {
  return request<ElaborazioneBatchDetail>(`/elaborazioni/batches/${batchId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
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
  ElaborazioneRichiesta,
  ElaborazioneRichiestaCreateInput,
} from "@/types/api";
