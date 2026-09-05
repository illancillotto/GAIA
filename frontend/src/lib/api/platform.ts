import type { ApplicationUser, ApplicationUserCreateInput, ApplicationUserInviteResponse, ApplicationUserListResponse, ApplicationUserUpdateInput, AuthProvidersResponse, GatePresenzeTeam, GatePresenzeTeamCreateInput, GatePresenzeTeamMembership, GatePresenzeTeamMembershipCreateInput, GatePresenzeRulesResponse, GatePresenzeTeamSupervisor, GatePresenzeTeamSupervisorCreateInput, GatePresenzeTeamUpdateInput, CurrentUser, DashboardSummary, LoginResponse, MePresenzeStatusResponse, MeStraordinariExportRequest, MeStraordinariPreviewResponse, MePresenzeSummaryResponse, MeModuleStatusResponse, MeOperazioniActivityListResponse, MeOperazioniCaseListResponse, MeOperazioniReportListResponse, MeOperazioniSummaryResponse, MeSummaryResponse, MeAssignedDeviceListResponse, MeVehicleAssignmentListResponse, MeVehicleUsageSessionListResponse, MyPermissionsResponse, PresenzeDailyRecord, PresenzeDailyRecordListResponse, OrgStructureAssignment, OrgStructureAssignmentUpdateInput, OrgStructureBootstrapResult, OrgStructureWorkspace, UserPermissionsAdminView, UserPresenceHeartbeatInput, UserPresenceHeartbeatResponse, UserPresenceSummary, NasGroup, NasUser, SectionResponse, Share } from "@/types/api";
import type { WikiArticleGroup } from "@/features/wiki/types";
import { request, requestBlob } from "./core";

export async function login(
  username: string,
  password: string,
  device?: { deviceId?: string | null; deviceLabel?: string | null },
): Promise<LoginResponse> {
  const body: { username: string; password: string; device_id?: string; device_label?: string } = { username, password };
  if (device?.deviceId) {
    body.device_id = device.deviceId;
  }
  if (device?.deviceLabel) {
    body.device_label = device.deviceLabel;
  }
  return request<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getAuthProviders(): Promise<AuthProvidersResponse> {
  return request<AuthProvidersResponse>("/auth/providers");
}

export async function getCurrentUser(token: string, options?: { timeoutMs?: number }): Promise<CurrentUser> {
  return request<CurrentUser>("/auth/me", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    timeoutMs: options?.timeoutMs,
  });
}

export async function sendPresenceHeartbeat(
  token: string,
  payload: UserPresenceHeartbeatInput,
): Promise<UserPresenceHeartbeatResponse> {
  return request<UserPresenceHeartbeatResponse>("/auth/presence/heartbeat", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function getPresenceSummary(
  token: string,
  params: { windowMinutes?: number } = {},
): Promise<UserPresenceSummary> {
  const query = new URLSearchParams();
  if (params.windowMinutes != null) {
    query.set("window_minutes", String(params.windowMinutes));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<UserPresenceSummary>(`/auth/presence/summary${suffix}`, {
    headers: authHeaders(token),
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
const PRESENZE_SELF_SERVICE_API_BASE = "/me/presenze";
const GATE_PRESENZE_API_BASE = "/gate/presenze";
function authHeaders(token: string): HeadersInit { return { Authorization: `Bearer ${token}` }; }
export async function getGatePresenzeRules(token: string): Promise<GatePresenzeRulesResponse> {
  return request<GatePresenzeRulesResponse>(`${GATE_PRESENZE_API_BASE}/rules`, {
    headers: authHeaders(token),
  });
}

export async function listGatePresenzeTeams(token: string): Promise<GatePresenzeTeam[]> {
  return request<GatePresenzeTeam[]>(`${GATE_PRESENZE_API_BASE}/teams`, {
    headers: authHeaders(token),
  });
}

export async function createGatePresenzeTeam(token: string, payload: GatePresenzeTeamCreateInput): Promise<GatePresenzeTeam> {
  return request<GatePresenzeTeam>(`${GATE_PRESENZE_API_BASE}/teams`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function updateGatePresenzeTeam(token: string, teamId: string, payload: GatePresenzeTeamUpdateInput): Promise<GatePresenzeTeam> {
  return request<GatePresenzeTeam>(`${GATE_PRESENZE_API_BASE}/teams/${teamId}`, {
    method: "PUT",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function createGatePresenzeTeamMembership(
  token: string,
  teamId: string,
  payload: GatePresenzeTeamMembershipCreateInput,
): Promise<GatePresenzeTeamMembership> {
  return request<GatePresenzeTeamMembership>(`${GATE_PRESENZE_API_BASE}/teams/${teamId}/memberships`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function createGatePresenzeTeamSupervisor(
  token: string,
  teamId: string,
  payload: GatePresenzeTeamSupervisorCreateInput,
): Promise<GatePresenzeTeamSupervisor> {
  return request<GatePresenzeTeamSupervisor>(`${GATE_PRESENZE_API_BASE}/teams/${teamId}/supervisors`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function getMePresenzeStatus(token: string): Promise<MePresenzeStatusResponse> {
  return request<MePresenzeStatusResponse>(PRESENZE_SELF_SERVICE_API_BASE, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function previewMeStraordinariRequest(token: string): Promise<MeStraordinariPreviewResponse> {
  return request<MeStraordinariPreviewResponse>(`${PRESENZE_SELF_SERVICE_API_BASE}/straordinari/preview`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function downloadMeStraordinariRequest(
  token: string,
  format: "xlsx" | "pdf",
  payload: MeStraordinariExportRequest,
): Promise<Blob> {
  return requestBlob(`${PRESENZE_SELF_SERVICE_API_BASE}/straordinari/export/${format}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function listMePresenzeDailyRecords(
  token: string,
  params: {
    collaboratorId?: string;
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
  return request<PresenzeDailyRecordListResponse>(`${PRESENZE_SELF_SERVICE_API_BASE}/daily-records${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getMePresenzeDailyRecord(token: string, recordId: string): Promise<PresenzeDailyRecord> {
  return request<PresenzeDailyRecord>(`${PRESENZE_SELF_SERVICE_API_BASE}/daily-records/${recordId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getMePresenzeSummary(token: string, periodStart: string, periodEnd: string): Promise<MePresenzeSummaryResponse> {
  const query = new URLSearchParams({ period_start: periodStart, period_end: periodEnd });
  return request<MePresenzeSummaryResponse>(`${PRESENZE_SELF_SERVICE_API_BASE}/summary?${query.toString()}`, {
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

export async function getMyPermissions(token: string, options?: { timeoutMs?: number }): Promise<MyPermissionsResponse> {
  return request<MyPermissionsResponse>("/auth/my-permissions", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    timeoutMs: options?.timeoutMs,
  });
}

export async function getDashboardSummary(token: string, options?: { timeoutMs?: number }): Promise<DashboardSummary> {
  return request<DashboardSummary>("/dashboard/summary", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    timeoutMs: options?.timeoutMs,
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

export async function sendApplicationUserInvite(token: string, userId: number): Promise<ApplicationUserInviteResponse> {
  return request<ApplicationUserInviteResponse>(`/admin/users/${userId}/send-invite`, {
    method: "POST",
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
