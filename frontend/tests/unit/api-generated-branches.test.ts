import { afterEach, beforeEach, describe, test, vi } from "vitest";

import * as api from "@/lib/api";

const TOKEN = "test-token";
const STRING_FILTERS = {
  q: "query",
  comune: "comune",
  foglio: "1",
  particella: "2",
  created_from: "2026-08-01",
  created_to: "2026-08-31",
};
const FULL_OPTIONS = new Proxy<Record<string, unknown>>(
  {
    page: 1,
    pageSize: 20,
    periodStart: "2026-08-01",
    periodEnd: "2026-08-31",
    dateFrom: "2026-08-01",
    dateTo: "2026-08-31",
    limit: 20,
    offset: 1,
    skip: 1,
    status: "active",
    q: "query",
    query: "query",
    activeOnly: true,
    mappedOnly: true,
    success: true,
    windowHours: 24,
    windowMinutes: 15,
    bustCache: true,
    timeoutMs: 1,
  },
  {
    get: (target, property) =>
      property === "toJSON" ? undefined : Reflect.get(target, property) ?? "value",
  },
);
const FALSE_OPTIONS = new Proxy<Record<string, unknown>>(
  {
    mappedOnly: false,
    requiresReview: false,
    resolved: false,
    success: false,
    activeOnly: false,
    bustCache: false,
  },
  { get: (target, property) => Reflect.get(target, property) },
);

class MockXHR {
  static instances: MockXHR[] = [];
  upload = { addEventListener: vi.fn() };
  status = 200;
  statusText = "OK";
  response: unknown = { ok: true, items: [], total: 0 };
  open = vi.fn();
  setRequestHeader = vi.fn();
  send = vi.fn();
  loadHandler: (() => void) | null = null;
  addEventListener = vi.fn((event: string, handler: () => void) => {
    if (event === "load") this.loadHandler = handler;
  });

  constructor() {
    MockXHR.instances.push(this);
  }
}

function response(): Response {
  return new Response(JSON.stringify({ ok: true, items: [], total: 0 }), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

async function exerciseFetchErrors(call: () => Promise<unknown>) {
  const errors = [
    new Response(JSON.stringify({ detail: "explicit detail" }), { status: 400, statusText: "Bad Request" }),
    new Response(JSON.stringify({ detail: null }), { status: 400, statusText: "Bad Request" }),
    new Response("not-json", { status: 500, statusText: "Server Error" }),
    new Response("not-json", { status: 500, statusText: "" }),
  ];
  for (const errorResponse of errors) {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(errorResponse));
    await call().catch(() => undefined);
  }
}

describe("generated API optional-parameter characterization", () => {
  beforeEach(() => {
    MockXHR.instances = [];
    vi.stubGlobal("XMLHttpRequest", MockXHR as unknown as typeof XMLHttpRequest);
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async () => response()));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("login: populated and empty optional values", async () => {
    await api.login("value", "value", "value");
    await api.login("", "");
  });
  test("getAuthProviders: populated and empty optional values", async () => {
    await api.getAuthProviders();
  });
  test("getCurrentUser: populated and empty optional values", async () => {
    await api.getCurrentUser(TOKEN, FULL_OPTIONS);
    await api.getCurrentUser(TOKEN);
    await api.getCurrentUser(TOKEN, FALSE_OPTIONS);
  });
  test("sendPresenceHeartbeat: populated and empty optional values", async () => {
    await api.sendPresenceHeartbeat(TOKEN, {});
    await api.sendPresenceHeartbeat(TOKEN, FULL_OPTIONS);
  });
  test("getPresenceSummary: populated and empty optional values", async () => {
    await api.getPresenceSummary(TOKEN, FULL_OPTIONS);
    await api.getPresenceSummary(TOKEN);
  });
  test("getWikiArticles: populated and empty optional values", async () => {
    await api.getWikiArticles(TOKEN);
  });
  test("getMeStatus: populated and empty optional values", async () => {
    await api.getMeStatus(TOKEN);
  });
  test("getGatePresenzeRules: populated and empty optional values", async () => {
    await api.getGatePresenzeRules(TOKEN);
  });
  test("listGatePresenzeTeams: populated and empty optional values", async () => {
    await api.listGatePresenzeTeams(TOKEN);
  });
  test("createGatePresenzeTeam: populated and empty optional values", async () => {
    await api.createGatePresenzeTeam(TOKEN, {});
    await api.createGatePresenzeTeam(TOKEN, FULL_OPTIONS);
  });
  test("updateGatePresenzeTeam: populated and empty optional values", async () => {
    await api.updateGatePresenzeTeam(TOKEN, "value", {});
    await api.updateGatePresenzeTeam(TOKEN, "", FULL_OPTIONS);
  });
  test("createGatePresenzeTeamMembership: populated and empty optional values", async () => {
    await api.createGatePresenzeTeamMembership(TOKEN, "value", {});
    await api.createGatePresenzeTeamMembership(TOKEN, "", FULL_OPTIONS);
  });
  test("createGatePresenzeTeamSupervisor: populated and empty optional values", async () => {
    await api.createGatePresenzeTeamSupervisor(TOKEN, "value", {});
    await api.createGatePresenzeTeamSupervisor(TOKEN, "", FULL_OPTIONS);
  });
  test("getMePresenzeStatus: populated and empty optional values", async () => {
    await api.getMePresenzeStatus(TOKEN);
  });
  test("previewMeStraordinariRequest: populated and empty optional values", async () => {
    await api.previewMeStraordinariRequest(TOKEN);
  });
  test("downloadMeStraordinariRequest: populated and empty optional values", async () => {
    await api.downloadMeStraordinariRequest(TOKEN, 'xlsx', {});
    await api.downloadMeStraordinariRequest(TOKEN, 'xlsx', FULL_OPTIONS);
  });
  test("listMePresenzeDailyRecords: populated and empty optional values", async () => {
    await api.listMePresenzeDailyRecords(TOKEN, FULL_OPTIONS);
    await api.listMePresenzeDailyRecords(TOKEN);
  });
  test("getMePresenzeDailyRecord: populated and empty optional values", async () => {
    await api.getMePresenzeDailyRecord(TOKEN, "value");
    await api.getMePresenzeDailyRecord(TOKEN, "");
  });
  test("getMePresenzeSummary: populated and empty optional values", async () => {
    await api.getMePresenzeSummary(TOKEN, "value", "value");
    await api.getMePresenzeSummary(TOKEN, "", "");
  });
  test("getMeSummary: populated and empty optional values", async () => {
    await api.getMeSummary(TOKEN, FULL_OPTIONS);
    await api.getMeSummary(TOKEN);
    await api.getMeSummary(TOKEN, FALSE_OPTIONS);
  });
  test("getMeOperazioniSummary: populated and empty optional values", async () => {
    await api.getMeOperazioniSummary(TOKEN, FULL_OPTIONS);
    await api.getMeOperazioniSummary(TOKEN);
    await api.getMeOperazioniSummary(TOKEN, FALSE_OPTIONS);
  });
  test("listMeOperazioniActivities: populated and empty optional values", async () => {
    await api.listMeOperazioniActivities(TOKEN, FULL_OPTIONS);
    await api.listMeOperazioniActivities(TOKEN);
    await api.listMeOperazioniActivities(TOKEN, FALSE_OPTIONS);
  });
  test("listMeOperazioniReports: populated and empty optional values", async () => {
    await api.listMeOperazioniReports(TOKEN, FULL_OPTIONS);
    await api.listMeOperazioniReports(TOKEN);
    await api.listMeOperazioniReports(TOKEN, FALSE_OPTIONS);
  });
  test("listMeOperazioniCases: populated and empty optional values", async () => {
    await api.listMeOperazioniCases(TOKEN, FULL_OPTIONS);
    await api.listMeOperazioniCases(TOKEN);
    await api.listMeOperazioniCases(TOKEN, FALSE_OPTIONS);
  });
  test("listMeVehicleSessions: populated and empty optional values", async () => {
    await api.listMeVehicleSessions(TOKEN, FULL_OPTIONS);
    await api.listMeVehicleSessions(TOKEN);
    await api.listMeVehicleSessions(TOKEN, FALSE_OPTIONS);
  });
  test("listMeAssignedDevices: populated and empty optional values", async () => {
    await api.listMeAssignedDevices(TOKEN);
  });
  test("listMeVehicleAssignments: populated and empty optional values", async () => {
    await api.listMeVehicleAssignments(TOKEN);
  });
  test("getMyPermissions: populated and empty optional values", async () => {
    await api.getMyPermissions(TOKEN, FULL_OPTIONS);
    await api.getMyPermissions(TOKEN);
    await api.getMyPermissions(TOKEN, FALSE_OPTIONS);
  });
  test("getDashboardSummary: populated and empty optional values", async () => {
    await api.getDashboardSummary(TOKEN, FULL_OPTIONS);
    await api.getDashboardSummary(TOKEN);
    await api.getDashboardSummary(TOKEN, FALSE_OPTIONS);
  });
  test("getShares: populated and empty optional values", async () => {
    await api.getShares(TOKEN);
  });
  test("getNasUsers: populated and empty optional values", async () => {
    await api.getNasUsers(TOKEN);
  });
  test("getNasUsersForUsersSection: populated and empty optional values", async () => {
    await api.getNasUsersForUsersSection(TOKEN);
  });
  test("listApplicationUsers: populated and empty optional values", async () => {
    await api.listApplicationUsers(TOKEN, FULL_OPTIONS);
    await api.listApplicationUsers(TOKEN);
  });
  test("listAllApplicationUsers: populated and empty optional values", async () => {
    await api.listAllApplicationUsers(TOKEN);
  });
  test("getApplicationUserPermissions: populated and empty optional values", async () => {
    await api.getApplicationUserPermissions(TOKEN, 1);
    await api.getApplicationUserPermissions(TOKEN, 0);
  });
  test("listSectionCatalog: populated and empty optional values", async () => {
    await api.listSectionCatalog(TOKEN, FULL_OPTIONS);
    await api.listSectionCatalog(TOKEN);
  });
  test("updateApplicationUserPermissions: populated and empty optional values", async () => {
    await api.updateApplicationUserPermissions(TOKEN, 1, [1]);
    await api.updateApplicationUserPermissions(TOKEN, 0, []);
  });
  test("deleteApplicationUserPermissionOverride: populated and empty optional values", async () => {
    await api.deleteApplicationUserPermissionOverride(TOKEN, 1, 1);
    await api.deleteApplicationUserPermissionOverride(TOKEN, 0, 0);
  });
  test("getOrgStructureWorkspace: populated and empty optional values", async () => {
    await api.getOrgStructureWorkspace(TOKEN);
  });
  test("bootstrapOrgStructureFromWhiteCompany: populated and empty optional values", async () => {
    await api.bootstrapOrgStructureFromWhiteCompany(TOKEN);
  });
  test("upsertOrgStructureAssignment: populated and empty optional values", async () => {
    await api.upsertOrgStructureAssignment(TOKEN, 1, {});
    await api.upsertOrgStructureAssignment(TOKEN, 0, FULL_OPTIONS);
  });
  test("deleteOrgStructureAssignment: populated and empty optional values", async () => {
    await api.deleteOrgStructureAssignment(TOKEN, 1);
    await api.deleteOrgStructureAssignment(TOKEN, 0);
  });
  test("createApplicationUser: populated and empty optional values", async () => {
    await api.createApplicationUser(TOKEN, {});
    await api.createApplicationUser(TOKEN, FULL_OPTIONS);
  });
  test("updateApplicationUser: populated and empty optional values", async () => {
    await api.updateApplicationUser(TOKEN, 1, {});
    await api.updateApplicationUser(TOKEN, 0, FULL_OPTIONS);
  });
  test("deleteApplicationUser: populated and empty optional values", async () => {
    await api.deleteApplicationUser(TOKEN, 1);
    await api.deleteApplicationUser(TOKEN, 0);
  });
  test("sendApplicationUserInvite: populated and empty optional values", async () => {
    await api.sendApplicationUserInvite(TOKEN, 1);
    await api.sendApplicationUserInvite(TOKEN, 0);
  });
  test("getNasGroups: populated and empty optional values", async () => {
    await api.getNasGroups(TOKEN);
  });
  test("getOrgUnits: populated and empty optional values", async () => {
    await api.getOrgUnits(TOKEN, FULL_OPTIONS);
    await api.getOrgUnits(TOKEN);
  });
  test("getOrgTree: populated and empty optional values", async () => {
    await api.getOrgTree(TOKEN, 'organigramma');
    await api.getOrgTree(TOKEN);
  });
  test("getOrgUnit: populated and empty optional values", async () => {
    await api.getOrgUnit(TOKEN, "value", 'organigramma');
    await api.getOrgUnit(TOKEN, "");
  });
  test("createOrgUnit: populated and empty optional values", async () => {
    await api.createOrgUnit(TOKEN, {}, 'organigramma');
    await api.createOrgUnit(TOKEN, FULL_OPTIONS);
  });
  test("updateOrgUnit: populated and empty optional values", async () => {
    await api.updateOrgUnit(TOKEN, "value", {}, 'organigramma');
    await api.updateOrgUnit(TOKEN, "", FULL_OPTIONS);
  });
  test("deleteOrgUnit: populated and empty optional values", async () => {
    await api.deleteOrgUnit(TOKEN, "value", 'organigramma');
    await api.deleteOrgUnit(TOKEN, "");
  });
  test("getOrgAssignments: populated and empty optional values", async () => {
    await api.getOrgAssignments(TOKEN, FULL_OPTIONS);
    await api.getOrgAssignments(TOKEN);
  });
  test("createOrgAssignment: populated and empty optional values", async () => {
    await api.createOrgAssignment(TOKEN, {}, 'organigramma');
    await api.createOrgAssignment(TOKEN, FULL_OPTIONS);
  });
  test("updateOrgAssignment: populated and empty optional values", async () => {
    await api.updateOrgAssignment(TOKEN, "value", {}, 'organigramma');
    await api.updateOrgAssignment(TOKEN, "", FULL_OPTIONS);
  });
  test("deleteOrgAssignment: populated and empty optional values", async () => {
    await api.deleteOrgAssignment(TOKEN, "value", 'organigramma');
    await api.deleteOrgAssignment(TOKEN, "");
  });
  test("getOrgOverrides: populated and empty optional values", async () => {
    await api.getOrgOverrides(TOKEN, 'organigramma');
    await api.getOrgOverrides(TOKEN);
  });
  test("createOrgOverride: populated and empty optional values", async () => {
    await api.createOrgOverride(TOKEN, {}, 'organigramma');
    await api.createOrgOverride(TOKEN, FULL_OPTIONS);
  });
  test("updateOrgOverride: populated and empty optional values", async () => {
    await api.updateOrgOverride(TOKEN, "value", {}, 'organigramma');
    await api.updateOrgOverride(TOKEN, "", FULL_OPTIONS);
  });
  test("deleteOrgOverride: populated and empty optional values", async () => {
    await api.deleteOrgOverride(TOKEN, "value", 'organigramma');
    await api.deleteOrgOverride(TOKEN, "");
  });
  test("getOrgVisibility: populated and empty optional values", async () => {
    await api.getOrgVisibility(TOKEN, 1, 'organigramma');
    await api.getOrgVisibility(TOKEN, 0);
  });
  test("syncOrgWhiteCompany: populated and empty optional values", async () => {
    await api.syncOrgWhiteCompany(TOKEN);
  });
  test("exportOrganigrammaSnapshot: populated and empty optional values", async () => {
    await api.exportOrganigrammaSnapshot(TOKEN, 'organigramma');
    await api.exportOrganigrammaSnapshot(TOKEN);
  });
  test("importOrganigrammaSnapshot: populated and empty optional values", async () => {
    await api.importOrganigrammaSnapshot(TOKEN, {}, 'merge', 'organigramma');
    await api.importOrganigrammaSnapshot(TOKEN, FULL_OPTIONS);
  });
  test("listPresenzeCollaborators: populated and empty optional values", async () => {
    await api.listPresenzeCollaborators(TOKEN, FULL_OPTIONS);
    await api.listPresenzeCollaborators(TOKEN);
  });
  test("listAllPresenzeCollaborators: populated and empty optional values", async () => {
    await api.listAllPresenzeCollaborators(TOKEN);
  });
  test("listPresenzeApplicationUsers: populated and empty optional values", async () => {
    await api.listPresenzeApplicationUsers(TOKEN);
  });
  test("listPresenzeCredentials: populated and empty optional values", async () => {
    await api.listPresenzeCredentials(TOKEN);
  });
  test("getPresenzeAccessContext: populated and empty optional values", async () => {
    await api.getPresenzeAccessContext(TOKEN);
  });
  test("listPresenzeSupervisorAssignments: populated and empty optional values", async () => {
    await api.listPresenzeSupervisorAssignments(TOKEN, 1);
    await api.listPresenzeSupervisorAssignments(TOKEN);
  });
  test("updatePresenzeSupervisorAssignment: populated and empty optional values", async () => {
    await api.updatePresenzeSupervisorAssignment(TOKEN, "value", 1);
    await api.updatePresenzeSupervisorAssignment(TOKEN, "", 0);
  });
  test("createPresenzeCredential: populated and empty optional values", async () => {
    await api.createPresenzeCredential(TOKEN, {});
    await api.createPresenzeCredential(TOKEN, FULL_OPTIONS);
  });
  test("updatePresenzeCredential: populated and empty optional values", async () => {
    await api.updatePresenzeCredential(TOKEN, 1, {});
    await api.updatePresenzeCredential(TOKEN, 0, FULL_OPTIONS);
  });
  test("deletePresenzeCredential: populated and empty optional values", async () => {
    await api.deletePresenzeCredential(TOKEN, 1);
    await api.deletePresenzeCredential(TOKEN, 0);
    await exerciseFetchErrors(() => api.deletePresenzeCredential(TOKEN, 1));
  });
  test("testPresenzeCredential: populated and empty optional values", async () => {
    await api.testPresenzeCredential(TOKEN, 1);
    await api.testPresenzeCredential(TOKEN, 0);
  });
  test("mapPresenzeCollaboratorApplicationUser: populated and empty optional values", async () => {
    await api.mapPresenzeCollaboratorApplicationUser(TOKEN, "value", 1);
    await api.mapPresenzeCollaboratorApplicationUser(TOKEN, "", 0);
  });
  test("updatePresenzeCollaboratorContractProfile: populated and empty optional values", async () => {
    await api.updatePresenzeCollaboratorContractProfile(TOKEN, "value", {});
    await api.updatePresenzeCollaboratorContractProfile(TOKEN, "", FULL_OPTIONS);
  });
  test("getPresenzeCollaboratorCalendar: populated and empty optional values", async () => {
    await api.getPresenzeCollaboratorCalendar(TOKEN, "value", "value", "value");
    await api.getPresenzeCollaboratorCalendar(TOKEN, "", "", "");
  });
  test("getPresenzeCollaboratorSummary: populated and empty optional values", async () => {
    await api.getPresenzeCollaboratorSummary(TOKEN, "value", "value", "value");
    await api.getPresenzeCollaboratorSummary(TOKEN, "", "", "");
  });
  test("listPresenzeDailyRecords: populated and empty optional values", async () => {
    await api.listPresenzeDailyRecords(TOKEN, FULL_OPTIONS);
    await api.listPresenzeDailyRecords(TOKEN);
  });
  test("listPresenzeAnomalyRecords: populated and empty optional values", async () => {
    await api.listPresenzeAnomalyRecords(TOKEN, FULL_OPTIONS);
    await api.listPresenzeAnomalyRecords(TOKEN);
  });
  test("getPresenzeAnomalyMonthSummary: populated and empty optional values", async () => {
    await api.getPresenzeAnomalyMonthSummary(TOKEN, FULL_OPTIONS);
    await api.getPresenzeAnomalyMonthSummary(TOKEN);
  });
  test("listPresenzeDailyMatrixRecords: populated and empty optional values", async () => {
    await api.listPresenzeDailyMatrixRecords(TOKEN, FULL_OPTIONS);
    await api.listPresenzeDailyMatrixRecords(TOKEN);
  });
  test("getPresenzeDailyRecord: populated and empty optional values", async () => {
    await api.getPresenzeDailyRecord(TOKEN, "value");
    await api.getPresenzeDailyRecord(TOKEN, "");
  });
  test("refreshPresenzeDailyRecordFromInaz: populated and empty optional values", async () => {
    await api.refreshPresenzeDailyRecordFromInaz(TOKEN, "value");
    await api.refreshPresenzeDailyRecordFromInaz(TOKEN, "");
  });
  test("getPresenzeDashboardSummary: populated and empty optional values", async () => {
    await api.getPresenzeDashboardSummary(TOKEN, FULL_OPTIONS);
    await api.getPresenzeDashboardSummary(TOKEN, "");
  });
  test("updatePresenzeDailyRecord: populated and empty optional values", async () => {
    await api.updatePresenzeDailyRecord(TOKEN, "value", {});
    await api.updatePresenzeDailyRecord(TOKEN, "", FULL_OPTIONS);
  });
  test("getPresenzeRecoveryDashboard: populated and empty optional values", async () => {
    await api.getPresenzeRecoveryDashboard(TOKEN, FULL_OPTIONS);
    await api.getPresenzeRecoveryDashboard(TOKEN);
  });
  test("listPresenzeRecoveryAdjustments: populated and empty optional values", async () => {
    await api.listPresenzeRecoveryAdjustments(TOKEN, "value", 'pending');
    await api.listPresenzeRecoveryAdjustments(TOKEN);
  });
  test("createPresenzeRecoveryAdjustment: populated and empty optional values", async () => {
    await api.createPresenzeRecoveryAdjustment(TOKEN, {});
    await api.createPresenzeRecoveryAdjustment(TOKEN, FULL_OPTIONS);
  });
  test("updatePresenzeRecoveryAdjustment: populated and empty optional values", async () => {
    await api.updatePresenzeRecoveryAdjustment(TOKEN, "value", {});
    await api.updatePresenzeRecoveryAdjustment(TOKEN, "", FULL_OPTIONS);
  });
  test("deletePresenzeRecoveryAdjustment: populated and empty optional values", async () => {
    await api.deletePresenzeRecoveryAdjustment(TOKEN, "value");
    await api.deletePresenzeRecoveryAdjustment(TOKEN, "");
  });
  test("reviewPresenzeRecoveryAdjustment: populated and empty optional values", async () => {
    await api.reviewPresenzeRecoveryAdjustment(TOKEN, "value", {});
    await api.reviewPresenzeRecoveryAdjustment(TOKEN, "", FULL_OPTIONS);
  });
  test("getPresenzeBankHoursDashboard: populated and empty optional values", async () => {
    await api.getPresenzeBankHoursDashboard(TOKEN, FULL_OPTIONS);
    await api.getPresenzeBankHoursDashboard(TOKEN, false);
  });
  test("getPresenzeBankHoursCollaboratorDetail: populated and empty optional values", async () => {
    await api.getPresenzeBankHoursCollaboratorDetail(TOKEN, "value", FULL_OPTIONS);
    await api.getPresenzeBankHoursCollaboratorDetail(TOKEN, "", "");
  });
  test("listPresenzeBankHoursAdjustments: populated and empty optional values", async () => {
    await api.listPresenzeBankHoursAdjustments(TOKEN, "value", 'pending');
    await api.listPresenzeBankHoursAdjustments(TOKEN);
  });
  test("createPresenzeBankHoursAdjustment: populated and empty optional values", async () => {
    await api.createPresenzeBankHoursAdjustment(TOKEN, {});
    await api.createPresenzeBankHoursAdjustment(TOKEN, FULL_OPTIONS);
  });
  test("updatePresenzeBankHoursAdjustment: populated and empty optional values", async () => {
    await api.updatePresenzeBankHoursAdjustment(TOKEN, "value", {});
    await api.updatePresenzeBankHoursAdjustment(TOKEN, "", FULL_OPTIONS);
  });
  test("deletePresenzeBankHoursAdjustment: populated and empty optional values", async () => {
    await api.deletePresenzeBankHoursAdjustment(TOKEN, "value");
    await api.deletePresenzeBankHoursAdjustment(TOKEN, "");
  });
  test("reviewPresenzeBankHoursAdjustment: populated and empty optional values", async () => {
    await api.reviewPresenzeBankHoursAdjustment(TOKEN, "value", {});
    await api.reviewPresenzeBankHoursAdjustment(TOKEN, "", FULL_OPTIONS);
  });
  test("listPresenzeHolidays: populated and empty optional values", async () => {
    await api.listPresenzeHolidays(TOKEN, 1);
    await api.listPresenzeHolidays(TOKEN);
  });
  test("bootstrapPresenzeHolidays: populated and empty optional values", async () => {
    await api.bootstrapPresenzeHolidays(TOKEN, 1);
    await api.bootstrapPresenzeHolidays(TOKEN, 0);
  });
  test("createPresenzeHoliday: populated and empty optional values", async () => {
    await api.createPresenzeHoliday(TOKEN, {});
    await api.createPresenzeHoliday(TOKEN, FULL_OPTIONS);
  });
  test("updatePresenzeHoliday: populated and empty optional values", async () => {
    await api.updatePresenzeHoliday(TOKEN, 1, {});
    await api.updatePresenzeHoliday(TOKEN, 0, FULL_OPTIONS);
  });
  test("deletePresenzeHoliday: populated and empty optional values", async () => {
    await api.deletePresenzeHoliday(TOKEN, 1);
    await api.deletePresenzeHoliday(TOKEN, 0);
  });
  test("listPresenzeScheduleTemplates: populated and empty optional values", async () => {
    await api.listPresenzeScheduleTemplates(TOKEN);
  });
  test("createPresenzeScheduleTemplate: populated and empty optional values", async () => {
    await api.createPresenzeScheduleTemplate(TOKEN, {});
    await api.createPresenzeScheduleTemplate(TOKEN, FULL_OPTIONS);
  });
  test("updatePresenzeScheduleTemplate: populated and empty optional values", async () => {
    await api.updatePresenzeScheduleTemplate(TOKEN, 1, {});
    await api.updatePresenzeScheduleTemplate(TOKEN, 0, FULL_OPTIONS);
  });
  test("deletePresenzeScheduleTemplate: populated and empty optional values", async () => {
    await api.deletePresenzeScheduleTemplate(TOKEN, 1);
    await api.deletePresenzeScheduleTemplate(TOKEN, 0);
  });
  test("createPresenzeScheduleRule: populated and empty optional values", async () => {
    await api.createPresenzeScheduleRule(TOKEN, 1, {});
    await api.createPresenzeScheduleRule(TOKEN, 0, FULL_OPTIONS);
  });
  test("updatePresenzeScheduleRule: populated and empty optional values", async () => {
    await api.updatePresenzeScheduleRule(TOKEN, 1, {});
    await api.updatePresenzeScheduleRule(TOKEN, 0, FULL_OPTIONS);
  });
  test("deletePresenzeScheduleRule: populated and empty optional values", async () => {
    await api.deletePresenzeScheduleRule(TOKEN, 1);
    await api.deletePresenzeScheduleRule(TOKEN, 0);
  });
  test("listPresenzeCollaboratorScheduleAssignments: populated and empty optional values", async () => {
    await api.listPresenzeCollaboratorScheduleAssignments(TOKEN, "value");
    await api.listPresenzeCollaboratorScheduleAssignments(TOKEN, "");
  });
  test("createPresenzeCollaboratorScheduleAssignment: populated and empty optional values", async () => {
    await api.createPresenzeCollaboratorScheduleAssignment(TOKEN, "value", {});
    await api.createPresenzeCollaboratorScheduleAssignment(TOKEN, "", FULL_OPTIONS);
  });
  test("deletePresenzeCollaboratorScheduleAssignment: populated and empty optional values", async () => {
    await api.deletePresenzeCollaboratorScheduleAssignment(TOKEN, 1);
    await api.deletePresenzeCollaboratorScheduleAssignment(TOKEN, 0);
    await exerciseFetchErrors(() => api.deletePresenzeCollaboratorScheduleAssignment(TOKEN, 1));
  });
  test("deletePresenzeScheduleAssignment: populated and empty optional values", async () => {
    await api.deletePresenzeScheduleAssignment(TOKEN, 1);
    await api.deletePresenzeScheduleAssignment(TOKEN, 0);
  });
  test("getPresenzeScheduleBootstrapPreview: populated and empty optional values", async () => {
    await api.getPresenzeScheduleBootstrapPreview(TOKEN);
  });
  test("applyPresenzeScheduleBootstrap: populated and empty optional values", async () => {
    await api.applyPresenzeScheduleBootstrap(TOKEN, {});
    await api.applyPresenzeScheduleBootstrap(TOKEN);
  });
  test("previewPresenzeImport: populated and empty optional values", async () => {
    await api.previewPresenzeImport(TOKEN, new File(['x'], 'file.csv'));
    await api.previewPresenzeImport(TOKEN, new File([''], 'empty.csv'));
  });
  test("importPresenzeJson: populated and empty optional values", async () => {
    await api.importPresenzeJson(TOKEN, new File(['x'], 'file.csv'));
    await api.importPresenzeJson(TOKEN, new File([''], 'empty.csv'));
  });
  test("listPresenzeImportJobs: populated and empty optional values", async () => {
    await api.listPresenzeImportJobs(TOKEN);
  });
  test("getPresenzeImportJob: populated and empty optional values", async () => {
    await api.getPresenzeImportJob(TOKEN, "value");
    await api.getPresenzeImportJob(TOKEN, "");
  });
  test("createPresenzeSyncJob: populated and empty optional values", async () => {
    await api.createPresenzeSyncJob(TOKEN, {});
    await api.createPresenzeSyncJob(TOKEN, FULL_OPTIONS);
  });
  test("createPresenzeXlsmExportJob: populated and empty optional values", async () => {
    await api.createPresenzeXlsmExportJob(TOKEN, {});
    await api.createPresenzeXlsmExportJob(TOKEN, FULL_OPTIONS);
  });
  test("previewPresenzeStraordinariExport: populated and empty optional values", async () => {
    await api.previewPresenzeStraordinariExport(TOKEN, FULL_OPTIONS);
    await api.previewPresenzeStraordinariExport(TOKEN);
  });
  test("createPresenzeStraordinariExportJob: populated and empty optional values", async () => {
    await api.createPresenzeStraordinariExportJob(TOKEN, {});
    await api.createPresenzeStraordinariExportJob(TOKEN, FULL_OPTIONS);
  });
  test("getPresenzeAutoSyncConfig: populated and empty optional values", async () => {
    await api.getPresenzeAutoSyncConfig(TOKEN);
  });
  test("updatePresenzeAutoSyncConfig: populated and empty optional values", async () => {
    await api.updatePresenzeAutoSyncConfig(TOKEN, {});
    await api.updatePresenzeAutoSyncConfig(TOKEN, FULL_OPTIONS);
  });
  test("getPresenzeBankHoursGuidanceConfig: populated and empty optional values", async () => {
    await api.getPresenzeBankHoursGuidanceConfig(TOKEN);
  });
  test("updatePresenzeBankHoursGuidanceConfig: populated and empty optional values", async () => {
    await api.updatePresenzeBankHoursGuidanceConfig(TOKEN, {});
    await api.updatePresenzeBankHoursGuidanceConfig(TOKEN, FULL_OPTIONS);
  });
  test("listPresenzeBankHoursGuidanceConfigHistory: populated and empty optional values", async () => {
    await api.listPresenzeBankHoursGuidanceConfigHistory(TOKEN);
  });
  test("listPresenzeSyncJobs: populated and empty optional values", async () => {
    await api.listPresenzeSyncJobs(TOKEN, FULL_OPTIONS);
    await api.listPresenzeSyncJobs(TOKEN);
  });
  test("getPresenzeSyncJob: populated and empty optional values", async () => {
    await api.getPresenzeSyncJob(TOKEN, "value");
    await api.getPresenzeSyncJob(TOKEN, "");
  });
  test("listPresenzeXlsmExportJobs: populated and empty optional values", async () => {
    await api.listPresenzeXlsmExportJobs(TOKEN, FULL_OPTIONS);
    await api.listPresenzeXlsmExportJobs(TOKEN);
  });
  test("getPresenzeXlsmExportJob: populated and empty optional values", async () => {
    await api.getPresenzeXlsmExportJob(TOKEN, "value");
    await api.getPresenzeXlsmExportJob(TOKEN, "");
  });
  test("listPresenzeStraordinariExportJobs: populated and empty optional values", async () => {
    await api.listPresenzeStraordinariExportJobs(TOKEN, FULL_OPTIONS);
    await api.listPresenzeStraordinariExportJobs(TOKEN);
  });
  test("getPresenzeStraordinariExportJob: populated and empty optional values", async () => {
    await api.getPresenzeStraordinariExportJob(TOKEN, "value");
    await api.getPresenzeStraordinariExportJob(TOKEN, "");
  });
  test("deletePresenzeStraordinariExportJob: populated and empty optional values", async () => {
    await api.deletePresenzeStraordinariExportJob(TOKEN, "value");
    await api.deletePresenzeStraordinariExportJob(TOKEN, "");
  });
  test("downloadPresenzeStraordinariExportArtifact: populated and empty optional values", async () => {
    await api.downloadPresenzeStraordinariExportArtifact(TOKEN, "value", 'xlsx');
    await api.downloadPresenzeStraordinariExportArtifact(TOKEN, "", 'xlsx');
  });
  test("deletePresenzeXlsmExportJob: populated and empty optional values", async () => {
    await api.deletePresenzeXlsmExportJob(TOKEN, "value");
    await api.deletePresenzeXlsmExportJob(TOKEN, "");
  });
  test("downloadPresenzeXlsmExportArtifact: populated and empty optional values", async () => {
    await api.downloadPresenzeXlsmExportArtifact(TOKEN, "value", 'xlsm');
    await api.downloadPresenzeXlsmExportArtifact(TOKEN, "", 'xlsm');
  });
  test("retryPresenzeSyncJob: populated and empty optional values", async () => {
    await api.retryPresenzeSyncJob(TOKEN, "value");
    await api.retryPresenzeSyncJob(TOKEN, "");
  });
  test("retrySelectedPresenzeSyncJob: populated and empty optional values", async () => {
    await api.retrySelectedPresenzeSyncJob(TOKEN, "value", {});
    await api.retrySelectedPresenzeSyncJob(TOKEN, "", FULL_OPTIONS);
  });
  test("cancelPresenzeSyncJob: populated and empty optional values", async () => {
    await api.cancelPresenzeSyncJob(TOKEN, "value");
    await api.cancelPresenzeSyncJob(TOKEN, "");
  });
  test("deletePresenzeSyncJob: populated and empty optional values", async () => {
    await api.deletePresenzeSyncJob(TOKEN, "value");
    await api.deletePresenzeSyncJob(TOKEN, "");
  });
  test("downloadPresenzeSyncArtifact: populated and empty optional values", async () => {
    await api.downloadPresenzeSyncArtifact(TOKEN, "value", 'json');
    await api.downloadPresenzeSyncArtifact(TOKEN, "", 'json');
  });
  test("exportPresenzeXlsm: populated and empty optional values", async () => {
    await api.exportPresenzeXlsm(TOKEN, ["value"]);
    await api.exportPresenzeXlsm(TOKEN, []);
  });
  test("getWikiToolAuditLogs: populated and empty optional values", async () => {
    await api.getWikiToolAuditLogs(TOKEN, FULL_OPTIONS);
    await api.getWikiToolAuditLogs(TOKEN);
  });
  test("getWikiRequests: populated and empty optional values", async () => {
    await api.getWikiRequests(TOKEN);
  });
  test("getWikiRequest: populated and empty optional values", async () => {
    await api.getWikiRequest(TOKEN, "value");
    await api.getWikiRequest(TOKEN, "");
  });
  test("getWikiRequestArtifacts: populated and empty optional values", async () => {
    await api.getWikiRequestArtifacts(TOKEN, "value");
    await api.getWikiRequestArtifacts(TOKEN, "");
  });
  test("downloadWikiRequestArtifact: populated and empty optional values", async () => {
    await api.downloadWikiRequestArtifact(TOKEN, "value", "value");
    await api.downloadWikiRequestArtifact(TOKEN, "", "");
    await exerciseFetchErrors(() => api.downloadWikiRequestArtifact(TOKEN, "value", "value"));
  });
  test("getWikiRequestAssignees: populated and empty optional values", async () => {
    await api.getWikiRequestAssignees(TOKEN);
  });
  test("getWikiRequestEvents: populated and empty optional values", async () => {
    await api.getWikiRequestEvents(TOKEN, "value");
    await api.getWikiRequestEvents(TOKEN, "");
  });
  test("getWikiRequestDuplicates: populated and empty optional values", async () => {
    await api.getWikiRequestDuplicates(TOKEN, "value");
    await api.getWikiRequestDuplicates(TOKEN, "");
  });
  test("getWikiRequestLinkedDuplicates: populated and empty optional values", async () => {
    await api.getWikiRequestLinkedDuplicates(TOKEN, "value");
    await api.getWikiRequestLinkedDuplicates(TOKEN, "");
  });
  test("getWikiRequestFamily: populated and empty optional values", async () => {
    await api.getWikiRequestFamily(TOKEN, "value");
    await api.getWikiRequestFamily(TOKEN, "");
  });
  test("getMyWikiRequests: populated and empty optional values", async () => {
    await api.getMyWikiRequests(TOKEN);
  });
  test("getMyWikiRequestsSummary: populated and empty optional values", async () => {
    await api.getMyWikiRequestsSummary(TOKEN);
  });
  test("markWikiRequestViewed: populated and empty optional values", async () => {
    await api.markWikiRequestViewed(TOKEN, "value");
    await api.markWikiRequestViewed(TOKEN, "");
  });
  test("reopenWikiRequest: populated and empty optional values", async () => {
    await api.reopenWikiRequest(TOKEN, "value", {});
    await api.reopenWikiRequest(TOKEN, "", FULL_OPTIONS);
  });
  test("createWikiRequest: populated and empty optional values", async () => {
    await api.createWikiRequest(TOKEN, {});
    await api.createWikiRequest(TOKEN, FULL_OPTIONS);
  });
  test("createWikiRequestWithArtifacts: populated and empty optional values", async () => {
    await api.createWikiRequestWithArtifacts(TOKEN, {}, {});
    await api.createWikiRequestWithArtifacts(TOKEN, FULL_OPTIONS, FULL_OPTIONS);
  });
  test("updateWikiRequest: populated and empty optional values", async () => {
    await api.updateWikiRequest(TOKEN, "value", {});
    await api.updateWikiRequest(TOKEN, "", FULL_OPTIONS);
  });
  test("markWikiRequestDuplicate: populated and empty optional values", async () => {
    await api.markWikiRequestDuplicate(TOKEN, "value", {});
    await api.markWikiRequestDuplicate(TOKEN, "", FULL_OPTIONS);
  });
  test("unlinkWikiRequestDuplicate: populated and empty optional values", async () => {
    await api.unlinkWikiRequestDuplicate(TOKEN, "value");
    await api.unlinkWikiRequestDuplicate(TOKEN, "");
  });
  test("makeWikiRequestCanonical: populated and empty optional values", async () => {
    await api.makeWikiRequestCanonical(TOKEN, "value", {});
    await api.makeWikiRequestCanonical(TOKEN, "");
  });
  test("updateWikiRequestFeedback: populated and empty optional values", async () => {
    await api.updateWikiRequestFeedback(TOKEN, "value", {});
    await api.updateWikiRequestFeedback(TOKEN, "", FULL_OPTIONS);
  });
  test("getWikiSupportAnalyticsSummary: populated and empty optional values", async () => {
    await api.getWikiSupportAnalyticsSummary(TOKEN, FULL_OPTIONS);
    await api.getWikiSupportAnalyticsSummary(TOKEN);
  });
  test("getWikiSupportAnalyticsSeries: populated and empty optional values", async () => {
    await api.getWikiSupportAnalyticsSeries(TOKEN, FULL_OPTIONS);
    await api.getWikiSupportAnalyticsSeries(TOKEN);
  });
  test("getWikiSupportAnalyticsClusters: populated and empty optional values", async () => {
    await api.getWikiSupportAnalyticsClusters(TOKEN, FULL_OPTIONS);
    await api.getWikiSupportAnalyticsClusters(TOKEN);
  });
  test("getWikiSupportAnalyticsInsights: populated and empty optional values", async () => {
    await api.getWikiSupportAnalyticsInsights(TOKEN, FULL_OPTIONS);
    await api.getWikiSupportAnalyticsInsights(TOKEN);
  });
  test("getWikiToolAuditSummary: populated and empty optional values", async () => {
    await api.getWikiToolAuditSummary(TOKEN, FULL_OPTIONS);
    await api.getWikiToolAuditSummary(TOKEN);
  });
  test("getWikiToolAuditLogDetail: populated and empty optional values", async () => {
    await api.getWikiToolAuditLogDetail(TOKEN, "value");
    await api.getWikiToolAuditLogDetail(TOKEN, "");
  });
  test("getWikiToolAuditRelatedLogs: populated and empty optional values", async () => {
    await api.getWikiToolAuditRelatedLogs(TOKEN, "value", FULL_OPTIONS);
    await api.getWikiToolAuditRelatedLogs(TOKEN, "");
  });
  test("exportWikiToolAuditLogs: populated and empty optional values", async () => {
    await api.exportWikiToolAuditLogs(TOKEN, FULL_OPTIONS);
    await api.exportWikiToolAuditLogs(TOKEN);
  });
  test("getWikiTelemetrySummary: populated and empty optional values", async () => {
    await api.getWikiTelemetrySummary(TOKEN, FULL_OPTIONS);
    await api.getWikiTelemetrySummary(TOKEN);
  });
  test("getWikiTelemetrySeries: populated and empty optional values", async () => {
    await api.getWikiTelemetrySeries(TOKEN, FULL_OPTIONS);
    await api.getWikiTelemetrySeries(TOKEN);
  });
  test("refreshWikiTelemetry: populated and empty optional values", async () => {
    await api.refreshWikiTelemetry(TOKEN, FULL_OPTIONS);
    await api.refreshWikiTelemetry(TOKEN);
  });
  test("getWikiTelemetrySchedule: populated and empty optional values", async () => {
    await api.getWikiTelemetrySchedule(TOKEN);
  });
  test("getWikiTelemetryRetention: populated and empty optional values", async () => {
    await api.getWikiTelemetryRetention(TOKEN);
  });
  test("pruneWikiTelemetry: populated and empty optional values", async () => {
    await api.pruneWikiTelemetry(TOKEN);
  });
  test("exportWikiTelemetrySeries: populated and empty optional values", async () => {
    await api.exportWikiTelemetrySeries(TOKEN, FULL_OPTIONS);
    await api.exportWikiTelemetrySeries(TOKEN);
  });
  test("getWikiConversationMetricsSummary: populated and empty optional values", async () => {
    await api.getWikiConversationMetricsSummary(TOKEN, FULL_OPTIONS);
    await api.getWikiConversationMetricsSummary(TOKEN);
  });
  test("getWikiConversationMetricsSeries: populated and empty optional values", async () => {
    await api.getWikiConversationMetricsSeries(TOKEN, FULL_OPTIONS);
    await api.getWikiConversationMetricsSeries(TOKEN);
  });
  test("getWikiConversations: populated and empty optional values", async () => {
    await api.getWikiConversations(TOKEN, FULL_OPTIONS);
    await api.getWikiConversations(TOKEN);
  });
  test("getWikiConversationSummary: populated and empty optional values", async () => {
    await api.getWikiConversationSummary(TOKEN);
  });
  test("getWikiConversationDetail: populated and empty optional values", async () => {
    await api.getWikiConversationDetail(TOKEN, "value");
    await api.getWikiConversationDetail(TOKEN, "");
  });
  test("updateWikiConversation: populated and empty optional values", async () => {
    await api.updateWikiConversation(TOKEN, "value", 'status');
    await api.updateWikiConversation(TOKEN, "", 'status');
  });
  test("resolveWikiConversationContextLink: populated and empty optional values", async () => {
    await api.resolveWikiConversationContextLink(TOKEN, FULL_OPTIONS);
    await api.resolveWikiConversationContextLink(TOKEN);
  });
  test("getWikiConversationGovernanceConfig: populated and empty optional values", async () => {
    await api.getWikiConversationGovernanceConfig(TOKEN);
  });
  test("updateWikiConversationGovernanceConfig: populated and empty optional values", async () => {
    await api.updateWikiConversationGovernanceConfig(TOKEN, 1);
    await api.updateWikiConversationGovernanceConfig(TOKEN, 0);
  });
  test("backfillWikiConversationMetrics: populated and empty optional values", async () => {
    await api.backfillWikiConversationMetrics(TOKEN, "value");
    await api.backfillWikiConversationMetrics(TOKEN, "");
  });
  test("enqueueWikiConversationMetricsBackfill: populated and empty optional values", async () => {
    await api.enqueueWikiConversationMetricsBackfill(TOKEN, "value");
    await api.enqueueWikiConversationMetricsBackfill(TOKEN, "");
  });
  test("getLatestWikiConversationMetricsBackfillJob: populated and empty optional values", async () => {
    await api.getLatestWikiConversationMetricsBackfillJob(TOKEN);
  });
  test("listWikiConversationMetricsBackfillJobChains: populated and empty optional values", async () => {
    await api.listWikiConversationMetricsBackfillJobChains(TOKEN, 1, FULL_OPTIONS);
    await api.listWikiConversationMetricsBackfillJobChains(TOKEN);
  });
  test("getWikiConversationMetricsBackfillJobChainSummary: populated and empty optional values", async () => {
    await api.getWikiConversationMetricsBackfillJobChainSummary(TOKEN, FULL_OPTIONS);
    await api.getWikiConversationMetricsBackfillJobChainSummary(TOKEN);
  });
  test("getWikiConversationMetricsBackfillJobChainDetail: populated and empty optional values", async () => {
    await api.getWikiConversationMetricsBackfillJobChainDetail(TOKEN, "value");
    await api.getWikiConversationMetricsBackfillJobChainDetail(TOKEN, "");
  });
  test("retryWikiConversationMetricsBackfillJob: populated and empty optional values", async () => {
    await api.retryWikiConversationMetricsBackfillJob(TOKEN, "value");
    await api.retryWikiConversationMetricsBackfillJob(TOKEN, "");
  });
  test("clearWikiConversationMetricsBackfillJobHistory: populated and empty optional values", async () => {
    await api.clearWikiConversationMetricsBackfillJobHistory(TOKEN);
  });
  test("getNetworkDashboard: populated and empty optional values", async () => {
    await api.getNetworkDashboard(TOKEN);
  });
  test("getNetworkStatistics: populated and empty optional values", async () => {
    await api.getNetworkStatistics(TOKEN, FULL_OPTIONS);
    await api.getNetworkStatistics(TOKEN);
  });
  test("getNetworkDevices: populated and empty optional values", async () => {
    await api.getNetworkDevices(TOKEN, FULL_OPTIONS);
    await api.getNetworkDevices(TOKEN);
    await api.getNetworkDevices(TOKEN, FALSE_OPTIONS);
  });
  test("getNetworkDevice: populated and empty optional values", async () => {
    await api.getNetworkDevice(TOKEN, 1);
    await api.getNetworkDevice(TOKEN, 0);
  });
  test("listNetworkDeviceAssignees: populated and empty optional values", async () => {
    await api.listNetworkDeviceAssignees(TOKEN);
  });
  test("listNetworkTrackedSubjects: populated and empty optional values", async () => {
    await api.listNetworkTrackedSubjects(TOKEN, FULL_OPTIONS);
    await api.listNetworkTrackedSubjects(TOKEN);
    await api.listNetworkTrackedSubjects(TOKEN, FALSE_OPTIONS);
  });
  test("createNetworkTrackedSubject: populated and empty optional values", async () => {
    await api.createNetworkTrackedSubject(TOKEN, {});
    await api.createNetworkTrackedSubject(TOKEN, FULL_OPTIONS);
  });
  test("updateNetworkTrackedSubject: populated and empty optional values", async () => {
    await api.updateNetworkTrackedSubject(TOKEN, 1, {});
    await api.updateNetworkTrackedSubject(TOKEN, 0, FULL_OPTIONS);
  });
  test("getNetworkIpWhois: populated and empty optional values", async () => {
    await api.getNetworkIpWhois(TOKEN, "value");
    await api.getNetworkIpWhois(TOKEN, "");
  });
  test("getNetworkTrackedSubjectActivities: populated and empty optional values", async () => {
    await api.getNetworkTrackedSubjectActivities(TOKEN, 1, FULL_OPTIONS);
    await api.getNetworkTrackedSubjectActivities(TOKEN, 0);
    await api.getNetworkTrackedSubjectActivities(TOKEN, 1, FALSE_OPTIONS);
  });
  test("getNetworkDetectionWatchlist: populated and empty optional values", async () => {
    await api.getNetworkDetectionWatchlist(TOKEN);
  });
  test("createNetworkDetectionWatchlistRule: populated and empty optional values", async () => {
    await api.createNetworkDetectionWatchlistRule(TOKEN, {});
    await api.createNetworkDetectionWatchlistRule(TOKEN, FULL_OPTIONS);
  });
  test("updateNetworkDetectionWatchlistRule: populated and empty optional values", async () => {
    await api.updateNetworkDetectionWatchlistRule(TOKEN, 1, {});
    await api.updateNetworkDetectionWatchlistRule(TOKEN, 0, FULL_OPTIONS);
  });
  test("getNetworkVpnBypassSummary: populated and empty optional values", async () => {
    await api.getNetworkVpnBypassSummary(TOKEN, FULL_OPTIONS);
    await api.getNetworkVpnBypassSummary(TOKEN);
    await api.getNetworkVpnBypassSummary(TOKEN, FALSE_OPTIONS);
  });
  test("getNetworkVpnBypassArpTimeline: populated and empty optional values", async () => {
    await api.getNetworkVpnBypassArpTimeline(TOKEN, FULL_OPTIONS);
    await api.getNetworkVpnBypassArpTimeline(TOKEN);
    await api.getNetworkVpnBypassArpTimeline(TOKEN, FALSE_OPTIONS);
  });
  test("listNetworkVpnAccessDevices: populated and empty optional values", async () => {
    await api.listNetworkVpnAccessDevices(TOKEN, FULL_OPTIONS);
    await api.listNetworkVpnAccessDevices(TOKEN);
    await api.listNetworkVpnAccessDevices(TOKEN, FALSE_OPTIONS);
  });
  test("listNetworkVpnAccessSessions: populated and empty optional values", async () => {
    await api.listNetworkVpnAccessSessions(TOKEN, FULL_OPTIONS);
    await api.listNetworkVpnAccessSessions(TOKEN);
    await api.listNetworkVpnAccessSessions(TOKEN, FALSE_OPTIONS);
  });
  test("updateNetworkVpnAccessDeviceStatus: populated and empty optional values", async () => {
    await api.updateNetworkVpnAccessDeviceStatus(TOKEN, 1, {});
    await api.updateNetworkVpnAccessDeviceStatus(TOKEN, 0, FULL_OPTIONS);
  });
  test("updateNetworkDevice: populated and empty optional values", async () => {
    await api.updateNetworkDevice(TOKEN, 1, {});
    await api.updateNetworkDevice(TOKEN, 0, FULL_OPTIONS);
  });
  test("bulkUpdateNetworkDevices: populated and empty optional values", async () => {
    await api.bulkUpdateNetworkDevices(TOKEN, {});
    await api.bulkUpdateNetworkDevices(TOKEN, FULL_OPTIONS);
  });
  test("getNetworkAlerts: populated and empty optional values", async () => {
    await api.getNetworkAlerts(TOKEN);
  });
  test("getNetworkFirewalls: populated and empty optional values", async () => {
    await api.getNetworkFirewalls(TOKEN);
  });
  test("getNetworkSophosConfig: populated and empty optional values", async () => {
    await api.getNetworkSophosConfig(TOKEN);
  });
  test("updateNetworkSophosConfig: populated and empty optional values", async () => {
    await api.updateNetworkSophosConfig(TOKEN, {});
    await api.updateNetworkSophosConfig(TOKEN, FULL_OPTIONS);
  });
  test("getNetworkFirewallEvents: populated and empty optional values", async () => {
    await api.getNetworkFirewallEvents(TOKEN, 1, FULL_OPTIONS);
    await api.getNetworkFirewallEvents(TOKEN, 0);
    await api.getNetworkFirewallEvents(TOKEN, 1, FALSE_OPTIONS);
  });
  test("getNetworkFirewallLogCoverage: populated and empty optional values", async () => {
    await api.getNetworkFirewallLogCoverage(TOKEN, 1, FULL_OPTIONS);
    await api.getNetworkFirewallLogCoverage(TOKEN, 0);
  });
  test("getNetworkFirewallMetrics: populated and empty optional values", async () => {
    await api.getNetworkFirewallMetrics(TOKEN, 1, FULL_OPTIONS);
    await api.getNetworkFirewallMetrics(TOKEN, 0);
    await api.getNetworkFirewallMetrics(TOKEN, 1, FALSE_OPTIONS);
  });
  test("pollNetworkFirewallMetrics: populated and empty optional values", async () => {
    await api.pollNetworkFirewallMetrics(TOKEN, 1);
    await api.pollNetworkFirewallMetrics(TOKEN, 0);
  });
  test("updateNetworkAlert: populated and empty optional values", async () => {
    await api.updateNetworkAlert(TOKEN, 1, {});
    await api.updateNetworkAlert(TOKEN, 0, FULL_OPTIONS);
  });
  test("getNetworkScans: populated and empty optional values", async () => {
    await api.getNetworkScans(TOKEN);
  });
  test("getNetworkScan: populated and empty optional values", async () => {
    await api.getNetworkScan(TOKEN, 1);
    await api.getNetworkScan(TOKEN, 0);
  });
  test("getNetworkScanDiff: populated and empty optional values", async () => {
    await api.getNetworkScanDiff(TOKEN, 1, 1);
    await api.getNetworkScanDiff(TOKEN, 0, 0);
  });
  test("triggerNetworkScan: populated and empty optional values", async () => {
    await api.triggerNetworkScan(TOKEN, {});
    await api.triggerNetworkScan(TOKEN);
  });
  test("getNetworkFloorPlans: populated and empty optional values", async () => {
    await api.getNetworkFloorPlans(TOKEN);
  });
  test("createNetworkFloorPlan: populated and empty optional values", async () => {
    await api.createNetworkFloorPlan(TOKEN, {});
    await api.createNetworkFloorPlan(TOKEN, FULL_OPTIONS);
  });
  test("getNetworkFloorPlan: populated and empty optional values", async () => {
    await api.getNetworkFloorPlan(TOKEN, 1);
    await api.getNetworkFloorPlan(TOKEN, 0);
  });
  test("getNetworkFloorPlanDevices: populated and empty optional values", async () => {
    await api.getNetworkFloorPlanDevices(TOKEN, 1);
    await api.getNetworkFloorPlanDevices(TOKEN, 0);
  });
  test("updateNetworkDevicePosition: populated and empty optional values", async () => {
    await api.updateNetworkDevicePosition(TOKEN, 1, {});
    await api.updateNetworkDevicePosition(TOKEN, 0, FULL_OPTIONS);
  });
  test("getAnagraficaStats: populated and empty optional values", async () => {
    await api.getAnagraficaStats(TOKEN);
  });
  test("getAnagraficaDocumentSummary: populated and empty optional values", async () => {
    await api.getAnagraficaDocumentSummary(TOKEN);
  });
  test("getAnagraficaSubjects: populated and empty optional values", async () => {
    await api.getAnagraficaSubjects(TOKEN, FULL_OPTIONS);
    await api.getAnagraficaSubjects(TOKEN);
    await api.getAnagraficaSubjects(TOKEN, FALSE_OPTIONS);
  });
  test("getAnagraficaSubject: populated and empty optional values", async () => {
    await api.getAnagraficaSubject(TOKEN, "value");
    await api.getAnagraficaSubject(TOKEN, "");
  });
  test("createAnagraficaSubject: populated and empty optional values", async () => {
    await api.createAnagraficaSubject(TOKEN, {});
    await api.createAnagraficaSubject(TOKEN, FULL_OPTIONS);
  });
  test("importAnagraficaSubjectsCsv: populated and empty optional values", async () => {
    {
      const pending = api.importAnagraficaSubjectsCsv(TOKEN, new File(['x'], 'file.csv'), () => undefined);
      MockXHR.instances.at(-1)!.loadHandler?.();
      await pending;
    }
    {
      const pending = api.importAnagraficaSubjectsCsv(TOKEN, new File([''], 'empty.csv'));
      MockXHR.instances.at(-1)!.loadHandler?.();
      await pending;
    }
  });
  test("importUtenzeSubjectsXlsx: populated and empty optional values", async () => {
    {
      const pending = api.importUtenzeSubjectsXlsx(TOKEN, new File(['x'], 'file.csv'), () => undefined);
      MockXHR.instances.at(-1)!.loadHandler?.();
      await pending;
    }
    {
      const pending = api.importUtenzeSubjectsXlsx(TOKEN, new File([''], 'empty.csv'));
      MockXHR.instances.at(-1)!.loadHandler?.();
      await pending;
    }
  });
  test("getUtenzeXlsxImportBatch: populated and empty optional values", async () => {
    await api.getUtenzeXlsxImportBatch(TOKEN, "value");
    await api.getUtenzeXlsxImportBatch(TOKEN, "");
  });
  test("getUtenzeXlsxImportBatches: populated and empty optional values", async () => {
    await api.getUtenzeXlsxImportBatches(TOKEN);
  });
  test("getUtenzeSubjectAuditLog: populated and empty optional values", async () => {
    await api.getUtenzeSubjectAuditLog(TOKEN, "value");
    await api.getUtenzeSubjectAuditLog(TOKEN, "");
  });
  test("getUtenzeSubjectPaymentNotices: populated and empty optional values", async () => {
    await api.getUtenzeSubjectPaymentNotices(TOKEN, "value");
    await api.getUtenzeSubjectPaymentNotices(TOKEN, "");
  });
  test("getUtenzeAnprStatus: populated and empty optional values", async () => {
    await api.getUtenzeAnprStatus(TOKEN, "value");
    await api.getUtenzeAnprStatus(TOKEN, "");
  });
  test("syncUtenzeAnprSubject: populated and empty optional values", async () => {
    await api.syncUtenzeAnprSubject(TOKEN, "value");
    await api.syncUtenzeAnprSubject(TOKEN, "");
  });
  test("verifyUtenzeAnprAlive: populated and empty optional values", async () => {
    await api.verifyUtenzeAnprAlive(TOKEN, "value");
    await api.verifyUtenzeAnprAlive(TOKEN, "");
  });
  test("verifyUtenzeAnprDeathDate: populated and empty optional values", async () => {
    await api.verifyUtenzeAnprDeathDate(TOKEN, "value");
    await api.verifyUtenzeAnprDeathDate(TOKEN, "");
  });
  test("previewLookupUtenzeAnprByCf: populated and empty optional values", async () => {
    await api.previewLookupUtenzeAnprByCf(TOKEN, "value");
    await api.previewLookupUtenzeAnprByCf(TOKEN, "");
  });
  test("getUtenzeAnprConfig: populated and empty optional values", async () => {
    await api.getUtenzeAnprConfig(TOKEN);
  });
  test("updateUtenzeAnprConfig: populated and empty optional values", async () => {
    await api.updateUtenzeAnprConfig(TOKEN, {});
    await api.updateUtenzeAnprConfig(TOKEN, FULL_OPTIONS);
  });
  test("getUtenzeAnprJobStatus: populated and empty optional values", async () => {
    await api.getUtenzeAnprJobStatus(TOKEN);
  });
  test("triggerUtenzeAnprJob: populated and empty optional values", async () => {
    await api.triggerUtenzeAnprJob(TOKEN);
  });
  test("updateAnagraficaSubject: populated and empty optional values", async () => {
    await api.updateAnagraficaSubject(TOKEN, "value", {});
    await api.updateAnagraficaSubject(TOKEN, "", FULL_OPTIONS);
  });
  test("deactivateAnagraficaSubject: populated and empty optional values", async () => {
    await api.deactivateAnagraficaSubject(TOKEN, "value");
    await api.deactivateAnagraficaSubject(TOKEN, "");
  });
  test("getAnagraficaSubjectDocuments: populated and empty optional values", async () => {
    await api.getAnagraficaSubjectDocuments(TOKEN, "value");
    await api.getAnagraficaSubjectDocuments(TOKEN, "");
  });
  test("updateAnagraficaDocument: populated and empty optional values", async () => {
    await api.updateAnagraficaDocument(TOKEN, "value", "value");
    await api.updateAnagraficaDocument(TOKEN, "", "");
  });
  test("classifyAnagraficaDocumentContent: populated and empty optional values", async () => {
    await api.classifyAnagraficaDocumentContent(TOKEN, "value", "value");
    await api.classifyAnagraficaDocumentContent(TOKEN, "");
  });
  test("deleteAnagraficaDocument: populated and empty optional values", async () => {
    await api.deleteAnagraficaDocument(TOKEN, "value", "value");
    await api.deleteAnagraficaDocument(TOKEN, "");
    await exerciseFetchErrors(() => api.deleteAnagraficaDocument(TOKEN, "value", "value"));
  });
  test("downloadAnagraficaDocumentBlob: populated and empty optional values", async () => {
    await api.downloadAnagraficaDocumentBlob(TOKEN, "value");
    await api.downloadAnagraficaDocumentBlob(TOKEN, "");
  });
  test("downloadAnagraficaExportBlob: populated and empty optional values", async () => {
    await api.downloadAnagraficaExportBlob(TOKEN, FULL_OPTIONS);
    await api.downloadAnagraficaExportBlob(TOKEN);
    await api.downloadAnagraficaExportBlob(TOKEN, FALSE_OPTIONS);
  });
  test("previewAnagraficaImport: populated and empty optional values", async () => {
    await api.previewAnagraficaImport(TOKEN, "value");
    await api.previewAnagraficaImport(TOKEN);
  });
  test("runAnagraficaImport: populated and empty optional values", async () => {
    await api.runAnagraficaImport(TOKEN, "value");
    await api.runAnagraficaImport(TOKEN);
  });
  test("runAnagraficaImportFromSubjects: populated and empty optional values", async () => {
    await api.runAnagraficaImportFromSubjects(TOKEN);
  });
  test("getAnagraficaImportJobs: populated and empty optional values", async () => {
    await api.getAnagraficaImportJobs(TOKEN);
  });
  test("getUtenzeVisureRoutingAnomalies: populated and empty optional values", async () => {
    await api.getUtenzeVisureRoutingAnomalies(TOKEN, FULL_OPTIONS);
    await api.getUtenzeVisureRoutingAnomalies(TOKEN);
    await api.getUtenzeVisureRoutingAnomalies(TOKEN, FALSE_OPTIONS);
  });
  test("getAnagraficaImportJob: populated and empty optional values", async () => {
    await api.getAnagraficaImportJob(TOKEN, "value");
    await api.getAnagraficaImportJob(TOKEN, "");
  });
  test("resolveUtenzeVisureRoutingAnomaly: populated and empty optional values", async () => {
    await api.resolveUtenzeVisureRoutingAnomaly(TOKEN, "value");
    await api.resolveUtenzeVisureRoutingAnomaly(TOKEN, "");
  });
  test("abortUtenzeRegistryImportJob: populated and empty optional values", async () => {
    await api.abortUtenzeRegistryImportJob(TOKEN, "value");
    await api.abortUtenzeRegistryImportJob(TOKEN, "");
  });
  test("resumeUtenzeRegistryImportJob: populated and empty optional values", async () => {
    await api.resumeUtenzeRegistryImportJob(TOKEN, "value");
    await api.resumeUtenzeRegistryImportJob(TOKEN, "");
  });
  test("deleteUtenzeRegistryImportJob: populated and empty optional values", async () => {
    await api.deleteUtenzeRegistryImportJob(TOKEN, "value");
    await api.deleteUtenzeRegistryImportJob(TOKEN, "");
  });
  test("resumeAnagraficaImportJob: populated and empty optional values", async () => {
    await api.resumeAnagraficaImportJob(TOKEN, "value");
    await api.resumeAnagraficaImportJob(TOKEN, "");
  });
  test("searchAnagraficaSubjects: populated and empty optional values", async () => {
    await api.searchAnagraficaSubjects(TOKEN, "value", 1);
    await api.searchAnagraficaSubjects(TOKEN, "");
  });
  test("importAnagraficaSubjectFromNas: populated and empty optional values", async () => {
    await api.importAnagraficaSubjectFromNas(TOKEN, "value");
    await api.importAnagraficaSubjectFromNas(TOKEN, "");
  });
  test("getAnagraficaSubjectNasCandidates: populated and empty optional values", async () => {
    await api.getAnagraficaSubjectNasCandidates(TOKEN, "value", 1);
    await api.getAnagraficaSubjectNasCandidates(TOKEN, "");
  });
  test("getAnagraficaSubjectNasImportStatus: populated and empty optional values", async () => {
    await api.getAnagraficaSubjectNasImportStatus(TOKEN, "value");
    await api.getAnagraficaSubjectNasImportStatus(TOKEN, "");
  });
  test("uploadAnagraficaSubjectDocument: populated and empty optional values", async () => {
    await api.uploadAnagraficaSubjectDocument(TOKEN, "value", new File(['x'], 'file.csv'), "value", "value");
    await api.uploadAnagraficaSubjectDocument(TOKEN, "", new File([''], 'empty.csv'), "");
  });
  test("resetAnagraficaData: populated and empty optional values", async () => {
    await api.resetAnagraficaData(TOKEN, {});
    await api.resetAnagraficaData(TOKEN);
  });
  test("getReviews: populated and empty optional values", async () => {
    await api.getReviews(TOKEN);
  });
  test("getSyncCapabilities: populated and empty optional values", async () => {
    await api.getSyncCapabilities(TOKEN);
  });
  test("previewSync: populated and empty optional values", async () => {
    await api.previewSync(TOKEN, {});
    await api.previewSync(TOKEN, FULL_OPTIONS);
  });
  test("applySync: populated and empty optional values", async () => {
    await api.applySync(TOKEN, {});
    await api.applySync(TOKEN, FULL_OPTIONS);
  });
  test("createSyncJob: populated and empty optional values", async () => {
    await api.createSyncJob(TOKEN, 'quick');
    await api.createSyncJob(TOKEN);
  });
  test("getSyncRuns: populated and empty optional values", async () => {
    await api.getSyncRuns(TOKEN);
  });
  test("getSyncJobs: populated and empty optional values", async () => {
    await api.getSyncJobs(TOKEN);
  });
  test("retrySyncJob: populated and empty optional values", async () => {
    await api.retrySyncJob(TOKEN, 1);
    await api.retrySyncJob(TOKEN, 0);
  });
  test("cancelSyncJob: populated and empty optional values", async () => {
    await api.cancelSyncJob(TOKEN, 1);
    await api.cancelSyncJob(TOKEN, 0);
  });
  test("getEffectivePermissions: populated and empty optional values", async () => {
    await api.getEffectivePermissions(TOKEN);
  });
  test("calculatePermissionPreview: populated and empty optional values", async () => {
    await api.calculatePermissionPreview(TOKEN, [FULL_OPTIONS], [FULL_OPTIONS]);
    await api.calculatePermissionPreview(TOKEN, [], []);
  });
  test("getElaborazioneCredentials: populated and empty optional values", async () => {
    await api.getElaborazioneCredentials(TOKEN);
  });
  test("saveElaborazioneCredentials: populated and empty optional values", async () => {
    await api.saveElaborazioneCredentials(TOKEN, true);
    await api.saveElaborazioneCredentials(TOKEN, false);
  });
  test("updateElaborazioneCredential: populated and empty optional values", async () => {
    await api.updateElaborazioneCredential(TOKEN, "value", true);
    await api.updateElaborazioneCredential(TOKEN, "", false);
  });
  test("deleteElaborazioneCredentials: populated and empty optional values", async () => {
    await api.deleteElaborazioneCredentials(TOKEN);
  });
  test("deleteElaborazioneCredential: populated and empty optional values", async () => {
    await api.deleteElaborazioneCredential(TOKEN, "value");
    await api.deleteElaborazioneCredential(TOKEN, "");
  });
  test("releaseElaborazioneCredentials: populated and empty optional values", async () => {
    await api.releaseElaborazioneCredentials(TOKEN);
  });
  test("testElaborazioneCredentials: populated and empty optional values", async () => {
    await api.testElaborazioneCredentials(TOKEN, "value");
    await api.testElaborazioneCredentials(TOKEN);
  });
  test("getElaborazioneCredentialTest: populated and empty optional values", async () => {
    await api.getElaborazioneCredentialTest(TOKEN, "value");
    await api.getElaborazioneCredentialTest(TOKEN, "");
  });
  test("listCapacitasCredentials: populated and empty optional values", async () => {
    await api.listCapacitasCredentials(TOKEN);
  });
  test("createCapacitasCredential: populated and empty optional values", async () => {
    await api.createCapacitasCredential(TOKEN, {});
    await api.createCapacitasCredential(TOKEN, FULL_OPTIONS);
  });
  test("updateCapacitasCredential: populated and empty optional values", async () => {
    await api.updateCapacitasCredential(TOKEN, 1, {});
    await api.updateCapacitasCredential(TOKEN, 0, FULL_OPTIONS);
  });
  test("deleteCapacitasCredential: populated and empty optional values", async () => {
    await api.deleteCapacitasCredential(TOKEN, 1);
    await api.deleteCapacitasCredential(TOKEN, 0);
    await exerciseFetchErrors(() => api.deleteCapacitasCredential(TOKEN, 1));
  });
  test("testCapacitasCredential: populated and empty optional values", async () => {
    await api.testCapacitasCredential(TOKEN, 1);
    await api.testCapacitasCredential(TOKEN, 0);
  });
  test("listBonificaOristaneseCredentials: populated and empty optional values", async () => {
    await api.listBonificaOristaneseCredentials(TOKEN);
  });
  test("createBonificaOristaneseCredential: populated and empty optional values", async () => {
    await api.createBonificaOristaneseCredential(TOKEN, {});
    await api.createBonificaOristaneseCredential(TOKEN, FULL_OPTIONS);
  });
  test("updateBonificaOristaneseCredential: populated and empty optional values", async () => {
    await api.updateBonificaOristaneseCredential(TOKEN, 1, {});
    await api.updateBonificaOristaneseCredential(TOKEN, 0, FULL_OPTIONS);
  });
  test("deleteBonificaOristaneseCredential: populated and empty optional values", async () => {
    await api.deleteBonificaOristaneseCredential(TOKEN, 1);
    await api.deleteBonificaOristaneseCredential(TOKEN, 0);
    await exerciseFetchErrors(() => api.deleteBonificaOristaneseCredential(TOKEN, 1));
  });
  test("testBonificaOristaneseCredential: populated and empty optional values", async () => {
    await api.testBonificaOristaneseCredential(TOKEN, 1);
    await api.testBonificaOristaneseCredential(TOKEN, 0);
  });
  test("listPostaOnlineCredentials: populated and empty optional values", async () => {
    await api.listPostaOnlineCredentials(TOKEN);
  });
  test("createPostaOnlineCredential: populated and empty optional values", async () => {
    await api.createPostaOnlineCredential(TOKEN, {});
    await api.createPostaOnlineCredential(TOKEN, FULL_OPTIONS);
  });
  test("updatePostaOnlineCredential: populated and empty optional values", async () => {
    await api.updatePostaOnlineCredential(TOKEN, 1, {});
    await api.updatePostaOnlineCredential(TOKEN, 0, FULL_OPTIONS);
  });
  test("deletePostaOnlineCredential: populated and empty optional values", async () => {
    await api.deletePostaOnlineCredential(TOKEN, 1);
    await api.deletePostaOnlineCredential(TOKEN, 0);
  });
  test("testPostaOnlineCredential: populated and empty optional values", async () => {
    await api.testPostaOnlineCredential(TOKEN, 1, {});
    await api.testPostaOnlineCredential(TOKEN, 0);
  });
  test("listPostaOnlineRegisteredMailJobs: populated and empty optional values", async () => {
    await api.listPostaOnlineRegisteredMailJobs(TOKEN);
  });
  test("createPostaOnlineRegisteredMailJob: populated and empty optional values", async () => {
    await api.createPostaOnlineRegisteredMailJob(TOKEN, {});
    await api.createPostaOnlineRegisteredMailJob(TOKEN, FULL_OPTIONS);
  });
  test("rerunPostaOnlineRegisteredMailJob: populated and empty optional values", async () => {
    await api.rerunPostaOnlineRegisteredMailJob(TOKEN, 1);
    await api.rerunPostaOnlineRegisteredMailJob(TOKEN, 0);
  });
  test("deletePostaOnlineRegisteredMailJob: populated and empty optional values", async () => {
    await api.deletePostaOnlineRegisteredMailJob(TOKEN, 1);
    await api.deletePostaOnlineRegisteredMailJob(TOKEN, 0);
  });
  test("getBonificaSyncStatus: populated and empty optional values", async () => {
    await api.getBonificaSyncStatus(TOKEN);
  });
  test("runBonificaSync: populated and empty optional values", async () => {
    await api.runBonificaSync(TOKEN, {});
    await api.runBonificaSync(TOKEN, FULL_OPTIONS);
  });
  test("deleteBonificaSyncJob: populated and empty optional values", async () => {
    await api.deleteBonificaSyncJob(TOKEN, "value");
    await api.deleteBonificaSyncJob(TOKEN, "");
  });
  test("getUtenzeBonificaStaging: populated and empty optional values", async () => {
    await api.getUtenzeBonificaStaging(TOKEN, FULL_OPTIONS);
    await api.getUtenzeBonificaStaging(TOKEN);
  });
  test("getUtenzeBonificaStagingItem: populated and empty optional values", async () => {
    await api.getUtenzeBonificaStagingItem(TOKEN, "value");
    await api.getUtenzeBonificaStagingItem(TOKEN, "");
  });
  test("approveUtenzeBonificaStagingItem: populated and empty optional values", async () => {
    await api.approveUtenzeBonificaStagingItem(TOKEN, "value");
    await api.approveUtenzeBonificaStagingItem(TOKEN, "");
  });
  test("rejectUtenzeBonificaStagingItem: populated and empty optional values", async () => {
    await api.rejectUtenzeBonificaStagingItem(TOKEN, "value");
    await api.rejectUtenzeBonificaStagingItem(TOKEN, "");
  });
  test("bulkApproveUtenzeBonificaStaging: populated and empty optional values", async () => {
    await api.bulkApproveUtenzeBonificaStaging(TOKEN, ["value"]);
    await api.bulkApproveUtenzeBonificaStaging(TOKEN, []);
  });
  test("searchCapacitasInvolture: populated and empty optional values", async () => {
    await api.searchCapacitasInvolture(TOKEN, {});
    await api.searchCapacitasInvolture(TOKEN, FULL_OPTIONS);
  });
  test("importCapacitasAnagraficaHistory: populated and empty optional values", async () => {
    await api.importCapacitasAnagraficaHistory(TOKEN, {});
    await api.importCapacitasAnagraficaHistory(TOKEN, FULL_OPTIONS);
  });
  test("createCapacitasAnagraficaHistoryJob: populated and empty optional values", async () => {
    await api.createCapacitasAnagraficaHistoryJob(TOKEN, {});
    await api.createCapacitasAnagraficaHistoryJob(TOKEN, FULL_OPTIONS);
  });
  test("listCapacitasAnagraficaHistoryJobs: populated and empty optional values", async () => {
    await api.listCapacitasAnagraficaHistoryJobs(TOKEN);
  });
  test("createCapacitasDomandeIrrigueSyncJob: populated and empty optional values", async () => {
    await api.createCapacitasDomandeIrrigueSyncJob(TOKEN, {});
    await api.createCapacitasDomandeIrrigueSyncJob(TOKEN, FULL_OPTIONS);
  });
  test("listCapacitasDomandeIrrigueSyncJobs: populated and empty optional values", async () => {
    await api.listCapacitasDomandeIrrigueSyncJobs(TOKEN);
  });
  test("rerunCapacitasDomandeIrrigueSyncJob: populated and empty optional values", async () => {
    await api.rerunCapacitasDomandeIrrigueSyncJob(TOKEN, 1);
    await api.rerunCapacitasDomandeIrrigueSyncJob(TOKEN, 0);
  });
  test("deleteCapacitasDomandeIrrigueSyncJob: populated and empty optional values", async () => {
    await api.deleteCapacitasDomandeIrrigueSyncJob(TOKEN, 1);
    await api.deleteCapacitasDomandeIrrigueSyncJob(TOKEN, 0);
  });
  test("createCapacitasInCassSyncJob: populated and empty optional values", async () => {
    await api.createCapacitasInCassSyncJob(TOKEN, {});
    await api.createCapacitasInCassSyncJob(TOKEN, FULL_OPTIONS);
  });
  test("createCapacitasInCassRuoloHarvest: populated and empty optional values", async () => {
    await api.createCapacitasInCassRuoloHarvest(TOKEN, {});
    await api.createCapacitasInCassRuoloHarvest(TOKEN, FULL_OPTIONS);
  });
  test("listCapacitasInCassSyncJobs: populated and empty optional values", async () => {
    await api.listCapacitasInCassSyncJobs(TOKEN, FULL_OPTIONS);
    await api.listCapacitasInCassSyncJobs(TOKEN);
  });
  test("rerunCapacitasInCassSyncJob: populated and empty optional values", async () => {
    await api.rerunCapacitasInCassSyncJob(TOKEN, 1);
    await api.rerunCapacitasInCassSyncJob(TOKEN, 0);
  });
  test("deleteCapacitasInCassSyncJob: populated and empty optional values", async () => {
    await api.deleteCapacitasInCassSyncJob(TOKEN, 1);
    await api.deleteCapacitasInCassSyncJob(TOKEN, 0);
  });
  test("rerunCapacitasAnagraficaHistoryJob: populated and empty optional values", async () => {
    await api.rerunCapacitasAnagraficaHistoryJob(TOKEN, 1);
    await api.rerunCapacitasAnagraficaHistoryJob(TOKEN, 0);
  });
  test("deleteCapacitasAnagraficaHistoryJob: populated and empty optional values", async () => {
    await api.deleteCapacitasAnagraficaHistoryJob(TOKEN, 1);
    await api.deleteCapacitasAnagraficaHistoryJob(TOKEN, 0);
    await exerciseFetchErrors(() => api.deleteCapacitasAnagraficaHistoryJob(TOKEN, 1));
  });
  test("importCapacitasAnagraficaHistoryFile: populated and empty optional values", async () => {
    await api.importCapacitasAnagraficaHistoryFile(TOKEN, new File(['x'], 'file.csv'), FULL_OPTIONS);
    await api.importCapacitasAnagraficaHistoryFile(TOKEN, new File([''], 'empty.csv'));
    await api.importCapacitasAnagraficaHistoryFile(TOKEN, new File(['x'], 'file.csv'), FALSE_OPTIONS);
  });
  test("searchCapacitasFrazioni: populated and empty optional values", async () => {
    await api.searchCapacitasFrazioni(TOKEN, "value", 1);
    await api.searchCapacitasFrazioni(TOKEN, "");
  });
  test("getCapacitasSezioni: populated and empty optional values", async () => {
    await api.getCapacitasSezioni(TOKEN, "value", 1);
    await api.getCapacitasSezioni(TOKEN, "");
  });
  test("getCapacitasFogli: populated and empty optional values", async () => {
    await api.getCapacitasFogli(TOKEN, "value", "value", 1);
    await api.getCapacitasFogli(TOKEN, "");
  });
  test("searchCapacitasTerreni: populated and empty optional values", async () => {
    await api.searchCapacitasTerreni(TOKEN, {});
    await api.searchCapacitasTerreni(TOKEN, FULL_OPTIONS);
  });
  test("createCapacitasTerreniJob: populated and empty optional values", async () => {
    await api.createCapacitasTerreniJob(TOKEN, {});
    await api.createCapacitasTerreniJob(TOKEN, FULL_OPTIONS);
  });
  test("listCapacitasTerreniJobs: populated and empty optional values", async () => {
    await api.listCapacitasTerreniJobs(TOKEN);
  });
  test("rerunCapacitasTerreniJob: populated and empty optional values", async () => {
    await api.rerunCapacitasTerreniJob(TOKEN, 1);
    await api.rerunCapacitasTerreniJob(TOKEN, 0);
  });
  test("deleteCapacitasTerreniJob: populated and empty optional values", async () => {
    await api.deleteCapacitasTerreniJob(TOKEN, 1);
    await api.deleteCapacitasTerreniJob(TOKEN, 0);
  });
  test("createCapacitasParticelleSyncJob: populated and empty optional values", async () => {
    await api.createCapacitasParticelleSyncJob(TOKEN, {});
    await api.createCapacitasParticelleSyncJob(TOKEN, FULL_OPTIONS);
  });
  test("listCapacitasParticelleSyncJobs: populated and empty optional values", async () => {
    await api.listCapacitasParticelleSyncJobs(TOKEN);
  });
  test("rerunCapacitasParticelleSyncJob: populated and empty optional values", async () => {
    await api.rerunCapacitasParticelleSyncJob(TOKEN, 1);
    await api.rerunCapacitasParticelleSyncJob(TOKEN, 0);
  });
  test("deleteCapacitasParticelleSyncJob: populated and empty optional values", async () => {
    await api.deleteCapacitasParticelleSyncJob(TOKEN, 1);
    await api.deleteCapacitasParticelleSyncJob(TOKEN, 0);
  });
  test("stopCapacitasParticelleSyncJob: populated and empty optional values", async () => {
    await api.stopCapacitasParticelleSyncJob(TOKEN, 1);
    await api.stopCapacitasParticelleSyncJob(TOKEN, 0);
  });
  test("patchCapacitasParticelleSyncJobSpeed: populated and empty optional values", async () => {
    await api.patchCapacitasParticelleSyncJobSpeed(TOKEN, 1, true);
    await api.patchCapacitasParticelleSyncJobSpeed(TOKEN, 0, false);
  });
  test("refetchCapacitasCertificatiEmpty: populated and empty optional values", async () => {
    await api.refetchCapacitasCertificatiEmpty(TOKEN, {});
    await api.refetchCapacitasCertificatiEmpty(TOKEN, FULL_OPTIONS);
  });
  test("listCapacitasParticelleAnomalie: populated and empty optional values", async () => {
    await api.listCapacitasParticelleAnomalie(TOKEN, FULL_OPTIONS);
    await api.listCapacitasParticelleAnomalie(TOKEN);
    await api.listCapacitasParticelleAnomalie(TOKEN, FALSE_OPTIONS);
  });
  test("resolveCapacitasParticellaFrazione: populated and empty optional values", async () => {
    await api.resolveCapacitasParticellaFrazione(TOKEN, "value", {});
    await api.resolveCapacitasParticellaFrazione(TOKEN, "", FULL_OPTIONS);
  });
  test("getCatastoComuni: populated and empty optional values", async () => {
    await api.getCatastoComuni(TOKEN, "value");
    await api.getCatastoComuni(TOKEN);
  });
  test("createElaborazioneBatch: populated and empty optional values", async () => {
    await api.createElaborazioneBatch(TOKEN, new File(['x'], 'file.csv'), "value", ["value"]);
    await api.createElaborazioneBatch(TOKEN, new File([''], 'empty.csv'));
  });
  test("getElaborazioneBatches: populated and empty optional values", async () => {
    await api.getElaborazioneBatches(TOKEN, "value");
    await api.getElaborazioneBatches(TOKEN);
  });
  test("getElaborazioneBatch: populated and empty optional values", async () => {
    await api.getElaborazioneBatch(TOKEN, "value", FULL_OPTIONS);
    await api.getElaborazioneBatch(TOKEN, "");
    await api.getElaborazioneBatch(TOKEN, "value", FALSE_OPTIONS);
  });
  test("startElaborazioneBatch: populated and empty optional values", async () => {
    await api.startElaborazioneBatch(TOKEN, "value");
    await api.startElaborazioneBatch(TOKEN, "");
  });
  test("cancelElaborazioneBatch: populated and empty optional values", async () => {
    await api.cancelElaborazioneBatch(TOKEN, "value");
    await api.cancelElaborazioneBatch(TOKEN, "");
  });
  test("retryFailedElaborazioneBatch: populated and empty optional values", async () => {
    await api.retryFailedElaborazioneBatch(TOKEN, "value");
    await api.retryFailedElaborazioneBatch(TOKEN, "");
  });
  test("createElaborazioneRichiesta: populated and empty optional values", async () => {
    await api.createElaborazioneRichiesta(TOKEN, {});
    await api.createElaborazioneRichiesta(TOKEN, FULL_OPTIONS);
  });
  test("getPendingElaborazioneCaptcha: populated and empty optional values", async () => {
    await api.getPendingElaborazioneCaptcha(TOKEN);
  });
  test("getElaborazioneCaptchaSummary: populated and empty optional values", async () => {
    await api.getElaborazioneCaptchaSummary(TOKEN);
  });
  test("getElaborazioneAnprSummary: populated and empty optional values", async () => {
    await api.getElaborazioneAnprSummary(TOKEN);
  });
  test("getElaborazioneRuntimeMetrics: populated and empty optional values", async () => {
    await api.getElaborazioneRuntimeMetrics(TOKEN);
  });
  test("getElaborazioneAutoJobControls: populated and empty optional values", async () => {
    await api.getElaborazioneAutoJobControls(TOKEN);
  });
  test("updateElaborazioneAutoJobControl: populated and empty optional values", async () => {
    await api.updateElaborazioneAutoJobControl(TOKEN, "value", true);
    await api.updateElaborazioneAutoJobControl(TOKEN, "", false);
  });
  test("getElaborazioneRuoloAutoSyncStatus: populated and empty optional values", async () => {
    await api.getElaborazioneRuoloAutoSyncStatus(TOKEN);
  });
  test("getElaborazioneRuoloAutoSyncConfig: populated and empty optional values", async () => {
    await api.getElaborazioneRuoloAutoSyncConfig(TOKEN);
  });
  test("updateElaborazioneRuoloAutoSyncConfig: populated and empty optional values", async () => {
    await api.updateElaborazioneRuoloAutoSyncConfig(TOKEN, {});
    await api.updateElaborazioneRuoloAutoSyncConfig(TOKEN, FULL_OPTIONS);
  });
  test("refreshElaborazioneRuoloAutoSyncSource: populated and empty optional values", async () => {
    await api.refreshElaborazioneRuoloAutoSyncSource(TOKEN);
  });
  test("runElaborazioneRuoloAutoSyncNow: populated and empty optional values", async () => {
    await api.runElaborazioneRuoloAutoSyncNow(TOKEN);
  });
  test("getGateMobileSyncStatus: populated and empty optional values", async () => {
    await api.getGateMobileSyncStatus(TOKEN);
  });
  test("triggerGateMobileSyncRun: populated and empty optional values", async () => {
    await api.triggerGateMobileSyncRun(TOKEN);
  });
  test("solveElaborazioneCaptcha: populated and empty optional values", async () => {
    await api.solveElaborazioneCaptcha(TOKEN, "value", "value");
    await api.solveElaborazioneCaptcha(TOKEN, "", "");
  });
  test("skipElaborazioneCaptcha: populated and empty optional values", async () => {
    await api.skipElaborazioneCaptcha(TOKEN, "value");
    await api.skipElaborazioneCaptcha(TOKEN, "");
  });
  test("getCatastoDocuments: populated and empty optional values", async () => {
    await api.getCatastoDocuments(TOKEN, STRING_FILTERS);
    await api.getCatastoDocuments(TOKEN);
  });
  test("searchCatastoDocuments: populated and empty optional values", async () => {
    await api.searchCatastoDocuments(TOKEN, STRING_FILTERS);
    await api.searchCatastoDocuments(TOKEN);
  });
  test("getCatastoDocument: populated and empty optional values", async () => {
    await api.getCatastoDocument(TOKEN, "value");
    await api.getCatastoDocument(TOKEN, "");
  });
  test("fetchElaborazioneCaptchaImageBlob: populated and empty optional values", async () => {
    await api.fetchElaborazioneCaptchaImageBlob(TOKEN, "value");
    await api.fetchElaborazioneCaptchaImageBlob(TOKEN, "");
  });
  test("downloadCatastoDocumentBlob: populated and empty optional values", async () => {
    await api.downloadCatastoDocumentBlob(TOKEN, "value");
    await api.downloadCatastoDocumentBlob(TOKEN, "");
  });
  test("downloadElaborazioneBatchZipBlob: populated and empty optional values", async () => {
    await api.downloadElaborazioneBatchZipBlob(TOKEN, "value");
    await api.downloadElaborazioneBatchZipBlob(TOKEN, "");
  });
  test("downloadElaborazioneBatchReportJsonBlob: populated and empty optional values", async () => {
    await api.downloadElaborazioneBatchReportJsonBlob(TOKEN, "value");
    await api.downloadElaborazioneBatchReportJsonBlob(TOKEN, "");
  });
  test("downloadElaborazioneBatchReportMarkdownBlob: populated and empty optional values", async () => {
    await api.downloadElaborazioneBatchReportMarkdownBlob(TOKEN, "value");
    await api.downloadElaborazioneBatchReportMarkdownBlob(TOKEN, "");
  });
  test("downloadElaborazioneRequestArtifactsBlob: populated and empty optional values", async () => {
    await api.downloadElaborazioneRequestArtifactsBlob(TOKEN, "value");
    await api.downloadElaborazioneRequestArtifactsBlob(TOKEN, "");
  });
  test("fetchElaborazioneRequestArtifactPreviewBlob: populated and empty optional values", async () => {
    await api.fetchElaborazioneRequestArtifactPreviewBlob(TOKEN, "value");
    await api.fetchElaborazioneRequestArtifactPreviewBlob(TOKEN, "");
  });
  test("downloadSelectedCatastoDocumentsZipBlob: populated and empty optional values", async () => {
    await api.downloadSelectedCatastoDocumentsZipBlob(TOKEN, ["value"]);
    await api.downloadSelectedCatastoDocumentsZipBlob(TOKEN, []);
  });
});
