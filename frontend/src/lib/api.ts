import type {
  AnagraficaCsvImportResult,
  AnagraficaDocument,
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
  ApplicationUser,
  ApplicationUserCreateInput,
  ApplicationUserListResponse,
  ApplicationUserUpdateInput,
  CatastoBatch,
  CatastoBatchDetail,
  CatastoCaptchaSummary,
  CatastoDocument,
  CatastoBatchWebSocketEvent,
  CatastoComune,
  CatastoCredential,
  CatastoCredentialTestResult,
  CatastoCredentialTestWebSocketEvent,
  CatastoCredentialStatus,
  CatastoOperationResponse,
  CatastoSingleVisuraPayload,
  CatastoVisuraRequest,
  CapacitasCredential,
  CapacitasCredentialCreateInput,
  CapacitasCredentialTestResult as CapacitasCredentialProbeResult,
  CapacitasCredentialUpdateInput,
  CapacitasSearchInput,
  CapacitasSearchResult,
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
  const value = process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL;
  return value.replace(/\/+$/, "");
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
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

async function requestBlob(path: string, init?: RequestInit): Promise<Blob> {
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

async function requestFormDataWithUploadProgress<T>(
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

function createQueryString(params: Record<string, string | undefined>): string {
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

export async function getCatastoCredentials(token: string): Promise<CatastoCredentialStatus> {
  return request<CatastoCredentialStatus>("/catasto/credentials", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function saveCatastoCredentials(
  token: string,
  payload: {
    sister_username: string;
    sister_password: string;
    convenzione?: string;
    codice_richiesta?: string;
    ufficio_provinciale?: string;
  },
): Promise<CatastoCredential> {
  return request<CatastoCredential>("/catasto/credentials", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function deleteCatastoCredentials(token: string): Promise<CatastoOperationResponse> {
  return request<CatastoOperationResponse>("/catasto/credentials", {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function testCatastoCredentials(
  token: string,
  payload?: {
    sister_username: string;
    sister_password: string;
    convenzione?: string;
    codice_richiesta?: string;
    ufficio_provinciale?: string;
  },
): Promise<CatastoCredentialTestResult> {
  return request<CatastoCredentialTestResult>("/catasto/credentials/test", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: payload ? JSON.stringify(payload) : undefined,
  });
}

export async function getCatastoCredentialTest(
  token: string,
  testId: string,
): Promise<CatastoCredentialTestResult> {
  return request<CatastoCredentialTestResult>(`/catasto/credentials/test/${testId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export function createCatastoCredentialTestWebSocket(testId: string, token: string): WebSocket | null {
  if (typeof window === "undefined") {
    return null;
  }

  const url = new URL(`${getWebSocketBaseUrl()}/catasto/ws/credentials-test/${testId}`);
  url.searchParams.set("token", token);
  return new WebSocket(url.toString());
}

export async function listCapacitasCredentials(token: string): Promise<CapacitasCredential[]> {
  return request<CapacitasCredential[]>("/catasto/capacitas/credentials", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createCapacitasCredential(
  token: string,
  payload: CapacitasCredentialCreateInput,
): Promise<CapacitasCredential> {
  return request<CapacitasCredential>("/catasto/capacitas/credentials", {
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
  return request<CapacitasCredential>(`/catasto/capacitas/credentials/${credentialId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function deleteCapacitasCredential(token: string, credentialId: number): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/catasto/capacitas/credentials/${credentialId}`, {
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
  return request<CapacitasCredentialProbeResult>(`/catasto/capacitas/credentials/${credentialId}/test`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function searchCapacitasInvolture(
  token: string,
  payload: CapacitasSearchInput,
): Promise<CapacitasSearchResult> {
  return request<CapacitasSearchResult>("/catasto/capacitas/involture/search", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getCatastoComuni(token: string, search?: string): Promise<CatastoComune[]> {
  const query = createQueryString({ search });
  return request<CatastoComune[]>(`/catasto/comuni${query}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createCatastoBatch(
  token: string,
  file: File,
  name?: string,
): Promise<CatastoBatchDetail> {
  const formData = new FormData();
  formData.append("file", file);
  if (name) {
    formData.append("name", name);
  }

  return request<CatastoBatchDetail>("/catasto/batches", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });
}

export async function getCatastoBatches(token: string, status?: string): Promise<CatastoBatch[]> {
  const query = createQueryString({ status });
  return request<CatastoBatch[]>(`/catasto/batches${query}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getCatastoBatch(token: string, batchId: string): Promise<CatastoBatchDetail> {
  return request<CatastoBatchDetail>(`/catasto/batches/${batchId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function startCatastoBatch(token: string, batchId: string): Promise<CatastoBatch> {
  return request<CatastoBatch>(`/catasto/batches/${batchId}/start`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function cancelCatastoBatch(token: string, batchId: string): Promise<CatastoBatch> {
  return request<CatastoBatch>(`/catasto/batches/${batchId}/cancel`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function retryFailedCatastoBatch(token: string, batchId: string): Promise<CatastoBatch> {
  return request<CatastoBatch>(`/catasto/batches/${batchId}/retry-failed`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createCatastoSingleVisura(
  token: string,
  payload: CatastoSingleVisuraPayload,
): Promise<CatastoBatchDetail> {
  return request<CatastoBatchDetail>("/catasto/visure", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getPendingCatastoCaptcha(token: string): Promise<CatastoVisuraRequest[]> {
  return request<CatastoVisuraRequest[]>("/catasto/captcha/pending", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getCatastoCaptchaSummary(token: string): Promise<CatastoCaptchaSummary> {
  return request<CatastoCaptchaSummary>("/catasto/captcha/summary", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function solveCatastoCaptcha(
  token: string,
  requestId: string,
  text: string,
): Promise<CatastoVisuraRequest> {
  return request<CatastoVisuraRequest>(`/catasto/captcha/${requestId}/solve`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ text }),
  });
}

export async function skipCatastoCaptcha(token: string, requestId: string): Promise<CatastoVisuraRequest> {
  return request<CatastoVisuraRequest>(`/catasto/captcha/${requestId}/skip`, {
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

export async function fetchCatastoCaptchaImageBlob(token: string, requestId: string): Promise<Blob> {
  return requestBlob(`/catasto/captcha/${requestId}/image`, {
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

export async function downloadCatastoBatchZipBlob(token: string, batchId: string): Promise<Blob> {
  return requestBlob(`/catasto/batches/${batchId}/download`, {
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

export function createCatastoBatchWebSocket(batchId: string, token: string): WebSocket | null {
  if (typeof window === "undefined") {
    return null;
  }

  const url = new URL(`${getWebSocketBaseUrl()}/catasto/ws/${batchId}`);
  url.searchParams.set("token", token);
  return new WebSocket(url.toString());
}

export type { CatastoBatchWebSocketEvent };
export type { CatastoCredentialTestWebSocketEvent };
