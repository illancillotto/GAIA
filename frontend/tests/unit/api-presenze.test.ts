import { afterEach, describe, expect, test, vi } from "vitest";

import {
  applyPresenzeScheduleBootstrap,
  bootstrapPresenzeHolidays,
  cancelPresenzeSyncJob,
  createGatePresenzeTeam,
  createGatePresenzeTeamMembership,
  createGatePresenzeTeamSupervisor,
  createPresenzeBankHoursAdjustment,
  createPresenzeCollaboratorScheduleAssignment,
  createPresenzeCredential,
  createPresenzeHoliday,
  createPresenzeRecoveryAdjustment,
  createPresenzeScheduleRule,
  createPresenzeScheduleTemplate,
  createPresenzeStraordinariExportJob,
  createPresenzeSyncJob,
  createPresenzeXlsmExportJob,
  deletePresenzeBankHoursAdjustment,
  deletePresenzeCollaboratorScheduleAssignment,
  deletePresenzeCredential,
  deletePresenzeHoliday,
  deletePresenzeRecoveryAdjustment,
  deletePresenzeScheduleAssignment,
  deletePresenzeScheduleRule,
  deletePresenzeScheduleTemplate,
  deletePresenzeStraordinariExportJob,
  deletePresenzeSyncJob,
  deletePresenzeXlsmExportJob,
  downloadMeStraordinariRequest,
  downloadPresenzeStraordinariExportArtifact,
  downloadPresenzeSyncArtifact,
  downloadPresenzeXlsmExportArtifact,
  exportPresenzeXlsm,
  getGatePresenzeRules,
  getMePresenzeDailyRecord,
  getMePresenzeStatus,
  getMePresenzeSummary,
  getPresenzeAccessContext,
  getPresenzeAnomalyMonthSummary,
  getPresenzeAutoSyncConfig,
  getPresenzeBankHoursCollaboratorDetail,
  getPresenzeBankHoursDashboard,
  getPresenzeBankHoursGuidanceConfig,
  getPresenzeCollaboratorCalendar,
  getPresenzeCollaboratorSummary,
  getPresenzeDailyRecord,
  getPresenzeDashboardSummary,
  getPresenzeImportJob,
  getPresenzeRecoveryDashboard,
  getPresenzeScheduleBootstrapPreview,
  getPresenzeStraordinariExportJob,
  getPresenzeSyncJob,
  getPresenzeXlsmExportJob,
  importPresenzeJson,
  listAllPresenzeCollaborators,
  listGatePresenzeTeams,
  listMePresenzeDailyRecords,
  listPresenzeAnomalyRecords,
  listPresenzeApplicationUsers,
  listPresenzeBankHoursAdjustments,
  listPresenzeBankHoursGuidanceConfigHistory,
  listPresenzeCollaboratorScheduleAssignments,
  listPresenzeCollaborators,
  listPresenzeCredentials,
  listPresenzeDailyMatrixRecords,
  listPresenzeDailyRecords,
  listPresenzeHolidays,
  listPresenzeImportJobs,
  listPresenzeRecoveryAdjustments,
  listPresenzeScheduleTemplates,
  listPresenzeStraordinariExportJobs,
  listPresenzeSupervisorAssignments,
  listPresenzeSyncJobs,
  listPresenzeXlsmExportJobs,
  mapPresenzeCollaboratorApplicationUser,
  previewPresenzeImport,
  previewMeStraordinariRequest,
  previewPresenzeStraordinariExport,
  refreshPresenzeDailyRecordFromInaz,
  retryPresenzeSyncJob,
  retrySelectedPresenzeSyncJob,
  reviewPresenzeBankHoursAdjustment,
  reviewPresenzeRecoveryAdjustment,
  testPresenzeCredential,
  updateGatePresenzeTeam,
  updatePresenzeAutoSyncConfig,
  updatePresenzeBankHoursAdjustment,
  updatePresenzeBankHoursGuidanceConfig,
  updatePresenzeCollaboratorContractProfile,
  updatePresenzeCredential,
  updatePresenzeDailyRecord,
  updatePresenzeHoliday,
  updatePresenzeRecoveryAdjustment,
  updatePresenzeScheduleRule,
  updatePresenzeScheduleTemplate,
  updatePresenzeSupervisorAssignment,
} from "@/lib/api";

const TOKEN = "test-token";
const AUTH = { Authorization: `Bearer ${TOKEN}` };

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function blobResponse(content = "blob-data"): Response {
  return new Response(new Blob([content]), { status: 200 });
}

function emptyOkResponse(status = 204): Response {
  return new Response(null, { status });
}

function stubFetch(...responses: Response[]) {
  const fetchMock = vi.fn();
  for (const response of responses) {
    fetchMock.mockResolvedValueOnce(response);
  }
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("api presenze clients", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("getGatePresenzeRules", async () => {
    const payload = { rules: [] };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(getGatePresenzeRules(TOKEN)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/gate/presenze/rules",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("listGatePresenzeTeams", async () => {
    const payload = [{ id: "team-1", name: "Team A" }];
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(listGatePresenzeTeams(TOKEN)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/gate/presenze/teams",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("createGatePresenzeTeam", async () => {
    const payload = { id: "team-1", name: "Team A" };
    const input = { name: "Team A", code: "TEAM-A", personnel_area: "AGRARIO" as const };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(createGatePresenzeTeam(TOKEN, input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/gate/presenze/teams",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("updateGatePresenzeTeam", async () => {
    const payload = { id: "team-1", name: "Team B" };
    const input = { name: "Team B" };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(updateGatePresenzeTeam(TOKEN, "team-1", input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/gate/presenze/teams/team-1",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("createGatePresenzeTeamMembership", async () => {
    const payload = { id: "mem-1", user_id: 7 };
    const input = { user_id: 7 };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(createGatePresenzeTeamMembership(TOKEN, "team-1", input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/gate/presenze/teams/team-1/memberships",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("createGatePresenzeTeamSupervisor", async () => {
    const payload = { id: "sup-1", user_id: 3 };
    const input = { user_id: 3 };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(createGatePresenzeTeamSupervisor(TOKEN, "team-1", input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/gate/presenze/teams/team-1/supervisors",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("getMePresenzeStatus", async () => {
    const payload = { period_start: "2026-08-01", period_end: "2026-08-31", records: [] };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(getMePresenzeStatus(TOKEN)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/me/presenze",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("listMePresenzeDailyRecords", async () => {
    const payload = { items: [], total: 0 };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(
      listMePresenzeDailyRecords(TOKEN, {
        collaboratorId: "col-1",
        dateFrom: "2026-08-01",
        dateTo: "2026-08-31",
        q: "rossi",
        page: 2,
        pageSize: 50,
      }),
    ).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/me/presenze/daily-records?collaborator_id=col-1&date_from=2026-08-01&date_to=2026-08-31&q=rossi&page=2&page_size=50",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("getMePresenzeDailyRecord", async () => {
    const payload = { id: "rec-1" };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(getMePresenzeDailyRecord(TOKEN, "rec-1")).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/me/presenze/daily-records/rec-1",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("getMePresenzeSummary", async () => {
    const payload = { period_start: "2026-08-01", period_end: "2026-08-31", totals: {} };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(getMePresenzeSummary(TOKEN, "2026-08-01", "2026-08-31")).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/me/presenze/summary?period_start=2026-08-01&period_end=2026-08-31",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("previewMeStraordinariRequest", async () => {
    const payload = { items: [] };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(previewMeStraordinariRequest(TOKEN)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/me/presenze/straordinari/preview",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("downloadMeStraordinariRequest", async () => {
    const input = { items: [{ record_id: "record-1", motivation: "Servizio urgente" }] };
    const fetchMock = stubFetch(blobResponse("xlsx"));
    const result = await downloadMeStraordinariRequest(TOKEN, "xlsx", input);
    expect(result).toBeInstanceOf(Blob);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/me/presenze/straordinari/export/xlsx",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(input),
        headers: expect.objectContaining({ ...AUTH, "Content-Type": "application/json" }),
      }),
    );
  });

  test("listPresenzeCollaborators", async () => {
    const payload = { items: [], total: 0 };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(
      listPresenzeCollaborators(TOKEN, { q: "rossi", mappedOnly: true, page: 1, pageSize: 100 }),
    ).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/collaborators?q=rossi&mapped_only=true&page=1&page_size=100",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("listAllPresenzeCollaborators paginates until complete", async () => {
    const fetchMock = stubFetch(
      jsonResponse({ items: [{ id: "c1" }], total: 2 }),
      jsonResponse({ items: [{ id: "c2" }], total: 2 }),
    );
    await expect(listAllPresenzeCollaborators(TOKEN)).resolves.toEqual([{ id: "c1" }, { id: "c2" }]);
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/presenze/collaborators?page=1&page_size=200",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/presenze/collaborators?page=2&page_size=200",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("listPresenzeApplicationUsers", async () => {
    const payload = [{ id: 1, username: "user1" }];
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(listPresenzeApplicationUsers(TOKEN)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/application-users",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("listPresenzeCredentials", async () => {
    const payload = [{ id: 1, label: "Inaz" }];
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(listPresenzeCredentials(TOKEN)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/credentials",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("getPresenzeAccessContext", async () => {
    const payload = { role: "admin" };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(getPresenzeAccessContext(TOKEN)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/access-context",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("listPresenzeSupervisorAssignments", async () => {
    const payload = [{ collaborator_id: "col-1", supervisor_user_id: 5 }];
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(listPresenzeSupervisorAssignments(TOKEN, 5)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/supervisor-assignments?supervisor_user_id=5",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("updatePresenzeSupervisorAssignment", async () => {
    const payload = { collaborator_id: "col-1", supervisor_user_id: 5 };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(updatePresenzeSupervisorAssignment(TOKEN, "col-1", 5)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/supervisor-assignments/col-1",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({ supervisor_user_id: 5 }),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("createPresenzeCredential", async () => {
    const input = { label: "Inaz", username: "u", password: "p" };
    const payload = { id: 1, ...input };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(createPresenzeCredential(TOKEN, input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/credentials",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("updatePresenzeCredential", async () => {
    const input = { label: "Inaz updated" };
    const payload = { id: 1, label: "Inaz updated" };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(updatePresenzeCredential(TOKEN, 1, input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/credentials/1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("deletePresenzeCredential", async () => {
    const fetchMock = stubFetch(emptyOkResponse());
    await expect(deletePresenzeCredential(TOKEN, 1)).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/credentials/1",
      expect.objectContaining({
        method: "DELETE",
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("testPresenzeCredential", async () => {
    const payload = { ok: true, message: "connected" };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(testPresenzeCredential(TOKEN, 1)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/credentials/1/test",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("mapPresenzeCollaboratorApplicationUser", async () => {
    const payload = { id: "col-1", application_user_id: 7 };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(mapPresenzeCollaboratorApplicationUser(TOKEN, "col-1", 7)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/collaborators/col-1/application-user",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({ application_user_id: 7 }),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("updatePresenzeCollaboratorContractProfile", async () => {
    const input = { contract_hours_per_day: 8 };
    const payload = { id: "col-1", contract_hours_per_day: 8 };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(updatePresenzeCollaboratorContractProfile(TOKEN, "col-1", input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/collaborators/col-1/contract-profile",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("getPresenzeCollaboratorCalendar", async () => {
    const payload = { days: [] };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(getPresenzeCollaboratorCalendar(TOKEN, "col-1", "2026-08-01", "2026-08-31")).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/collaborators/col-1/calendar?date_from=2026-08-01&date_to=2026-08-31",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("getPresenzeCollaboratorSummary", async () => {
    const payload = { totals: {} };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(getPresenzeCollaboratorSummary(TOKEN, "col-1", "2026-08-01", "2026-08-31")).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/collaborators/col-1/summary?period_start=2026-08-01&period_end=2026-08-31",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("listPresenzeDailyRecords", async () => {
    const payload = { items: [], total: 0 };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(
      listPresenzeDailyRecords(TOKEN, {
        collaboratorId: "col-1",
        applicationUserId: 7,
        dateFrom: "2026-08-01",
        dateTo: "2026-08-31",
        q: "rossi",
        includePunches: true,
        includeRawPayload: false,
        page: 1,
        pageSize: 50,
      }),
    ).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/giornaliere?collaborator_id=col-1&application_user_id=7&date_from=2026-08-01&date_to=2026-08-31&q=rossi&include_punches=true&include_raw_payload=false&page=1&page_size=50",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("listPresenzeAnomalyRecords", async () => {
    const payload = { items: [], total: 0 };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(
      listPresenzeAnomalyRecords(TOKEN, {
        collaboratorId: "col-1",
        applicationUserId: 7,
        dateFrom: "2026-08-01",
        dateTo: "2026-08-31",
        q: "anomaly",
        onlyAnomalies: true,
        onlyRequests: false,
        page: 1,
        pageSize: 25,
      }),
    ).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/anomalie?collaborator_id=col-1&application_user_id=7&date_from=2026-08-01&date_to=2026-08-31&q=anomaly&only_anomalies=true&only_requests=false&page=1&page_size=25",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("getPresenzeAnomalyMonthSummary", async () => {
    const payload = { months: [] };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(
      getPresenzeAnomalyMonthSummary(TOKEN, {
        collaboratorId: "col-1",
        applicationUserId: 7,
        months: 6,
        anchorMonth: "2026-08",
      }),
    ).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/anomalie/month-summary?collaborator_id=col-1&application_user_id=7&months=6&anchor_month=2026-08",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("listPresenzeDailyMatrixRecords", async () => {
    const payload = { items: [], total: 0 };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(
      listPresenzeDailyMatrixRecords(TOKEN, {
        collaboratorId: "col-1",
        applicationUserId: 7,
        dateFrom: "2026-08-01",
        dateTo: "2026-08-31",
        q: "rossi",
        page: 1,
        pageSize: 50,
      }),
    ).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/giornaliere/matrix?collaborator_id=col-1&application_user_id=7&date_from=2026-08-01&date_to=2026-08-31&q=rossi&page=1&page_size=50",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("getPresenzeDailyRecord", async () => {
    const payload = { id: "rec-1" };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(getPresenzeDailyRecord(TOKEN, "rec-1")).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/giornaliere/rec-1",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("refreshPresenzeDailyRecordFromInaz", async () => {
    const payload = { id: "job-1", status: "queued" };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(refreshPresenzeDailyRecordFromInaz(TOKEN, "rec-1")).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/giornaliere/rec-1/refresh-from-inaz",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("getPresenzeDashboardSummary", async () => {
    const payload = { totals: {} };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(getPresenzeDashboardSummary(TOKEN, { periodStart: "2026-08-01", periodEnd: "2026-08-31" })).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/dashboard/summary?period_start=2026-08-01&period_end=2026-08-31",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("updatePresenzeDailyRecord", async () => {
    const input = { notes: "manual fix" };
    const payload = { id: "rec-1", notes: "manual fix" };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(updatePresenzeDailyRecord(TOKEN, "rec-1", input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/giornaliere/rec-1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("getPresenzeRecoveryDashboard", async () => {
    const payload = { items: [] };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(
      getPresenzeRecoveryDashboard(TOKEN, {
        dateFrom: "2026-08-01",
        dateTo: "2026-08-31",
        q: "rossi",
        negativeOnly: true,
        pendingValidationOnly: true,
        pendingAdjustmentsOnly: true,
        manualAdjustmentsOnly: true,
      }),
    ).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/recovery/dashboard?date_from=2026-08-01&date_to=2026-08-31&q=rossi&negative_only=true&pending_validation_only=true&pending_adjustments_only=true&manual_adjustments_only=true",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("listPresenzeRecoveryAdjustments", async () => {
    const payload = [{ id: "adj-1" }];
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(listPresenzeRecoveryAdjustments(TOKEN, "col-1", "pending")).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/recovery/adjustments?collaborator_id=col-1&approval_status=pending",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("createPresenzeRecoveryAdjustment", async () => {
    const input = { collaborator_id: "col-1", minutes: 60 };
    const payload = { id: "adj-1", ...input };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(createPresenzeRecoveryAdjustment(TOKEN, input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/recovery/adjustments",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("updatePresenzeRecoveryAdjustment", async () => {
    const input = { minutes: 90 };
    const payload = { id: "adj-1", minutes: 90 };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(updatePresenzeRecoveryAdjustment(TOKEN, "adj-1", input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/recovery/adjustments/adj-1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("deletePresenzeRecoveryAdjustment", async () => {
    const fetchMock = stubFetch(emptyOkResponse());
    await expect(deletePresenzeRecoveryAdjustment(TOKEN, "adj-1")).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/recovery/adjustments/adj-1",
      expect.objectContaining({
        method: "DELETE",
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("reviewPresenzeRecoveryAdjustment", async () => {
    const input = { approved: true, review_notes: "ok" };
    const payload = { id: "adj-1", approval_status: "approved" };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(reviewPresenzeRecoveryAdjustment(TOKEN, "adj-1", input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/recovery/adjustments/adj-1/review",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("getPresenzeBankHoursDashboard", async () => {
    const payload = { items: [] };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(
      getPresenzeBankHoursDashboard(TOKEN, {
        dateFrom: "2026-08-01",
        dateTo: "2026-08-31",
        q: "rossi",
        negativeOnly: true,
        pendingAdjustmentsOnly: true,
        manualAdjustmentsOnly: true,
      }),
    ).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/bank-hours/dashboard?date_from=2026-08-01&date_to=2026-08-31&q=rossi&negative_only=true&pending_adjustments_only=true&manual_adjustments_only=true",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("getPresenzeBankHoursCollaboratorDetail", async () => {
    const payload = { collaborator_id: "col-1", entries: [] };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(
      getPresenzeBankHoursCollaboratorDetail(TOKEN, "col-1", {
        dateFrom: "2026-08-01",
        dateTo: "2026-08-31",
      }),
    ).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/bank-hours/collaborators/col-1?date_from=2026-08-01&date_to=2026-08-31",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("listPresenzeBankHoursAdjustments", async () => {
    const payload = [{ id: "adj-1" }];
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(listPresenzeBankHoursAdjustments(TOKEN, "col-1", "approved")).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/bank-hours/adjustments?collaborator_id=col-1&approval_status=approved",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("createPresenzeBankHoursAdjustment", async () => {
    const input = { collaborator_id: "col-1", minutes: 120 };
    const payload = { id: "adj-1", ...input };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(createPresenzeBankHoursAdjustment(TOKEN, input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/bank-hours/adjustments",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("updatePresenzeBankHoursAdjustment", async () => {
    const input = { minutes: 150 };
    const payload = { id: "adj-1", minutes: 150 };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(updatePresenzeBankHoursAdjustment(TOKEN, "adj-1", input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/bank-hours/adjustments/adj-1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("deletePresenzeBankHoursAdjustment", async () => {
    const fetchMock = stubFetch(emptyOkResponse());
    await expect(deletePresenzeBankHoursAdjustment(TOKEN, "adj-1")).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/bank-hours/adjustments/adj-1",
      expect.objectContaining({
        method: "DELETE",
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("reviewPresenzeBankHoursAdjustment", async () => {
    const input = { approved: true };
    const payload = { id: "adj-1", approval_status: "approved" };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(reviewPresenzeBankHoursAdjustment(TOKEN, "adj-1", input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/bank-hours/adjustments/adj-1/review",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("listPresenzeHolidays", async () => {
    const payload = [{ id: 1, date: "2026-01-01" }];
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(listPresenzeHolidays(TOKEN, 2026)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/holidays?year=2026",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("bootstrapPresenzeHolidays", async () => {
    const payload = { year: 2026, created: 12, items: [] };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(bootstrapPresenzeHolidays(TOKEN, 2026)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/holidays/bootstrap?year=2026",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("createPresenzeHoliday", async () => {
    const input = { date: "2026-12-25", label: "Natale" };
    const payload = { id: 1, ...input };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(createPresenzeHoliday(TOKEN, input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/holidays",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("updatePresenzeHoliday", async () => {
    const input = { label: "Natale aggiornato" };
    const payload = { id: 1, label: "Natale aggiornato" };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(updatePresenzeHoliday(TOKEN, 1, input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/holidays/1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("deletePresenzeHoliday", async () => {
    const fetchMock = stubFetch(emptyOkResponse());
    await expect(deletePresenzeHoliday(TOKEN, 1)).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/holidays/1",
      expect.objectContaining({
        method: "DELETE",
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("listPresenzeScheduleTemplates", async () => {
    const payload = [{ id: 1, name: "Standard" }];
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(listPresenzeScheduleTemplates(TOKEN)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/schedule/templates",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("createPresenzeScheduleTemplate", async () => {
    const input = { name: "Standard", slug: "standard" };
    const payload = { id: 1, ...input };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(createPresenzeScheduleTemplate(TOKEN, input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/schedule/templates",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("updatePresenzeScheduleTemplate", async () => {
    const input = { name: "Standard updated" };
    const payload = { id: 1, name: "Standard updated" };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(updatePresenzeScheduleTemplate(TOKEN, 1, input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/schedule/templates/1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("deletePresenzeScheduleTemplate", async () => {
    const fetchMock = stubFetch(emptyOkResponse());
    await expect(deletePresenzeScheduleTemplate(TOKEN, 1)).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/schedule/templates/1",
      expect.objectContaining({
        method: "DELETE",
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("createPresenzeScheduleRule", async () => {
    const input = { weekday: 1, start_time: "09:00", end_time: "18:00" };
    const payload = { id: 1, ...input };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(createPresenzeScheduleRule(TOKEN, 1, input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/schedule/templates/1/rules",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("updatePresenzeScheduleRule", async () => {
    const input = { end_time: "17:00" };
    const payload = { id: 1, end_time: "17:00" };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(updatePresenzeScheduleRule(TOKEN, 1, input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/schedule/rules/1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("deletePresenzeScheduleRule", async () => {
    const fetchMock = stubFetch(emptyOkResponse());
    await expect(deletePresenzeScheduleRule(TOKEN, 1)).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/schedule/rules/1",
      expect.objectContaining({
        method: "DELETE",
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("listPresenzeCollaboratorScheduleAssignments", async () => {
    const payload = [{ id: 1, template_id: 2 }];
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(listPresenzeCollaboratorScheduleAssignments(TOKEN, "col-1")).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/collaborators/col-1/schedule-assignments",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("createPresenzeCollaboratorScheduleAssignment", async () => {
    const input = { template_id: 2, valid_from: "2026-08-01" };
    const payload = { id: 1, ...input };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(createPresenzeCollaboratorScheduleAssignment(TOKEN, "col-1", input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/collaborators/col-1/schedule-assignments",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("deletePresenzeCollaboratorScheduleAssignment", async () => {
    const fetchMock = stubFetch(emptyOkResponse());
    await expect(deletePresenzeCollaboratorScheduleAssignment(TOKEN, 1)).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/schedule-assignments/1",
      expect.objectContaining({
        method: "DELETE",
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("deletePresenzeScheduleAssignment delegates to collaborator schedule delete", async () => {
    const fetchMock = stubFetch(emptyOkResponse());
    await expect(deletePresenzeScheduleAssignment(TOKEN, 1)).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/schedule-assignments/1",
      expect.objectContaining({
        method: "DELETE",
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("getPresenzeScheduleBootstrapPreview", async () => {
    const payload = { templates: [] };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(getPresenzeScheduleBootstrapPreview(TOKEN)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/configuration/schedule-bootstrap-preview",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("applyPresenzeScheduleBootstrap", async () => {
    const input = { dry_run: false };
    const payload = { applied: 3 };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(applyPresenzeScheduleBootstrap(TOKEN, input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/configuration/schedule-bootstrap-apply",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("previewPresenzeImport", async () => {
    const payload = { rows: 10 };
    const file = new File(["{}"], "import.json", { type: "application/json" });
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(previewPresenzeImport(TOKEN, file)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/import/preview",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining(AUTH),
        body: expect.any(FormData),
      }),
    );
  });

  test("importPresenzeJson", async () => {
    const payload = { imported: 5 };
    const file = new File(["{}"], "import.json", { type: "application/json" });
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(importPresenzeJson(TOKEN, file)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/import/json",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining(AUTH),
        body: expect.any(FormData),
      }),
    );
  });

  test("listPresenzeImportJobs", async () => {
    const payload = { items: [{ id: "job-1" }] };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(listPresenzeImportJobs(TOKEN)).resolves.toEqual(payload.items);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/import/jobs",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("getPresenzeImportJob", async () => {
    const payload = { id: "job-1", status: "done" };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(getPresenzeImportJob(TOKEN, "job-1")).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/import/jobs/job-1",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("createPresenzeSyncJob", async () => {
    const input = { date_from: "2026-08-01", date_to: "2026-08-31" };
    const payload = { id: "job-1", status: "queued" };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(createPresenzeSyncJob(TOKEN, input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/sync/jobs",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("createPresenzeXlsmExportJob", async () => {
    const input = { period_start: "2026-08-01" };
    const payload = { id: "job-1", status: "queued" };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(createPresenzeXlsmExportJob(TOKEN, input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/export/jobs/xlsm",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("previewPresenzeStraordinariExport", async () => {
    const payload = { rows: 3 };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(previewPresenzeStraordinariExport(TOKEN, { collaboratorId: "col-1" })).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/export/straordinari/preview?collaborator_id=col-1",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("createPresenzeStraordinariExportJob", async () => {
    const input = { period_start: "2026-08-01" };
    const payload = { id: "job-1", status: "queued" };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(createPresenzeStraordinariExportJob(TOKEN, input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/export/jobs/straordinari",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("getPresenzeAutoSyncConfig", async () => {
    const payload = { enabled: true };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(getPresenzeAutoSyncConfig(TOKEN)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/sync/config",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("updatePresenzeAutoSyncConfig", async () => {
    const input = { enabled: false };
    const payload = { enabled: false };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(updatePresenzeAutoSyncConfig(TOKEN, input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/sync/config",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("getPresenzeBankHoursGuidanceConfig", async () => {
    const payload = { threshold_minutes: 600 };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(getPresenzeBankHoursGuidanceConfig(TOKEN)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/bank-hours/guidance-config",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("updatePresenzeBankHoursGuidanceConfig", async () => {
    const input = { threshold_minutes: 720 };
    const payload = { threshold_minutes: 720 };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(updatePresenzeBankHoursGuidanceConfig(TOKEN, input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/bank-hours/guidance-config",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("listPresenzeBankHoursGuidanceConfigHistory", async () => {
    const payload = [{ id: 1, threshold_minutes: 600 }];
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(listPresenzeBankHoursGuidanceConfigHistory(TOKEN)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/bank-hours/guidance-config/history",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("listPresenzeSyncJobs", async () => {
    const payload = { items: [{ id: "job-1" }] };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(listPresenzeSyncJobs(TOKEN, { limit: 10 })).resolves.toEqual(payload.items);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/sync/jobs?limit=10",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("getPresenzeSyncJob", async () => {
    const payload = { id: "job-1", status: "done" };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(getPresenzeSyncJob(TOKEN, "job-1")).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/sync/jobs/job-1",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("listPresenzeXlsmExportJobs", async () => {
    const payload = { items: [{ id: "job-1" }] };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(listPresenzeXlsmExportJobs(TOKEN, { limit: 5 })).resolves.toEqual(payload.items);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/export/jobs/xlsm?limit=5",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("getPresenzeXlsmExportJob", async () => {
    const payload = { id: "job-1", status: "done" };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(getPresenzeXlsmExportJob(TOKEN, "job-1")).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/export/jobs/xlsm/job-1",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("listPresenzeStraordinariExportJobs", async () => {
    const payload = { items: [{ id: "job-1" }] };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(listPresenzeStraordinariExportJobs(TOKEN, { limit: 5 })).resolves.toEqual(payload.items);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/export/jobs/straordinari?limit=5",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("getPresenzeStraordinariExportJob", async () => {
    const payload = { id: "job-1", status: "done" };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(getPresenzeStraordinariExportJob(TOKEN, "job-1")).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/export/jobs/straordinari/job-1",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("deletePresenzeStraordinariExportJob", async () => {
    const fetchMock = stubFetch(emptyOkResponse());
    await expect(deletePresenzeStraordinariExportJob(TOKEN, "job-1")).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/export/jobs/straordinari/job-1",
      expect.objectContaining({
        method: "DELETE",
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("downloadPresenzeStraordinariExportArtifact", async () => {
    const fetchMock = stubFetch(blobResponse("xlsx"));
    const result = await downloadPresenzeStraordinariExportArtifact(TOKEN, "job-1", "xlsx");
    expect(result).toBeInstanceOf(Blob);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/export/jobs/straordinari/job-1/artifacts/xlsx",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("deletePresenzeXlsmExportJob", async () => {
    const fetchMock = stubFetch(emptyOkResponse());
    await expect(deletePresenzeXlsmExportJob(TOKEN, "job-1")).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/export/jobs/xlsm/job-1",
      expect.objectContaining({
        method: "DELETE",
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("downloadPresenzeXlsmExportArtifact", async () => {
    const fetchMock = stubFetch(blobResponse("xlsm"));
    const result = await downloadPresenzeXlsmExportArtifact(TOKEN, "job-1", "xlsm");
    expect(result).toBeInstanceOf(Blob);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/export/jobs/xlsm/job-1/artifacts/xlsm",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("retryPresenzeSyncJob", async () => {
    const payload = { id: "job-1", status: "queued" };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(retryPresenzeSyncJob(TOKEN, "job-1")).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/sync/jobs/job-1/retry",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("retrySelectedPresenzeSyncJob", async () => {
    const input = { collaborator_ids: ["col-1", "col-2"] };
    const payload = { id: "job-1", status: "queued" };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(retrySelectedPresenzeSyncJob(TOKEN, "job-1", input)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/sync/jobs/job-1/retry-selected",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(input),
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("cancelPresenzeSyncJob", async () => {
    const payload = { id: "job-1", status: "cancelled" };
    const fetchMock = stubFetch(jsonResponse(payload));
    await expect(cancelPresenzeSyncJob(TOKEN, "job-1")).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/sync/jobs/job-1/cancel",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("deletePresenzeSyncJob", async () => {
    const fetchMock = stubFetch(emptyOkResponse());
    await expect(deletePresenzeSyncJob(TOKEN, "job-1")).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/sync/jobs/job-1",
      expect.objectContaining({
        method: "DELETE",
        headers: expect.objectContaining(AUTH),
      }),
    );
  });

  test("downloadPresenzeSyncArtifact", async () => {
    const fetchMock = stubFetch(blobResponse("json"));
    const result = await downloadPresenzeSyncArtifact(TOKEN, "job-1", "json");
    expect(result).toBeInstanceOf(Blob);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/sync/jobs/job-1/artifacts/json",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });

  test("exportPresenzeXlsm", async () => {
    const fetchMock = stubFetch(blobResponse("xlsm"));
    const result = await exportPresenzeXlsm(TOKEN, {
      periodStart: "2026-08-01",
      collaboratorIds: ["col-1", "col-2"],
      employeeKind: "interno",
      templatePath: "/templates/default.xlsm",
    });
    expect(result).toBeInstanceOf(Blob);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presenze/export/giornaliere.xlsm?period_start=2026-08-01&employee_kind=interno&template_path=%2Ftemplates%2Fdefault.xlsm&collaborator_id=col-1&collaborator_id=col-2",
      expect.objectContaining({ headers: expect.objectContaining(AUTH) }),
    );
  });
});
